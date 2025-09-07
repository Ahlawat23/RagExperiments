from __future__ import annotations

from typing import List, Dict, Any, Optional
from pathlib import Path
import os
import re
import numpy as np
from dotenv import load_dotenv

from qdrant_client import QdrantClient, models
from qdrant_client.models import Distance, VectorParams, PointStruct
from qdrant_client.conversions.common_types import Filter
from uuid import uuid5, NAMESPACE_URL

load_dotenv(override=True)


class QdrantHandler:
    def __init__(self, embed_fn=None) -> None:
        """
        embed_fn: optional callable that takes List[str] and returns np.ndarray (N, D).
                  Required for search(query_text=...) unless you pass query_vector directly.
        """
        # Load config from .env
        self.qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY") or None
        self.collection = os.getenv("QDRANT_COLLECTION", "pdf_pages")
        self.vector_size = int(os.getenv("QDRANT_VECTOR_SIZE", "768"))
        # Accept COSINE / EUCLID / DOT
        self.distance_name = os.getenv("QDRANT_DISTANCE", "COSINE").upper()
        self.distance_enum = getattr(Distance, self.distance_name, Distance.COSINE)

        # Optional embedder (SentenceTransformer/OpenAI/etc.)
        self.embed_fn = embed_fn

        # Connect
        self.client = QdrantClient(url=self.qdrant_url, api_key=self.qdrant_api_key)
        self._ensure_collection()

    # ---------------------------
    # Collection setup
    # ---------------------------
    def _ensure_collection(self) -> None:
        """Create (or re-create) the collection if it does not exist."""
        try:
            self.client.get_collection(self.collection)
        except Exception:
            self.client.recreate_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=self.vector_size, distance=self.distance_enum),
            )

    def create_common_payload_indexes(self) -> None:
        """Optional: build indexes for faster filtering/text search."""
        fields_kw = ["city", "country", "seniority", "file_name", "normalized_keywords"]
        for f in fields_kw:
            try:
                self.client.create_payload_index(
                    collection_name=self.collection,
                    field_name=f,
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )
            except Exception:
                pass

        # numeric yoe
        try:
            self.client.create_payload_index(
                collection_name=self.collection,
                field_name="yoe",
                field_schema=models.PayloadSchemaType.INTEGER,
            )
        except Exception:
            pass

        # full-text examples (only if you plan to query via MatchText)
        for f in ["roles.title", "education.institution", "certs", "current_title"]:
            try:
                self.client.create_payload_index(
                    collection_name=self.collection,
                    field_name=f,
                    field_schema=models.PayloadSchemaType.TEXT,
                )
            except Exception:
                pass

    # ---------------------------
    # Deterministic point id
    # ---------------------------
    def _stable_pid(self, meta: Dict[str, Any]) -> str:
        """
        Build a deterministic UUIDv5 from stable fields, so re-upserts overwrite (not duplicate).
        """
        basis = (
            f"{meta.get('document_id','')}::"
            f"{meta.get('file_name','')}::"
            f"p{meta.get('page_no','?')}::"
            f"c{meta.get('chunk_index','?')}"
        )
        return str(uuid5(NAMESPACE_URL, basis))

    # ---------------------------
    # Upsert
    # ---------------------------
    def upsert_items(
        self,
        items: List[Dict[str, Any]],
        embed_fn=None,                    # callable: List[str] -> np.ndarray (N, D)
        batch_size: int = 128,
        wait: bool = True,
    ) -> int:
        """
        items: [{"text": str, "metadata": dict}, ...]
        embed_fn: if None, uses self.embed_fn
        """
        total = 0
        if embed_fn is None:
            if self.embed_fn is None:
                raise ValueError("embed_fn is required (pass as arg or set on class).")
            embed_fn = self.embed_fn

        def _batches(seq: List[Dict[str, Any]], n: int):
            for i in range(0, len(seq), n):
                yield seq[i : i + n]

        for batch in _batches(items, batch_size):
            texts = [it["text"] for it in batch]
            vecs: np.ndarray = embed_fn(texts)  # (B, D)
            if not isinstance(vecs, np.ndarray):
                vecs = np.asarray(vecs, dtype=np.float32)
            if vecs.dtype != np.float32:
                vecs = vecs.astype(np.float32)

            points: List[PointStruct] = []
            for it, vec in zip(batch, vecs):
                meta = it.get("metadata", {}) or {}
                pid = self._stable_pid(meta)
                payload = dict(meta)
                payload["pid_human"] = (
                    f"{meta.get('file_name','file')}::p{meta.get('page_no','?')}::c{meta.get('chunk_index','?')}"
                )
                payload["text"] = it["text"]

                points.append(
                    PointStruct(
                        id=pid,
                        vector=vec.tolist(),
                        payload=payload,
                    )
                )

            if points:
                self.client.upsert(collection_name=self.collection, points=points, wait=wait)
                total += len(points)

        return total

    # ---------------------------
    # Filter utilities
    # ---------------------------
    @staticmethod
    def build_qdrant_filter(schema_filters: Dict[str, Any]) -> Optional[Filter]:
        """
        Convert a dict of filters to a Qdrant Filter.

        Operators per field:
          - eq: exact value (MatchValue)
          - in: list of values (MatchAny)
          - any: list -> payload array must contain any of them
          - all: list -> payload array must contain all of them
          - gte/lte/gt/lt: numeric range (Range)
          - text: full-text search on a string field (MatchText). Requires an index.

        Accepts optional boolean buckets: must / should / must_not (list of {key, <ops...>}).
        """
        if not schema_filters:
            return None

        def to_condition(key: str, spec: Dict[str, Any]) -> List[models.FieldCondition]:
            conds: List[models.FieldCondition] = []
            if "eq" in spec:
                conds.append(models.FieldCondition(key=key, match=models.MatchValue(value=spec["eq"])))
            if "in" in spec:
                conds.append(models.FieldCondition(key=key, match=models.MatchAny(any=spec["in"])))
            if "any" in spec:
                conds.append(models.FieldCondition(key=key, match=models.MatchAny(any=spec["any"])))
            if "all" in spec:
                conds.append(models.FieldCondition(key=key, match=models.MatchAll(all=spec["all"])))
            rng = {k: spec[k] for k in ("gte", "lte", "gt", "lt") if k in spec}
            if rng:
                conds.append(models.FieldCondition(key=key, range=models.Range(**rng)))
            if "text" in spec and spec["text"]:
                conds.append(models.FieldCondition(key=key, match=models.MatchText(text=spec["text"])))
            return conds

        must: List[models.Condition] = []
        should: List[models.Condition] = []
        must_not: List[models.Condition] = []

        # explicit boolean buckets (optional)
        for bucket, target in (("must", must), ("should", should), ("must_not", must_not)):
            if bucket in schema_filters:
                for it in schema_filters[bucket] or []:
                    k = it.get("key")
                    spec = {kk: vv for kk, vv in it.items() if kk != "key"}
                    target.extend(to_condition(k, spec))

        # top-level specs
        for key, spec in schema_filters.items():
            if key in ("must", "should", "must_not"):
                continue
            must.extend(to_condition(key, spec))

        if must or should or must_not:
            return models.Filter(must=must or None, should=should or None, must_not=must_not or None)
        return None

    # ---------------------------
    # NL → schema filters
    # ---------------------------
    SENIORITY_WORDS = [
        "intern",
        "junior",
        "jr",
        "associate",
        "mid",
        "senior",
        "sr",
        "lead",
        "principal",
        "staff",
        "manager",
        "head",
        "director",
        "vp",
        "chief",
        "cto",
        "cpo",
        "coo",
        "ceo",
    ]
    YOE_PAT = re.compile(r"(?P<num>\d{1,2})\s*\+?\s*(?:years|yrs|yoe)\b", re.I)
    CITY_COUNTRY_PAT = re.compile(r"\b(?:in|from|at)\s+(?P<place>[A-Za-z .'-]+)\b", re.I)
    FILE_PAT = re.compile(r"\bfile\s*:\s*(?P<fname>[\w.\- ]+\.pdf)\b", re.I)

    @classmethod
    def parse_nl_filters(cls, query_text: str) -> Dict[str, Any]:
        """
        Extract simple filters from NL query (yoe, seniority, location, file_name, skills).
        This is intentionally light; extend as your patterns evolve.
        """
        filt: Dict[str, Any] = {}
        qt = query_text or ""

        # yoe
        m = cls.YOE_PAT.search(qt)
        if m:
            years = int(m.group("num"))
            filt["yoe"] = {"gte": years}

        # seniority
        for w in cls.SENIORITY_WORDS:
            if re.search(rf"\b{re.escape(w)}\b", qt, re.I):
                norm = {"jr": "junior", "sr": "senior"}.get(w.lower(), w.lower())
                filt["seniority"] = {"eq": norm}
                break

        # location (simple “in Dublin” / “in Dublin, Ireland”)
        m = cls.CITY_COUNTRY_PAT.search(qt)
        if m:
            place = m.group("place").strip()
            if "," in place:
                city, country = [p.strip() for p in place.split(",", 1)]
                if city:
                    filt["city"] = {"eq": city}
                if country:
                    filt["country"] = {"eq": country}
            else:
                filt["should"] = [{"key": "city", "eq": place}, {"key": "country", "eq": place}]

        # file scoping: "file: Andrew_Cole.pdf"
        m = cls.FILE_PAT.search(qt)
        if m:
            filt["file_name"] = {"eq": m.group("fname").strip()}

        # skills/tools/clouds/langs extraction (very light)
        skills = []
        for kw in ["with", "having", "skills", "skill", "expert in", "using"]:
            pat = re.compile(rf"{kw}\s+([A-Za-z0-9+/#., &\-]+)", re.I)
            mm = pat.search(qt)
            if mm:
                chunk = mm.group(1)
                chunk = re.split(r"\b(?:for|in|of|and then|who|that|where)\b", chunk, 1, flags=re.I)[0]
                skills.extend([s.strip(" ,.&") for s in re.split(r",|/| and ", chunk) if s.strip()])
        if skills:
            filt["normalized_keywords"] = {"any": [s.lower() for s in skills]}

        return filt

    # ---------------------------
    # Enhanced search
    # ---------------------------
    def search( self, query_vector: np.ndarray, top_k: int = 3, file_filter: Optional[str] = None, ):
        """Search Qdrant by vector, optional filter by file path"""
  
        
        result = self.client.search(
            collection_name=self.collection,
            query_vector=query_vector.tolist(),
            with_payload=True,
            with_vectors=False,
        )
        return result


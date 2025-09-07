from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field
import re
import hashlib
from datetime import datetime
import fitz  # PyMuPDF


# ----------------------------
# Utilities
# ----------------------------

ISO_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"(?:(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{4,})(?:x\d+)?")
URL_RE = re.compile(r"\bhttps?://\S+\b", re.I)
LINKEDIN_RE = re.compile(r"(https?://(www\.)?linkedin\.com/[^\s]+)", re.I)
CITY_COUNTRY_RE = re.compile(r"\b([A-Za-z .'-]+),\s*([A-Za-z .'-]+)\b")

CLOUD_KEYWORDS = {"aws", "amazon web services", "azure", "gcp", "google cloud", "google cloud platform"}
TOOL_HINTS = {"figma", "photoshop", "illustrator", "autocad", "solidworks", "blender", "sketch", "jira", "confluence"}
SENIORITY_KEYWORDS = {
    "intern": "intern",
    "junior": "junior",
    "jr": "junior",
    "associate": "associate",
    "mid": "mid",
    "senior": "senior",
    "sr": "senior",
    "lead": "lead",
    "principal": "principal",
    "staff": "staff",
    "manager": "manager",
    "head": "head",
    "director": "director",
    "vp": "vp",
    "chief": "c-level",
    "cto": "c-level",
    "cpo": "c-level",
    "coo": "c-level",
    "ceo": "c-level",
}


def sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="ignore")).hexdigest()


def safe_strip(s: Optional[str]) -> Optional[str]:
    return s.strip() if isinstance(s, str) else s


def parse_iso_date(s: str) -> Optional[datetime]:
    m = ISO_DATE.search(s)
    if not m:
        return None
    y, mo, d = map(int, m.groups())
    try:
        return datetime(y, mo, d)
    except ValueError:
        return None


def diff_years(d1: datetime, d2: datetime) -> float:
    # Approximate year difference
    return (d2 - d1).days / 365.25


# ----------------------------
# Data containers (optional)
# ----------------------------

@dataclass
class Role:
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    start: Optional[str] = None   # keep original ISO or parsable string
    end: Optional[str] = None
    bullets: List[str] = field(default_factory=list)


@dataclass
class EducationItem:
    institution: str
    degree: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    details: Optional[str] = None


# ----------------------------
# The PdfHandler
# ----------------------------

class PdfHandler:
    """
    Reads a resume PDF, extracts a structured candidate profile,
    and returns chunk+metadata pairs ready for embedding/Qdrant.
    """

    def __init__(self, chunk_size: int = 900, chunk_overlap: int = 150):
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    # === Public API ===
    def readPDF(self, pdf_path: str | Path) -> List[Dict[str, Any]]:
        pdf_path = Path(pdf_path).expanduser().resolve()

        # 1) Read pages
        pages = self._read_pages(pdf_path)
        full_text = "\n".join(t for _, t in pages)

        # 2) Extract document-level profile
        profile = self._extract_profile(full_text)

        # 3) Chunk per page with document-level metadata merged in
        document_id = self._build_document_id(pdf_path)
        results: List[Dict[str, Any]] = []
        for page_no, page_text in pages:
            for idx, (chunk_text, cstart, cend) in enumerate(
                self._chunk_text(page_text, self.chunk_size, self.chunk_overlap), start=1
            ):
                meta = {
                    # === candidate profile ===
                    "full_name": profile["full_name"],
                    "email": profile["email"],
                    "phone": profile["phone"],
                    "city": profile["city"],
                    "country": profile["country"],
                    "yoe": profile["yoe"],
                    "current_title": profile["current_title"],
                    "seniority": profile["seniority"],
                    "work_auth": profile["work_auth"],
                    "remote_pref": profile["remote_pref"],
                    "notice": profile["notice"],
                    "salary": profile["salary"],
                    "linkedin_url": profile["linkedin_url"],
                    "portfolio_url": profile["portfolio_url"],
                    "langs": profile["langs"],
                    "skills_primary": profile["skills_primary"],
                    "skills_secondary": profile["skills_secondary"],
                    "tools": profile["tools"],
                    "domains": profile["domains"],
                    "industries": profile["industries"],
                    "clouds": profile["clouds"],
                    "roles": profile["roles"],
                    "education": profile["education"],
                    "certs": profile["certs"],
                    "normalized_keywords": profile["normalized_keywords"],
                    "skillset_hash": profile["skillset_hash"],

                    # === chunk tracking ===
                    "document_id": document_id,
                    "file": str(pdf_path),
                    "file_name": pdf_path.name,
                    "page_no": page_no,
                    "chunk_index": idx,
                    "char_start": cstart,
                    "char_end": cend,
                }
                results.append({"text": chunk_text, "metadata": meta})

        return results

    # === Internals ===

    def _read_pages(self, pdf_path: Path) -> List[Tuple[int, str]]:
        out: List[Tuple[int, str]] = []
        with fitz.open(str(pdf_path)) as doc:
            for i, page in enumerate(doc, start=1):
                text = page.get_text("text") or ""
                text = text.replace("\x00", "").strip()
                out.append((i, text))
        return out

    def _build_document_id(self, pdf_path: Path) -> str:
        return hashlib.sha256(pdf_path.read_bytes()).hexdigest()

    def _chunk_text(self, text: str, chunk_size: int, overlap: int) -> List[Tuple[str, int, int]]:
        text = text.strip()
        n = len(text)
        if n == 0:
            return []
        chunks: List[Tuple[str, int, int]] = []
        start = 0
        while start < n:
            end = min(start + chunk_size, n)
            chunk = text[start:end].strip()
            if chunk:
                chunks.append((chunk, start, end))
            if end == n:
                break
            start = max(end - overlap, 0)
        return chunks

    # --- Profile extraction ---

    def _extract_profile(self, full_text: str) -> Dict[str, Any]:
        lines = [l.strip() for l in full_text.splitlines() if l.strip()]

        email = self._extract_email(full_text)
        phone = self._extract_phone(full_text)
        linkedin, portfolio = self._extract_links(full_text)

        # Try to guess header lines (name/title/city,country often near top)
        header_blk = "\n".join(lines[:8])
        full_name = self._guess_name(header_blk)
        current_title = self._guess_current_title(header_blk)
        city, country = self._guess_city_country(header_blk)

        # Sections
        work_section = self._extract_section(lines, ["work experience", "experience"])
        edu_section = self._extract_section(lines, ["education"])
        skills_section = self._extract_section(lines, ["skills"])
        certs_section = self._extract_section(lines, ["certifications", "certification"])
        langs_section = self._extract_section(lines, ["languages", "language"])

        roles = self._parse_roles(work_section)
        education = self._parse_education(edu_section)
        certs = self._parse_certs(certs_section)
        langs = self._parse_list_items(langs_section)

        # Skills + tools + clouds + domains/industries (basic heuristics)
        skills_primary, skills_secondary, tools, clouds, domains, industries = self._parse_skills_and_more(
            skills_section, full_text
        )

        # Seniority inference from title
        seniority = self._infer_seniority(current_title)

        # Years of experience (yoe) from role dates
        yoe = self._compute_yoe(roles)

        # Normalized keywords
        normalized_keywords = self._normalized_keywords(
            skills_primary, skills_secondary, tools, clouds, langs, domains, industries
        )
        skillset_hash = sha256_str("|".join(sorted(normalized_keywords))) if normalized_keywords else None

        profile = {
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "city": city,
            "country": country,
            "yoe": int(round(yoe)) if yoe is not None else 0,
            "current_title": current_title,
            "seniority": seniority,
            "work_auth": None,     # fill via form/LLM if needed
            "remote_pref": None,   # fill via form/LLM if needed
            "notice": None,
            "salary": None,
            "linkedin_url": linkedin,
            "portfolio_url": portfolio,
            "langs": langs or None,
            "skills_primary": skills_primary or None,
            "skills_secondary": skills_secondary or None,
            "tools": tools or None,
            "domains": domains or None,
            "industries": industries or None,
            "clouds": clouds or None,
            "roles": [r.__dict__ for r in roles] or None,
            "education": [e.__dict__ for e in education] or None,
            "certs": certs or None,
            "normalized_keywords": sorted(normalized_keywords) or None,
            "skillset_hash": skillset_hash,
        }
        return profile

    # --- Primitive extractors ---

    def _extract_email(self, text: str) -> Optional[str]:
        m = EMAIL_RE.search(text)
        return m.group(0) if m else None

    def _extract_phone(self, text: str) -> Optional[str]:
        # Pick the first phone-like string that isn't likely an ID
        candidates = PHONE_RE.findall(text)
        for c in candidates:
            s = c.strip()
            # Keep reasonable lengths (7-18 chars)
            if 7 <= len(re.sub(r"\D", "", s)) <= 18:
                return s
        return None

    def _extract_links(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        linkedin = None
        m = LINKEDIN_RE.search(text)
        if m:
            linkedin = m.group(1)

        # portfolio: any other URL not linkedin (first one)
        urls = URL_RE.findall(text)
        portfolio = None
        for u in urls:
            if linkedin and u.lower() in linkedin.lower():
                continue
            portfolio = u
            break
        return linkedin, portfolio

    def _guess_name(self, header_blk: str) -> Optional[str]:
        # Heuristic: first non-empty line with 2+ words, no email/phone/url
        for line in header_blk.splitlines():
            if EMAIL_RE.search(line) or URL_RE.search(line) or PHONE_RE.search(line):
                continue
            # Avoid section words
            if any(w in line.lower() for w in ["summary", "experience", "education", "skills", "certification", "languages"]):
                continue
            if len(line.split()) >= 2 and line.replace("-", "").strip():
                # Capitalization heuristic
                words = line.split()
                if sum(1 for w in words if w[:1].isupper()) >= 2:
                    return line.strip()
        return None

    def _guess_current_title(self, header_blk: str) -> Optional[str]:
        # Title often right after name line; pick a short line without url/email/phone
        lines = [l for l in header_blk.splitlines() if l.strip()]
        if not lines:
            return None
        # Skip first line (likely name), scan next few
        for line in lines[1:4]:
            if any(p.search(line) for p in (EMAIL_RE, URL_RE, PHONE_RE)):
                continue
            if 2 <= len(line.split()) <= 6:
                return line.strip()
        return None

    def _guess_city_country(self, header_blk: str) -> Tuple[Optional[str], Optional[str]]:
        # Look for "City, Country" in header
        m = CITY_COUNTRY_RE.search(header_blk)
        if not m:
            return None, None
        city = m.group(1).strip()
        country = m.group(2).strip()
        # very short city/country can be noise; sanity check
        if len(city) < 2 or len(country) < 2:
            return None, None
        return city, country

    def _extract_section(self, lines: List[str], headers: List[str]) -> List[str]:
        # Grab lines between a header and the next header among known set
        section_headers = ["professional summary", "summary", "work experience", "experience",
                           "education", "skills", "certifications", "certification", "languages", "language"]
        header_idx = None
        for i, l in enumerate(lines):
            ll = l.lower()
            if any(ll.startswith(h) for h in headers):
                header_idx = i
                break
        if header_idx is None:
            return []
        # Find next header boundary
        end = len(lines)
        for j in range(header_idx + 1, len(lines)):
            if any(lines[j].lower().startswith(h) for h in section_headers if h not in headers):
                end = j
                break
        return lines[header_idx + 1:end]

    def _parse_roles(self, section: List[str]) -> List[Role]:
        """
        Expected pattern examples:
          Title - Company, Location
          2016-10-09 - 2025-05-28
          • bullet
        """
        roles: List[Role] = []
        cur: Optional[Role] = None

        def flush():
            nonlocal cur
            if cur and (cur.title or cur.company or cur.start or cur.end or cur.bullets):
                roles.append(cur)
            cur = None

        i = 0
        while i < len(section):
            line = section[i]

            # A role header often looks like "Title - Company, Location"
            if "-" in line and not ISO_DATE.search(line):
                # Split only on first dash
                title_part, rest = [p.strip() for p in line.split("-", 1)]
                company = None
                location = None
                if "," in rest:
                    company, location = [p.strip() for p in rest.split(",", 1)]
                else:
                    company = rest.strip() if rest else None

                # Next line may be date range
                start, end = None, None
                if i + 1 < len(section) and ISO_DATE.search(section[i + 1]):
                    dates_line = section[i + 1]
                    ds = ISO_DATE.findall(dates_line)
                    if len(ds) >= 1:
                        start = "-".join(ds[0])
                        end = "-".join(ds[-1])
                    i += 1  # consume date line

                flush()
                cur = Role(title=title_part, company=company, location=location, start=start, end=end)
                i += 1
                continue

            # bullets
            if line.lstrip().startswith(("•", "-", "–", "*")):
                if not cur:
                    cur = Role(title="")
                cur.bullets.append(line.lstrip("•-–* ").strip())
                i += 1
                continue

            # Date-only line (sometimes titles appear elsewhere)
            if ISO_DATE.search(line):
                ds = ISO_DATE.findall(line)
                start = "-".join(ds[0]) if ds else None
                end = "-".join(ds[-1]) if ds else None
                if not cur:
                    cur = Role(title="")
                cur.start = cur.start or start
                cur.end = cur.end or end
                i += 1
                continue

            # Otherwise, could be continuation text—ignore or append
            i += 1

        flush()
        return roles

    def _parse_education(self, section: List[str]) -> List[EducationItem]:
        """
        Pattern examples:
          University Name - Degree
          Graduated: 1973
        """
        edu: List[EducationItem] = []
        cur: Optional[EducationItem] = None

        def flush():
            nonlocal cur
            if cur and cur.institution:
                edu.append(cur)
            cur = None

        i = 0
        while i < len(section):
            line = section[i]
            if "-" in line and not ISO_DATE.search(line):
                inst, deg = [p.strip() for p in line.split("-", 1)]
                flush()
                cur = EducationItem(institution=inst, degree=deg)
                i += 1
                continue

            # Graduated or year-only line
            lg = line.lower()
            if "graduated:" in lg:
                year = re.sub(r"[^0-9-]", "", line.split(":", 1)[1]).strip()
                if cur:
                    cur.end = year
                else:
                    cur = EducationItem(institution="", degree=None, end=year)
                i += 1
                continue

            # Handle bare year lines
            if re.fullmatch(r"\d{4}", line.strip()):
                if cur:
                    cur.end = line.strip()
                else:
                    cur = EducationItem(institution="", degree=None, end=line.strip())
                i += 1
                continue

            i += 1

        flush()
        return edu

    def _parse_certs(self, section: List[str]) -> List[str]:
        items: List[str] = []
        for line in section:
            if line.lstrip().startswith(("•", "-", "–", "*")):
                items.append(line.lstrip("•-–* ").strip())
            elif line and len(line.split()) >= 2:
                items.append(line.strip())
        return items

    def _parse_list_items(self, section: List[str]) -> List[str]:
        # Generic list parser: bullets or comma-separated
        items: List[str] = []
        for line in section:
            l = line.strip().strip(",")
            if not l:
                continue
            if l.lstrip().startswith(("•", "-", "–", "*")):
                items.append(l.lstrip("•-–* ").strip())
            elif "," in l:
                items.extend([x.strip() for x in l.split(",") if x.strip()])
            else:
                items.append(l)
        # de-dup, keep order
        seen = set()
        out = []
        for x in items:
            k = x.lower()
            if k not in seen:
                out.append(x)
                seen.add(k)
        return out

    def _parse_skills_and_more(
        self, skills_section: List[str], full_text: str
    ) -> Tuple[List[str], List[str], List[str], List[str], List[str], List[str]]:
        # Primary skills: first line(s) of skills section; Secondary: overflow or later lines
        skills_lines = [l for l in skills_section if l]
        prim: List[str] = []
        sec: List[str] = []

        if skills_lines:
            # First non-empty treated as primary
            first = skills_lines[0]
            prim = [x.strip() for x in re.split(r",|\|", first) if x.strip()]
            # Rest as secondary
            extra = skills_lines[1:]
            for l in extra:
                sec.extend([x.strip() for x in re.split(r",|\|", l) if x.strip()])

        # Tools (scan whole text for known tools)
        tools = sorted({t for t in TOOL_HINTS if re.search(rf"\b{re.escape(t)}\b", full_text, re.I)})

        # Clouds
        clouds = sorted({c for c in CLOUD_KEYWORDS if re.search(rf"\b{re.escape(c)}\b", full_text, re.I)})

        # Domains/Industries (very light heuristic – tune for your data)
        domains: List[str] = []
        industries: List[str] = []
        # Example: detect “exhibition design”, “print production”, “librarian/academic” etc.
        if re.search(r"\bexhibition design", full_text, re.I):
            domains.append("exhibition design")
            industries.append("design")
        if re.search(r"\bprint production", full_text, re.I):
            domains.append("print production")
            industries.append("printing")
        if re.search(r"\blibrarian", full_text, re.I):
            domains.append("library sciences")
            industries.append("education")

        # De-dup + clean
        def uniq(xs: List[str]) -> List[str]:
            seen = set()
            out = []
            for x in xs:
                k = x.lower()
                if k not in seen:
                    out.append(x)
                    seen.add(k)
            return out

        return uniq(prim), uniq(sec), uniq(tools), uniq(clouds), uniq(domains), uniq(industries)

    def _infer_seniority(self, title: Optional[str]) -> Optional[str]:
        if not title:
            return None
        t = title.lower()
        for k, v in SENIORITY_KEYWORDS.items():
            if re.search(rf"\b{k}\b", t):
                return v
        return None

    def _compute_yoe(self, roles: List[Role]) -> Optional[float]:
        # If we have multiple roles with start/end, compute from earliest start to latest end (or today)
        starts: List[datetime] = []
        ends: List[datetime] = []
        for r in roles:
            if r.start:
                ds = parse_iso_date(r.start)
                if ds:
                    starts.append(ds)
            if r.end:
                de = parse_iso_date(r.end)
                if de:
                    ends.append(de)
        if not starts:
            return None
        start = min(starts)
        end = max(ends) if ends else datetime.utcnow()
        years = diff_years(start, end)
        # clamp
        if years < 0:
            return None
        return years

    def _normalized_keywords(
        self,
        skills_primary: List[str],
        skills_secondary: List[str],
        tools: List[str],
        clouds: List[str],
        langs: List[str],
        domains: List[str],
        industries: List[str],
    ) -> List[str]:
        bag = set()
        for arr in (skills_primary, skills_secondary, tools, clouds, langs, domains, industries):
            for x in arr or []:
                xl = re.sub(r"\s+", " ", x.strip().lower())
                if xl:
                    bag.add(xl)
        return list(bag)


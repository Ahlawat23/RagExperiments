from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import UploadFile


class DataUploadHandler:

    def __init__( self, base_dir: Path) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.allowed_content_types = {
            "application/pdf",
            "application/octet-stream",
        }

    # ---------- Public API ----------

    async def save_all( self, files: List[UploadFile]) -> Dict[str, Any]:
        results: List[Dict[str, Any]] = []

        for f in files:
            result = await self._save_one(f)
            results.append(result)

        saved = sum(1 for r in results if r.get("saved"))
        skipped = len(results) - saved

        return {
            "message": "Processed uploads",
            "count": len(files),
            "saved": saved,
            "skipped": skipped,
            "results": results,
        }

    # ---------- Internals ----------

    async def _save_one(self, upload: UploadFile,) -> Dict[str, Any]:
        filename = (upload.filename or "").strip()
        content_type = (upload.content_type or "").lower()

        dest = self.base_dir / upload.filename
        try:
            await self._stream_to_disk(upload, dest)
        except Exception as exc:  # Keep simple; you can narrow to OSError, etc.
            return {
                "fileName": filename or "(unnamed)",
                "saved": False,
                "reason": f"Write error: {exc}",
                "contentType": content_type,
            }

        size_bytes = dest.stat().st_size if dest.exists() else 0

        return {
            "fileName": filename or "(unnamed)",
            "saved": True,
            "savedAs": dest.name,
            "path": str(dest.resolve()),
            "contentType": content_type,
            "sizeBytes": size_bytes,
        }



    async def _stream_to_disk(self, upload: UploadFile, dest: Path) -> None:
        # Ensure the file pointer is at start
        try:
            await upload.seek(0)
        except Exception:
            # Some backends may not support seek; ignore
            pass

        with dest.open("wb") as out:
            while True:
                chunk = await upload.read(1 << 20)
                if not chunk:
                    break
                out.write(chunk)

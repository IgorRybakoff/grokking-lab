from __future__ import annotations

import os
import shutil
import tempfile
import uuid
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from .audit import audit_run
from .evidence import export_evidence_package
from .web import HTML

try:
    from fastapi import FastAPI, File, HTTPException, UploadFile
    from fastapi.responses import FileResponse, HTMLResponse
except ImportError:  # pragma: no cover
    FastAPI = File = HTTPException = UploadFile = None  # type: ignore[assignment]
    FileResponse = HTMLResponse = None  # type: ignore[assignment]

MAX_UPLOAD_BYTES = 256 * 1024 * 1024
MAX_EXTRACTED_BYTES = 512 * 1024 * 1024
MAX_FILE_BYTES = 256 * 1024 * 1024
MAX_ZIP_ENTRIES = 5000


def _state_root() -> Path:
    root = Path(os.environ.get("GROKKINGLAB_STATE_DIR", tempfile.gettempdir())) / "grokkinglab-web"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _mode_type(info: zipfile.ZipInfo) -> int:
    return (info.external_attr >> 16) & 0o170000


def _validate_zip_member(info: zipfile.ZipInfo, seen: set[str]) -> None:
    raw_name = info.filename
    name = raw_name.replace("\\", "/")
    parts = PurePosixPath(name).parts
    if (
        not name
        or "\x00" in name
        or raw_name.startswith("/")
        or raw_name.startswith("\\")
        or "\\" in raw_name
        or ".." in parts
        or (parts and ":" in parts[0])
    ):
        raise ValueError(f"unsafe ZIP path: {raw_name}")
    if name in seen:
        raise ValueError(f"duplicate ZIP entry: {raw_name}")
    seen.add(name)

    mode_type = _mode_type(info)
    if info.create_system == 3 and mode_type not in (0, 0o100000, 0o040000):
        raise ValueError(f"symlink or special file is not accepted: {raw_name}")
    if info.flag_bits & 0x1:
        raise ValueError(f"encrypted ZIP entry is not accepted: {raw_name}")
    if info.file_size > MAX_FILE_BYTES:
        raise ValueError(f"ZIP entry exceeds the 256 MiB file limit: {raw_name}")


def _safe_extract_zip(zip_path: Path, destination: Path) -> None:
    try:
        with zipfile.ZipFile(zip_path) as zf:
            infos = zf.infolist()
            if len(infos) > MAX_ZIP_ENTRIES:
                raise ValueError(f"ZIP has too many entries ({len(infos)} > {MAX_ZIP_ENTRIES})")

            total = 0
            seen: set[str] = set()
            for info in infos:
                _validate_zip_member(info, seen)
                total += info.file_size
                if total > MAX_EXTRACTED_BYTES:
                    raise ValueError("ZIP expands beyond the 512 MiB MVP limit")

            root = destination.resolve()
            for info in infos:
                name = info.filename.replace("\\", "/")
                target = (root / Path(*PurePosixPath(name).parts)).resolve()
                if target != root and root not in target.parents:
                    raise ValueError(f"ZIP entry escapes destination: {info.filename}")
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                try:
                    with zf.open(info) as src, target.open("wb") as dst:
                        copied = 0
                        while True:
                            chunk = src.read(1024 * 1024)
                            if not chunk:
                                break
                            copied += len(chunk)
                            if copied > info.file_size or copied > MAX_FILE_BYTES:
                                raise ValueError(f"ZIP entry exceeded declared size: {info.filename}")
                            dst.write(chunk)
                except (zipfile.BadZipFile, EOFError) as exc:
                    raise ValueError(f"corrupt ZIP entry: {info.filename}") from exc
    except zipfile.BadZipFile as exc:
        raise ValueError("Upload is not a valid ZIP archive") from exc


def _locate_artifact_root(extracted: Path) -> Path:
    if (extracted / "experiment_manifest.json").is_file() and (extracted / "config.json").is_file():
        return extracted
    candidates = [
        path.parent
        for path in extracted.rglob("experiment_manifest.json")
        if (path.parent / "config.json").is_file()
    ]
    unique = sorted({path.resolve() for path in candidates})
    if not unique:
        raise ValueError("No experiment root found (need config.json + experiment_manifest.json)")
    if len(unique) > 1:
        raise ValueError("ZIP contains multiple experiment roots; upload one run per ZIP in MVP v0.1")
    return unique[0]


def _audit_to_job(root: Path, job_dir: Path) -> dict[str, Any]:
    audit = audit_run(root)
    package = job_dir / "grokkinglab_evidence.zip"
    export_evidence_package(root, package)
    return {
        "job_id": job_dir.name,
        "audit": audit,
        "download_url": f"/api/package/{job_dir.name}",
    }


def create_app():
    if FastAPI is None or File is None or HTTPException is None or UploadFile is None or FileResponse is None or HTMLResponse is None:
        raise RuntimeError("Web UI requires: pip install -e '.[web]'")

    app = FastAPI(title="Grokking Lab Experiment Audit", version="0.1.0")

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return HTML

    @app.get("/healthz")
    def health() -> dict[str, str]:
        return {"status": "ok", "product": "grokking-lab", "version": "0.1"}

    @app.post("/api/audit")
    async def audit_upload(file: UploadFile = File(...)):
        job_dir = _state_root() / uuid.uuid4().hex
        job_dir.mkdir(parents=True, exist_ok=False)
        zip_path = job_dir / "upload.zip"
        size = 0
        try:
            with zip_path.open("wb") as stream:
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > MAX_UPLOAD_BYTES:
                        raise ValueError("Upload exceeds the 256 MiB MVP limit")
                    stream.write(chunk)
            if not zipfile.is_zipfile(zip_path):
                raise ValueError("Upload is not a valid ZIP archive")
            extracted = job_dir / "run"
            extracted.mkdir()
            _safe_extract_zip(zip_path, extracted)
            root = _locate_artifact_root(extracted)
            return _audit_to_job(root, job_dir)
        except ValueError as exc:
            shutil.rmtree(job_dir, ignore_errors=True)
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except (zipfile.BadZipFile, EOFError) as exc:
            shutil.rmtree(job_dir, ignore_errors=True)
            raise HTTPException(status_code=400, detail=f"invalid ZIP archive: {exc}") from exc
        except Exception as exc:
            shutil.rmtree(job_dir, ignore_errors=True)
            raise HTTPException(status_code=500, detail=f"audit failed: {exc}") from exc
        finally:
            await file.close()

    @app.post("/api/demo")
    def audit_demo():
        root = _project_root() / "artifacts" / "p113_seed42_40k"
        if not root.is_dir():
            raise HTTPException(status_code=404, detail="Canonical demo artifacts are not installed")
        job_dir = _state_root() / uuid.uuid4().hex
        job_dir.mkdir(parents=True, exist_ok=False)
        try:
            return _audit_to_job(root, job_dir)
        except Exception as exc:
            shutil.rmtree(job_dir, ignore_errors=True)
            raise HTTPException(status_code=500, detail=f"demo audit failed: {exc}") from exc

    @app.get("/api/package/{job_id}")
    def download_package(job_id: str):
        if not job_id or any(ch not in "0123456789abcdef" for ch in job_id) or len(job_id) != 32:
            raise HTTPException(status_code=404, detail="package not found")
        package = _state_root() / job_id / "grokkinglab_evidence.zip"
        if not package.is_file():
            raise HTTPException(status_code=404, detail="package not found")
        return FileResponse(package, media_type="application/zip", filename="grokkinglab_evidence.zip")

    return app


app = create_app()

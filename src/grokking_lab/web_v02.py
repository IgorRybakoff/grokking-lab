from __future__ import annotations

from pathlib import Path

from . import web as _web
from .zipguard import safe_extract_zip


MAX_ZIP_ENTRY_BYTES = 256 * 1024 * 1024


def _safe_extract_zip(zip_path: Path, destination: Path) -> None:
    safe_extract_zip(
        zip_path,
        destination,
        max_entries=_web.MAX_ZIP_ENTRIES,
        max_total_bytes=_web.MAX_EXTRACTED_BYTES,
        max_file_bytes=MAX_ZIP_ENTRY_BYTES,
    )


def _locate_artifact_root(extracted: Path) -> Path:
    """Locate one experiment root, including damaged-but-auditable evidence packages.

    A complete package is identified by config + manifest. If one of those declared
    files has been removed by an adversary, a unique SHA256SUMS parent is still a
    sufficient root anchor so the audit can return FAILED rather than a generic 400.
    """
    if (extracted / "experiment_manifest.json").is_file() and (extracted / "config.json").is_file():
        return extracted

    complete = [
        path.parent
        for path in extracted.rglob("experiment_manifest.json")
        if (path.parent / "config.json").is_file()
    ]
    complete_unique = sorted({path.resolve() for path in complete})
    if len(complete_unique) == 1:
        return complete_unique[0]
    if len(complete_unique) > 1:
        raise ValueError("ZIP contains multiple experiment roots; upload one run per ZIP in MVP v0.1")

    evidence_roots = sorted({path.parent.resolve() for path in extracted.rglob("SHA256SUMS")})
    if len(evidence_roots) == 1:
        return evidence_roots[0]
    if len(evidence_roots) > 1:
        raise ValueError("ZIP contains multiple evidence roots; upload one run per ZIP in MVP v0.1")
    raise ValueError("No experiment root found (need config.json + experiment_manifest.json or a unique SHA256SUMS)")


# The existing FastAPI endpoint resolves these helpers from the web module at
# request time, so replace only the trust-boundary functions and keep the tested
# UI/API surface unchanged.
_web._safe_extract_zip = _safe_extract_zip
_web._locate_artifact_root = _locate_artifact_root

HTML = _web.HTML
create_app = _web.create_app
app = create_app()

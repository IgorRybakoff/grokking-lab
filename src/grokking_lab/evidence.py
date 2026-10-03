from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

from .audit import audit_run


_RESERVED_GENERATED = {
    "grokkinglab_audit.json",
    "grokkinglab_report.md",
    "package_manifest.json",
}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _deterministic_write(zf: zipfile.ZipFile, arcname: str, data: bytes) -> None:
    info = zipfile.ZipInfo(arcname, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    zf.writestr(info, data)


def _report_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# Grokking Lab Experiment Audit",
        "",
        f"- Verdict: **{audit['verdict']}**",
        f"- Experiment: `{audit['experiment_id']}`",
        f"- Adapter: `{audit['adapter']}`",
        f"- Schema: `{audit['schema_version']}`",
        "",
        "## Checks",
        "",
        "| Check | Status |",
        "|---|---|",
    ]
    lines.extend(f"| {item['id']} | {item['status']} |" for item in audit["checks"])
    lines.extend(
        [
            "",
            "This report is generated from machine-readable evidence. The JSON audit result is authoritative for this package.",
            "",
        ]
    )
    return "\n".join(lines)


def export_evidence_package(
    artifact_dir: str | Path,
    output: str | Path | None = None,
    *,
    checkpoint: str = "final_model_state.pt",
) -> dict[str, Any]:
    root = Path(artifact_dir)
    audit = audit_run(root, checkpoint=checkpoint, replay=True)
    output_path = Path(output) if output is not None else root.with_name(f"{root.name}_evidence.zip")

    source_files = [
        path
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name not in _RESERVED_GENERATED and path.resolve() != output_path.resolve()
    ]
    manifest_entries: list[dict[str, Any]] = []
    source_payloads: list[tuple[str, bytes]] = []
    for path in source_files:
        relative = path.relative_to(root).as_posix()
        data = path.read_bytes()
        source_payloads.append((relative, data))
        manifest_entries.append({"path": relative, "sha256": _sha256_bytes(data), "size": len(data)})

    audit_bytes = json.dumps(audit, indent=2, sort_keys=True, default=str).encode("utf-8") + b"\n"
    report_bytes = _report_markdown(audit).encode("utf-8")
    generated = [
        {"path": "grokkinglab_audit.json", "sha256": _sha256_bytes(audit_bytes), "size": len(audit_bytes)},
        {"path": "grokkinglab_report.md", "sha256": _sha256_bytes(report_bytes), "size": len(report_bytes)},
    ]
    package_manifest = {
        "schema_version": "grokkinglab.evidence-package.v0.1",
        "experiment_id": audit["experiment_id"],
        "verdict": audit["verdict"],
        "files": manifest_entries + generated,
    }
    manifest_bytes = json.dumps(package_manifest, indent=2, sort_keys=True).encode("utf-8") + b"\n"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w") as zf:
        for relative, data in source_payloads:
            _deterministic_write(zf, relative, data)
        _deterministic_write(zf, "grokkinglab_audit.json", audit_bytes)
        _deterministic_write(zf, "grokkinglab_report.md", report_bytes)
        _deterministic_write(zf, "package_manifest.json", manifest_bytes)

    package_bytes = output_path.read_bytes()
    return {
        "schema_version": "grokkinglab.evidence-export.v0.1",
        "status": audit["status"],
        "verdict": audit["verdict"],
        "experiment_id": audit["experiment_id"],
        "output": str(output_path),
        "package_sha256": _sha256_bytes(package_bytes),
        "source_file_count": len(source_files),
    }

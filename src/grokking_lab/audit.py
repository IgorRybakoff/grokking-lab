from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .artifacts import read_sha256sums, sha256_file, verify_artifact_directory
from .replay import replay_checkpoint


AUDIT_SCHEMA_VERSION = "grokkinglab.audit.v0.1"
BASE_REQUIRED = ("config.json", "experiment_manifest.json", "SHA256SUMS")
ENVIRONMENT_KEYS = ("python_version", "torch_version", "device")


def _check(check_id: str, status: str, **details: Any) -> dict[str, Any]:
    return {"id": check_id, "status": status, "details": details}


def _load_json_if_present(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _checksum_check(root: Path) -> dict[str, Any]:
    sums_path = root / "SHA256SUMS"
    if not sums_path.is_file():
        return _check("checksums", "INCOMPLETE", reason="SHA256SUMS missing")

    try:
        sums = read_sha256sums(sums_path)
    except Exception as exc:  # malformed evidence is a verification failure
        return _check("checksums", "FAIL", reason=f"cannot parse SHA256SUMS: {exc}")

    missing: list[str] = []
    mismatches: list[str] = []
    for relative, expected in sums.items():
        path = root / relative
        if not path.is_file():
            missing.append(relative)
        elif sha256_file(path) != expected:
            mismatches.append(relative)

    if mismatches:
        return _check("checksums", "FAIL", mismatches=mismatches, missing=missing, verified=len(sums) - len(mismatches) - len(missing))
    if missing:
        return _check("checksums", "INCOMPLETE", missing=missing, verified=len(sums) - len(missing))
    return _check("checksums", "PASS", verified=len(sums))


def _environment_check(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    environment_path = root / "environment.json"
    if environment_path.is_file():
        environment = _load_json_if_present(environment_path)
        if environment:
            return _check("environment", "PASS", source="environment.json", environment=environment)
        return _check("environment", "FAIL", source="environment.json", reason="environment.json is not a JSON object")

    environment = {key: manifest.get(key) for key in ENVIRONMENT_KEYS if manifest.get(key) is not None}
    missing = [key for key in ENVIRONMENT_KEYS if key not in environment]
    if missing:
        return _check("environment", "INCOMPLETE", source="experiment_manifest.json", missing=missing, environment=environment)
    return _check("environment", "PASS", source="experiment_manifest.json", environment=environment)


def _canonical_grokking_check(root: Path) -> dict[str, Any]:
    try:
        result = verify_artifact_directory(root)
    except FileNotFoundError as exc:
        return _check("canonical_grokking_contract", "INCOMPLETE", reason=str(exc))
    except ValueError as exc:
        message = str(exc)
        status = "INCOMPLETE" if message.startswith("missing required evidence") else "FAIL"
        return _check("canonical_grokking_contract", status, reason=message)
    except Exception as exc:
        return _check("canonical_grokking_contract", "FAIL", reason=f"unexpected verification error: {exc}")
    return _check("canonical_grokking_contract", "PASS", result=result)


def _replay_check(root: Path, checkpoint: str) -> dict[str, Any]:
    checkpoint_path = root / "checkpoints" / checkpoint
    if not checkpoint_path.is_file():
        return _check("replay", "INCOMPLETE", checkpoint=checkpoint, reason="checkpoint missing")
    try:
        result = replay_checkpoint(root, checkpoint)
    except FileNotFoundError as exc:
        return _check("replay", "INCOMPLETE", checkpoint=checkpoint, reason=str(exc))
    except Exception as exc:
        return _check("replay", "FAIL", checkpoint=checkpoint, reason=f"replay failed: {exc}")
    return _check("replay", result.get("status", "FAIL"), checkpoint=checkpoint, result=result)


def audit_run(
    artifact_dir: str | Path,
    *,
    checkpoint: str = "final_model_state.pt",
    replay: bool = True,
) -> dict[str, Any]:
    """Audit one frozen Grokking Lab run without changing the source evidence.

    v0.1 deliberately supports the existing canonical Grokking Lab artifact contract.
    The public result shape is generic so additional experiment adapters can be added
    later without changing the VERIFIED / FAILED / INCOMPLETE semantics.
    """

    root = Path(artifact_dir)
    manifest = _load_json_if_present(root / "experiment_manifest.json")

    missing = [name for name in BASE_REQUIRED if not (root / name).is_file()]
    checks: list[dict[str, Any]] = [
        _check("base_evidence", "PASS" if not missing else "INCOMPLETE", missing=missing),
        _environment_check(root, manifest),
        _checksum_check(root),
        _canonical_grokking_check(root),
    ]
    if replay:
        checks.append(_replay_check(root, checkpoint))

    statuses = {item["status"] for item in checks}
    if "FAIL" in statuses:
        status = "FAIL"
        verdict = "FAILED"
    elif "INCOMPLETE" in statuses:
        status = "INCOMPLETE"
        verdict = "INCOMPLETE"
    else:
        status = "PASS"
        verdict = "VERIFIED"

    return {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "status": status,
        "verdict": verdict,
        "adapter": "canonical_grokking_v1",
        "experiment_id": manifest.get("experiment_id", root.name),
        "artifact_dir": str(root),
        "checkpoint": checkpoint if replay else None,
        "checks": checks,
    }

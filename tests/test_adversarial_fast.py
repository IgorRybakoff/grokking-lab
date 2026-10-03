from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from grokking_lab.web_v02 import create_app

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "artifacts" / "p113_seed42_40k"
CHECKPOINT = "checkpoints/final_model_state.pt"
SUMS = "SHA256SUMS"


def _read_files() -> dict[str, bytes]:
    return {
        path.relative_to(CANONICAL).as_posix(): path.read_bytes()
        for path in sorted(CANONICAL.rglob("*"))
        if path.is_file()
    }


def _zip(files: dict[str, bytes], *, extra: list[tuple[zipfile.ZipInfo, bytes]] | None = None, stored: bool = False) -> bytes:
    buf = io.BytesIO()
    compression = zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED
    with pytest.warns(None) if False else _nullcontext():
        with zipfile.ZipFile(buf, "w", compression=compression) as zf:
            for name, data in files.items():
                zf.writestr(name, data)
            for info, data in extra or []:
                zf.writestr(info, data)
    return buf.getvalue()


class _nullcontext:
    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc, tb):
        return False


def _post(client: TestClient, data: bytes, name: str = "run.zip"):
    return client.post("/api/audit", files={"file": (name, data, "application/zip")})


def _audit(response) -> dict:
    assert response.status_code == 200, response.text[:500]
    return response.json()["audit"]


def _rewrite_checksum(files: dict[str, bytes], relative: str) -> dict[str, bytes]:
    out = dict(files)
    digest = hashlib.sha256(out[relative]).hexdigest()
    lines = []
    found = False
    for line in out[SUMS].decode("utf-8").splitlines():
        if not line.strip():
            continue
        old_digest, old_relative = line.split(maxsplit=1)
        path = old_relative.lstrip("* ")
        if path == relative:
            lines.append(f"{digest}  {relative}")
            found = True
        else:
            lines.append(f"{old_digest}  {path}")
    assert found, relative
    out[SUMS] = ("\n".join(lines) + "\n").encode("utf-8")
    return out


def _remove_checksum_declaration(files: dict[str, bytes], relative: str) -> dict[str, bytes]:
    out = dict(files)
    lines = []
    for line in out[SUMS].decode("utf-8").splitlines():
        if not line.strip():
            continue
        digest, raw_relative = line.split(maxsplit=1)
        path = raw_relative.lstrip("* ")
        if path != relative:
            lines.append(f"{digest}  {path}")
    out[SUMS] = ("\n".join(lines) + "\n").encode("utf-8")
    return out


def _corrupt_stored_member(data: bytes, member: str) -> bytes:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        info = zf.getinfo(member)
        assert info.compress_type == zipfile.ZIP_STORED
        offset = info.header_offset
        name_len = int.from_bytes(data[offset + 26 : offset + 28], "little")
        extra_len = int.from_bytes(data[offset + 28 : offset + 30], "little")
        pos = offset + 30 + name_len + extra_len + max(0, info.file_size // 2)
    mutable = bytearray(data)
    mutable[pos] ^= 0xFF
    return bytes(mutable)


@pytest.fixture(scope="session")
def canonical_files() -> dict[str, bytes]:
    assert CANONICAL.is_dir()
    return _read_files()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app(), raise_server_exceptions=False)


def test_honest_canonical_package_is_verified(client, canonical_files):
    response = _post(client, _zip(canonical_files))
    audit = _audit(response)
    assert audit["verdict"] == "VERIFIED"
    assert all(item["status"] == "PASS" for item in audit["checks"])


def test_filename_does_not_change_verdict(client, canonical_files):
    data = _zip(canonical_files)
    baseline = _audit(_post(client, data, "run.zip"))
    renamed = _audit(_post(client, data, "fail_corrupt_mismatch.zip"))
    assert baseline["verdict"] == renamed["verdict"] == "VERIFIED"
    assert [(c["id"], c["status"]) for c in baseline["checks"]] == [
        (c["id"], c["status"]) for c in renamed["checks"]
    ]


def test_stale_checksum_fails(client, canonical_files):
    files = dict(canonical_files)
    files["report.md"] = files["report.md"] + b"\nTAMPERED\n"
    audit = _audit(_post(client, _zip(files)))
    assert audit["verdict"] == "FAILED"
    statuses = {item["id"]: item["status"] for item in audit["checks"]}
    assert statuses["checksums"] == "FAIL"


def test_rehashed_altered_checkpoint_fails_via_replay(client, canonical_files):
    files = dict(canonical_files)
    blob = bytearray(files[CHECKPOINT])
    blob[len(blob) // 2] ^= 0x01
    files[CHECKPOINT] = bytes(blob)
    files = _rewrite_checksum(files, CHECKPOINT)
    audit = _audit(_post(client, _zip(files)))
    assert audit["verdict"] == "FAILED"
    statuses = {item["id"]: item["status"] for item in audit["checks"]}
    assert statuses["checksums"] == "PASS"
    assert "FAIL" in (statuses["replay"], statuses["canonical_grokking_contract"])


def test_declared_missing_file_is_failed(client, canonical_files):
    files = dict(canonical_files)
    del files["report.md"]
    audit = _audit(_post(client, _zip(files)))
    assert audit["verdict"] == "FAILED"
    statuses = {item["id"]: item["status"] for item in audit["checks"]}
    assert statuses["checksums"] == "FAIL"


def test_missing_checkpoint_and_declaration_is_incomplete(client, canonical_files):
    files = dict(canonical_files)
    del files[CHECKPOINT]
    files = _remove_checksum_declaration(files, CHECKPOINT)
    audit = _audit(_post(client, _zip(files)))
    assert audit["verdict"] == "INCOMPLETE"
    statuses = {item["id"]: item["status"] for item in audit["checks"]}
    assert statuses["replay"] == "INCOMPLETE"


def test_garbage_never_verifies(client):
    response = _post(client, b"not a zip")
    assert 400 <= response.status_code < 500
    assert "VERIFIED" not in response.text


def test_path_traversal_is_rejected(client):
    info = zipfile.ZipInfo("../evil.txt")
    data = _zip({}, extra=[(info, b"x")])
    response = _post(client, data)
    assert response.status_code == 400


def test_absolute_path_is_rejected(client):
    info = zipfile.ZipInfo("/tmp/evil.txt")
    data = _zip({}, extra=[(info, b"x")])
    response = _post(client, data)
    assert response.status_code == 400


def test_symlink_is_rejected(client):
    info = zipfile.ZipInfo("link")
    info.create_system = 3
    info.external_attr = 0o120777 << 16
    data = _zip({}, extra=[(info, b"/etc/passwd")])
    response = _post(client, data)
    assert response.status_code == 400


def test_duplicate_entry_is_rejected(client):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("same.txt", b"one")
        with pytest.warns(UserWarning):
            zf.writestr("same.txt", b"two")
    response = _post(client, buf.getvalue())
    assert response.status_code == 400
    assert "duplicate ZIP entry" in response.json()["detail"]


def test_corrupted_crc_is_client_error(client):
    data = _zip({"payload.bin": b"abcdef" * 1000}, stored=True)
    corrupted = _corrupt_stored_member(data, "payload.bin")
    response = _post(client, corrupted)
    assert 400 <= response.status_code < 500
    assert "VERIFIED" not in response.text


def test_public_response_does_not_expose_server_paths(client):
    response = client.post("/api/demo")
    assert response.status_code == 200
    text = response.text
    assert "artifact_dir" not in text
    assert "/tmp/" not in text
    assert "/var/folders" not in text

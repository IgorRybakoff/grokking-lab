from __future__ import annotations

import io
import zipfile

from fastapi.testclient import TestClient

from grokking_lab.web_v02 import create_app


def _post(data: bytes):
    client = TestClient(create_app(), raise_server_exceptions=False)
    return client.post("/api/audit", files={"file": ("limits.zip", data, "application/zip")})


def test_archive_expanded_size_limit_is_enforced():
    buf = io.BytesIO()
    chunk = b"\0" * (1024 * 1024)
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as zf:
        with zf.open("bomb/zeros.bin", "w", force_zip64=True) as stream:
            for _ in range(513):
                stream.write(chunk)
    response = _post(buf.getvalue())
    assert response.status_code in (400, 413), response.text[:300]
    assert "VERIFIED" not in response.text


def test_archive_entry_count_limit_is_enforced():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as zf:
        for index in range(5001):
            zf.writestr(f"filler/{index}.txt", b"")
    response = _post(buf.getvalue())
    assert response.status_code in (400, 413), response.text[:300]
    assert "VERIFIED" not in response.text

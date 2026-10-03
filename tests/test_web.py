from __future__ import annotations

import io
import zipfile

from fastapi.testclient import TestClient

from grokking_lab.web import create_app


def test_web_health_and_home():
    client = TestClient(create_app())
    health = client.get("/healthz")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    home = client.get("/")
    assert home.status_code == 200
    assert "Verify the experiment, not the claim." in home.text
    assert "Проверяйте эксперимент, а не утверждение." in home.text
    assert 'id="enBtn"' in home.text
    assert 'id="ruBtn"' in home.text
    assert "RUN CANONICAL DEMO" in home.text
    assert "ЗАПУСТИТЬ ЭТАЛОННЫЙ ПРИМЕР" in home.text
    assert "localStorage.getItem('grokkinglab_lang')" in home.text


def test_upload_requires_experiment_evidence():
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as zf:
        zf.writestr("README.txt", "not an experiment")
    payload.seek(0)

    client = TestClient(create_app())
    response = client.post(
        "/api/audit",
        files={"file": ("empty.zip", payload.getvalue(), "application/zip")},
    )
    assert response.status_code == 400
    assert "No experiment root found" in response.json()["detail"]


def test_upload_rejects_path_traversal():
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as zf:
        zf.writestr("../escape.txt", "blocked")
    payload.seek(0)

    client = TestClient(create_app())
    response = client.post(
        "/api/audit",
        files={"file": ("unsafe.zip", payload.getvalue(), "application/zip")},
    )
    assert response.status_code == 400
    assert "unsafe ZIP path" in response.json()["detail"]

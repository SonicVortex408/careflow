import time

from .conftest import OTHER_PATIENT, PATIENT, REPORT, SAMPLE_REPORT


def test_service_starts_without_llm_key_or_infra(client):
    assert client.get("/").status_code == 200
    assert client.get("/health").json() == {"status": "ok"}
    ready = client.get("/ready").json()
    assert ready["jobs"]["backend"] == "local"
    assert ready["graph"]["backend"] == "in_memory"
    assert ready["llm"]["configured"] is False


def test_invalid_ids_are_rejected_before_any_path_join(client):
    for bad in ("../../etc", "abc", "6a9d17d6b74cef0c8858926a/../x"):
        r = client.post(
            "/api/ocr",
            data={"patient_id": bad, "report_id": REPORT},
            files={"file": ("r.txt", b"TSH 2.0 mIU/L", "text/plain")},
        )
        assert r.status_code == 422
    r = client.post("/api/chat/", json={"message": "hi", "thread_id": "t", "patient_id": "../x"})
    assert r.status_code == 422


def test_unsupported_file_type(client):
    r = client.post(
        "/api/ocr",
        data={"patient_id": PATIENT, "report_id": REPORT},
        files={"file": ("r.exe", b"MZ", "application/octet-stream")},
    )
    assert r.status_code == 415


def test_internal_key_enforced_when_configured(monkeypatch, client):
    from fastapi.testclient import TestClient

    from app.core import config
    from app.main import create_app

    monkeypatch.setenv("INTERNAL_API_KEY", "s3cret")
    config.get_settings.cache_clear()
    c = TestClient(create_app())
    assert c.get("/api/inference/catalog").status_code == 401
    assert c.get("/api/inference/catalog", headers={"X-Internal-Key": "s3cret"}).status_code == 200
    assert c.get("/health").status_code == 200  # health stays open


def _wait(client, job_id, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = client.get(f"/api/ocr/jobs/{job_id}").json()
        if job["status"] in ("completed", "failed"):
            return job
        time.sleep(0.2)
    raise AssertionError("job did not finish")


def test_upload_to_interpretation_end_to_end(client):
    r = client.post(
        "/api/ocr",
        data={
            "patient_id": PATIENT,
            "report_id": REPORT,
            "proms": '{"fatigue_severity": 8, "brain_fog_frequency": "often", "hair_loss": "mild"}',
        },
        files={"file": ("report.txt", SAMPLE_REPORT.encode(), "text/plain")},
    )
    assert r.status_code == 202
    job = _wait(client, r.json()["job_id"])
    assert job["status"] == "completed", job
    out = job["result"]
    keys = {b["key"] for b in out["extraction"]["biomarkers"]}
    assert keys == {"TSH", "FT4", "FT3", "TPOAB", "VITD", "B12", "FERRITIN", "MG", "ZINC"}
    assert out["review"] == {"required": True, "status": "pending_clinician_review"}
    assert "synthetic data" in out["label"]
    assert out["summary"]["readability_grade"] <= 8
    assert out["guardrails"]["passed"]
    assert "cancer" not in out["summary"]["text"].lower()  # injected instruction ignored
    assert out["analytics"]["risk"]["fatigue"]["level"] in ("low", "moderate", "high")
    assert len(out["analytics"]["risk"]["fatigue"]["drivers"]) <= 3
    assert out["evidence"]["chains"] and all(
        "evidence_level" in c["edge"] for c in out["evidence"]["chains"]
    )
    assert out["appointment_guide"]


def test_unknown_job_is_404(client):
    assert client.get("/api/ocr/jobs/00000000-0000-0000-0000-000000000000").status_code == 404


def test_structured_interpretation(client):
    r = client.post(
        "/api/interpret",
        json={
            "patient_id": PATIENT,
            "biomarkers": [
                {"label": "Ferritin", "value": "8", "unit": "ng/mL"},
                {"label": "TSH", "value": 60, "unit": "mIU/L"},
                {"label": "Hemoglobin", "value": 12, "unit": "g/dL"},
            ],
            "sex": "F",
            "age": 35,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["escalation"]["level"] == "urgent"  # TSH > 50
    assert any(x["label"] == "Hemoglobin" for x in body["extraction"]["quality"]["rejected"])
    assert body["summary"]["text"].startswith("Important:")


def test_inference_endpoints(client):
    cohort = client.get("/api/inference/cohort").json()
    assert len(cohort["points"]) > 100 and cohort["profiles"]
    assert "synthetic" in cohort["label"]
    bands = client.get("/api/inference/bands").json()
    assert set(bands["bands"]) >= {"TSH", "FERRITIN"}
    model = client.get("/api/inference/model").json()
    assert model["available"] and model["metrics"]["risk"]["fatigue"]["auroc"] > 0.6
    r = client.post(
        "/api/inference",
        json={"markers": {"TSH": 2.0, "FT4": 15, "FERRITIN": 90}, "sex": "M", "age": 50},
    )
    assert r.json()["bands"]["TSH"]["reference_status"] == "within"


def test_chat_without_llm_is_grounded_and_guarded(client):
    r = client.post(
        "/api/chat/",
        json={
            "message": "What does low ferritin mean?",
            "thread_id": "t1",
            "patient_id": PATIENT,
            "patient_context": {
                "markers": {"FERRITIN": 12, "TSH": 5.8, "FT4": 12},
                "sex": "F",
                "age": 41,
            },
        },
    )
    body = r.json()
    assert r.status_code == 200
    assert "not a diagnosis" in body["response"]
    assert body["guardrails"]["source"] == "template"
    assert "ferritin" in body["response"].lower()


def test_chat_red_flag_escalates(client):
    r = client.post(
        "/api/chat/",
        json={
            "message": "I have chest pain and feel faint",
            "thread_id": "t2",
            "patient_id": OTHER_PATIENT,
        },
    )
    body = r.json()
    assert body["escalation"]["level"] == "emergency"
    assert body["response"].startswith("If you have chest pain")

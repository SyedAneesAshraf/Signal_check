from fastapi.testclient import TestClient
from io import BytesIO
from PIL import Image

import app.api.routes_cases as routes_cases
from app.main import app
from app.services.claim_extractor import ExtractedClaim
from app.services.pipeline import PipelineClaim, PipelineEvidence
from app.services.case_store import build_image_input


class StubPipeline:
    def analyze(self, text: str):
        claim = ExtractedClaim("claim_1", text, ["Bank"], "factual")
        evidence = PipelineEvidence(
            passage_id="evidence-1",
            title="Contradictory guidance",
            source_name="Example source",
            source_url="https://example.test/evidence",
            published_date=None,
            passage="The claim is contradicted.",
            retrieval_similarity=0.9,
            nli_label="contradiction",
            nli_score=0.9,
            source_type="official_guidance",
            source_quality="official",
            retrieved_date="2026-10-27",
        )
        return [PipelineClaim(claim, "refuted", [evidence], "Contradicted.")], "refuted"


def test_case_analysis_fuses_claim_url_and_correlation_signals(monkeypatch) -> None:
    monkeypatch.setattr(routes_cases, "case_store", routes_cases.CaseStore())
    monkeypatch.setattr(routes_cases, "get_pipeline", lambda: StubPipeline())
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    client = TestClient(app)
    case_id = client.post("/api/cases").json()["case_id"]
    client.post(
        f"/api/cases/{case_id}/inputs/text",
        json={"text": "Bank asks you to verify at http://192.168.1.1/login"},
    )
    client.post(
        f"/api/cases/{case_id}/inputs/url",
        json={"url": "http://192.168.1.1/login"},
    )

    result = client.post(f"/api/cases/{case_id}/analyze")

    assert result.status_code == 200
    body = result.json()
    assert body["verdict"] == "deceptive"
    assert body["risk_score"] >= 0.6
    assert body["claims"][0]["verification_status"] == "refuted"
    assert any(signal["signal_type"] == "phishing_risk" for signal in body["signals"])
    assert body["deception_risk"] == "high"
    assert body["intent_assessment"] == "not_determinable_from_content"


def test_case_analysis_marks_strong_phishing_url_deceptive(monkeypatch) -> None:
    monkeypatch.setattr(routes_cases, "case_store", routes_cases.CaseStore())
    monkeypatch.setattr(routes_cases, "get_pipeline", lambda: StubPipeline())
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    client = TestClient(app)
    case_id = client.post("/api/cases").json()["case_id"]
    client.post(
        f"/api/cases/{case_id}/inputs/url",
        json={"url": "http://192.168.1.1/login/verify-bank-account"},
    )

    result = client.post(f"/api/cases/{case_id}/analyze")

    assert result.status_code == 200
    body = result.json()
    assert body["verdict"] == "deceptive"
    assert body["risk_score"] >= 0.6


def test_case_analysis_marks_refuted_text_deceptive(monkeypatch) -> None:
    monkeypatch.setattr(routes_cases, "case_store", routes_cases.CaseStore())
    monkeypatch.setattr(routes_cases, "get_pipeline", lambda: StubPipeline())
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    client = TestClient(app)
    case_id = client.post("/api/cases").json()["case_id"]
    client.post(
        f"/api/cases/{case_id}/inputs/text",
        json={"text": "The bank claim is false."},
    )

    result = client.post(f"/api/cases/{case_id}/analyze")

    assert result.status_code == 200
    body = result.json()
    assert body["verdict"] == "deceptive"
    assert body["risk_score"] >= 0.6


def test_case_analysis_uses_message_context_for_linked_url(monkeypatch) -> None:
    monkeypatch.setattr(routes_cases, "case_store", routes_cases.CaseStore())
    monkeypatch.setattr(routes_cases, "get_pipeline", lambda: StubPipeline())
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    client = TestClient(app)
    case_id = client.post("/api/cases").json()["case_id"]
    client.post(
        f"/api/cases/{case_id}/inputs/text",
        json={"text": "bank acc expiry click to update pin"},
    )
    client.post(
        f"/api/cases/{case_id}/inputs/url",
        json={"url": "https://web.fishy.com/"},
    )

    result = client.post(f"/api/cases/{case_id}/analyze")

    assert result.status_code == 200
    body = result.json()
    assert body["verdict"] == "deceptive"
    assert body["risk_score"] >= 0.6


def test_case_analysis_runs_ocr_and_verifies_image_text(monkeypatch) -> None:
    monkeypatch.setattr(routes_cases, "case_store", routes_cases.CaseStore())
    monkeypatch.setattr(routes_cases, "get_pipeline", lambda: StubPipeline())
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr(
        "app.services.case_analysis.extract_image_text",
        lambda content: "The bank asks for your PIN.",
    )
    client = TestClient(app)
    image_buffer = BytesIO()
    Image.new("RGB", (2, 2), "white").save(image_buffer, format="PNG")
    case = routes_cases.case_store.create()
    routes_cases.case_store.add_input(
        case.case_id,
        build_image_input(image_buffer.getvalue(), file_name="test.png", mime_type="image/png"),
    )

    result = client.post(f"/api/cases/{case.case_id}/analyze")

    assert result.status_code == 200
    body = result.json()
    assert body["claims"][0]["source_input_ids"] == [body["inputs"][0]["input_id"]]
    assert body["signals"][0]["details"]["ocr_text"] == "The bank asks for your PIN."


def test_image_without_readable_text_needs_review(monkeypatch) -> None:
    monkeypatch.setattr(routes_cases, "case_store", routes_cases.CaseStore())
    monkeypatch.setattr(routes_cases, "get_pipeline", lambda: StubPipeline())
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr(
        "app.services.case_analysis.extract_image_text",
        lambda content: (_ for _ in ()).throw(ValueError("no text")),
    )
    image_buffer = BytesIO()
    Image.new("RGB", (2, 2), "white").save(image_buffer, format="PNG")
    case = routes_cases.case_store.create()
    routes_cases.case_store.add_input(
        case.case_id,
        build_image_input(image_buffer.getvalue(), file_name="scene.png", mime_type="image/png"),
    )

    result = TestClient(app).post(f"/api/cases/{case.case_id}/analyze")

    assert result.status_code == 200
    assert result.json()["verdict"] == "needs_review"

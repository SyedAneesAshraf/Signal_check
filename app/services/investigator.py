"""Groq-backed contextual investigation for combined manual cases."""

from dataclasses import dataclass
import json
import logging
import os
from typing import Any

import httpx

from app.services.multimodal import fetch_url_text

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class InvestigatorResult:
    verdict: str
    risk_score: float
    confidence: float
    summary: str
    reasons: tuple[str, ...]
    website_findings: tuple[str, ...]
    provider: str


def investigate_case(
    *,
    message_text: str,
    urls: list[str],
    claims: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    images: list[dict[str, Any]] | None = None,
    timeout: float = 30.0,
) -> InvestigatorResult | None:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    if timeout <= 0:
        raise ValueError("timeout must be greater than zero.")

    pages: list[dict[str, str]] = []
    for url in urls:
        try:
            page_text = fetch_url_text(url, timeout=timeout)
            pages.append({"url": url, "text": page_text})
            _trace(
                "investigator_page_fetched url=%s extracted_chars=%d",
                url,
                len(page_text),
            )
        except (OSError, RuntimeError, ValueError) as error:
            pages.append({"url": url, "text": f"Page inspection failed: {error}"})
            _trace(
                "investigator_page_fetch_failed url=%s error=%s",
                url,
                type(error).__name__,
            )

    prompt = _build_prompt(message_text, pages, claims, evidence, images or [])
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    _trace(
        "groq_investigation_started model=%s urls=%d claims=%d evidence=%d prompt_chars=%d",
        model,
        len(urls),
        len(claims),
        len(evidence),
        len(prompt),
    )
    _trace("groq_request_prompt_preview=%s", prompt[:4000])
    try:
        response = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a careful deception investigator. Analyze only "
                            "the supplied content and evidence. Do not invent facts. "
                            "Assess content risk, not the sender's private intent. "
                            "Never claim that a person knowingly lied based only on "
                            "the supplied content. "
                            "Treat a webpage's requests for passwords, PINs, payment, "
                            "or urgent account action as risk indicators, but explain "
                            "why. Return valid JSON only."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as error:
        status_code = getattr(getattr(error, "response", None), "status_code", None)
        logger.warning(
            "groq_investigation_request_failed status_code=%s error=%s",
            status_code,
            type(error).__name__,
        )
        raise RuntimeError("The Groq investigation request failed.") from error

    content = _response_content(payload)
    try:
        result = json.loads(content)
    except json.JSONDecodeError as error:
        raise RuntimeError("The Groq investigation returned invalid JSON.") from error
    parsed = _parse_result(result)
    _trace(
        "groq_investigation_completed provider=%s verdict=%s risk_score=%.3f "
        "confidence=%.3f reasons=%d findings=%d",
        parsed.provider,
        parsed.verdict,
        parsed.risk_score,
        parsed.confidence,
        len(parsed.reasons),
        len(parsed.website_findings),
    )
    _trace(
        "groq_response_result=%s",
        json.dumps(
            {
                "verdict": parsed.verdict,
                "risk_score": parsed.risk_score,
                "confidence": parsed.confidence,
                "summary": parsed.summary,
                "reasons": parsed.reasons,
                "website_findings": parsed.website_findings,
            },
            ensure_ascii=True,
        ),
    )
    return parsed


def _build_prompt(
    message_text: str,
    pages: list[dict[str, str]],
    claims: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    images: list[dict[str, Any]],
) -> str:
    return json.dumps(
        {
            "message": message_text,
            "web_pages": pages,
            "verified_claims": claims,
            "retrieved_evidence": evidence,
            "images": images,
            "required_output": {
                "verdict": "genuine, deceptive, or needs_review",
                "risk_score": "number from 0 to 1",
                "confidence": "number from 0 to 1",
                "summary": "short explanation",
                "reasons": ["specific reasons grounded in supplied content"],
                "website_findings": ["what the inspected page says or requests"],
                "image_findings": ["what the image evidence supports; use needs_review reasoning when pixels are not available"],
            },
        },
        ensure_ascii=True,
    )


def _response_content(payload: Any) -> str:
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise RuntimeError("The Groq investigation response was incomplete.") from error
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("The Groq investigation response was empty.")
    return content


def _parse_result(value: Any) -> InvestigatorResult:
    if not isinstance(value, dict):
        raise RuntimeError("The Groq investigation JSON was not an object.")
    verdict = value.get("verdict")
    if verdict not in {"genuine", "deceptive", "needs_review"}:
        raise RuntimeError("The Groq investigation returned an invalid verdict.")
    risk_score = _bounded_number(value.get("risk_score"), "risk_score")
    confidence = _bounded_number(value.get("confidence"), "confidence")
    summary = value.get("summary")
    reasons = value.get("reasons")
    findings = value.get("website_findings")
    if not isinstance(summary, str) or not summary.strip():
        raise RuntimeError("The Groq investigation returned no summary.")
    if not _string_list(reasons) or not _string_list(findings):
        raise RuntimeError("The Groq investigation returned invalid details.")
    return InvestigatorResult(
        verdict=verdict,
        risk_score=risk_score,
        confidence=confidence,
        summary=summary.strip(),
        reasons=tuple(reasons),
        website_findings=tuple(findings),
        provider="groq",
    )


def _bounded_number(value: Any, name: str) -> float:
    if not isinstance(value, (int, float)) or not 0 <= value <= 1:
        raise RuntimeError(f"The Groq investigation returned an invalid {name}.")
    return float(value)


def _string_list(value: Any) -> list[str] | None:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        return None
    return [item.strip() for item in value]


def _trace(message: str, *args: object) -> None:
    if os.getenv("ANALYSIS_TRACE", "").strip().lower() in {"1", "true", "yes", "on"}:
        logger.info(message, *args)

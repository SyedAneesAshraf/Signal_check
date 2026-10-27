"""End-to-end analysis for a manually collected verification case."""

from collections.abc import Callable
import logging

from app.schemas.common import (
    CaseAnalysisContract,
    CaseInputContract,
    ClaimContract,
    EvidenceContract,
    InputType,
    ModalitySignal,
    ProcessingStatus,
)
from app.services.case_store import VerificationCase
from app.services.correlation import correlate_texts
from app.services.fusion import fuse_signals
from app.services.image_analysis import assess_image
from app.services.investigator import investigate_case
from app.services.multimodal import extract_image_text
from app.services.phishing import assess_url


TextAnalyzer = Callable[[str], tuple[list[object], str]]
logger = logging.getLogger(__name__)


def analyze_case(
    case: VerificationCase,
    *,
    text_analyzer: TextAnalyzer,
) -> CaseAnalysisContract:
    """Analyze the available representations in a case and fuse their signals."""
    inputs = [
        CaseInputContract(
            input_id=item.input_id,
            input_type=InputType(item.input_type),
            created_at=item.created_at,
            content_hash=item.content_hash,
            text=item.text,
            source_url=item.source_url,
            file_name=item.file_name,
            mime_type=item.mime_type,
            size_bytes=item.size_bytes,
        )
        for item in case.inputs
    ]
    claims: list[ClaimContract] = []
    evidence: list[EvidenceContract] = []
    signals: list[ModalitySignal] = []
    text_items: list[tuple[str, str]] = []
    contradiction_score = 0.0
    phishing_score = 0.0
    image_anomaly_score = 0.0
    image_context: list[dict[str, object]] = []
    related_message_text = " ".join(
        item.text for item in case.inputs if item.text
    )

    for item in case.inputs:
        if item.source_url:
            text_items.append((item.input_id, item.source_url))
        if item.text:
            text_items.append((item.input_id, item.text))
            pipeline_claims, _ = text_analyzer(item.text)
            for result in pipeline_claims:
                claims.append(
                    ClaimContract(
                        claim_id=f"{item.input_id}_{result.claim.claim_id}",
                        claim_text=result.claim.claim_text,
                        source_input_ids=[item.input_id],
                        entities=result.claim.entities,
                        claim_type=result.claim.claim_type,
                        verification_status=result.status,
                    )
                )
                if result.status == "refuted":
                    contradiction_score = max(
                        contradiction_score,
                        max((entry.nli_score for entry in result.evidence), default=0.0),
                    )
                evidence.extend(
                    EvidenceContract(
                        evidence_id=f"{item.input_id}_{entry.passage_id}",
                        claim_id=f"{item.input_id}_{result.claim.claim_id}",
                        passage=entry.passage,
                        source_url=entry.source_url,
                        source_name=entry.source_name,
                        retrieval_score=max(0.0, min(1.0, entry.retrieval_similarity)),
                        nli_label=entry.nli_label,
                        nli_score=entry.nli_score,
                        source_type=entry.source_type,
                        source_quality=entry.source_quality,
                        source_quality_weight=entry.source_quality_weight,
                        published_date=entry.published_date,
                        retrieved_date=entry.retrieved_date,
                        provider=entry.provider,
                        domain=entry.domain,
                    )
                    for entry in result.evidence
                )

        if item.input_type == "url" and item.source_url:
            assessment = assess_url(item.source_url, related_message_text)
            phishing_score = max(phishing_score, assessment.risk_score)
            signals.append(
                ModalitySignal(
                    signal_id=f"{item.input_id}_phishing",
                    input_id=item.input_id,
                    modality=InputType.URL,
                    signal_type="phishing_risk",
                    status=ProcessingStatus.COMPLETED,
                    score=assessment.risk_score,
                    confidence=1.0,
                    details={
                        "status": assessment.status,
                        "indicators": list(assessment.indicators),
                    },
                )
            )

        if item.input_type == "image" and item.raw_content:
            image = assess_image(item.raw_content)
            ocr_text = ""
            try:
                ocr_text = extract_image_text(item.raw_content)
            except (OSError, RuntimeError, ValueError) as error:
                logger.warning(
                    "case_image_ocr_failed input_id=%s error=%s",
                    item.input_id,
                    type(error).__name__,
                )
            if ocr_text:
                text_items.append((item.input_id, ocr_text))
                pipeline_claims, _ = text_analyzer(ocr_text)
                for result in pipeline_claims:
                    claims.append(
                        ClaimContract(
                            claim_id=f"{item.input_id}_{result.claim.claim_id}",
                            claim_text=result.claim.claim_text,
                            source_input_ids=[item.input_id],
                            entities=result.claim.entities,
                            claim_type=result.claim.claim_type,
                            verification_status=result.status,
                        )
                    )
                    if result.status == "refuted":
                        contradiction_score = max(
                            contradiction_score,
                            max((entry.nli_score for entry in result.evidence), default=0.0),
                        )
                    evidence.extend(
                        EvidenceContract(
                            evidence_id=f"{item.input_id}_{entry.passage_id}",
                            claim_id=f"{item.input_id}_{result.claim.claim_id}",
                            passage=entry.passage,
                            source_url=entry.source_url,
                            source_name=entry.source_name,
                            retrieval_score=max(0.0, min(1.0, entry.retrieval_similarity)),
                            nli_label=entry.nli_label,
                            nli_score=entry.nli_score,
                            source_type=entry.source_type,
                            source_quality=entry.source_quality,
                            source_quality_weight=entry.source_quality_weight,
                            published_date=entry.published_date,
                            retrieved_date=entry.retrieved_date,
                            provider=entry.provider,
                            domain=entry.domain,
                        )
                        for entry in result.evidence
                    )
            image_context.append(
                {
                    "input_id": item.input_id,
                    "ocr_text": ocr_text,
                    "width": image.width,
                    "height": image.height,
                    "format": image.format,
                    "has_metadata": image.has_metadata,
                    "perceptual_hash": image.perceptual_hash,
                    "visual_truth_status": (
                        "needs_review"
                        if not ocr_text
                        else "text_extracted_only"
                    ),
                }
            )
            signals.append(
                ModalitySignal(
                    signal_id=f"{item.input_id}_image",
                    input_id=item.input_id,
                    modality=InputType.IMAGE,
                    signal_type="image_metadata",
                    status=ProcessingStatus.COMPLETED,
                    score=0.0,
                    confidence=1.0,
                    details={
                        "width": image.width,
                        "height": image.height,
                        "format": image.format,
                        "has_metadata": image.has_metadata,
                        "perceptual_hash": image.perceptual_hash,
                        "ocr_text": ocr_text,
                        "visual_truth_status": (
                            "needs_review" if not ocr_text else "text_extracted_only"
                        ),
                    },
                )
            )

    correlation = correlate_texts(text_items)
    if text_items:
        signals.append(
            ModalitySignal(
                signal_id=f"{case.case_id}_correlation",
                input_id=case.case_id,
                modality=InputType.TEXT,
                signal_type="cross_input_coordination",
                status=ProcessingStatus.COMPLETED,
                score=correlation.score,
                confidence=1.0,
                details={
                    "shared_urls": list(correlation.shared_urls),
                    "shared_entities": list(correlation.shared_entities),
                    "similar_pairs": [list(pair) for pair in correlation.similar_pairs],
                },
            )
        )

    fusion = fuse_signals(
        claim_contradiction=contradiction_score,
        phishing=phishing_score,
        coordination=correlation.score,
        image_anomaly=image_anomaly_score,
        has_evidence=bool(evidence),
    )
    ai_investigation = None
    ai_investigation_error = None
    try:
        ai_investigation = investigate_case(
            message_text=related_message_text,
            urls=[item.source_url for item in case.inputs if item.source_url],
            claims=[claim.model_dump() for claim in claims],
            evidence=[item.model_dump() for item in evidence],
            images=image_context,
        )
    except RuntimeError as error:
        logger.warning(
            "ai_investigation_unavailable error=%s",
            type(error).__name__,
        )
        ai_investigation_error = {
            "provider": "groq",
            "status": "unavailable",
            "message": str(error),
        }
    verdict = fusion.verdict
    risk_score = fusion.risk_score
    image_requires_review = any(
        image["visual_truth_status"] == "needs_review" for image in image_context
    )
    if ai_investigation is not None and (
        ai_investigation.verdict != "genuine"
        or bool(evidence)
        or ai_investigation.confidence >= 0.8
    ):
        verdict = ai_investigation.verdict
        risk_score = ai_investigation.risk_score
    if image_requires_review and verdict == "genuine":
        verdict = "needs_review"
        risk_score = max(risk_score, 0.5)
    if verdict == "deceptive":
        decision_basis = "Strong phishing, contradiction, or coordinated-risk signals crossed the decision threshold."
        recommended_action = "Do not trust the content or submit credentials; verify through an independent official channel."
        deception_risk = "high"
    elif evidence:
        decision_basis = "The available claim evidence did not indicate deception, but this is not proof of authenticity."
        recommended_action = "Review the linked sources and confirm the claim through an independent trusted source."
        deception_risk = "low"
    else:
        decision_basis = "There was not enough relevant, source-linked evidence to make a reliable decision."
        recommended_action = "Treat the content as unverified and seek confirmation from an independent trusted source."
        deception_risk = "unknown"
    if claims and all(claim.verification_status == "supported" for claim in claims):
        content_assessment = "supported"
    elif any(claim.verification_status == "refuted" for claim in claims):
        content_assessment = "refuted"
    else:
        content_assessment = "insufficient_evidence"
    limitations = [
        "Risk scores are prototype signal scores, not calibrated probabilities.",
        "A missing or inaccessible webpage is not evidence that the content is genuine.",
        "Image analysis currently verifies OCR text and metadata; it does not prove visual authenticity or detect deepfakes.",
    ]
    investigation_payload = (
        ai_investigation.__dict__ if ai_investigation is not None else ai_investigation_error
    )
    return CaseAnalysisContract(
        case_id=case.case_id,
        status=ProcessingStatus.COMPLETED,
        inputs=inputs,
        claims=claims,
        signals=signals,
        evidence=evidence,
        verdict=verdict,
        risk_score=risk_score,
        ai_investigation=investigation_payload,
        decision_basis=decision_basis,
        recommended_action=recommended_action,
        limitations=limitations,
        content_assessment=content_assessment,
        deception_risk=deception_risk,
        intent_assessment="not_determinable_from_content",
    )

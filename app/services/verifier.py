"""Natural-language-inference signals for claim/evidence pairs."""

from dataclasses import dataclass, field
import re
from typing import Any, Protocol


@dataclass(frozen=True)
class VerificationSignal:
    label: str
    score: float
    premise: str
    hypothesis: str
    class_scores: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceAssessment:
    signal: VerificationSignal
    similarity: float
    source_quality: str


_LIFE_STATUS_WORDS = (
    "alive",
    "dead",
    "died",
    "dies",
    "die",
    "dying",
    "death",
    "killed",
    "deceased",
    "survived",
)


def is_directly_relevant(claim: str, evidence: str) -> bool:
    """Reject keyword matches that do not describe the claim's subject."""
    claim_words = set(re.findall(r"[a-z0-9]+", claim.lower()))
    evidence_words = set(re.findall(r"[a-z0-9]+", evidence.lower()))
    if not claim_words or not evidence_words:
        return False

    subject_match = re.match(r"\s*([a-z][a-z0-9'-]*)", claim.lower())
    predicate_is_life_status = any(
        word in claim_words for word in _LIFE_STATUS_WORDS
    )
    if not subject_match or not predicate_is_life_status:
        return True

    subject = re.escape(subject_match.group(1))
    life_words = "|".join(_LIFE_STATUS_WORDS)
    direct_relation = re.compile(
        rf"(?:\b(?:president|donald)\s+)?\b{subject}\b\s+"
        rf"(?:(?:is|was|remains|appears|has been|has|did|does)\s+)?"
        rf"(?:not\s+)?(?:still\s+)?(?:dead|alive|killed|die|dying|died|dies|survived|deceased)\b"
        rf"|\b(?:death|killing|passing)\s+of\s+"
        rf"(?:\b(?:president|donald)\s+)?\b{subject}\b"
        rf"|\b{subject}\b['’]s\s+(?:death|killing|passing)\b",
        re.IGNORECASE,
    )
    return bool(direct_relation.search(evidence))


class NLIModel(Protocol):
    def __call__(self, premise: str, hypothesis: str) -> dict[str, Any]:
        """Return model labels and scores for a premise/hypothesis pair."""


class BartNLIModel:
    """Run facebook/bart-large-mnli without assuming label indices."""

    def __init__(self, model_name: str = "facebook/bart-large-mnli") -> None:
        from transformers import pipeline

        self._classifier = pipeline("text-classification", model=model_name, device=-1)

    def __call__(self, premise: str, hypothesis: str) -> dict[str, Any]:
        result = self._classifier(
            premise,
            text_pair=hypothesis,
            top_k=None,
        )
        if result and isinstance(result[0], dict):
            result = [result]
        if not result or not isinstance(result[0], list):
            raise ValueError("NLI model returned an unexpected result.")
        labels = {str(item["label"]): float(item["score"]) for item in result[0]}
        return {"labels": labels}


def verify_claim(
    claim: str,
    evidence: str,
    model: NLIModel,
) -> VerificationSignal:
    """Compare evidence as premise against claim as hypothesis."""
    if not claim.strip():
        raise ValueError("claim must not be empty.")
    if not evidence.strip():
        raise ValueError("evidence must not be empty.")

    raw_result = model(evidence, claim)
    labels = raw_result.get("labels")
    if not isinstance(labels, dict) or not labels:
        raise ValueError("NLI model response must contain non-empty labels.")

    normalized = {_normalize_label(label): float(score) for label, score in labels.items()}
    if any(not isinstance(score, (int, float)) or not 0 <= score <= 1 for score in normalized.values()):
        raise ValueError("NLI model returned invalid class scores.")
    label, score = max(normalized.items(), key=lambda item: item[1])
    if label not in {"entailment", "contradiction", "neutral"}:
        raise ValueError(f"Unsupported NLI label: {label}")
    return VerificationSignal(
        label=label,
        score=float(score),
        premise=evidence,
        hypothesis=claim,
        class_scores=normalized,
    )


def aggregate_status(signals: list[VerificationSignal], minimum_score: float = 0.5) -> str:
    """Map multiple NLI signals to a cautious application status."""
    if not signals:
        return "insufficient_evidence"
    confident = [signal for signal in signals if signal.score >= minimum_score]
    if not confident:
        return "insufficient_evidence"
    has_support = any(signal.label == "entailment" for signal in confident)
    has_refutation = any(signal.label == "contradiction" for signal in confident)
    if has_support and has_refutation:
        return "conflicting_evidence"
    if has_support:
        return "supported"
    if has_refutation:
        return "refuted"
    return "insufficient_evidence"


def aggregate_evidence_status(
    assessments: list[EvidenceAssessment],
    *,
    minimum_score: float = 0.5,
    minimum_weighted_score: float = 0.45,
) -> str:
    """Aggregate NLI signals after accounting for relevance and source quality."""
    if not assessments:
        return "insufficient_evidence"
    if not 0 <= minimum_score <= 1 or not 0 <= minimum_weighted_score <= 1:
        raise ValueError("aggregation thresholds must be between zero and one.")

    confident = [
        assessment
        for assessment in assessments
        if _is_usable_assessment(assessment, minimum_score)
    ]
    weighted = [
        (
            assessment,
            assessment.signal.score
            * assessment.similarity
            * _source_quality_weight(assessment.source_quality),
        )
        for assessment in confident
    ]
    usable = [
        (assessment, score)
        for assessment, score in weighted
        if score >= minimum_weighted_score
    ]
    if not usable:
        return "insufficient_evidence"
    has_support = any(
        assessment.signal.label == "entailment" for assessment, _ in usable
    )
    has_refutation = any(
        assessment.signal.label == "contradiction" for assessment, _ in usable
    )
    if has_support and has_refutation:
        return "conflicting_evidence"
    if has_support:
        return "supported"
    if has_refutation:
        return "refuted"
    return "insufficient_evidence"


def _is_usable_assessment(
    assessment: EvidenceAssessment,
    minimum_score: float,
) -> bool:
    """Require stronger alignment before treating generic context as refutation."""
    if assessment.signal.score < minimum_score or assessment.similarity < 0:
        return False
    if assessment.signal.label != "contradiction":
        return True
    premise = assessment.signal.premise.lower()
    explicit_negation = re.search(
        r"\b(?:not|n't|false|incorrect|debunk(?:ed)?|myth|no evidence)\b",
        premise,
    )
    if explicit_negation:
        return True
    return assessment.signal.score >= 0.9 and assessment.similarity >= 0.8


def _source_quality_weight(source_quality: str) -> float:
    return {
        "official": 1.0,
        "reputable": 0.95,
        "unknown": 0.8,
        "context_only": 0.5,
    }.get(source_quality, 0.8)


def _normalize_label(label: str) -> str:
    normalized = label.lower().replace("_", " ").replace("-", " ").strip()
    aliases = {
        "label 0": "contradiction",
        "label 1": "neutral",
        "label 2": "entailment",
    }
    return aliases.get(normalized, normalized)

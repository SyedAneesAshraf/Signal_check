"""Decision fusion for the first manual-case demonstration."""

from dataclasses import dataclass


@dataclass(frozen=True)
class FusionResult:
    verdict: str
    risk_score: float


def fuse_signals(
    *,
    claim_contradiction: float = 0.0,
    phishing: float = 0.0,
    coordination: float = 0.0,
    image_anomaly: float = 0.0,
    has_evidence: bool = False,
) -> FusionResult:
    values = (claim_contradiction, phishing, coordination, image_anomaly)
    if any(not 0 <= value <= 1 for value in values):
        raise ValueError("fusion signals must be between zero and one.")
    risk = min(
        1.0,
        0.7 * claim_contradiction
        + 0.8 * phishing
        + 0.2 * coordination
        + 0.1 * image_anomaly,
    )
    if risk >= 0.6:
        verdict = "deceptive"
    elif not has_evidence:
        verdict = "needs_review"
    else:
        verdict = "genuine"
    return FusionResult(verdict, risk)

import pytest

from app.services.verifier import (
    EvidenceAssessment,
    VerificationSignal,
    aggregate_evidence_status,
    aggregate_status,
    is_directly_relevant,
    verify_claim,
)


class StubNLI:
    def __init__(self, labels: dict[str, float]) -> None:
        self.labels = labels
        self.arguments: tuple[str, str] | None = None

    def __call__(self, premise: str, hypothesis: str) -> dict[str, dict[str, float]]:
        self.arguments = (premise, hypothesis)
        return {"labels": self.labels}


def test_uses_evidence_as_premise_and_claim_as_hypothesis() -> None:
    model = StubNLI({"entailment": 0.91, "neutral": 0.06, "contradiction": 0.03})

    signal = verify_claim("The claim", "The evidence", model)

    assert signal.label == "entailment"
    assert signal.score == 0.91
    assert model.arguments == ("The evidence", "The claim")


def test_maps_model_label_indices_explicitly() -> None:
    model = StubNLI({"LABEL_0": 0.10, "LABEL_1": 0.20, "LABEL_2": 0.70})

    signal = verify_claim("The claim", "The evidence", model)

    assert signal.label == "entailment"


@pytest.mark.parametrize(
    ("signals", "expected"),
    [
        ([], "insufficient_evidence"),
        ([VerificationSignal("neutral", 0.95, "p", "h")], "insufficient_evidence"),
        ([VerificationSignal("entailment", 0.90, "p", "h")], "supported"),
        ([VerificationSignal("contradiction", 0.90, "p", "h")], "refuted"),
        (
            [
                VerificationSignal("entailment", 0.90, "p", "h"),
                VerificationSignal("contradiction", 0.85, "p", "h"),
            ],
            "conflicting_evidence",
        ),
    ],
)
def test_aggregate_status_is_cautious(signals, expected) -> None:
    assert aggregate_status(signals) == expected


def test_empty_claim_or_evidence_is_rejected() -> None:
    with pytest.raises(ValueError, match="claim"):
        verify_claim("", "evidence", StubNLI({}))
    with pytest.raises(ValueError, match="evidence"):
        verify_claim("claim", " ", StubNLI({}))


def test_evidence_aggregation_requires_relevance_and_source_quality() -> None:
    supported = VerificationSignal("entailment", 0.95, "p", "h")

    assert aggregate_evidence_status(
        [EvidenceAssessment(supported, 0.2, "official")]
    ) == "insufficient_evidence"
    assert aggregate_evidence_status(
        [EvidenceAssessment(supported, 0.6, "official")]
    ) == "supported"
    assert aggregate_evidence_status(
        [EvidenceAssessment(supported, 0.6, "context_only")]
    ) == "insufficient_evidence"


def test_keyword_overlap_is_not_direct_evidence_for_life_status_claim() -> None:
    assert not is_directly_relevant(
        "Trump is dead",
        "Trump ally Lindsey Graham dies at 71.",
    )
    assert not is_directly_relevant(
        "Trump is dead",
        "Trump says the Anti-Weaponization Fund is dead.",
    )
    assert is_directly_relevant(
        "Trump is dead",
        "Officials confirmed that Trump died on Tuesday.",
    )
    assert is_directly_relevant(
        "Trump is dead",
        "The death of President Trump was confirmed by officials.",
    )
    assert is_directly_relevant(
        "Trump is dead",
        "Officials confirmed Trump's death.",
    )
    assert is_directly_relevant(
        "Trump is dead",
        "Fact checkers say Donald Trump did not die.",
    )
    assert not is_directly_relevant(
        "Trump is dead",
        "Trump ally Lindsey Graham died after a brief illness.",
    )

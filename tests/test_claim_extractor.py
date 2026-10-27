import pytest

from app.services.claim_extractor import claims_to_dicts, extract_claims


def test_extracts_multiple_domain_independent_claims_and_entities() -> None:
    claims = extract_claims(
        "The Central Bank announced a new account policy. "
        "Customers must verify accounts at https://example.com/verify."
    )

    assert [claim.claim_id for claim in claims] == ["claim_1", "claim_2"]
    assert claims[0].claim_text == "The Central Bank announced a new account policy"
    assert "Central Bank" in claims[0].entities
    assert claims[1].claim_type == "factual"
    assert "https://example.com/verify" in claims[1].entities


def test_question_is_not_presented_as_factual_claim() -> None:
    claims = extract_claims("Why did the university cancel the examination?")

    assert len(claims) == 1
    assert claims[0].claim_type == "non_factual"


def test_results_are_json_compatible() -> None:
    result = claims_to_dicts(extract_claims("NASA published a climate report."))

    assert result == [
        {
            "claim_id": "claim_1",
            "claim_text": "NASA published a climate report",
            "entities": ["NASA"],
            "claim_type": "factual",
        }
    ]


@pytest.mark.parametrize("value", ["", "   ", None])
def test_empty_input_is_rejected(value: str | None) -> None:
    with pytest.raises(ValueError, match="non-empty"):
        extract_claims(value)  # type: ignore[arg-type]

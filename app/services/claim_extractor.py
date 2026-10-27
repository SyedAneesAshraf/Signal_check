"""Transparent baseline for extracting claims and entities from text."""

from dataclasses import asdict, dataclass
import re


@dataclass(frozen=True)
class ExtractedClaim:
    claim_id: str
    claim_text: str
    entities: list[str]
    claim_type: str


_SENTENCE_PATTERN = re.compile(r"[^.!?]+(?:[.!?]+|$)")
_ENTITY_PATTERN = re.compile(
    r"\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*|[A-Z]{2,}(?:\s+[A-Z]{2,})*)\b"
)
_URL_PATTERN = re.compile(r"\b(?:https?://|www\.)[^\s]+", re.IGNORECASE)
_DATE_PATTERN = re.compile(
    r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|"
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{1,2}(?:,\s*\d{4})?)\b"
)
_NUMBER_PATTERN = re.compile(r"\b(?:\d+(?:[.,]\d+)?%?|[$€£₹]\s?\d+(?:[.,]\d+)?)\b")
_NON_FACTUAL_PREFIXES = (
    "how ",
    "why ",
    "when ",
    "where ",
    "who ",
    "can you ",
    "please ",
    "i think ",
    "i feel ",
    "in my opinion ",
)


def extract_claims(text: str) -> list[ExtractedClaim]:
    """Extract non-empty candidate claims without verifying them."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text must be a non-empty string.")

    urls: list[str] = []

    def replace_url(match: re.Match[str]) -> str:
        urls.append(match.group(0))
        return f"URLTOKEN{len(urls) - 1}"

    protected_text = _URL_PATTERN.sub(replace_url, text)
    claims: list[ExtractedClaim] = []
    seen_claims: set[str] = set()
    for sentence in _SENTENCE_PATTERN.findall(protected_text):
        normalized = " ".join(sentence.split()).strip(" -")
        if not normalized:
            continue
        for index, url in enumerate(urls):
            normalized = normalized.replace(f"URLTOKEN{index}", url)
        claim_text = normalized.rstrip(".!?")
        if len(re.sub(r"[^A-Za-z0-9]+", "", claim_text)) < 3:
            continue
        claim_key = claim_text.casefold()
        if claim_key in seen_claims:
            continue
        seen_claims.add(claim_key)
        claims.append(
            ExtractedClaim(
                claim_id=f"claim_{len(claims) + 1}",
                claim_text=claim_text,
                entities=_extract_entities(normalized),
                claim_type=_classify_claim(normalized),
            )
        )
    if not claims:
        raise ValueError("No candidate claims could be extracted.")
    return claims


def claims_to_dicts(claims: list[ExtractedClaim]) -> list[dict[str, object]]:
    """Convert validated extractor results to JSON-compatible dictionaries."""
    return [asdict(claim) for claim in claims]


def _extract_entities(sentence: str) -> list[str]:
    candidates = _ENTITY_PATTERN.findall(sentence)
    candidates.extend(_URL_PATTERN.findall(sentence))
    candidates.extend(_DATE_PATTERN.findall(sentence))
    candidates.extend(_NUMBER_PATTERN.findall(sentence))
    entities: list[str] = []
    for candidate in candidates:
        clean_candidate = candidate.rstrip(".,!?;:)")
        clean_candidate = re.sub(r"^(?:The|A|An)\s+", "", clean_candidate)
        if clean_candidate and clean_candidate not in entities:
            entities.append(clean_candidate)
    return entities


def _classify_claim(sentence: str) -> str:
    lowered = sentence.lower().strip()
    if lowered.startswith(_NON_FACTUAL_PREFIXES) or sentence.rstrip().endswith("?"):
        return "non_factual"
    return "factual"

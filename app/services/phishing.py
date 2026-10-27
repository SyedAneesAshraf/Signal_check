"""Controlled URL phishing-risk signals for the research prototype."""

from dataclasses import dataclass
import re
from urllib.parse import urlsplit


@dataclass(frozen=True)
class PhishingAssessment:
    status: str
    risk_score: float
    indicators: tuple[str, ...]


_SUSPICIOUS_TLDS = {".zip", ".mov", ".click", ".top", ".gq", ".tk"}
_URGENT_WORDS = {
    "urgent",
    "immediately",
    "verify",
    "suspended",
    "closed",
    "today",
    "expiry",
    "expire",
    "click",
    "update",
}
_SENSITIVE_WORDS = {
    "login",
    "signin",
    "verify",
    "password",
    "credential",
    "payment",
    "account",
    "pin",
}
_BRANDS = {"apple", "amazon", "bank", "paypal", "microsoft", "google", "dhl", "fedex"}
_FINANCIAL_WORDS = {"bank", "account", "pin", "card", "payment"}


def assess_url(url: str, page_text: str = "") -> PhishingAssessment:
    """Return deterministic URL/page risk signals without external API dependencies."""
    parsed = urlsplit(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("url must be an absolute http or https URL.")

    indicators: list[str] = []
    score = 0.0
    hostname = parsed.hostname.lower()
    lowered_url = url.lower()
    lowered_page = page_text.lower()

    if parsed.scheme != "https":
        indicators.append("unencrypted_http")
        score += 0.15
    if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", hostname):
        indicators.append("ip_address_host")
        score += 0.3
    if hostname.count(".") >= 3:
        indicators.append("many_subdomains")
        score += 0.15
    if any(hostname.endswith(tld) for tld in _SUSPICIOUS_TLDS):
        indicators.append("suspicious_top_level_domain")
        score += 0.2
    if "@" in parsed.netloc:
        indicators.append("embedded_credentials")
        score += 0.25
    if any(word in lowered_url for word in _SENSITIVE_WORDS):
        indicators.append("sensitive_action_in_url")
        score += 0.15

    matched_brands = [brand for brand in _BRANDS if brand in hostname]
    if matched_brands and not any(hostname.endswith(f".{brand}.com") for brand in matched_brands):
        indicators.append("brand_name_in_unverified_domain")
        score += 0.25

    urgent_matches = _URGENT_WORDS.intersection(re.findall(r"[a-z]+", lowered_page))
    if urgent_matches:
        indicators.append("urgent_message_language")
        score += 0.2
    sensitive_matches = {"password", "credential", "payment", "account", "pin"}.intersection(
        re.findall(r"[a-z]+", lowered_page)
    )
    if sensitive_matches:
        indicators.append("sensitive_request_on_page")
        score += 0.25
    message_words = set(re.findall(r"[a-z]+", lowered_page))
    if _FINANCIAL_WORDS.intersection(message_words):
        indicators.append("financial_account_message")
        score += 0.2
    if {"click", "update"}.issubset(message_words) and sensitive_matches:
        indicators.append("credential_update_call_to_action")
        score += 0.15

    risk_score = min(1.0, score)
    status = "likely_phishing" if risk_score >= 0.6 else (
        "suspicious" if risk_score >= 0.3 else "likely_safe"
    )
    return PhishingAssessment(status, risk_score, tuple(dict.fromkeys(indicators)))

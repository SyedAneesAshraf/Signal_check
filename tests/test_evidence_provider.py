import pytest

from app.services.evidence_provider import (
    LocalEvidenceProvider,
    LiveNewsEvidenceProvider,
    RetrievedEvidence,
    TavilyEvidenceProvider,
    _canonical_url,
)


def test_tavily_provider_requires_api_key() -> None:
    with pytest.raises(ValueError, match="TAVILY_API_KEY"):
        TavilyEvidenceProvider(api_key="")


def test_canonical_url_removes_tracking_query_and_fragment() -> None:
    assert _canonical_url("HTTPS://Example.com/page/?utm_source=test#section") == (
        "https://example.com/page"
    )


def test_local_evidence_is_marked_official() -> None:
    from app.services.corpus import EvidencePassage

    passage = EvidencePassage(
        "p1", "d1", "Title", "Agency", "https://example.com", None,
        "2026-10-27", "official_reference", "Official", "Text",
    )
    class Index:
        def search(self, query, embedder, top_k):
            return [(passage, 0.8)]
    result = LocalEvidenceProvider(Index(), object()).search("claim", top_k=1)[0]
    assert result.source_quality == "official"


def test_live_news_provider_parses_feed(monkeypatch) -> None:
    class Response:
        content = b"""<rss><channel><item>
          <title>Trump is alive, officials say</title>
          <link>https://example.com/story</link>
          <description>Officials said the claim is false.</description>
          <source>Example News</source>
        </item></channel></rss>"""

        def raise_for_status(self):
            return None

    monkeypatch.setattr("httpx.get", lambda *args, **kwargs: Response())
    result = LiveNewsEvidenceProvider().search("Trump is dead", top_k=1)
    assert result[0].provider == "live"
    assert result[0].source_name == "Example News"
    assert result[0].passage == "Officials said the claim is false."


def test_live_news_provider_returns_empty_for_empty_feed(monkeypatch) -> None:
    class Response:
        content = b"<rss><channel /></rss>"
        status_code = 200

        def raise_for_status(self):
            return None

    monkeypatch.setattr("httpx.get", lambda *args, **kwargs: Response())
    assert LiveNewsEvidenceProvider().search("no matching story", top_k=3) == []


def test_live_news_provider_surfaces_request_failure(monkeypatch) -> None:
    import httpx

    def fail(*args, **kwargs):
        raise httpx.ReadTimeout("timed out")

    monkeypatch.setattr("httpx.get", fail)
    with pytest.raises(RuntimeError, match="Live news search failed"):
        LiveNewsEvidenceProvider().search("claim", top_k=1)

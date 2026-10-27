from pathlib import Path

from app.core.preflight import run_preflight


def test_live_preflight_does_not_require_local_index(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("EVIDENCE_PROVIDER", "live")

    checks = run_preflight(tmp_path)

    names = {check.name for check in checks}
    assert "data/index/evidence.faiss" not in names
    assert "data/index/metadata.json" not in names
    assert all(check.ok for check in checks)


def test_local_preflight_reports_missing_index(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("EVIDENCE_PROVIDER", "local")

    checks = run_preflight(tmp_path)

    missing = {
        check.name for check in checks if not check.ok
    }
    assert "data/index/evidence.faiss" in missing
    assert "data/index/metadata.json" in missing

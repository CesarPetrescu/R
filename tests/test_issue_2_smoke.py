from pathlib import Path


def test_issue_2_smoke_marker_records_issue_watcher_round_trip():
    marker = Path("tests/fixtures/issue-2-smoke.txt")

    assert marker.read_text(encoding="utf-8").strip() == "Issue #2 AI issue watcher smoke test completed."

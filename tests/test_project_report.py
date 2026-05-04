import json
import os
import subprocess
import sys
from pathlib import Path

from r_project.report import analyze_project


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_analyze_project_reports_backlog_counts_and_next_item(tmp_path):
    write(tmp_path / "README.md", "# Demo\n")
    write(
        tmp_path / "status" / "missing-features.md",
        """# Missing Features

## P0
- [x] Completed scaffold.
- [ ] Add CLI entry point.
- [ ] Add examples.
""",
    )
    write(
        tmp_path / "status" / "stuck.md",
        """# Stuck

## Active blockers
- None verified.
""",
    )

    report = analyze_project(tmp_path)

    assert report.project_name == "Demo"
    assert report.completed_backlog_items == 1
    assert report.open_backlog_items == 2
    assert report.next_backlog_item == "Add CLI entry point."
    assert report.has_active_blockers is False


def test_analyze_project_detects_active_blockers(tmp_path):
    write(tmp_path / "README.md", "# Blocked Demo\n")
    write(tmp_path / "status" / "missing-features.md", "- [ ] Resume work.\n")
    write(
        tmp_path / "status" / "stuck.md",
        """# Stuck

## Active blockers
- Push authentication is missing.
""",
    )

    report = analyze_project(tmp_path)

    assert report.has_active_blockers is True
    assert report.active_blockers == ["Push authentication is missing."]


def test_cli_outputs_json_report_for_repository(tmp_path):
    write(tmp_path / "README.md", "# CLI Demo\n")
    write(tmp_path / "status" / "missing-features.md", "- [x] Scaffold.\n- [ ] Ship feature.\n")
    write(tmp_path / "status" / "stuck.md", "## Active blockers\n- None.\n")

    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}
    result = subprocess.run(
        [sys.executable, "-m", "r_project", "--root", str(tmp_path), "--json"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    payload = json.loads(result.stdout)
    assert payload["project_name"] == "CLI Demo"
    assert payload["completed_backlog_items"] == 1
    assert payload["open_backlog_items"] == 1
    assert payload["next_backlog_item"] == "Ship feature."

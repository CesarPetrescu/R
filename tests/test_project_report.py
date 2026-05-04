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


def test_analyze_project_groups_backlog_counts_by_priority_heading(tmp_path):
    write(tmp_path / "README.md", "# Priority Demo\n")
    write(
        tmp_path / "status" / "missing-features.md",
        """# Missing Features

## P0 — make the repo real
- [x] Create scaffold.
- [ ] Add tests.

## P1 — implementation depth
- [x] Add JSON output.
- [ ] Add priority grouping.
- [ ] Add installer docs.

## P2 — project quality
- [ ] Add release notes.
""",
    )
    write(tmp_path / "status" / "stuck.md", "## Active blockers\n- None.\n")

    report = analyze_project(tmp_path)

    assert report.priority_backlog_groups == {
        "P0": {"completed": 1, "open": 1, "next_item": "Add tests."},
        "P1": {"completed": 1, "open": 2, "next_item": "Add priority grouping."},
        "P2": {"completed": 0, "open": 1, "next_item": "Add release notes."},
    }


def test_report_formats_markdown_for_human_status_pages(tmp_path):
    write(tmp_path / "README.md", "# Markdown Demo\n")
    write(
        tmp_path / "status" / "missing-features.md",
        """# Missing Features
## P1
- [x] Finish scaffold.
- [ ] Add markdown output.
""",
    )
    write(
        tmp_path / "status" / "stuck.md",
        """# Stuck
## Active blockers
- Awaiting deploy key.
""",
    )

    markdown = analyze_project(tmp_path).to_markdown()

    assert markdown == "\n".join(
        [
            "# Markdown Demo Readiness Report",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
            "| Completed backlog items | 1 |",
            "| Open backlog items | 1 |",
            "| Active blockers | 1 |",
            "",
            "## Backlog by priority",
            "",
            "| Priority | Completed | Open | Next item |",
            "| --- | ---: | ---: | --- |",
            "| P1 | 1 | 1 | Add markdown output. |",
            "",
            "## Next backlog item",
            "",
            "Add markdown output.",
            "",
            "## Active blockers",
            "",
            "- Awaiting deploy key.",
        ]
    )


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


def test_cli_outputs_markdown_report_for_repository(tmp_path):
    fixture_root = Path("tests/fixtures/readiness-repo")
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [sys.executable, "-m", "r_project", "--root", str(fixture_root), "--markdown"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.stdout.startswith("# Fixture Repo Readiness Report\n")
    assert "| Completed backlog items | 2 |" in result.stdout
    assert "| Open backlog items | 2 |" in result.stdout
    assert "Document expected fixture reports." in result.stdout


def test_cli_fail_on_blockers_returns_nonzero_when_active_blockers_exist(tmp_path):
    write(tmp_path / "README.md", "# Blocked CLI Demo\n")
    write(tmp_path / "status" / "missing-features.md", "- [ ] Resume work.\n")
    write(tmp_path / "status" / "stuck.md", "## Active blockers\n- Deploy key lacks write access.\n")

    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}
    result = subprocess.run(
        [sys.executable, "-m", "r_project", "--root", str(tmp_path), "--json", "--fail-on-blockers"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["has_active_blockers"] is True
    assert payload["active_blockers"] == ["Deploy key lacks write access."]
    assert result.stderr == ""

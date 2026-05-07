import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

from r_project.report import analyze_project


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_repository_declares_strong_copyleft_license():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    license_text = Path("LICENSE").read_text(encoding="utf-8")

    assert pyproject["project"]["license"] == "AGPL-3.0-or-later"
    assert license_text.startswith("GNU AFFERO GENERAL PUBLIC LICENSE")
    assert "Version 3, 19 November 2007" in license_text
    assert "Appropriate Legal Notices" in license_text


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


def _readme_fenced_block(language: str) -> str:
    readme = Path("README.md").read_text(encoding="utf-8")
    start_marker = f"```{language}\n"
    start = readme.index(start_marker) + len(start_marker)
    end = readme.index("\n```", start)
    return readme[start:end]


def test_readme_json_example_matches_current_cli_output():
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [sys.executable, "-m", "r_project", "--root", ".", "--json"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert _readme_fenced_block("json") == result.stdout.strip()
    assert result.stderr == ""


def test_readme_markdown_example_matches_current_cli_output():
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [sys.executable, "-m", "r_project", "--root", ".", "--markdown"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert _readme_fenced_block("markdown") == result.stdout.strip()
    assert result.stderr == ""


def test_cli_check_readme_examples_succeeds_when_examples_match_current_output():
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [sys.executable, "-m", "r_project", "--root", ".", "--check-readme-examples"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 0
    assert result.stdout == "README examples match current CLI output.\n"
    assert result.stderr == ""


def test_cli_generates_readme_example_blocks_from_current_report(tmp_path):
    write(tmp_path / "README.md", "# Generator Demo\n")
    write(
        tmp_path / "status" / "missing-features.md",
        """# Missing Features
## P1
- [x] Build report.
- [ ] Add generated examples.
""",
    )
    write(tmp_path / "status" / "stuck.md", "## Active blockers\n- None.\n")
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [sys.executable, "-m", "r_project", "--root", str(tmp_path), "--generate-readme-examples"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    json_output = json.dumps(analyze_project(tmp_path).to_dict(), sort_keys=True)
    markdown_output = analyze_project(tmp_path).to_markdown()
    assert result.stdout == f"```json\n{json_output}\n```\n\n```markdown\n{markdown_output}\n```\n"
    assert result.stderr == ""


def test_cli_writes_readme_example_blocks_in_place(tmp_path):
    write(
        tmp_path / "README.md",
        """# Writer Demo

Intro stays.

```json
{}
```

Between stays.

```markdown
old report
```

Tail stays.
""",
    )
    write(
        tmp_path / "status" / "missing-features.md",
        """# Missing Features
## P1
- [x] Build report.
- [ ] Add written examples.
""",
    )
    write(tmp_path / "status" / "stuck.md", "## Active blockers\n- None.\n")
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [sys.executable, "-m", "r_project", "--root", str(tmp_path), "--write-readme-examples"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    json_output = json.dumps(analyze_project(tmp_path).to_dict(), sort_keys=True)
    markdown_output = analyze_project(tmp_path).to_markdown()
    assert result.stdout == "Updated README JSON and Markdown example fences.\n"
    assert result.stderr == ""
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == f"""# Writer Demo

Intro stays.

```json
{json_output}
```

Between stays.

```markdown
{markdown_output}
```

Tail stays.
"""


def test_cli_dry_runs_readme_example_writer_without_modifying_readme(tmp_path):
    original_readme = """# Dry Run Demo

Intro stays.

```json
{}
```

Between stays.

```markdown
old report
```

Tail stays.
"""
    write(tmp_path / "README.md", original_readme)
    write(
        tmp_path / "status" / "missing-features.md",
        """# Missing Features
## P1
- [x] Build report.
- [ ] Preview written examples.
""",
    )
    write(tmp_path / "status" / "stuck.md", "## Active blockers\n- None.\n")
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--root",
            str(tmp_path),
            "--write-readme-examples",
            "--dry-run-readme-examples",
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    json_output = json.dumps(analyze_project(tmp_path).to_dict(), sort_keys=True)
    markdown_output = analyze_project(tmp_path).to_markdown()
    assert result.stdout == f"""# Dry Run Demo

Intro stays.

```json
{json_output}
```

Between stays.

```markdown
{markdown_output}
```

Tail stays.
"""
    assert result.stderr == ""
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == original_readme


def test_cli_outputs_fixture_backed_memory_threshold_demo():
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}
    expected = Path("tests/fixtures/memory-threshold-violations.md").read_text(encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "r_project", "--memory-threshold-demo"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.stdout == expected
    assert result.stderr == ""


def test_cli_outputs_fixture_backed_memory_threshold_demo_json():
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}
    expected = Path("tests/fixtures/memory-threshold-violations.json").read_text(encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "r_project", "--memory-threshold-demo", "--json"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.stdout == expected
    assert result.stderr == ""


def test_cli_memory_threshold_demo_accepts_custom_budget_flags_for_markdown():
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--memory-threshold-demo",
            "--memory-overlap-max-count",
            "2",
            "--memory-overlap-max-bytes",
            "6",
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.stdout == "# Byte Span Overlap Threshold Violations by Tag\n\nNo grouped overlap threshold violations.\n"
    assert result.stderr == ""


def test_cli_memory_threshold_demo_accepts_custom_budget_flags_for_json():
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--memory-threshold-demo",
            "--json",
            "--memory-overlap-max-count",
            "2",
            "--memory-overlap-max-bytes",
            "6",
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert json.loads(result.stdout) == {
        "by": "tag",
        "max_overlap_count": 2,
        "max_total_overlap_size": 6,
        "violations": [],
    }
    assert result.stderr == ""


def test_cli_outputs_fixture_backed_memory_threshold_demo_by_name_prefix_depth():
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}
    expected = Path("tests/fixtures/memory-threshold-violations-name-prefix-depth-2.md").read_text(encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--memory-threshold-demo",
            "--memory-overlap-group-by",
            "name_prefix",
            "--memory-overlap-prefix-depth",
            "2",
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.stdout == expected
    assert result.stderr == ""


def test_cli_outputs_fixture_backed_memory_threshold_demo_by_name_prefix_depth_json():
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}
    expected = Path("tests/fixtures/memory-threshold-violations-name-prefix-depth-2.json").read_text(encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--memory-threshold-demo",
            "--json",
            "--memory-overlap-group-by",
            "name_prefix",
            "--memory-overlap-prefix-depth",
            "2",
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.stdout == expected
    assert result.stderr == ""


def test_cli_outputs_fixture_backed_memory_overlap_totals_demo():
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}
    expected = Path("tests/fixtures/memory-overlap-totals.md").read_text(encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "r_project", "--memory-overlap-totals-demo"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.stdout == expected
    assert result.stderr == ""


def test_cli_outputs_fixture_backed_memory_overlap_totals_demo_json():
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}
    expected = Path("tests/fixtures/memory-overlap-totals.json").read_text(encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "r_project", "--memory-overlap-totals-demo", "--json"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.stdout == expected
    assert result.stderr == ""


def test_cli_outputs_fixture_backed_memory_overlap_totals_demo_by_name_prefix_depth():
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}
    expected = Path("tests/fixtures/memory-overlap-totals-name-prefix-depth-2.md").read_text(encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--memory-overlap-totals-demo",
            "--memory-overlap-group-by",
            "name_prefix",
            "--memory-overlap-prefix-depth",
            "2",
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.stdout == expected
    assert result.stderr == ""


def test_cli_outputs_fixture_backed_memory_overlap_totals_demo_by_name_prefix_depth_json():
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}
    expected = Path("tests/fixtures/memory-overlap-totals-name-prefix-depth-2.json").read_text(encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--memory-overlap-totals-demo",
            "--json",
            "--memory-overlap-group-by",
            "name_prefix",
            "--memory-overlap-prefix-depth",
            "2",
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.stdout == expected
    assert result.stderr == ""


def test_cli_memory_overlap_totals_demo_filters_spans_by_name_prefix():
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--memory-overlap-totals-demo",
            "--memory-overlap-name-prefix",
            "left.",
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.stdout == "# Byte Span Overlap Totals by Tag\n\nNo overlapping byte spans.\n"
    assert result.stderr == ""


def test_cli_memory_threshold_demo_filters_spans_by_required_tag_before_json_budgeting():
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--memory-threshold-demo",
            "--json",
            "--memory-overlap-tag",
            "source:literal",
            "--memory-overlap-max-count",
            "0",
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert json.loads(result.stdout) == {
        "by": "tag",
        "max_overlap_count": 0,
        "max_total_overlap_size": 4,
        "violations": [
            {
                "exceeded": ["overlap_count"],
                "group": "source:literal",
                "max_overlap_count": 0,
                "max_total_overlap_size": 4,
                "overlap_count": 1,
                "total_overlap_size": 4,
            }
        ],
    }
    assert result.stderr == ""


def test_cli_outputs_fixture_backed_memory_overlap_demo_json_schema():
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}
    expected = Path("tests/fixtures/memory-overlap-demo-schema.json").read_text(encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "r_project", "--memory-overlap-demo-schema"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    schema = json.loads(result.stdout)
    assert result.stdout == expected
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert set(schema["$defs"]) == {"memoryOverlapTotalsDemo", "memoryThresholdDemo"}
    assert schema["$defs"]["memoryOverlapTotalsDemo"]["properties"]["totals"]["items"]["required"] == [
        "group",
        "overlap_count",
        "total_overlap_size",
    ]
    assert schema["$defs"]["memoryThresholdDemo"]["properties"]["violations"]["items"]["required"] == [
        "group",
        "overlap_count",
        "total_overlap_size",
        "max_overlap_count",
        "max_total_overlap_size",
        "exceeded",
    ]
    assert result.stderr == ""


def test_readme_documents_memory_overlap_schema_examples_for_dashboard_consumers():
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "## Memory overlap demo JSON Schemas" in readme
    assert "r-project --memory-overlap-demo-schema" in readme
    assert '"$schema": "https://json-schema.org/draft/2020-12/schema"' in readme
    assert '"memoryOverlapTotalsDemo"' in readme
    assert '"memoryThresholdDemo"' in readme
    assert '"required": ["group", "overlap_count", "total_overlap_size"]' in readme
    assert '"required": ["group", "overlap_count", "total_overlap_size", "max_overlap_count", "max_total_overlap_size", "exceeded"]' in readme


def test_cli_check_memory_overlap_demo_schema_succeeds_when_fixture_matches_current_schema():
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [sys.executable, "-m", "r_project", "--root", ".", "--check-memory-overlap-demo-schema"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 0
    assert result.stdout == "Memory overlap demo schema fixture matches current CLI output.\n"
    assert result.stderr == ""


def test_cli_check_memory_overlap_demo_schema_reports_fixture_drift(tmp_path):
    write(tmp_path / "tests" / "fixtures" / "memory-overlap-demo-schema.json", "{}\n")
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [sys.executable, "-m", "r_project", "--root", str(tmp_path), "--check-memory-overlap-demo-schema"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == "Memory overlap demo schema fixture is out of date.\n"


def test_cli_check_changelog_version_succeeds_when_docs_match_pyproject_version():
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [sys.executable, "-m", "r_project", "--root", ".", "--check-changelog-version"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 0
    assert result.stdout == "CHANGELOG and README mention pyproject version 0.1.0.\n"
    assert result.stderr == ""


def test_cli_check_changelog_version_reports_missing_documented_version(tmp_path):
    write(
        tmp_path / "pyproject.toml",
        """[project]
name = "r-project"
version = "0.2.0"
""",
    )
    write(tmp_path / "README.md", "# R\n\nPackage version is `0.1.0`.\n")
    write(tmp_path / "CHANGELOG.md", "# Changelog\n\n## Unreleased\n\n- Old notes for `0.1.0`.\n")
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [sys.executable, "-m", "r_project", "--root", str(tmp_path), "--check-changelog-version"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == (
        "README.md does not mention pyproject version 0.2.0.\n"
        "CHANGELOG.md does not mention pyproject version 0.2.0.\n"
    )


def test_cli_check_readme_examples_reports_drift(tmp_path):
    write(tmp_path / "README.md", """# Drift Demo\n\n```json\n{}\n```\n\n```markdown\nold report\n```\n""")
    write(tmp_path / "status" / "missing-features.md", "- [x] Current feature.\n")
    write(tmp_path / "status" / "stuck.md", "## Active blockers\n- None.\n")
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [sys.executable, "-m", "r_project", "--root", str(tmp_path), "--check-readme-examples"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == "README json example is out of date.\nREADME markdown example is out of date.\n"

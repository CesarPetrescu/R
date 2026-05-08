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


def test_cli_writes_readme_examples_to_alternate_docs_path(tmp_path):
    write(tmp_path / "README.md", "# Root README\n\nUntouched.\n")
    docs_readme = tmp_path / "docs" / "usage-examples.md"
    write(
        docs_readme,
        """# Usage Examples

```json
{}
```

```markdown
old report
```
""",
    )
    write(
        tmp_path / "status" / "missing-features.md",
        """# Missing Features
## P1
- [x] Build report.
- [ ] Write alternate docs examples.
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
            "--readme-examples-path",
            "docs/usage-examples.md",
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    json_output = json.dumps(analyze_project(tmp_path).to_dict(), sort_keys=True)
    markdown_output = analyze_project(tmp_path).to_markdown()
    assert result.stdout == "Updated docs/usage-examples.md JSON and Markdown example fences.\n"
    assert result.stderr == ""
    assert docs_readme.read_text(encoding="utf-8") == f"""# Usage Examples

```json
{json_output}
```

```markdown
{markdown_output}
```
"""
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == "# Root README\n\nUntouched.\n"


def test_cli_checks_readme_examples_at_alternate_docs_path(tmp_path):
    docs_readme = tmp_path / "docs" / "usage-examples.md"
    write(
        docs_readme,
        """# Usage Examples

```json
{}
```

```markdown
old report
```
""",
    )
    write(
        tmp_path / "status" / "missing-features.md",
        """# Missing Features
## P1
- [x] Build report.
- [ ] Check alternate docs examples.
""",
    )
    write(tmp_path / "status" / "stuck.md", "## Active blockers\n- None.\n")
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--root",
            str(tmp_path),
            "--write-readme-examples",
            "--readme-examples-path",
            "docs/usage-examples.md",
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--root",
            str(tmp_path),
            "--check-readme-examples",
            "--readme-examples-path",
            "docs/usage-examples.md",
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.stdout == "docs/usage-examples.md examples match current CLI output.\n"
    assert result.stderr == ""


def test_cli_rejects_readme_examples_path_that_escapes_root(tmp_path):
    outside = tmp_path.parent / "outside-readme-examples.md"
    write(
        outside,
        """# Outside Examples

```json
{}
```

```markdown
old report
```
""",
    )
    write(tmp_path / "README.md", "# Safe Root\n")
    write(tmp_path / "status" / "missing-features.md", "- [ ] Keep writer in root.\n")
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
            "--readme-examples-path",
            "../outside-readme-examples.md",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "--readme-examples-path must stay under --root" in result.stderr
    assert outside.read_text(encoding="utf-8") == """# Outside Examples

```json
{}
```

```markdown
old report
```
"""


def test_cli_check_rejects_absolute_readme_examples_path(tmp_path):
    write(tmp_path / "README.md", "# Safe Root\n")
    write(tmp_path / "status" / "missing-features.md", "- [ ] Keep checker in root.\n")
    write(tmp_path / "status" / "stuck.md", "## Active blockers\n- None.\n")
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--root",
            str(tmp_path),
            "--check-readme-examples",
            "--readme-examples-path",
            str(tmp_path / "README.md"),
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "--readme-examples-path must be relative to --root" in result.stderr


def test_standalone_usage_examples_document_matches_current_cli_output():
    usage_examples = Path("docs/usage-examples.md")
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--root",
            ".",
            "--check-readme-examples",
            "--readme-examples-path",
            str(usage_examples),
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert usage_examples.exists()
    assert result.returncode == 0
    assert result.stdout == "docs/usage-examples.md examples match current CLI output.\n"
    assert result.stderr == ""


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


def test_cli_check_readme_schema_examples_succeeds_when_docs_match_current_schema():
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [sys.executable, "-m", "r_project", "--root", ".", "--check-readme-schema-examples"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 0
    assert result.stdout == "README memory-overlap schema example matches current CLI output.\n"
    assert result.stderr == ""


def test_cli_check_readme_schema_examples_reports_compact_schema_doc_drift(tmp_path):
    write(
        tmp_path / "README.md",
        """# Schema Drift Demo

## Memory overlap demo JSON Schemas

```json
{}
```
""",
    )
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [sys.executable, "-m", "r_project", "--root", str(tmp_path), "--check-readme-schema-examples"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == "README memory-overlap schema example is out of date.\n"


def test_cli_writes_readme_schema_example_in_place(tmp_path):
    write(
        tmp_path / "README.md",
        """# Schema Writer Demo

Intro stays.

## Memory overlap demo JSON Schemas

```json
{}
```

Tail stays.
""",
    )
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [sys.executable, "-m", "r_project", "--root", str(tmp_path), "--write-readme-schema-examples"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    expected_schema = json.dumps(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$defs": {
                "memoryOverlapTotalsDemo": {
                    "required": ["by", "totals"],
                    "totals_item": {"required": ["group", "overlap_count", "total_overlap_size"]},
                },
                "memoryThresholdDemo": {
                    "required": ["by", "max_overlap_count", "max_total_overlap_size", "violations"],
                    "violations_item": {
                        "required": [
                            "group",
                            "overlap_count",
                            "total_overlap_size",
                            "max_overlap_count",
                            "max_total_overlap_size",
                            "exceeded",
                        ]
                    },
                },
            },
        }
    )
    assert result.returncode == 0
    assert result.stdout == "Updated README memory-overlap schema example fence.\n"
    assert result.stderr == ""
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == f"""# Schema Writer Demo

Intro stays.

## Memory overlap demo JSON Schemas

```json
{expected_schema}
```

Tail stays.
"""


def test_cli_dry_runs_readme_schema_example_writer_without_modifying_readme(tmp_path):
    original_readme = """# Schema Dry Run Demo

## Memory overlap demo JSON Schemas

```json
{}
```
"""
    write(tmp_path / "README.md", original_readme)
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--root",
            str(tmp_path),
            "--write-readme-schema-examples",
            "--dry-run-readme-schema-examples",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 0
    assert '"memoryOverlapTotalsDemo"' in result.stdout
    assert '"memoryThresholdDemo"' in result.stdout
    assert result.stderr == ""
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == original_readme


def test_cli_writes_readme_schema_example_to_alternate_docs_path(tmp_path):
    docs_readme = tmp_path / "docs" / "dashboard-schema.md"
    write(
        docs_readme,
        """# Dashboard Schema Docs

## Memory overlap demo JSON Schemas

```json
{}
```
""",
    )
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--root",
            str(tmp_path),
            "--write-readme-schema-examples",
            "--readme-schema-path",
            "docs/dashboard-schema.md",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 0
    assert result.stdout == "Updated docs/dashboard-schema.md memory-overlap schema example fence.\n"
    assert result.stderr == ""
    assert '"memoryOverlapTotalsDemo"' in docs_readme.read_text(encoding="utf-8")
    assert not (tmp_path / "README.md").exists()


def test_cli_checks_readme_schema_example_at_alternate_docs_path(tmp_path):
    docs_readme = tmp_path / "docs" / "dashboard-schema.md"
    write(
        docs_readme,
        """# Dashboard Schema Docs

## Memory overlap demo JSON Schemas

```json
{}
```
""",
    )
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    write_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--root",
            str(tmp_path),
            "--write-readme-schema-examples",
            "--readme-schema-path",
            "docs/dashboard-schema.md",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    check_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--root",
            str(tmp_path),
            "--check-readme-schema-examples",
            "--readme-schema-path",
            "docs/dashboard-schema.md",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert write_result.returncode == 0
    assert check_result.returncode == 0
    assert check_result.stdout == "docs/dashboard-schema.md memory-overlap schema example matches current CLI output.\n"
    assert check_result.stderr == ""


def test_standalone_dashboard_schema_document_matches_current_schema_output():
    dashboard_schema = Path("docs/dashboard-schema.md")
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--root",
            ".",
            "--check-readme-schema-examples",
            "--readme-schema-path",
            str(dashboard_schema),
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert dashboard_schema.exists()
    assert result.returncode == 0
    assert result.stdout == "docs/dashboard-schema.md memory-overlap schema example matches current CLI output.\n"
    assert result.stderr == ""


def test_standalone_dashboard_index_document_matches_report_and_schema_outputs():
    dashboard_index = Path("docs/dashboard-index.md")
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    report_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--root",
            ".",
            "--check-readme-examples",
            "--readme-examples-path",
            str(dashboard_index),
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    schema_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--root",
            ".",
            "--check-readme-schema-examples",
            "--readme-schema-path",
            str(dashboard_index),
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    text = dashboard_index.read_text(encoding="utf-8") if dashboard_index.exists() else ""

    assert dashboard_index.exists()
    assert "[Readiness report examples](usage-examples.md)" in text
    assert "[Memory overlap schema examples](dashboard-schema.md)" in text
    assert "r-project --root . --check-readme-examples --readme-examples-path docs/dashboard-index.md" in text
    assert "r-project --root . --check-readme-schema-examples --readme-schema-path docs/dashboard-index.md" in text
    assert report_result.returncode == 0
    assert report_result.stdout == "docs/dashboard-index.md examples match current CLI output.\n"
    assert report_result.stderr == ""
    assert schema_result.returncode == 0
    assert schema_result.stdout == "docs/dashboard-index.md memory-overlap schema example matches current CLI output.\n"
    assert schema_result.stderr == ""


def test_cli_rejects_readme_schema_path_that_escapes_root(tmp_path):
    outside = tmp_path.parent / "outside-dashboard-schema.md"
    write(
        outside,
        """# Outside Schema Docs

## Memory overlap demo JSON Schemas

```json
{}
```
""",
    )
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--root",
            str(tmp_path),
            "--write-readme-schema-examples",
            "--readme-schema-path",
            "../outside-dashboard-schema.md",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "--readme-schema-path must stay under --root" in result.stderr
    assert outside.read_text(encoding="utf-8") == """# Outside Schema Docs

## Memory overlap demo JSON Schemas

```json
{}
```
"""


def test_cli_check_rejects_readme_schema_path_that_escapes_root(tmp_path):
    outside = tmp_path.parent / "outside-check-dashboard-schema.md"
    write(
        outside,
        """# Outside Check Schema Docs

## Memory overlap demo JSON Schemas

```json
{}
```
""",
    )
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--root",
            str(tmp_path),
            "--check-readme-schema-examples",
            "--readme-schema-path",
            "../outside-check-dashboard-schema.md",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "--readme-schema-path must stay under --root" in result.stderr


def test_cli_check_rejects_absolute_readme_schema_path(tmp_path):
    outside = tmp_path / "absolute-dashboard-schema.md"
    write(
        outside,
        """# Absolute Schema Docs

## Memory overlap demo JSON Schemas

```json
{}
```
""",
    )
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--root",
            str(tmp_path),
            "--check-readme-schema-examples",
            "--readme-schema-path",
            str(outside),
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "--readme-schema-path must be relative to --root" in result.stderr


def test_cli_write_rejects_absolute_readme_schema_path(tmp_path):
    outside = tmp_path / "absolute-write-dashboard-schema.md"
    write(
        outside,
        """# Absolute Write Schema Docs

## Memory overlap demo JSON Schemas

```json
{}
```
""",
    )
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--root",
            str(tmp_path),
            "--write-readme-schema-examples",
            "--readme-schema-path",
            str(outside),
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "--readme-schema-path must be relative to --root" in result.stderr
    assert outside.read_text(encoding="utf-8") == """# Absolute Write Schema Docs

## Memory overlap demo JSON Schemas

```json
{}
```
"""


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


def test_cli_check_release_tag_succeeds_for_matching_tag_clean_tree_and_docker_evidence():
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--root",
            ".",
            "--check-release-tag",
            "v0.1.0",
            "--docker-verified",
            "--skip-git-clean-check",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 0
    assert result.stdout == "Release tag v0.1.0 matches pyproject version 0.1.0 and Docker verification evidence is present.\n"
    assert result.stderr == ""


def test_cli_check_release_tag_json_summarizes_matching_tag_clean_tree_and_docker_evidence():
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--root",
            ".",
            "--json",
            "--check-release-tag",
            "v0.1.0",
            "--docker-verified",
            "--skip-git-clean-check",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 0
    assert json.loads(result.stdout) == {
        "checks": {
            "docker_verified": True,
            "git_clean": "skipped",
            "tag_matches_version": True,
        },
        "expected_tag": "v0.1.0",
        "ready": True,
        "tag": "v0.1.0",
        "version": "0.1.0",
    }
    assert result.stderr == ""



def test_release_tag_checklist_json_fixture_matches_current_cli_output():
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--root",
            ".",
            "--json",
            "--check-release-tag",
            "v0.1.0",
            "--docker-verified",
            "--skip-git-clean-check",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 0
    assert result.stdout == Path("tests/fixtures/release-tag-checklist.json").read_text(encoding="utf-8")



def test_cli_check_release_tag_fixture_reports_drift(tmp_path):
    write(
        tmp_path / "pyproject.toml",
        """[project]
name = "r-project"
version = "0.1.0"
""",
    )
    write(tmp_path / "tests" / "fixtures" / "release-tag-checklist.json", "{}\n")
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [sys.executable, "-m", "r_project", "--root", str(tmp_path), "--check-release-tag-fixture"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == "Release tag checklist fixture is out of date.\n"


def test_cli_write_release_tag_fixture_updates_stale_fixture(tmp_path):
    write(
        tmp_path / "pyproject.toml",
        """[project]
name = "r-project"
version = "0.1.0"
""",
    )
    fixture = tmp_path / "tests" / "fixtures" / "release-tag-checklist.json"
    write(fixture, "{}\n")
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [sys.executable, "-m", "r_project", "--root", str(tmp_path), "--write-release-tag-fixture"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 0
    assert result.stdout == "Updated release tag checklist fixture.\n"
    assert result.stderr == ""
    assert json.loads(fixture.read_text(encoding="utf-8")) == {
        "checks": {
            "docker_verified": True,
            "git_clean": "skipped",
            "tag_matches_version": True,
        },
        "expected_tag": "v0.1.0",
        "ready": True,
        "tag": "v0.1.0",
        "version": "0.1.0",
    }


def test_cli_write_release_tag_fixture_dry_run_prints_without_modifying_fixture(tmp_path):
    write(
        tmp_path / "pyproject.toml",
        """[project]
name = "r-project"
version = "0.1.0"
""",
    )
    fixture = tmp_path / "tests" / "fixtures" / "release-tag-checklist.json"
    write(fixture, "{}\n")
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--root",
            str(tmp_path),
            "--write-release-tag-fixture",
            "--dry-run-release-tag-fixture",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 0
    assert json.loads(result.stdout) == {
        "checks": {
            "docker_verified": True,
            "git_clean": "skipped",
            "tag_matches_version": True,
        },
        "expected_tag": "v0.1.0",
        "ready": True,
        "tag": "v0.1.0",
        "version": "0.1.0",
    }
    assert result.stderr == ""
    assert fixture.read_text(encoding="utf-8") == "{}\n"


def test_cli_write_release_tag_fixture_dry_run_targets_future_version_without_pyproject_change(tmp_path):
    write(
        tmp_path / "pyproject.toml",
        """[project]
name = "r-project"
version = "0.1.0"
""",
    )
    fixture = tmp_path / "tests" / "fixtures" / "release-tag-checklist.json"
    write(fixture, "{}\n")
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--root",
            str(tmp_path),
            "--write-release-tag-fixture",
            "--dry-run-release-tag-fixture",
            "--release-tag-fixture-version",
            "0.2.0",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 0
    assert json.loads(result.stdout) == {
        "checks": {
            "docker_verified": True,
            "git_clean": "skipped",
            "tag_matches_version": True,
        },
        "expected_tag": "v0.2.0",
        "ready": True,
        "tag": "v0.2.0",
        "version": "0.2.0",
    }
    assert result.stderr == ""
    assert fixture.read_text(encoding="utf-8") == "{}\n"


def test_cli_check_release_tag_fixture_targets_future_version(tmp_path):
    write(
        tmp_path / "pyproject.toml",
        """[project]
name = "r-project"
version = "0.1.0"
""",
    )
    write(
        tmp_path / "tests" / "fixtures" / "release-tag-checklist.json",
        json.dumps(
            {
                "checks": {
                    "docker_verified": True,
                    "git_clean": "skipped",
                    "tag_matches_version": True,
                },
                "expected_tag": "v0.2.0",
                "ready": True,
                "tag": "v0.2.0",
                "version": "0.2.0",
            },
            sort_keys=True,
        )
        + "\n",
    )
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--root",
            str(tmp_path),
            "--check-release-tag-fixture",
            "--release-tag-fixture-version",
            "0.2.0",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 0
    assert result.stdout == "Release tag checklist fixture matches current CLI output.\n"
    assert result.stderr == ""


def test_cli_write_release_tag_fixture_supports_root_relative_path_override(tmp_path):
    write(
        tmp_path / "pyproject.toml",
        """[project]
name = "r-project"
version = "0.1.0"
""",
    )
    fixture = tmp_path / "docs" / "release" / "checklist.json"
    write(fixture, "{}\n")
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--root",
            str(tmp_path),
            "--write-release-tag-fixture",
            "--release-tag-fixture-path",
            "docs/release/checklist.json",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 0
    assert result.stdout == "Updated docs/release/checklist.json release tag checklist fixture.\n"
    assert result.stderr == ""
    assert json.loads(fixture.read_text(encoding="utf-8"))["tag"] == "v0.1.0"
    assert not (tmp_path / "tests" / "fixtures" / "release-tag-checklist.json").exists()


def test_cli_check_release_tag_fixture_supports_root_relative_path_override(tmp_path):
    write(
        tmp_path / "pyproject.toml",
        """[project]
name = "r-project"
version = "0.1.0"
""",
    )
    write(
        tmp_path / "docs" / "release" / "checklist.json",
        json.dumps(
            {
                "checks": {
                    "docker_verified": True,
                    "git_clean": "skipped",
                    "tag_matches_version": True,
                },
                "expected_tag": "v0.1.0",
                "ready": True,
                "tag": "v0.1.0",
                "version": "0.1.0",
            },
            sort_keys=True,
        )
        + "\n",
    )
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--root",
            str(tmp_path),
            "--check-release-tag-fixture",
            "--release-tag-fixture-path",
            "docs/release/checklist.json",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 0
    assert result.stdout == "docs/release/checklist.json release tag checklist fixture matches current CLI output.\n"
    assert result.stderr == ""


def test_cli_check_release_examples_supports_readme_style_markdown_path(tmp_path):
    write(
        tmp_path / "pyproject.toml",
        """[project]
name = "r-project"
version = "0.1.0"
""",
    )
    write(
        tmp_path / "docs" / "release-examples.md",
        """# Release Examples

```json
{"checks": {"docker_verified": true, "git_clean": "skipped", "tag_matches_version": true}, "expected_tag": "v0.1.0", "ready": true, "tag": "v0.1.0", "version": "0.1.0"}
```
""",
    )
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--root",
            str(tmp_path),
            "--check-release-examples",
            "--release-examples-path",
            "docs/release-examples.md",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 0
    assert result.stdout == "docs/release-examples.md release checklist example matches current CLI output.\n"
    assert result.stderr == ""


def test_cli_write_release_examples_dry_run_refreshes_json_fence_without_modifying_file(tmp_path):
    write(
        tmp_path / "pyproject.toml",
        """[project]
name = "r-project"
version = "0.1.0"
""",
    )
    examples = tmp_path / "docs" / "release-examples.md"
    original = """# Release Examples

```json
{}
```
"""
    write(examples, original)
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--root",
            str(tmp_path),
            "--write-release-examples",
            "--dry-run-release-examples",
            "--release-examples-path",
            "docs/release-examples.md",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 0
    assert '"tag": "v0.1.0"' in result.stdout
    assert '"ready": true' in result.stdout
    assert result.stderr == ""
    assert examples.read_text(encoding="utf-8") == original


def test_cli_write_release_examples_rejects_path_that_escapes_root(tmp_path):
    write(
        tmp_path / "pyproject.toml",
        """[project]
name = "r-project"
version = "0.1.0"
""",
    )
    outside_examples = tmp_path.parent / "outside-release-examples.md"
    outside_examples.write_text("do not touch\n", encoding="utf-8")
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--root",
            str(tmp_path),
            "--write-release-examples",
            "--release-examples-path",
            "../outside-release-examples.md",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 2
    assert "--release-examples-path must stay under --root" in result.stderr
    assert outside_examples.read_text(encoding="utf-8") == "do not touch\n"


def test_cli_write_release_tag_fixture_rejects_path_that_escapes_root(tmp_path):
    write(
        tmp_path / "pyproject.toml",
        """[project]
name = "r-project"
version = "0.1.0"
""",
    )
    outside_fixture = tmp_path.parent / "outside-release-tag-checklist.json"
    outside_fixture.write_text("do not touch\n", encoding="utf-8")
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--root",
            str(tmp_path),
            "--write-release-tag-fixture",
            "--release-tag-fixture-path",
            "../outside-release-tag-checklist.json",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 2
    assert "--release-tag-fixture-path must stay under --root" in result.stderr
    assert outside_fixture.read_text(encoding="utf-8") == "do not touch\n"


def test_cli_check_release_tag_fixture_rejects_absolute_path(tmp_path):
    write(
        tmp_path / "pyproject.toml",
        """[project]
name = "r-project"
version = "0.1.0"
""",
    )
    outside_fixture = tmp_path.parent / "outside-release-tag-checklist.json"
    outside_fixture.write_text("{}\n", encoding="utf-8")
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--root",
            str(tmp_path),
            "--check-release-tag-fixture",
            "--release-tag-fixture-path",
            str(outside_fixture),
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 2
    assert "--release-tag-fixture-path must be relative to --root" in result.stderr


def test_cli_check_release_tag_reports_mismatched_tag_name():
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--root",
            ".",
            "--check-release-tag",
            "v0.2.0",
            "--docker-verified",
            "--skip-git-clean-check",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == "Release tag v0.2.0 does not match expected tag v0.1.0 from pyproject version 0.1.0.\n"


def test_cli_check_release_tag_requires_docker_verification_evidence():
    env = os.environ | {"PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--root",
            ".",
            "--check-release-tag",
            "v0.1.0",
            "--skip-git-clean-check",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == "Release tag check requires --docker-verified evidence from docker compose run --build --rm test.\n"


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

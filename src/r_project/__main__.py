from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tomllib
from pathlib import Path

from .memory import (
    ByteSpan,
    filter_byte_spans,
    find_grouped_byte_span_overlap_total_violations,
    group_byte_span_overlap_totals,
    render_grouped_byte_span_overlap_threshold_violations,
    render_grouped_byte_span_overlap_totals,
)
from .report import analyze_project


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Report project R autonomous-maintenance readiness.")
    parser.add_argument("--root", default=".", help="Project root to analyze (default: current directory).")
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    output_group.add_argument("--markdown", action="store_true", help="Emit a GitHub-flavored Markdown report.")
    parser.add_argument(
        "--fail-on-blockers",
        action="store_true",
        help="Exit with status 2 when active blockers are present after emitting the report.",
    )
    parser.add_argument(
        "--check-readme-examples",
        action="store_true",
        help="Exit nonzero when README JSON/Markdown examples drift from current CLI output.",
    )
    parser.add_argument(
        "--generate-readme-examples",
        action="store_true",
        help="Emit README-ready JSON and Markdown example fences from the current report.",
    )
    parser.add_argument(
        "--write-readme-examples",
        action="store_true",
        help="Patch README JSON and Markdown example fences in place with current report output.",
    )
    parser.add_argument(
        "--dry-run-readme-examples",
        action="store_true",
        help="With --write-readme-examples, print the updated README content without modifying README.md.",
    )
    parser.add_argument(
        "--readme-examples-path",
        default="README.md",
        help="README-style Markdown path, relative to --root, whose JSON/Markdown report examples are checked or written.",
    )
    parser.add_argument(
        "--readme-examples-section",
        help=(
            "With --check-readme-examples or --write-readme-examples, check or replace the first JSON and "
            "Markdown fences after this Markdown heading instead of the first matching fences in the document."
        ),
    )
    parser.add_argument(
        "--check-memory-overlap-demo-schema",
        action="store_true",
        help="Exit nonzero when the memory overlap demo schema fixture drifts from current CLI output.",
    )
    parser.add_argument(
        "--check-readme-schema-examples",
        action="store_true",
        help="Exit nonzero when README compact memory-overlap JSON Schema examples drift from current CLI output.",
    )
    parser.add_argument(
        "--write-readme-schema-examples",
        action="store_true",
        help="Patch the README compact memory-overlap JSON Schema example fence in place with current CLI output.",
    )
    parser.add_argument(
        "--dry-run-readme-schema-examples",
        action="store_true",
        help="With --write-readme-schema-examples, print updated README content without modifying README.md.",
    )
    parser.add_argument(
        "--readme-schema-path",
        default="README.md",
        help="README-style Markdown path, relative to --root, whose compact memory-overlap schema example is checked or written.",
    )
    parser.add_argument(
        "--readme-schema-section",
        help=(
            "With --check-readme-schema-examples or --write-readme-schema-examples, check or replace the first "
            "JSON fence after this Markdown heading instead of the default memory-overlap schema section."
        ),
    )
    parser.add_argument(
        "--check-changelog-version",
        action="store_true",
        help="Exit nonzero when README/CHANGELOG do not mention the pyproject package version.",
    )
    parser.add_argument(
        "--check-release-tag",
        metavar="TAG",
        help="Exit nonzero unless TAG matches the pyproject version, Docker verification evidence is present, and git is clean.",
    )
    parser.add_argument(
        "--check-release-tag-fixture",
        action="store_true",
        help="Exit nonzero when the release tag checklist JSON fixture drifts from current CLI output.",
    )
    parser.add_argument(
        "--write-release-tag-fixture",
        action="store_true",
        help="Patch the release tag checklist JSON fixture in place with current generated output.",
    )
    parser.add_argument(
        "--dry-run-release-tag-fixture",
        action="store_true",
        help="With --write-release-tag-fixture, print the updated fixture content without modifying it.",
    )
    parser.add_argument(
        "--release-tag-fixture-version",
        metavar="VERSION",
        help=(
            "With --check-release-tag-fixture or --write-release-tag-fixture, generate the fixture for a future "
            "package version without editing pyproject.toml."
        ),
    )
    parser.add_argument(
        "--release-tag-fixture-path",
        default="tests/fixtures/release-tag-checklist.json",
        help=(
            "Release checklist JSON fixture path, relative to --root, checked or written by "
            "--check-release-tag-fixture and --write-release-tag-fixture."
        ),
    )
    parser.add_argument(
        "--check-release-examples",
        action="store_true",
        help="Exit nonzero when a README-style release checklist JSON example drifts from current CLI output.",
    )
    parser.add_argument(
        "--write-release-examples",
        action="store_true",
        help="Patch a README-style release checklist JSON example fence in place with current generated output.",
    )
    parser.add_argument(
        "--dry-run-release-examples",
        action="store_true",
        help="With --write-release-examples, print the updated Markdown content without modifying it.",
    )
    parser.add_argument(
        "--release-examples-path",
        default="docs/release-examples.md",
        help=(
            "README-style Markdown path, relative to --root, whose release checklist JSON example is checked or written."
        ),
    )
    parser.add_argument(
        "--release-examples-version",
        metavar="VERSION",
        help=(
            "With --check-release-examples or --write-release-examples, generate the README-style release "
            "checklist example for a future package version without editing pyproject.toml."
        ),
    )
    parser.add_argument(
        "--release-examples-section",
        help=(
            "With --check-release-examples or --write-release-examples, check or replace the first JSON fence "
            "after this Markdown heading instead of the first JSON fence in the document."
        ),
    )
    parser.add_argument(
        "--check-release-example-fixtures",
        action="store_true",
        help=(
            "Exit nonzero when docs/release-example-fixtures.md lists release-example smoke fixture commands "
            "that are not exercised by docker-compose.yml."
        ),
    )
    parser.add_argument(
        "--check-release-example-sections",
        action="store_true",
        help=(
            "Exit nonzero when docs/release-example-sections.md lists named release checklist sections "
            "that are not exercised by docker-compose.yml."
        ),
    )
    parser.add_argument(
        "--check-release-section-writer-matrix",
        action="store_true",
        help=(
            "Exit nonzero when docs/release-section-writer-matrix.md omits current/future release "
            "section writer commands or Docker coverage."
        ),
    )
    parser.add_argument(
        "--generate-release-section-writer-matrix",
        action="store_true",
        help=(
            "Emit current-version and future-version release section writer matrix rows derived from "
            "docs/release-example-sections.md."
        ),
    )
    parser.add_argument(
        "--write-release-section-writer-matrix",
        action="store_true",
        help=(
            "Append missing current-version and future-version release section writer matrix rows derived from "
            "docs/release-example-sections.md."
        ),
    )
    parser.add_argument(
        "--dry-run-release-section-writer-matrix",
        action="store_true",
        help=(
            "With --write-release-section-writer-matrix, print the updated matrix document without modifying it."
        ),
    )
    parser.add_argument(
        "--check-release-automation-index",
        action="store_true",
        help="Exit nonzero when docs/release-automation-index.md omits release links or Docker-covered commands.",
    )
    parser.add_argument(
        "--generate-release-automation-index",
        action="store_true",
        help="Emit release automation index link and command rows derived from the built-in release surface registry.",
    )
    parser.add_argument(
        "--write-release-automation-index",
        action="store_true",
        help="Append missing release automation index links and commands derived from the built-in release surface registry.",
    )
    parser.add_argument(
        "--dry-run-release-automation-index",
        action="store_true",
        help="With --write-release-automation-index, print the updated release automation index without modifying it.",
    )
    parser.add_argument(
        "--release-automation-index-version",
        default="0.2.0",
        metavar="VERSION",
        help=(
            "With --check-release-automation-index, --generate-release-automation-index, "
            "or --write-release-automation-index, use this release preview version instead of "
            "the default 0.2.0 target."
        ),
    )
    parser.add_argument(
        "--release-section-writer-matrix-version",
        default="0.2.0",
        metavar="VERSION",
        help=(
            "With --check-release-section-writer-matrix, --generate-release-section-writer-matrix, "
            "or --write-release-section-writer-matrix, use this package version instead of the default 0.2.0 "
            "preview target."
        ),
    )
    parser.add_argument(
        "--check-release-examples-path-safety",
        action="store_true",
        help="Exit nonzero when release example path override safety checks do not reject unsafe paths.",
    )
    parser.add_argument(
        "--check-automation-index-links",
        action="store_true",
        help="Exit nonzero when docs/automation-index.md does not link every standalone automation docs surface.",
    )
    parser.add_argument(
        "--check-automation-index-commands",
        action="store_true",
        help="Exit nonzero when docs/automation-index.md documents r-project commands missing from docker-compose.yml.",
    )
    parser.add_argument(
        "--check-automation-command-fixtures",
        action="store_true",
        help="Exit nonzero when docs/automation-command-fixtures.md lists commands missing from docker-compose.yml.",
    )
    parser.add_argument(
        "--check-dashboard-automation-index",
        action="store_true",
        help="Exit nonzero when docs/dashboard-automation-index.md omits dashboard links or Docker-covered commands.",
    )
    parser.add_argument(
        "--generate-dashboard-automation-index",
        action="store_true",
        help="Emit dashboard automation index link and command rows derived from the built-in dashboard surface registry.",
    )
    parser.add_argument(
        "--write-dashboard-automation-index",
        action="store_true",
        help="Append missing dashboard automation index links and commands derived from the built-in dashboard surface registry.",
    )
    parser.add_argument(
        "--dry-run-dashboard-automation-index",
        action="store_true",
        help="With --write-dashboard-automation-index, print the updated dashboard automation index without modifying it.",
    )
    parser.add_argument(
        "--dashboard-automation-index-variant",
        metavar="LABEL",
        help=(
            "With --check-dashboard-automation-index, require dashboard automation index commands for this "
            "section-writer preview variant; with --generate-dashboard-automation-index or "
            "--write-dashboard-automation-index, emit commands for this variant instead of compact."
        ),
    )
    parser.add_argument(
        "--check-dashboard-example-fixtures",
        action="store_true",
        help="Exit nonzero when docs/dashboard-example-fixtures.md lists dashboard commands missing from docker-compose.yml.",
    )
    parser.add_argument(
        "--generate-dashboard-example-fixtures",
        action="store_true",
        help="Emit dashboard example fixture registry rows derived from docs/dashboard-index.md commands.",
    )
    parser.add_argument(
        "--write-dashboard-example-fixtures",
        action="store_true",
        help="Append missing dashboard example fixture registry rows derived from docs/dashboard-index.md commands.",
    )
    parser.add_argument(
        "--dry-run-dashboard-example-fixtures",
        action="store_true",
        help="With --write-dashboard-example-fixtures, print the updated fixture registry without modifying it.",
    )
    parser.add_argument(
        "--check-dashboard-section-writer-matrix",
        action="store_true",
        help=(
            "Exit nonzero when docs/dashboard-section-writer-matrix.md omits dashboard example writer "
            "dry-runs or Docker coverage."
        ),
    )
    parser.add_argument(
        "--generate-dashboard-section-writer-matrix",
        action="store_true",
        help=(
            "Emit dashboard section writer matrix rows derived from docs/dashboard-example-fixtures.md, "
            "optionally labeled with --dashboard-section-writer-matrix-variant."
        ),
    )
    parser.add_argument(
        "--write-dashboard-section-writer-matrix",
        action="store_true",
        help=(
            "Append missing variant-labeled dashboard section writer matrix rows derived from "
            "docs/dashboard-example-fixtures.md."
        ),
    )
    parser.add_argument(
        "--dry-run-dashboard-section-writer-matrix",
        action="store_true",
        help=(
            "With --write-dashboard-section-writer-matrix, print the updated matrix document without modifying it."
        ),
    )
    parser.add_argument(
        "--dashboard-section-writer-matrix-variant",
        metavar="LABEL",
        help=(
            "With --check-dashboard-section-writer-matrix, require writer matrix rows for this dashboard "
            "preview variant label in addition to default writer coverage; with "
            "--generate-dashboard-section-writer-matrix, label generated rows for this preview variant."
        ),
    )
    parser.add_argument(
        "--docker-verified",
        action="store_true",
        help="With --check-release-tag, confirm docker compose run --build --rm test has passed in this release run.",
    )
    parser.add_argument(
        "--skip-git-clean-check",
        action="store_true",
        help="With --check-release-tag, skip git status cleanliness checks for copied container test contexts.",
    )
    parser.add_argument(
        "--memory-threshold-demo",
        action="store_true",
        help="Emit a fixture-backed memory overlap threshold violation Markdown demo.",
    )
    parser.add_argument(
        "--memory-overlap-totals-demo",
        action="store_true",
        help="Emit a fixture-backed grouped memory overlap totals demo.",
    )
    parser.add_argument(
        "--memory-overlap-demo-schema",
        action="store_true",
        help="Emit JSON Schema definitions for memory overlap demo JSON outputs.",
    )
    parser.add_argument(
        "--memory-overlap-group-by",
        choices=("tag", "name_prefix"),
        default="tag",
        help="Group memory overlap demo totals by shared tag or qualified-name prefix (default: tag).",
    )
    parser.add_argument(
        "--memory-overlap-prefix-depth",
        type=int,
        default=1,
        help="Qualified-name prefix depth when grouping memory overlap demo totals by name_prefix (default: 1).",
    )
    parser.add_argument(
        "--memory-overlap-max-count",
        type=_non_negative_int,
        default=None,
        help="Maximum grouped overlap count budget for the memory threshold demo (default: demo preset).",
    )
    parser.add_argument(
        "--memory-overlap-max-bytes",
        type=_non_negative_int,
        default=None,
        help="Maximum grouped intersecting-byte budget for the memory threshold demo (default: demo preset).",
    )
    parser.add_argument(
        "--memory-overlap-name-prefix",
        default=None,
        help="Only include memory overlap demo fixture spans whose qualified names start with this prefix.",
    )
    parser.add_argument(
        "--memory-overlap-tag",
        action="append",
        default=[],
        help="Only include memory overlap demo fixture spans with this provenance tag; repeat to require multiple tags.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.memory_overlap_demo_schema:
        print(json.dumps(memory_overlap_demo_schema(), sort_keys=True))
        return 0
    if args.check_memory_overlap_demo_schema:
        root = Path(args.root)
        expected = json.dumps(memory_overlap_demo_schema(), sort_keys=True) + "\n"
        fixture = root / "tests" / "fixtures" / "memory-overlap-demo-schema.json"
        actual = fixture.read_text(encoding="utf-8") if fixture.exists() else ""
        if actual != expected:
            print("Memory overlap demo schema fixture is out of date.", file=sys.stderr)
            return 1
        print("Memory overlap demo schema fixture matches current CLI output.")
        return 0
    if args.check_readme_schema_examples:
        root = Path(args.root)
        try:
            readme_schema_path = _readme_schema_path_under_root(root, Path(args.readme_schema_path))
        except ValueError as error:
            parser.error(str(error))
        label = _readme_schema_path_label(readme_schema_path)
        if _readme_schema_example_mismatch(root, readme_schema_path, section=args.readme_schema_section):
            print(f"{label} memory-overlap schema example is out of date.", file=sys.stderr)
            return 1
        print(f"{label} memory-overlap schema example matches current CLI output.")
        return 0
    if args.write_readme_schema_examples:
        root = Path(args.root)
        try:
            readme_schema_path = _readme_schema_path_under_root(root, Path(args.readme_schema_path))
        except ValueError as error:
            parser.error(str(error))
        updated = _updated_readme_schema_example_block(root, readme_schema_path, section=args.readme_schema_section)
        if args.dry_run_readme_schema_examples:
            print(updated, end="")
        else:
            (root / readme_schema_path).write_text(updated, encoding="utf-8")
            print(f"Updated {_readme_schema_path_label(readme_schema_path)} memory-overlap schema example fence.")
        return 0
    if args.check_changelog_version:
        return _check_changelog_version(Path(args.root))
    if args.check_release_tag_fixture:
        root = Path(args.root)
        try:
            release_tag_fixture_path = _release_tag_fixture_path_under_root(
                root, Path(args.release_tag_fixture_path)
            )
        except ValueError as error:
            parser.error(str(error))
        return _check_release_tag_fixture(
            root, version=args.release_tag_fixture_version, fixture_path=release_tag_fixture_path
        )
    if args.write_release_tag_fixture:
        root = Path(args.root)
        try:
            release_tag_fixture_path = _release_tag_fixture_path_under_root(
                root, Path(args.release_tag_fixture_path)
            )
        except ValueError as error:
            parser.error(str(error))
        return _write_release_tag_fixture(
            root,
            dry_run=args.dry_run_release_tag_fixture,
            version=args.release_tag_fixture_version,
            fixture_path=release_tag_fixture_path,
        )
    if args.check_release_examples:
        root = Path(args.root)
        try:
            release_examples_path = _release_examples_path_under_root(root, Path(args.release_examples_path))
        except ValueError as error:
            parser.error(str(error))
        if _release_examples_mismatch(
            root,
            release_examples_path,
            version=args.release_examples_version,
            section=args.release_examples_section,
        ):
            print(f"{release_examples_path.as_posix()} release checklist example is out of date.", file=sys.stderr)
            return 1
        print(f"{release_examples_path.as_posix()} release checklist example matches current CLI output.")
        return 0
    if args.check_release_example_fixtures:
        return _check_release_example_fixtures(Path(args.root))
    if args.check_release_example_sections:
        return _check_release_example_sections(Path(args.root))
    if args.generate_release_section_writer_matrix:
        return _generate_release_section_writer_matrix(Path(args.root), args.release_section_writer_matrix_version)
    if args.write_release_section_writer_matrix:
        return _write_release_section_writer_matrix(
            Path(args.root),
            args.release_section_writer_matrix_version,
            dry_run=args.dry_run_release_section_writer_matrix,
        )
    if args.check_release_section_writer_matrix:
        return _check_release_section_writer_matrix(Path(args.root), args.release_section_writer_matrix_version)
    if args.check_release_automation_index:
        return _check_release_automation_index(Path(args.root), args.release_automation_index_version)
    if args.generate_release_automation_index:
        return _generate_release_automation_index(Path(args.root), args.release_automation_index_version)
    if args.write_release_automation_index:
        return _write_release_automation_index(
            Path(args.root),
            dry_run=args.dry_run_release_automation_index,
            version=args.release_automation_index_version,
        )
    if args.check_release_examples_path_safety:
        return _check_release_examples_path_safety(Path(args.root))
    if args.check_automation_index_links:
        return _check_automation_index_links(Path(args.root))
    if args.check_automation_index_commands:
        return _check_automation_index_commands(Path(args.root))
    if args.check_automation_command_fixtures:
        return _check_automation_command_fixtures(Path(args.root))
    if args.check_dashboard_automation_index:
        return _check_dashboard_automation_index(Path(args.root), args.dashboard_automation_index_variant)
    if args.generate_dashboard_automation_index:
        return _generate_dashboard_automation_index(Path(args.root), args.dashboard_automation_index_variant)
    if args.write_dashboard_automation_index:
        return _write_dashboard_automation_index(
            Path(args.root),
            dry_run=args.dry_run_dashboard_automation_index,
            variant=args.dashboard_automation_index_variant,
        )
    if args.generate_dashboard_example_fixtures:
        return _generate_dashboard_example_fixtures(Path(args.root))
    if args.write_dashboard_example_fixtures:
        return _write_dashboard_example_fixtures(
            Path(args.root),
            dry_run=args.dry_run_dashboard_example_fixtures,
        )
    if args.check_dashboard_example_fixtures:
        return _check_dashboard_example_fixtures(Path(args.root))
    if args.write_dashboard_section_writer_matrix:
        if not args.dashboard_section_writer_matrix_variant:
            parser.error(
                "--write-dashboard-section-writer-matrix requires --dashboard-section-writer-matrix-variant"
            )
        return _write_dashboard_section_writer_matrix(
            Path(args.root),
            args.dashboard_section_writer_matrix_variant,
            dry_run=args.dry_run_dashboard_section_writer_matrix,
        )
    if args.generate_dashboard_section_writer_matrix:
        return _generate_dashboard_section_writer_matrix(Path(args.root), args.dashboard_section_writer_matrix_variant)
    if args.check_dashboard_section_writer_matrix:
        return _check_dashboard_section_writer_matrix(Path(args.root), args.dashboard_section_writer_matrix_variant)
    if args.write_release_examples:
        root = Path(args.root)
        try:
            release_examples_path = _release_examples_path_under_root(root, Path(args.release_examples_path))
        except ValueError as error:
            parser.error(str(error))
        updated = _updated_release_examples(
            root,
            release_examples_path,
            version=args.release_examples_version,
            section=args.release_examples_section,
        )
        if args.dry_run_release_examples:
            print(updated, end="")
        else:
            (root / release_examples_path).write_text(updated, encoding="utf-8")
            print(f"Updated {release_examples_path.as_posix()} release checklist example fence.")
        return 0
    if args.check_release_tag:
        return _check_release_tag(
            Path(args.root),
            args.check_release_tag,
            docker_verified=args.docker_verified,
            skip_git_clean_check=args.skip_git_clean_check,
            json_output=args.json,
        )
    if args.memory_threshold_demo:
        if args.json:
            print(
                json.dumps(
                    memory_threshold_demo_json(
                        by=args.memory_overlap_group_by,
                        prefix_depth=args.memory_overlap_prefix_depth,
                        max_overlap_count=args.memory_overlap_max_count,
                        max_total_overlap_size=args.memory_overlap_max_bytes,
                        name_prefix=args.memory_overlap_name_prefix,
                        tags_all=tuple(args.memory_overlap_tag),
                    ),
                    sort_keys=True,
                )
            )
        else:
            print(
                memory_threshold_demo_markdown(
                    by=args.memory_overlap_group_by,
                    prefix_depth=args.memory_overlap_prefix_depth,
                    max_overlap_count=args.memory_overlap_max_count,
                    max_total_overlap_size=args.memory_overlap_max_bytes,
                    name_prefix=args.memory_overlap_name_prefix,
                    tags_all=tuple(args.memory_overlap_tag),
                )
            )
        return 0
    if args.memory_overlap_totals_demo:
        if args.json:
            print(
                json.dumps(
                    memory_overlap_totals_demo_json(
                        by=args.memory_overlap_group_by,
                        prefix_depth=args.memory_overlap_prefix_depth,
                        name_prefix=args.memory_overlap_name_prefix,
                        tags_all=tuple(args.memory_overlap_tag),
                    ),
                    sort_keys=True,
                )
            )
        else:
            print(
                memory_overlap_totals_demo_markdown(
                    by=args.memory_overlap_group_by,
                    prefix_depth=args.memory_overlap_prefix_depth,
                    name_prefix=args.memory_overlap_name_prefix,
                    tags_all=tuple(args.memory_overlap_tag),
                )
            )
        return 0
    root = Path(args.root)
    report = analyze_project(root)
    try:
        readme_examples_path = _readme_examples_path_under_root(root, Path(args.readme_examples_path))
    except ValueError as error:
        parser.error(str(error))
    if args.generate_readme_examples:
        print(_readme_example_blocks(report))
        return 0
    if args.write_readme_examples:
        if args.dry_run_readme_examples:
            print(
                _updated_readme_example_blocks(
                    root, report, readme_examples_path, section=args.readme_examples_section
                ),
                end="",
            )
        else:
            _write_readme_example_blocks(root, report, readme_examples_path, section=args.readme_examples_section)
            print(
                f"Updated {_readme_examples_path_label(readme_examples_path)} JSON and Markdown example fences."
            )
        return 0
    if args.check_readme_examples:
        mismatches = _readme_example_mismatches(
            root, report, readme_examples_path, section=args.readme_examples_section
        )
        if mismatches:
            label = _readme_examples_path_label(readme_examples_path)
            for language in mismatches:
                print(f"{label} {language} example is out of date.", file=sys.stderr)
            return 1
        print(f"{_readme_examples_path_label(readme_examples_path)} examples match current CLI output.")
        return 0
    if args.json:
        print(json.dumps(report.to_dict(), sort_keys=True))
    elif args.markdown:
        print(report.to_markdown())
    else:
        print(f"Project: {report.project_name}")
        print(f"Backlog: {report.completed_backlog_items} completed, {report.open_backlog_items} open")
        print(f"Next: {report.next_backlog_item or 'None'}")
        if report.has_active_blockers:
            print("Active blockers:")
            for blocker in report.active_blockers:
                print(f"- {blocker}")
        else:
            print("Active blockers: none")
    if args.fail_on_blockers and report.has_active_blockers:
        return 2
    return 0


def _non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return parsed


def _check_changelog_version(root: Path) -> int:
    version = _pyproject_version(root)
    required = f"`{version}`"
    missing = []
    for filename in ("README.md", "CHANGELOG.md"):
        path = root / filename
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        if required not in text:
            missing.append(filename)
    if missing:
        for filename in missing:
            print(f"{filename} does not mention pyproject version {version}.", file=sys.stderr)
        return 1
    print(f"CHANGELOG and README mention pyproject version {version}.")
    return 0


def _pyproject_version(root: Path) -> str:
    pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    return pyproject["project"]["version"]


def _check_release_tag(
    root: Path,
    tag: str,
    *,
    docker_verified: bool,
    skip_git_clean_check: bool,
    json_output: bool = False,
) -> int:
    checklist = _release_tag_checklist(
        root,
        tag,
        docker_verified=docker_verified,
        skip_git_clean_check=skip_git_clean_check,
    )
    version = checklist["version"]
    expected_tag = checklist["expected_tag"]
    tag_matches_version = checklist["checks"]["tag_matches_version"]
    git_clean = checklist["checks"]["git_clean"]
    git_error = checklist["git_error"]
    ready = checklist["ready"]
    if json_output:
        print(json.dumps(_release_tag_checklist_json_payload(checklist), sort_keys=True))
        return 0 if ready else 1

    if not tag_matches_version:
        print(
            f"Release tag {tag} does not match expected tag {expected_tag} from pyproject version {version}.",
            file=sys.stderr,
        )
        return 1
    if not docker_verified:
        print(
            "Release tag check requires --docker-verified evidence from docker compose run --build --rm test.",
            file=sys.stderr,
        )
        return 1
    if git_error:
        print(git_error, end="", file=sys.stderr)
        return 1
    if git_clean is False:
        print("Release tag check requires a clean git working tree.", file=sys.stderr)
        return 1
    print(f"Release tag {tag} matches pyproject version {version} and Docker verification evidence is present.")
    return 0


def _release_tag_checklist(
    root: Path,
    tag: str,
    *,
    docker_verified: bool,
    skip_git_clean_check: bool,
) -> dict:
    version = _pyproject_version(root)
    expected_tag = f"v{version}"
    tag_matches_version = tag == expected_tag
    git_clean: bool | str = "skipped" if skip_git_clean_check else True
    git_error = ""
    if not skip_git_clean_check:
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if status.returncode != 0:
            git_clean = False
            git_error = status.stderr or "git status --porcelain failed.\n"
        elif status.stdout:
            git_clean = False
    ready = tag_matches_version and docker_verified and (git_clean is True or git_clean == "skipped")
    return {
        "checks": {
            "docker_verified": docker_verified,
            "git_clean": git_clean,
            "tag_matches_version": tag_matches_version,
        },
        "expected_tag": expected_tag,
        "git_error": git_error,
        "ready": ready,
        "tag": tag,
        "version": version,
    }


def _release_tag_checklist_json_payload(checklist: dict) -> dict:
    return {key: value for key, value in checklist.items() if key != "git_error"}


def _release_tag_checklist_fixture_output(root: Path, *, version: str | None = None) -> str:
    version = _pyproject_version(root) if version is None else version
    checklist = _release_tag_checklist_for_version(version)
    return json.dumps(_release_tag_checklist_json_payload(checklist), sort_keys=True) + "\n"


def _release_tag_checklist_for_version(version: str) -> dict:
    tag = f"v{version}"
    return {
        "checks": {
            "docker_verified": True,
            "git_clean": "skipped",
            "tag_matches_version": True,
        },
        "expected_tag": tag,
        "git_error": "",
        "ready": True,
        "tag": tag,
        "version": version,
    }


def _check_release_tag_fixture(root: Path, *, version: str | None = None, fixture_path: Path | None = None) -> int:
    expected = _release_tag_checklist_fixture_output(root, version=version)
    fixture_path = Path("tests/fixtures/release-tag-checklist.json") if fixture_path is None else fixture_path
    fixture = root / fixture_path
    actual = fixture.read_text(encoding="utf-8") if fixture.exists() else ""
    label = _release_tag_fixture_path_label(fixture_path)
    if actual != expected:
        print(f"{label} is out of date.", file=sys.stderr)
        return 1
    print(f"{label} matches current CLI output.")
    return 0


def _write_release_tag_fixture(
    root: Path, *, dry_run: bool, version: str | None = None, fixture_path: Path | None = None
) -> int:
    output = _release_tag_checklist_fixture_output(root, version=version)
    if dry_run:
        print(output, end="")
        return 0
    fixture_path = Path("tests/fixtures/release-tag-checklist.json") if fixture_path is None else fixture_path
    fixture = root / fixture_path
    fixture.parent.mkdir(parents=True, exist_ok=True)
    fixture.write_text(output, encoding="utf-8")
    print(f"Updated {_release_tag_fixture_update_label(fixture_path)}.")
    return 0


def _release_tag_fixture_path_label(fixture_path: Path) -> str:
    path_text = fixture_path.as_posix()
    if path_text == "tests/fixtures/release-tag-checklist.json":
        return "Release tag checklist fixture"
    return f"{path_text} release tag checklist fixture"


def _release_tag_fixture_update_label(fixture_path: Path) -> str:
    path_text = fixture_path.as_posix()
    if path_text == "tests/fixtures/release-tag-checklist.json":
        return "release tag checklist fixture"
    return f"{path_text} release tag checklist fixture"


def _release_tag_fixture_path_under_root(root: Path, fixture_path: Path) -> Path:
    if fixture_path.is_absolute():
        raise ValueError("--release-tag-fixture-path must be relative to --root")
    root_resolved = root.resolve()
    target_resolved = (root / fixture_path).resolve()
    try:
        return target_resolved.relative_to(root_resolved)
    except ValueError as error:
        raise ValueError("--release-tag-fixture-path must stay under --root") from error


def _release_examples_mismatch(
    root: Path, examples_path: Path, *, version: str | None = None, section: str | None = None
) -> bool:
    examples = root / examples_path
    text = examples.read_text(encoding="utf-8") if examples.exists() else ""
    expected = _release_tag_checklist_fixture_output(root, version=version).rstrip("\n")
    return _fenced_block_in_section(text, "json", section) != expected


def _updated_release_examples(
    root: Path, examples_path: Path, *, version: str | None = None, section: str | None = None
) -> str:
    examples = root / examples_path
    text = examples.read_text(encoding="utf-8")
    output = _release_tag_checklist_fixture_output(root, version=version).rstrip("\n")
    return _replace_fenced_block_in_section(text, "json", output, section)


def _release_examples_path_under_root(root: Path, examples_path: Path) -> Path:
    if examples_path.is_absolute():
        raise ValueError("--release-examples-path must be relative to --root")
    root_resolved = root.resolve()
    target_resolved = (root / examples_path).resolve()
    try:
        return target_resolved.relative_to(root_resolved)
    except ValueError as error:
        raise ValueError("--release-examples-path must stay under --root") from error


def _check_release_example_fixtures(root: Path) -> int:
    index = root / "docs" / "release-example-fixtures.md"
    compose = root / "docker-compose.yml"
    index_text = index.read_text(encoding="utf-8") if index.exists() else ""
    compose_text = compose.read_text(encoding="utf-8") if compose.exists() else ""
    documented_commands = _release_example_fixture_index_commands(index_text)
    missing_commands = [
        command for command in documented_commands if not _docker_harness_contains_equivalent_command(compose_text, command)
    ]
    if not documented_commands:
        print("Release example fixture index does not list any Docker verification commands.", file=sys.stderr)
        return 1
    if missing_commands:
        for command in missing_commands:
            print(f"Docker harness is missing release example fixture command: {command}", file=sys.stderr)
        return 1
    print("Release example fixture index matches Docker harness commands.")
    return 0


def _check_release_example_sections(root: Path) -> int:
    index = root / "docs" / "release-example-sections.md"
    compose = root / "docker-compose.yml"
    index_text = index.read_text(encoding="utf-8") if index.exists() else ""
    compose_text = compose.read_text(encoding="utf-8") if compose.exists() else ""
    documented_commands = _release_example_section_registry_commands(index_text)
    missing_commands = [
        command for command in documented_commands if not _docker_harness_contains_equivalent_command(compose_text, command)
    ]
    if not documented_commands:
        print("Release example section registry does not list any Docker verification commands.", file=sys.stderr)
        return 1
    if missing_commands:
        for command in missing_commands:
            print(f"Docker harness is missing release example section command: {command}", file=sys.stderr)
        return 1
    print("Release example section registry matches Docker harness commands.")
    return 0


def _check_release_section_writer_matrix(root: Path, future_version: str = "0.2.0") -> int:
    matrix = root / "docs" / "release-section-writer-matrix.md"
    registry = root / "docs" / "release-example-sections.md"
    compose = root / "docker-compose.yml"
    matrix_text = matrix.read_text(encoding="utf-8") if matrix.exists() else ""
    registry_text = registry.read_text(encoding="utf-8") if registry.exists() else ""
    compose_text = compose.read_text(encoding="utf-8") if compose.exists() else ""
    matrix_commands = _release_section_writer_matrix_commands(matrix_text)
    required_current_commands = [
        _release_section_writer_command(command) for command in _release_example_section_registry_commands(registry_text)
    ]
    required_future_commands = [_future_release_section_writer_command(command, future_version) for command in required_current_commands]

    if not matrix_commands:
        print("Release section writer matrix does not list any writer commands.", file=sys.stderr)
        return 1

    missing_current_commands = [command for command in required_current_commands if command not in matrix_commands]
    if missing_current_commands:
        for command in missing_current_commands:
            print(
                f"Release section writer matrix is missing current-version writer command for release section: {command}",
                file=sys.stderr,
            )
        return 1

    missing_future_commands = [command for command in required_future_commands if command not in matrix_commands]
    if missing_future_commands:
        for command in missing_future_commands:
            print(
                f"Release section writer matrix is missing future-version writer command for release section: {command}",
                file=sys.stderr,
            )
        return 1

    missing_docker_commands = [
        command for command in matrix_commands if not _docker_harness_contains_equivalent_command(compose_text, command)
    ]
    if missing_docker_commands:
        for command in missing_docker_commands:
            print(f"Docker harness is missing release section writer matrix command: {command}", file=sys.stderr)
        return 1

    print("Release section writer matrix matches section registry and Docker harness commands.")
    return 0


def _release_section_writer_matrix_rows(root: Path, future_version: str = "0.2.0") -> list[str]:
    registry = root / "docs" / "release-example-sections.md"
    registry_text = registry.read_text(encoding="utf-8") if registry.exists() else ""
    rows: list[str] = []
    for path, section, check_command in _release_example_section_registry_rows(registry_text):
        current_command = _release_section_writer_command(check_command)
        future_command = _future_release_section_writer_command(current_command, future_version)
        rows.append(f"| `{path}` | {section} | Current package version | `{current_command}` |")
        rows.append(f"| `{path}` | {section} | Future package version `{future_version}` | `{future_command}` |")
    return rows


def _generate_release_section_writer_matrix(root: Path, future_version: str = "0.2.0") -> int:
    rows = _release_section_writer_matrix_rows(root, future_version)
    if not rows:
        print("Release example section registry does not list any Docker verification commands.", file=sys.stderr)
        return 1
    for row in rows:
        print(row)
    return 0


def _write_release_section_writer_matrix(root: Path, future_version: str = "0.2.0", *, dry_run: bool = False) -> int:
    rows = _release_section_writer_matrix_rows(root, future_version)
    if not rows:
        print("Release example section registry does not list any Docker verification commands.", file=sys.stderr)
        return 1

    matrix_path = root / "docs" / "release-section-writer-matrix.md"
    matrix_text = matrix_path.read_text(encoding="utf-8") if matrix_path.exists() else ""
    existing_commands = set(_release_section_writer_matrix_commands(matrix_text))
    missing_rows = [row for row in rows if (_single_code_span(row.split("|")[-2]) or "") not in existing_commands]
    if not missing_rows:
        print("docs/release-section-writer-matrix.md already contains release section writer rows.")
        return 0

    updated = _append_release_section_writer_matrix_rows(matrix_text, missing_rows)
    if dry_run:
        print(updated, end="")
    else:
        matrix_path.write_text(updated, encoding="utf-8")
        row_label = "row" if len(missing_rows) == 1 else "rows"
        print(f"Updated docs/release-section-writer-matrix.md with {len(missing_rows)} release section writer {row_label}.")
    return 0


def _append_release_section_writer_matrix_rows(matrix_text: str, rows: list[str]) -> str:
    lines = matrix_text.splitlines()
    insertion_index = 0
    for index, line in enumerate(lines):
        if line.startswith("|"):
            insertion_index = index + 1
    updated_lines = lines[:insertion_index] + rows + lines[insertion_index:]
    trailing_newline = "\n" if matrix_text.endswith("\n") or matrix_text else ""
    return "\n".join(updated_lines) + trailing_newline


def _release_section_writer_command(check_command: str) -> str:
    return check_command.replace("--check-release-examples", "--write-release-examples --dry-run-release-examples", 1)


def _future_release_section_writer_command(writer_command: str, version: str = "0.2.0") -> str:
    marker = " --release-examples-path "
    if marker in writer_command:
        return writer_command.replace(marker, f" --release-examples-version {version} --release-examples-path ", 1)
    return f"{writer_command} --release-examples-version {version}"


def _check_release_examples_path_safety(root: Path) -> int:
    unsafe_cases = (
        (Path("../outside-release-examples.md"), "--release-examples-path must stay under --root"),
        (root.resolve() / "absolute-release-examples.md", "--release-examples-path must be relative to --root"),
    )
    failures: list[str] = []
    for unsafe_path, expected_message in unsafe_cases:
        try:
            _release_examples_path_under_root(root, unsafe_path)
        except ValueError as error:
            if str(error) != expected_message:
                failures.append(f"{unsafe_path}: expected {expected_message!r}, got {str(error)!r}")
        else:
            failures.append(f"{unsafe_path}: accepted unsafe release examples path")
    if failures:
        for failure in failures:
            print(f"Release examples path safety audit failed: {failure}", file=sys.stderr)
        return 1
    print("Release examples path safety audit passed.")
    return 0


def _check_automation_index_links(root: Path) -> int:
    automation_index = root / "docs" / "automation-index.md"
    text = automation_index.read_text(encoding="utf-8") if automation_index.exists() else ""
    missing = [
        docs_path
        for docs_path in _standalone_automation_surface_paths()
        if f"({_automation_index_href(docs_path)})" not in text
    ]
    if missing:
        for docs_path in missing:
            print(f"Automation index is missing link to {docs_path}.", file=sys.stderr)
        return 1
    print("Automation index links every standalone automation surface.")
    return 0


def _check_automation_index_commands(root: Path) -> int:
    automation_index = root / "docs" / "automation-index.md"
    compose = root / "docker-compose.yml"
    index_text = automation_index.read_text(encoding="utf-8") if automation_index.exists() else ""
    compose_text = compose.read_text(encoding="utf-8") if compose.exists() else ""
    documented_commands = _automation_index_r_project_commands(index_text)
    missing_commands = [
        command for command in documented_commands if not _docker_harness_contains_equivalent_command(compose_text, command)
    ]
    if not documented_commands:
        print("Automation index does not document any r-project verification commands.", file=sys.stderr)
        return 1
    if missing_commands:
        for command in missing_commands:
            print(f"Docker harness is missing automation index command: {command}", file=sys.stderr)
        return 1
    print("Automation index commands match Docker harness commands.")
    return 0


def _check_automation_command_fixtures(root: Path) -> int:
    fixture_index = root / "docs" / "automation-command-fixtures.md"
    automation_index = root / "docs" / "automation-index.md"
    compose = root / "docker-compose.yml"
    index_text = fixture_index.read_text(encoding="utf-8") if fixture_index.exists() else ""
    automation_index_text = automation_index.read_text(encoding="utf-8") if automation_index.exists() else ""
    compose_text = compose.read_text(encoding="utf-8") if compose.exists() else ""
    documented_commands = _automation_command_fixture_index_commands(index_text)
    missing_index_commands = [
        command for command in _automation_index_r_project_commands(automation_index_text) if command not in documented_commands
    ]
    missing_commands = [
        command for command in documented_commands if not _docker_harness_contains_equivalent_command(compose_text, command)
    ]
    if not documented_commands:
        print("Automation command fixture index does not document any r-project commands.", file=sys.stderr)
        return 1
    if missing_index_commands:
        for command in missing_index_commands:
            print(f"Automation command fixture index is missing automation-index command: {command}", file=sys.stderr)
        return 1
    if missing_commands:
        for command in missing_commands:
            print(f"Docker harness is missing automation command fixture: {command}", file=sys.stderr)
        return 1
    print("Automation command fixture index matches Docker harness commands.")
    return 0


def _check_release_automation_index(root: Path, version: str = "0.2.0") -> int:
    release_index = root / "docs" / "release-automation-index.md"
    compose = root / "docker-compose.yml"
    index_text = release_index.read_text(encoding="utf-8") if release_index.exists() else ""
    compose_text = compose.read_text(encoding="utf-8") if compose.exists() else ""

    missing_links = [
        docs_path
        for docs_path in _standalone_release_automation_surface_paths()
        if f"({_automation_index_href(docs_path)})" not in index_text
    ]
    if missing_links:
        for docs_path in missing_links:
            print(f"Release automation index is missing link to {docs_path}.", file=sys.stderr)
        return 1

    documented_commands = _release_automation_index_r_project_commands(index_text)
    if not documented_commands:
        print("Release automation index does not document any r-project verification commands.", file=sys.stderr)
        return 1

    missing_profile_commands = [
        command for command in _release_automation_index_required_commands(version) if command not in documented_commands
    ]
    if version != "0.2.0" and missing_profile_commands:
        for command in missing_profile_commands:
            print(f"Release automation index is missing version {version} command: {command}", file=sys.stderr)
        return 1

    missing_commands = [
        command for command in documented_commands if not _docker_harness_contains_equivalent_command(compose_text, command)
    ]
    if missing_commands:
        for command in missing_commands:
            print(f"Docker harness is missing release automation index command: {command}", file=sys.stderr)
        return 1

    print(f"Release automation index links release surfaces, version {version} commands, and Docker harness commands.")
    return 0


def _generate_release_automation_index(root: Path, version: str = "0.2.0") -> int:
    del root
    for row in _release_automation_index_surface_rows():
        print(row)
    print()
    print("```bash")
    for command in _release_automation_index_required_commands(version):
        print(command)
    print("```")
    return 0


def _write_release_automation_index(root: Path, *, dry_run: bool = False, version: str = "0.2.0") -> int:
    release_index = root / "docs" / "release-automation-index.md"
    index_text = release_index.read_text(encoding="utf-8") if release_index.exists() else _release_automation_index_skeleton()
    updated = _updated_release_automation_index(index_text, version)
    if updated == index_text:
        print("docs/release-automation-index.md already contains release automation links and commands.")
        return 0
    if dry_run:
        print(updated, end="")
    else:
        release_index.parent.mkdir(parents=True, exist_ok=True)
        release_index.write_text(updated, encoding="utf-8")
        print("Updated docs/release-automation-index.md with release automation links and commands.")
    return 0


def _updated_release_automation_index(index_text: str, version: str = "0.2.0") -> str:
    text = index_text if index_text else _release_automation_index_skeleton()
    existing_links = {
        docs_path
        for docs_path in _standalone_release_automation_surface_paths()
        if f"({_automation_index_href(docs_path)})" in text
    }
    missing_link_rows = [
        row
        for docs_path, row in zip(_standalone_release_automation_surface_paths(), _release_automation_index_surface_rows())
        if docs_path not in existing_links
    ]
    existing_commands = set(_release_automation_index_r_project_commands(text))
    missing_commands = [command for command in _release_automation_index_required_commands(version) if command not in existing_commands]
    if missing_link_rows:
        text = _append_markdown_list_rows_to_section(text, "Release surfaces", missing_link_rows)
    if missing_commands:
        text = _append_bash_fence_commands(text, missing_commands)
    return text


def _release_automation_index_skeleton() -> str:
    return """# Release Automation Index

## Release surfaces

## Verification commands

```bash
```
"""


def _release_automation_index_surface_rows() -> list[str]:
    return [
        f"- [{_release_automation_surface_label(docs_path)}]({_automation_index_href(docs_path)})"
        for docs_path in _standalone_release_automation_surface_paths()
    ]


def _release_automation_surface_label(docs_path: str) -> str:
    labels = {
        "docs/release-index.md": "release readiness index",
        "docs/release-checklist.md": "release checklist fixture docs",
        "docs/release/checklist.json": "release checklist JSON fixture",
        "docs/release-examples.md": "release checklist examples",
        "docs/release-example-fixtures.md": "release example fixture registry",
        "docs/release-example-sections.md": "release example section registry",
        "docs/release-section-writer-matrix.md": "release section writer matrix",
    }
    return labels[docs_path]


def _release_automation_index_required_commands(version: str = "0.2.0") -> list[str]:
    return [
        "r-project --root . --check-changelog-version",
        "r-project --root . --check-release-tag v0.1.0 --docker-verified",
        "r-project --root . --check-release-tag-fixture --release-tag-fixture-path docs/release/checklist.json",
        "r-project --root . --check-release-examples --release-examples-path docs/release-examples.md",
        f"r-project --root . --write-release-examples --dry-run-release-examples --release-examples-version {version} --release-examples-path docs/release-examples.md",
        f"r-project --root . --write-release-examples --dry-run-release-examples --release-examples-version {version} --release-examples-path tests/fixtures/release-examples-future-version-smoke.md",
        "r-project --root . --check-release-example-fixtures",
        "r-project --root . --check-release-example-sections",
        "r-project --root . --check-release-section-writer-matrix",
        f"r-project --root . --check-release-section-writer-matrix --release-section-writer-matrix-version {version}",
        f"r-project --root . --generate-release-section-writer-matrix --release-section-writer-matrix-version {version}",
        f"r-project --root . --write-release-section-writer-matrix --dry-run-release-section-writer-matrix --release-section-writer-matrix-version {version}",
        "r-project --root . --check-release-examples-path-safety",
        "r-project --root . --generate-release-automation-index",
        "r-project --root . --write-release-automation-index --dry-run-release-automation-index",
        "r-project --root . --check-release-automation-index",
    ]


def _check_dashboard_automation_index(root: Path, variant: str | None = None) -> int:
    dashboard_index = root / "docs" / "dashboard-automation-index.md"
    compose = root / "docker-compose.yml"
    index_text = dashboard_index.read_text(encoding="utf-8") if dashboard_index.exists() else ""
    compose_text = compose.read_text(encoding="utf-8") if compose.exists() else ""

    missing_links = [
        docs_path
        for docs_path in _standalone_dashboard_automation_surface_paths()
        if f"({_automation_index_href(docs_path)})" not in index_text
    ]
    if missing_links:
        for docs_path in missing_links:
            print(f"Dashboard automation index is missing link to {docs_path}.", file=sys.stderr)
        return 1

    documented_commands = _dashboard_automation_index_r_project_commands(index_text)
    if not documented_commands:
        print("Dashboard automation index does not document any r-project verification commands.", file=sys.stderr)
        return 1

    required_commands = _dashboard_automation_index_required_commands(variant)
    missing_required_commands = [command for command in required_commands if command not in documented_commands]
    if missing_required_commands:
        for command in missing_required_commands:
            label = "variant command" if variant else "command"
            print(f"Dashboard automation index is missing {label}: {command}", file=sys.stderr)
        return 1

    missing_commands = [
        command for command in documented_commands if not _docker_harness_contains_equivalent_command(compose_text, command)
    ]
    if missing_commands:
        for command in missing_commands:
            print(f"Docker harness is missing dashboard automation index command: {command}", file=sys.stderr)
        return 1

    print("Dashboard automation index links dashboard surfaces and matches Docker harness commands.")
    return 0


def _generate_dashboard_automation_index(root: Path, variant: str | None = None) -> int:
    del root
    for row in _dashboard_automation_index_surface_rows():
        print(row)
    print()
    print("```bash")
    for command in _dashboard_automation_index_required_commands(variant):
        print(command)
    print("```")
    return 0


def _write_dashboard_automation_index(root: Path, *, dry_run: bool = False, variant: str | None = None) -> int:
    dashboard_index = root / "docs" / "dashboard-automation-index.md"
    index_text = dashboard_index.read_text(encoding="utf-8") if dashboard_index.exists() else _dashboard_automation_index_skeleton()
    updated = _updated_dashboard_automation_index(index_text, variant)
    if updated == index_text:
        print("docs/dashboard-automation-index.md already contains dashboard automation links and commands.")
        return 0
    if dry_run:
        print(updated, end="")
    else:
        dashboard_index.parent.mkdir(parents=True, exist_ok=True)
        dashboard_index.write_text(updated, encoding="utf-8")
        print("Updated docs/dashboard-automation-index.md with dashboard automation links and commands.")
    return 0


def _updated_dashboard_automation_index(index_text: str, variant: str | None = None) -> str:
    text = index_text if index_text else _dashboard_automation_index_skeleton()
    existing_links = {
        docs_path
        for docs_path in _standalone_dashboard_automation_surface_paths()
        if f"({_automation_index_href(docs_path)})" in text
    }
    missing_link_rows = [
        row
        for docs_path, row in zip(_standalone_dashboard_automation_surface_paths(), _dashboard_automation_index_surface_rows())
        if docs_path not in existing_links
    ]
    existing_commands = set(_dashboard_automation_index_r_project_commands(text))
    missing_commands = [
        command for command in _dashboard_automation_index_required_commands(variant) if command not in existing_commands
    ]
    if missing_link_rows:
        text = _append_markdown_list_rows_to_section(text, "Dashboard surfaces", missing_link_rows)
    if missing_commands:
        text = _append_bash_fence_commands(text, missing_commands)
    return text


def _dashboard_automation_index_skeleton() -> str:
    return """# Dashboard Automation Index

## Dashboard surfaces

## Verification commands

```bash
```
"""


def _dashboard_automation_index_surface_rows() -> list[str]:
    return [
        f"- [{_dashboard_automation_surface_label(docs_path)}]({_automation_index_href(docs_path)})"
        for docs_path in _standalone_dashboard_automation_surface_paths()
    ]


def _dashboard_automation_surface_label(docs_path: str) -> str:
    labels = {
        "docs/dashboard-index.md": "dashboard readiness/schema index",
        "docs/usage-examples.md": "readiness report examples",
        "docs/dashboard-schema.md": "memory-overlap schema examples",
        "docs/dashboard-example-fixtures.md": "dashboard example fixture registry",
        "docs/dashboard-section-writer-matrix.md": "dashboard section writer matrix",
    }
    return labels[docs_path]


def _dashboard_automation_index_required_commands(variant: str | None = None) -> list[str]:
    section_writer_variant = variant or "compact"
    automation_variant_suffix = f" --dashboard-automation-index-variant {variant}" if variant else ""
    return [
        "r-project --root . --check-readme-examples --readme-examples-path docs/dashboard-index.md",
        "r-project --root . --check-readme-schema-examples --readme-schema-path docs/dashboard-index.md",
        "r-project --root . --generate-dashboard-example-fixtures",
        "r-project --root . --write-dashboard-example-fixtures --dry-run-dashboard-example-fixtures",
        "r-project --root . --check-dashboard-example-fixtures",
        "r-project --root . --check-dashboard-section-writer-matrix",
        f"r-project --root . --check-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant {section_writer_variant}",
        f"r-project --root . --generate-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant {section_writer_variant}",
        f"r-project --root . --write-dashboard-section-writer-matrix --dry-run-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant {section_writer_variant}",
        f"r-project --root . --generate-dashboard-automation-index{automation_variant_suffix}",
        f"r-project --root . --write-dashboard-automation-index --dry-run-dashboard-automation-index{automation_variant_suffix}",
        f"r-project --root . --check-dashboard-automation-index{automation_variant_suffix}",
    ]


def _append_markdown_list_rows_to_section(text: str, section: str, rows: list[str]) -> str:
    section_start = _markdown_section_start(text, section)
    if section_start == -1:
        insertion = f"\n## {section}\n\n" + "\n".join(rows) + "\n"
        return text.rstrip() + insertion + ("\n" if text else "")
    next_section = _next_markdown_section_start(text, section_start + 1)
    section_end = len(text) if next_section == -1 else next_section
    insertion_index = section_end
    section_text = text[section_start:section_end]
    for line_start, line in _line_offsets(section_text):
        if line.startswith("-"):
            insertion_index = section_start + line_start + len(line)
    insertion = ("\n" if insertion_index > 0 and text[insertion_index - 1] != "\n" else "") + "\n".join(rows) + "\n"
    return text[:insertion_index] + insertion + text[insertion_index:]


def _append_bash_fence_commands(text: str, commands: list[str]) -> str:
    fence_start = text.find("```bash\n")
    if fence_start == -1:
        insertion = "\n```bash\n" + "\n".join(commands) + "\n```\n"
        return text.rstrip() + insertion
    fence_end = text.find("\n```", fence_start + len("```bash\n"))
    if fence_end == -1:
        return text.rstrip() + "\n" + "\n".join(commands) + "\n```\n"
    insertion = ("\n" if fence_end > 0 and text[fence_end - 1] != "\n" else "") + "\n".join(commands)
    return text[:fence_end] + insertion + text[fence_end:]


def _line_offsets(text: str) -> list[tuple[int, str]]:
    offsets: list[tuple[int, str]] = []
    start = 0
    for line in text.splitlines(keepends=True):
        offsets.append((start, line))
        start += len(line)
    return offsets


def _check_dashboard_example_fixtures(root: Path) -> int:
    fixture_index = root / "docs" / "dashboard-example-fixtures.md"
    dashboard_index = root / "docs" / "dashboard-index.md"
    compose = root / "docker-compose.yml"
    index_text = fixture_index.read_text(encoding="utf-8") if fixture_index.exists() else ""
    dashboard_index_text = dashboard_index.read_text(encoding="utf-8") if dashboard_index.exists() else ""
    compose_text = compose.read_text(encoding="utf-8") if compose.exists() else ""
    documented_commands = _dashboard_example_fixture_registry_commands(index_text)
    missing_index_commands = [
        command for command in _dashboard_index_r_project_commands(dashboard_index_text) if command not in documented_commands
    ]
    missing_commands = [
        command for command in documented_commands if not _docker_harness_contains_equivalent_command(compose_text, command)
    ]
    if not documented_commands:
        print("Dashboard example fixture registry does not document any r-project commands.", file=sys.stderr)
        return 1
    if missing_index_commands:
        for command in missing_index_commands:
            print(f"Dashboard example fixture registry is missing dashboard-index command: {command}", file=sys.stderr)
        return 1
    if missing_commands:
        for command in missing_commands:
            print(f"Docker harness is missing dashboard example fixture command: {command}", file=sys.stderr)
        return 1
    print("Dashboard example fixture registry matches Docker harness commands.")
    return 0


def _dashboard_example_fixture_rows_from_dashboard_index(root: Path) -> list[str]:
    dashboard_index = root / "docs" / "dashboard-index.md"
    dashboard_index_text = dashboard_index.read_text(encoding="utf-8") if dashboard_index.exists() else ""
    return [
        f"| `{_dashboard_example_command_path(command)}` | {_dashboard_example_command_purpose(command)} | `{command}` |"
        for command in _dashboard_index_r_project_commands(dashboard_index_text)
    ]


def _generate_dashboard_example_fixtures(root: Path) -> int:
    rows = _dashboard_example_fixture_rows_from_dashboard_index(root)
    if not rows:
        print("Dashboard index does not document any r-project commands.", file=sys.stderr)
        return 1
    for row in rows:
        print(row)
    return 0


def _write_dashboard_example_fixtures(root: Path, *, dry_run: bool = False) -> int:
    rows = _dashboard_example_fixture_rows_from_dashboard_index(root)
    if not rows:
        print("Dashboard index does not document any r-project commands.", file=sys.stderr)
        return 1

    fixture_path = root / "docs" / "dashboard-example-fixtures.md"
    fixture_text = fixture_path.read_text(encoding="utf-8") if fixture_path.exists() else ""
    existing_commands = set(_dashboard_example_fixture_registry_commands(fixture_text))
    missing_rows = [row for row in rows if (_single_code_span(row.split("|")[-2]) or "") not in existing_commands]
    if not missing_rows:
        print("docs/dashboard-example-fixtures.md already contains dashboard fixture rows.")
        return 0

    updated = _append_dashboard_example_fixture_rows(fixture_text, missing_rows)
    if dry_run:
        print(updated, end="")
    else:
        fixture_path.write_text(updated, encoding="utf-8")
        row_label = "row" if len(missing_rows) == 1 else "rows"
        print(f"Updated docs/dashboard-example-fixtures.md with {len(missing_rows)} dashboard fixture {row_label}.")
    return 0


def _append_dashboard_example_fixture_rows(fixture_text: str, rows: list[str]) -> str:
    lines = fixture_text.splitlines()
    insertion_index = 0
    for index, line in enumerate(lines):
        if line.startswith("|"):
            insertion_index = index + 1
    updated_lines = lines[:insertion_index] + rows + lines[insertion_index:]
    trailing_newline = "\n" if fixture_text.endswith("\n") or fixture_text else ""
    return "\n".join(updated_lines) + trailing_newline


def _dashboard_example_command_path(command: str) -> str:
    parts = command.split()
    for option in ("--readme-examples-path", "--readme-schema-path"):
        if option in parts:
            option_index = parts.index(option)
            if option_index + 1 < len(parts):
                return parts[option_index + 1]
    return "docs/dashboard-index.md"


def _dashboard_example_command_purpose(command: str) -> str:
    path = _dashboard_example_command_path(command)
    prefix = "Dashboard" if path == "docs/dashboard-index.md" else "Standalone"
    if "--check-readme-examples" in command:
        return f"{prefix} readiness report examples."
    if "--check-readme-schema-examples" in command:
        return f"{prefix} memory-overlap schema example."
    return f"{prefix} dashboard verification command."


def _dashboard_section_writer_matrix_rows(root: Path, variant: str | None = None) -> list[str]:
    registry = root / "docs" / "dashboard-example-fixtures.md"
    registry_text = registry.read_text(encoding="utf-8") if registry.exists() else ""
    rows: list[str] = []
    for path, purpose, check_command in _dashboard_example_fixture_registry_rows(registry_text):
        writer_command = _dashboard_section_writer_command(check_command)
        section = _dashboard_section_writer_section_label(writer_command)
        example_type = purpose.rstrip(".")
        if variant:
            section = f"Variant `{variant}` {section}"
            if example_type:
                example_type = f"Variant `{variant}` {example_type[0].lower()}{example_type[1:]}"
            else:
                example_type = f"Variant `{variant}` dashboard writer dry-run"
        rows.append(f"| `{path}` | {section} | {example_type} | `{writer_command}` |")
    return rows


def _generate_dashboard_section_writer_matrix(root: Path, variant: str | None = None) -> int:
    rows = _dashboard_section_writer_matrix_rows(root, variant)
    if not rows:
        print("Dashboard example fixture registry does not document any r-project commands.", file=sys.stderr)
        return 1
    for row in rows:
        print(row)
    return 0


def _write_dashboard_section_writer_matrix(root: Path, variant: str, *, dry_run: bool = False) -> int:
    rows = _dashboard_section_writer_matrix_rows(root, variant)
    if not rows:
        print("Dashboard example fixture registry does not document any r-project commands.", file=sys.stderr)
        return 1

    matrix_path = root / "docs" / "dashboard-section-writer-matrix.md"
    matrix_text = matrix_path.read_text(encoding="utf-8") if matrix_path.exists() else ""
    existing_variant_commands = set(_dashboard_section_writer_matrix_variant_commands(matrix_text, variant))
    missing_rows = [
        row
        for row in rows
        if (_single_code_span(row.split("|")[-2]) or "") not in existing_variant_commands
    ]
    if not missing_rows:
        print(f"docs/dashboard-section-writer-matrix.md already contains dashboard variant {variant} writer rows.")
        return 0

    updated = _append_dashboard_section_writer_matrix_rows(matrix_text, missing_rows)
    if dry_run:
        print(updated, end="")
    else:
        matrix_path.write_text(updated, encoding="utf-8")
        row_label = "row" if len(missing_rows) == 1 else "rows"
        print(
            f"Updated docs/dashboard-section-writer-matrix.md with {len(missing_rows)} "
            f"dashboard variant {variant} writer {row_label}."
        )
    return 0


def _append_dashboard_section_writer_matrix_rows(matrix_text: str, rows: list[str]) -> str:
    lines = matrix_text.splitlines()
    insertion_index = 0
    for index, line in enumerate(lines):
        if line.startswith("|"):
            insertion_index = index + 1
    updated_lines = lines[:insertion_index] + rows + lines[insertion_index:]
    trailing_newline = "\n" if matrix_text.endswith("\n") or matrix_text else ""
    return "\n".join(updated_lines) + trailing_newline


def _check_dashboard_section_writer_matrix(root: Path, variant: str | None = None) -> int:
    matrix = root / "docs" / "dashboard-section-writer-matrix.md"
    registry = root / "docs" / "dashboard-example-fixtures.md"
    compose = root / "docker-compose.yml"
    matrix_text = matrix.read_text(encoding="utf-8") if matrix.exists() else ""
    registry_text = registry.read_text(encoding="utf-8") if registry.exists() else ""
    compose_text = compose.read_text(encoding="utf-8") if compose.exists() else ""
    matrix_commands = _dashboard_section_writer_matrix_commands(matrix_text)
    required_writer_commands = [
        _dashboard_section_writer_command(command) for command in _dashboard_example_fixture_registry_commands(registry_text)
    ]

    if not matrix_commands:
        print("Dashboard section writer matrix does not list any writer commands.", file=sys.stderr)
        return 1

    missing_writer_commands = [command for command in required_writer_commands if command not in matrix_commands]
    if missing_writer_commands:
        for command in missing_writer_commands:
            print(
                f"Dashboard section writer matrix is missing writer command for dashboard fixture: {command}",
                file=sys.stderr,
            )
        return 1

    if variant:
        variant_commands = _dashboard_section_writer_matrix_variant_commands(matrix_text, variant)
        missing_variant_commands = [command for command in required_writer_commands if command not in variant_commands]
        if missing_variant_commands:
            for command in missing_variant_commands:
                print(
                    f"Dashboard section writer matrix is missing variant {variant} writer command for dashboard fixture: {command}",
                    file=sys.stderr,
                )
            return 1

    missing_docker_commands = [
        command for command in matrix_commands if not _docker_harness_contains_equivalent_command(compose_text, command)
    ]
    if missing_docker_commands:
        for command in missing_docker_commands:
            print(f"Docker harness is missing dashboard section writer matrix command: {command}", file=sys.stderr)
        return 1

    if variant:
        print(f"Dashboard section writer matrix matches fixture registry, variant {variant} rows, and Docker harness commands.")
    else:
        print("Dashboard section writer matrix matches fixture registry and Docker harness commands.")
    return 0


def _dashboard_section_writer_command(check_command: str) -> str:
    if "--check-readme-examples" in check_command:
        return check_command.replace("--check-readme-examples", "--write-readme-examples --dry-run-readme-examples", 1)
    if "--check-readme-schema-examples" in check_command:
        return check_command.replace(
            "--check-readme-schema-examples", "--write-readme-schema-examples --dry-run-readme-schema-examples", 1
        )
    return check_command


def _standalone_automation_surface_paths() -> tuple[str, ...]:
    return (
        "docs/dashboard-automation-index.md",
        "docs/dashboard-index.md",
        "docs/usage-examples.md",
        "docs/dashboard-schema.md",
        "docs/dashboard-example-fixtures.md",
        "docs/dashboard-section-writer-matrix.md",
        "docs/release-automation-index.md",
        "docs/release-index.md",
        "docs/release-checklist.md",
        "docs/release/checklist.json",
        "docs/release-examples.md",
        "docs/release-example-fixtures.md",
        "docs/release-example-sections.md",
        "docs/release-section-writer-matrix.md",
        "docs/automation-command-fixtures.md",
    )


def _standalone_dashboard_automation_surface_paths() -> tuple[str, ...]:
    return (
        "docs/dashboard-index.md",
        "docs/usage-examples.md",
        "docs/dashboard-schema.md",
        "docs/dashboard-example-fixtures.md",
        "docs/dashboard-section-writer-matrix.md",
    )


def _standalone_release_automation_surface_paths() -> tuple[str, ...]:
    return (
        "docs/release-index.md",
        "docs/release-checklist.md",
        "docs/release/checklist.json",
        "docs/release-examples.md",
        "docs/release-example-fixtures.md",
        "docs/release-example-sections.md",
        "docs/release-section-writer-matrix.md",
    )


def _automation_index_href(docs_path: str) -> str:
    return docs_path.removeprefix("docs/")


def _automation_index_r_project_commands(index_text: str) -> list[str]:
    return _r_project_commands_in_bash_fences(index_text)


def _release_automation_index_r_project_commands(index_text: str) -> list[str]:
    return _r_project_commands_in_bash_fences(index_text)


def _dashboard_automation_index_r_project_commands(index_text: str) -> list[str]:
    return _r_project_commands_in_bash_fences(index_text)


def _dashboard_index_r_project_commands(index_text: str) -> list[str]:
    return _r_project_commands_in_bash_fences(index_text)


def _r_project_commands_in_bash_fences(index_text: str) -> list[str]:
    commands: list[str] = []
    in_bash_fence = False
    for line in index_text.splitlines():
        stripped = line.strip()
        if stripped == "```bash":
            in_bash_fence = True
            continue
        if in_bash_fence and stripped == "```":
            in_bash_fence = False
            continue
        if in_bash_fence and stripped.startswith(("r-project ", "python -m r_project ")):
            commands.append(stripped)
    return commands


def _release_example_fixture_index_commands(index_text: str) -> list[str]:
    return _markdown_table_code_span_commands(index_text)


def _release_example_section_registry_commands(index_text: str) -> list[str]:
    return _markdown_table_code_span_commands(index_text)


def _release_example_section_registry_rows(index_text: str) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for line in index_text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 3 or cells[0] in {"Markdown path", "---"}:
            continue
        path = _single_code_span(cells[0])
        command = _single_code_span(cells[-1])
        if path is not None and command is not None:
            rows.append((path, cells[1], command))
    return rows


def _release_section_writer_matrix_commands(index_text: str) -> list[str]:
    return _markdown_table_code_span_commands(index_text)


def _automation_command_fixture_index_commands(index_text: str) -> list[str]:
    return _markdown_table_code_span_commands(index_text)


def _dashboard_example_fixture_registry_commands(index_text: str) -> list[str]:
    return _markdown_table_code_span_commands(index_text)


def _dashboard_example_fixture_registry_rows(index_text: str) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for line in index_text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 3 or cells[0] in {"Markdown path", "---"}:
            continue
        path = _single_code_span(cells[0])
        command = _single_code_span(cells[-1])
        if path is not None and command is not None:
            rows.append((path, cells[1], command))
    return rows


def _dashboard_section_writer_section_label(writer_command: str) -> str:
    if "--write-readme-examples" in writer_command:
        return "first JSON and Markdown fences"
    if "--write-readme-schema-examples" in writer_command:
        return "memory overlap demo JSON Schemas"
    return "writer dry-run"


def _dashboard_section_writer_matrix_commands(index_text: str) -> list[str]:
    return _markdown_table_code_span_commands(index_text)


def _dashboard_section_writer_matrix_variant_commands(index_text: str, variant: str) -> list[str]:
    commands: list[str] = []
    variant_marker = f"Variant `{variant}`"
    for line in index_text.splitlines():
        if variant_marker not in line:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells:
            continue
        command = _single_code_span(cells[-1])
        if command is not None:
            commands.append(command)
    return commands


def _markdown_table_code_span_commands(index_text: str) -> list[str]:
    commands: list[str] = []
    for line in index_text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 3 or cells[0] in {"Fixture", "---"}:
            continue
        command = _single_code_span(cells[-1])
        if command is not None:
            commands.append(command)
    return commands


def _single_code_span(text: str) -> str | None:
    start = text.find("`")
    if start == -1:
        return None
    end = text.find("`", start + 1)
    if end == -1:
        return None
    return text[start + 1 : end]


def _docker_harness_contains_equivalent_command(compose_text: str, documented_command: str) -> bool:
    documented_suffix = _release_example_command_suffix(documented_command)
    return documented_suffix in compose_text


def _release_example_command_suffix(command: str) -> str:
    for prefix in ("r-project ", "python -m r_project "):
        if command.startswith(prefix):
            return command[len(prefix) :]
    return command


def _readme_example_mismatches(
    root: Path, report, readme_examples_path: Path = Path("README.md"), *, section: str | None = None
) -> list[str]:
    readme = root / readme_examples_path
    text = readme.read_text(encoding="utf-8") if readme.exists() else ""
    expected = {
        "json": json.dumps(report.to_dict(), sort_keys=True),
        "markdown": report.to_markdown(),
    }
    return [language for language, output in expected.items() if _fenced_block_in_section(text, language, section) != output]


def _readme_example_blocks(report) -> str:
    return "\n\n".join(
        [
            f"```json\n{json.dumps(report.to_dict(), sort_keys=True)}\n```",
            f"```markdown\n{report.to_markdown()}\n```",
        ]
    )


def _write_readme_example_blocks(
    root: Path, report, readme_examples_path: Path = Path("README.md"), *, section: str | None = None
) -> None:
    readme = root / readme_examples_path
    readme.write_text(_updated_readme_example_blocks(root, report, readme_examples_path, section=section), encoding="utf-8")


def _updated_readme_example_blocks(
    root: Path, report, readme_examples_path: Path = Path("README.md"), *, section: str | None = None
) -> str:
    readme = root / readme_examples_path
    text = readme.read_text(encoding="utf-8")
    replacements = {
        "json": json.dumps(report.to_dict(), sort_keys=True),
        "markdown": report.to_markdown(),
    }
    for language, output in replacements.items():
        text = _replace_fenced_block_in_section(text, language, output, section)
    return text


def _readme_examples_path_label(readme_examples_path: Path) -> str:
    path_text = readme_examples_path.as_posix()
    return "README" if path_text == "README.md" else path_text


def _readme_examples_path_under_root(root: Path, readme_examples_path: Path) -> Path:
    if readme_examples_path.is_absolute():
        raise ValueError("--readme-examples-path must be relative to --root")
    root_resolved = root.resolve()
    target_resolved = (root / readme_examples_path).resolve()
    try:
        return target_resolved.relative_to(root_resolved)
    except ValueError as error:
        raise ValueError("--readme-examples-path must stay under --root") from error


def _fenced_block(text: str, language: str) -> str | None:
    marker = f"```{language}\n"
    start = text.find(marker)
    if start == -1:
        return None
    content_start = start + len(marker)
    end = text.find("\n```", content_start)
    if end == -1:
        return None
    return text[content_start:end]


def _fenced_block_in_section(text: str, language: str, section: str | None) -> str | None:
    if section is None:
        return _fenced_block(text, language)
    section_text = _markdown_section_text(text, section)
    if section_text is None:
        return None
    return _fenced_block(section_text, language)


def _replace_fenced_block_in_section(text: str, language: str, output: str, section: str | None) -> str:
    if section is None:
        return _replace_fenced_block(text, language, output)
    section_start = _markdown_section_start(text, section)
    if section_start == -1:
        raise ValueError(f"README is missing a {section} section")
    marker = f"```{language}\n"
    start = text.find(marker, section_start)
    if start == -1:
        raise ValueError(f"README section {section} is missing a {language} fenced block")
    next_section = _next_markdown_section_start(text, section_start + 1)
    if next_section != -1 and start > next_section:
        raise ValueError(f"README section {section} is missing a {language} fenced block")
    content_start = start + len(marker)
    end = text.find("\n```", content_start)
    if end == -1 or (next_section != -1 and end > next_section):
        raise ValueError(f"README section {section} has an unterminated {language} fenced block")
    return f"{text[:content_start]}{output}{text[end:]}"


def _markdown_section_text(text: str, section: str) -> str | None:
    section_start = _markdown_section_start(text, section)
    if section_start == -1:
        return None
    next_section = _next_markdown_section_start(text, section_start + 1)
    if next_section == -1:
        return text[section_start:]
    return text[section_start:next_section]


def _markdown_section_start(text: str, section: str) -> int:
    for prefix in ("#", "##", "###", "####", "#####", "######"):
        marker = f"{prefix} {section}\n"
        start = text.find(marker)
        if start != -1:
            return start
    return -1


def _next_markdown_section_start(text: str, start: int) -> int:
    in_fence = False
    line_start = 0
    while line_start < len(text):
        line_end = text.find("\n", line_start)
        if line_end == -1:
            line_end = len(text)
        line = text[line_start:line_end]
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
        if line_start >= start and not in_fence and line.startswith(("# ", "## ", "### ", "#### ", "##### ", "###### ")):
            return line_start
        line_start = line_end + 1
    return -1


def _replace_fenced_block(text: str, language: str, output: str) -> str:
    marker = f"```{language}\n"
    start = text.find(marker)
    if start == -1:
        raise ValueError(f"README is missing a {language} fenced block")
    content_start = start + len(marker)
    end = text.find("\n```", content_start)
    if end == -1:
        raise ValueError(f"README has an unterminated {language} fenced block")
    return f"{text[:content_start]}{output}{text[end:]}"


def _readme_schema_example_mismatch(
    root: Path, readme_schema_path: Path = Path("README.md"), *, section: str | None = None
) -> bool:
    readme = root / readme_schema_path
    text = readme.read_text(encoding="utf-8") if readme.exists() else ""
    return _memory_overlap_schema_fenced_block(text, section=section) != _compact_memory_overlap_demo_schema_output()


def _updated_readme_schema_example_block(
    root: Path, readme_schema_path: Path = Path("README.md"), *, section: str | None = None
) -> str:
    readme = root / readme_schema_path
    text = readme.read_text(encoding="utf-8")
    if section is not None:
        return _replace_fenced_block_in_section(text, "json", _compact_memory_overlap_demo_schema_output(), section)
    heading = "## Memory overlap demo JSON Schemas"
    heading_start = text.find(heading)
    if heading_start == -1:
        raise ValueError(f"{_readme_schema_path_label(readme_schema_path)} is missing the memory-overlap schema section")
    return text[:heading_start] + _replace_fenced_block(
        text[heading_start:], "json", _compact_memory_overlap_demo_schema_output()
    )


def _readme_schema_path_label(readme_schema_path: Path) -> str:
    path_text = readme_schema_path.as_posix()
    return "README" if path_text == "README.md" else path_text


def _readme_schema_path_under_root(root: Path, readme_schema_path: Path) -> Path:
    if readme_schema_path.is_absolute():
        raise ValueError("--readme-schema-path must be relative to --root")
    root_resolved = root.resolve()
    target_resolved = (root / readme_schema_path).resolve()
    try:
        return target_resolved.relative_to(root_resolved)
    except ValueError as error:
        raise ValueError("--readme-schema-path must stay under --root") from error


def _memory_overlap_schema_fenced_block(text: str, *, section: str | None = None) -> str | None:
    if section is not None:
        return _fenced_block_in_section(text, "json", section)
    heading = "## Memory overlap demo JSON Schemas"
    heading_start = text.find(heading)
    if heading_start == -1:
        return None
    return _fenced_block(text[heading_start:], "json")


def _compact_memory_overlap_demo_schema_output() -> str:
    return json.dumps(_compact_memory_overlap_demo_schema())


def _compact_memory_overlap_demo_schema() -> dict:
    schema = memory_overlap_demo_schema()
    totals = schema["$defs"]["memoryOverlapTotalsDemo"]
    threshold = schema["$defs"]["memoryThresholdDemo"]
    return {
        "$schema": schema["$schema"],
        "$defs": {
            "memoryOverlapTotalsDemo": {
                "required": totals["required"],
                "totals_item": {"required": totals["properties"]["totals"]["items"]["required"]},
            },
            "memoryThresholdDemo": {
                "required": threshold["required"],
                "violations_item": {"required": threshold["properties"]["violations"]["items"]["required"]},
            },
        },
    }


def memory_threshold_demo_markdown(
    *,
    by: str = "tag",
    prefix_depth: int = 1,
    max_overlap_count: int | None = None,
    max_total_overlap_size: int | None = None,
    name_prefix: str | None = None,
    tags_all: tuple[str, ...] = (),
) -> str:
    """Return the stable fixture-backed memory threshold violation demo."""

    max_overlap_count, max_total_overlap_size = _memory_threshold_demo_budgets(
        by, max_overlap_count=max_overlap_count, max_total_overlap_size=max_total_overlap_size
    )
    return render_grouped_byte_span_overlap_threshold_violations(
        _filtered_memory_threshold_demo_spans(name_prefix=name_prefix, tags_all=tags_all),
        by=by,
        prefix_depth=prefix_depth,
        max_overlap_count=max_overlap_count,
        max_total_overlap_size=max_total_overlap_size,
    )


def memory_threshold_demo_json(
    *,
    by: str = "tag",
    prefix_depth: int = 1,
    max_overlap_count: int | None = None,
    max_total_overlap_size: int | None = None,
    name_prefix: str | None = None,
    tags_all: tuple[str, ...] = (),
) -> dict:
    """Return stable machine-readable memory threshold violation demo data."""

    max_overlap_count, max_total_overlap_size = _memory_threshold_demo_budgets(
        by, max_overlap_count=max_overlap_count, max_total_overlap_size=max_total_overlap_size
    )
    violations = find_grouped_byte_span_overlap_total_violations(
        _filtered_memory_threshold_demo_spans(name_prefix=name_prefix, tags_all=tags_all),
        by=by,
        prefix_depth=prefix_depth,
        max_overlap_count=max_overlap_count,
        max_total_overlap_size=max_total_overlap_size,
    )
    payload = {
        "by": by,
        "max_overlap_count": max_overlap_count,
        "max_total_overlap_size": max_total_overlap_size,
        "violations": [
            {
                "group": violation.group_name,
                "overlap_count": violation.overlap_count,
                "total_overlap_size": violation.total_overlap_size,
                "max_overlap_count": violation.max_overlap_count,
                "max_total_overlap_size": violation.max_total_overlap_size,
                "exceeded": _threshold_exceeded_labels(violation),
            }
            for violation in violations.values()
        ],
    }
    if by == "name_prefix":
        payload["prefix_depth"] = prefix_depth
    return payload


def _memory_threshold_demo_budgets(
    by: str, *, max_overlap_count: int | None = None, max_total_overlap_size: int | None = None
) -> tuple[int, int]:
    if by == "tag":
        preset = (1, 4)
    elif by == "name_prefix":
        preset = (0, 3)
    else:
        raise ValueError("by must be 'tag' or 'name_prefix'")
    return (
        preset[0] if max_overlap_count is None else max_overlap_count,
        preset[1] if max_total_overlap_size is None else max_total_overlap_size,
    )


def _threshold_exceeded_labels(violation) -> list[str]:
    labels = []
    if violation.exceeds_overlap_count:
        labels.append("overlap_count")
    if violation.exceeds_total_overlap_size:
        labels.append("total_overlap_size")
    return labels


def memory_overlap_totals_demo_markdown(
    *, by: str = "tag", prefix_depth: int = 1, name_prefix: str | None = None, tags_all: tuple[str, ...] = ()
) -> str:
    """Return the stable fixture-backed memory overlap totals demo."""

    return render_grouped_byte_span_overlap_totals(
        _filtered_memory_threshold_demo_spans(name_prefix=name_prefix, tags_all=tags_all), by=by, prefix_depth=prefix_depth
    )


def memory_overlap_totals_demo_json(
    *, by: str = "tag", prefix_depth: int = 1, name_prefix: str | None = None, tags_all: tuple[str, ...] = ()
) -> dict:
    """Return stable machine-readable memory overlap totals demo data."""

    totals = group_byte_span_overlap_totals(
        _filtered_memory_threshold_demo_spans(name_prefix=name_prefix, tags_all=tags_all), by=by, prefix_depth=prefix_depth
    )
    payload = {
        "by": by,
        "totals": [
            {
                "group": group_name,
                "overlap_count": total.overlap_count,
                "total_overlap_size": total.total_overlap_size,
            }
            for group_name, total in totals.items()
        ],
    }
    if by == "name_prefix":
        payload["prefix_depth"] = prefix_depth
    return payload


def _filtered_memory_threshold_demo_spans(*, name_prefix: str | None = None, tags_all: tuple[str, ...] = ()) -> list[ByteSpan]:
    return filter_byte_spans(_memory_threshold_demo_spans(), name_prefix=name_prefix, tags_all=tags_all)


def _memory_threshold_demo_spans() -> list[ByteSpan]:
    return [
        ByteSpan("left.value", 0, 8, tags=("source:literal", "runtime:left")),
        ByteSpan("right.value", 4, 12, tags=("source:literal", "runtime:right")),
        ByteSpan("scratch", 6, 10),
    ]


def memory_overlap_demo_schema() -> dict:
    """Return JSON Schema definitions for memory overlap demo JSON payloads."""

    non_negative_integer = {"type": "integer", "minimum": 0}
    positive_integer = {"type": "integer", "minimum": 1}
    group_by = {"enum": ["tag", "name_prefix"]}
    total_row = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "group": {"type": "string"},
            "overlap_count": non_negative_integer,
            "total_overlap_size": non_negative_integer,
        },
        "required": ["group", "overlap_count", "total_overlap_size"],
    }
    violation_row = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            **total_row["properties"],
            "max_overlap_count": non_negative_integer,
            "max_total_overlap_size": non_negative_integer,
            "exceeded": {"type": "array", "items": {"enum": ["overlap_count", "total_overlap_size"]}},
        },
        "required": [
            "group",
            "overlap_count",
            "total_overlap_size",
            "max_overlap_count",
            "max_total_overlap_size",
            "exceeded",
        ],
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "R Memory Overlap Demo JSON Schemas",
        "description": (
            "Schemas for R memory overlap demo JSON outputs. Use $defs.memoryOverlapTotalsDemo for "
            "--memory-overlap-totals-demo --json and $defs.memoryThresholdDemo for --memory-threshold-demo --json."
        ),
        "type": "object",
        "$defs": {
            "memoryOverlapTotalsDemo": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "by": group_by,
                    "prefix_depth": positive_integer,
                    "totals": {"type": "array", "items": total_row},
                },
                "required": ["by", "totals"],
            },
            "memoryThresholdDemo": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "by": group_by,
                    "prefix_depth": positive_integer,
                    "max_overlap_count": non_negative_integer,
                    "max_total_overlap_size": non_negative_integer,
                    "violations": {"type": "array", "items": violation_row},
                },
                "required": ["by", "max_overlap_count", "max_total_overlap_size", "violations"],
            },
        },
    }


if __name__ == "__main__":
    raise SystemExit(main())

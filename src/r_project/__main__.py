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
        if _readme_schema_example_mismatch(root, readme_schema_path):
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
        updated = _updated_readme_schema_example_block(root, readme_schema_path)
        if args.dry_run_readme_schema_examples:
            print(updated, end="")
        else:
            (root / readme_schema_path).write_text(updated, encoding="utf-8")
            print(f"Updated {_readme_schema_path_label(readme_schema_path)} memory-overlap schema example fence.")
        return 0
    if args.check_changelog_version:
        return _check_changelog_version(Path(args.root))
    if args.check_release_tag_fixture:
        return _check_release_tag_fixture(Path(args.root), version=args.release_tag_fixture_version)
    if args.write_release_tag_fixture:
        return _write_release_tag_fixture(
            Path(args.root), dry_run=args.dry_run_release_tag_fixture, version=args.release_tag_fixture_version
        )
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
    if args.generate_readme_examples:
        print(_readme_example_blocks(report))
        return 0
    if args.write_readme_examples:
        if args.dry_run_readme_examples:
            print(_updated_readme_example_blocks(root, report), end="")
        else:
            _write_readme_example_blocks(root, report)
            print("Updated README JSON and Markdown example fences.")
        return 0
    if args.check_readme_examples:
        mismatches = _readme_example_mismatches(root, report)
        if mismatches:
            for language in mismatches:
                print(f"README {language} example is out of date.", file=sys.stderr)
            return 1
        print("README examples match current CLI output.")
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


def _check_release_tag_fixture(root: Path, *, version: str | None = None) -> int:
    expected = _release_tag_checklist_fixture_output(root, version=version)
    fixture = root / "tests" / "fixtures" / "release-tag-checklist.json"
    actual = fixture.read_text(encoding="utf-8") if fixture.exists() else ""
    if actual != expected:
        print("Release tag checklist fixture is out of date.", file=sys.stderr)
        return 1
    print("Release tag checklist fixture matches current CLI output.")
    return 0


def _write_release_tag_fixture(root: Path, *, dry_run: bool, version: str | None = None) -> int:
    output = _release_tag_checklist_fixture_output(root, version=version)
    if dry_run:
        print(output, end="")
        return 0
    fixture = root / "tests" / "fixtures" / "release-tag-checklist.json"
    fixture.parent.mkdir(parents=True, exist_ok=True)
    fixture.write_text(output, encoding="utf-8")
    print("Updated release tag checklist fixture.")
    return 0


def _readme_example_mismatches(root: Path, report) -> list[str]:
    readme = root / "README.md"
    text = readme.read_text(encoding="utf-8") if readme.exists() else ""
    expected = {
        "json": json.dumps(report.to_dict(), sort_keys=True),
        "markdown": report.to_markdown(),
    }
    return [language for language, output in expected.items() if _fenced_block(text, language) != output]


def _readme_example_blocks(report) -> str:
    return "\n\n".join(
        [
            f"```json\n{json.dumps(report.to_dict(), sort_keys=True)}\n```",
            f"```markdown\n{report.to_markdown()}\n```",
        ]
    )


def _write_readme_example_blocks(root: Path, report) -> None:
    readme = root / "README.md"
    readme.write_text(_updated_readme_example_blocks(root, report), encoding="utf-8")


def _updated_readme_example_blocks(root: Path, report) -> str:
    readme = root / "README.md"
    text = readme.read_text(encoding="utf-8")
    replacements = {
        "json": json.dumps(report.to_dict(), sort_keys=True),
        "markdown": report.to_markdown(),
    }
    for language, output in replacements.items():
        text = _replace_fenced_block(text, language, output)
    return text


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


def _readme_schema_example_mismatch(root: Path, readme_schema_path: Path = Path("README.md")) -> bool:
    readme = root / readme_schema_path
    text = readme.read_text(encoding="utf-8") if readme.exists() else ""
    return _memory_overlap_schema_fenced_block(text) != _compact_memory_overlap_demo_schema_output()


def _updated_readme_schema_example_block(root: Path, readme_schema_path: Path = Path("README.md")) -> str:
    readme = root / readme_schema_path
    text = readme.read_text(encoding="utf-8")
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


def _memory_overlap_schema_fenced_block(text: str) -> str | None:
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

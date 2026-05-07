from __future__ import annotations

import argparse
import json
import sys
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
    args = build_parser().parse_args(argv)
    if args.memory_overlap_demo_schema:
        print(json.dumps(memory_overlap_demo_schema(), sort_keys=True))
        return 0
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


def _readme_example_mismatches(root: Path, report) -> list[str]:
    readme = root / "README.md"
    text = readme.read_text(encoding="utf-8") if readme.exists() else ""
    expected = {
        "json": json.dumps(report.to_dict(), sort_keys=True),
        "markdown": report.to_markdown(),
    }
    return [language for language, output in expected.items() if _fenced_block(text, language) != output]


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

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .memory import ByteSpan, render_grouped_byte_span_overlap_threshold_violations
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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.memory_threshold_demo:
        print(memory_threshold_demo_markdown())
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


def memory_threshold_demo_markdown() -> str:
    """Return the stable fixture-backed memory threshold violation demo."""

    spans = [
        ByteSpan("left.value", 0, 8, tags=("source:literal", "runtime:left")),
        ByteSpan("right.value", 4, 12, tags=("source:literal", "runtime:right")),
        ByteSpan("scratch", 6, 10),
    ]
    return render_grouped_byte_span_overlap_threshold_violations(
        spans,
        by="tag",
        max_overlap_count=1,
        max_total_overlap_size=4,
    )


if __name__ == "__main__":
    raise SystemExit(main())

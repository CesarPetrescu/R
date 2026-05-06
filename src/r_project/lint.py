from __future__ import annotations

import argparse
import ast
from pathlib import Path


DEFAULT_CHECK_DIRS = ("src", "tests")


def iter_python_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for directory_name in DEFAULT_CHECK_DIRS:
        directory = root / directory_name
        if directory.exists():
            files.extend(path for path in directory.rglob("*.py") if path.is_file())
    return sorted(files)


def check_python_syntax(root: Path) -> list[str]:
    failures: list[str] = []
    for path in iter_python_files(root):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            location = f"{path.relative_to(root)}:{exc.lineno}:{exc.offset}"
            failures.append(f"{location}: {exc.msg}")
    return failures


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Project R's lightweight Python syntax lint checks.")
    parser.add_argument("--root", default=".", help="Project root to lint (default: current directory).")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root)
    failures = check_python_syntax(root)
    if failures:
        print("Syntax check failed")
        for failure in failures:
            print(f"- {failure}")
        return 1

    checked = len(iter_python_files(root))
    print(f"Syntax check passed ({checked} Python files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

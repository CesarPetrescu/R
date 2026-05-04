from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path

_CHECKBOX_RE = re.compile(r"^\s*-\s+\[(?P<mark>[ xX])]\s+(?P<text>.+?)\s*$")
_HEADING_RE = re.compile(r"^#\s+(?P<title>.+?)\s*$")
_PRIORITY_HEADING_RE = re.compile(r"^##\s+(?P<priority>P\d+)\b.*$")


@dataclass(frozen=True)
class ProjectReport:
    project_name: str
    completed_backlog_items: int
    open_backlog_items: int
    next_backlog_item: str | None
    has_active_blockers: bool
    active_blockers: list[str]
    priority_backlog_groups: dict[str, dict[str, object]]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_markdown(self) -> str:
        """Format the readiness report as GitHub-flavored Markdown."""
        lines = [
            f"# {self.project_name} Readiness Report",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
            f"| Completed backlog items | {self.completed_backlog_items} |",
            f"| Open backlog items | {self.open_backlog_items} |",
            f"| Active blockers | {len(self.active_blockers)} |",
            "",
        ]
        if self.priority_backlog_groups:
            lines.extend(
                [
                    "## Backlog by priority",
                    "",
                    "| Priority | Completed | Open | Next item |",
                    "| --- | ---: | ---: | --- |",
                ]
            )
            for priority, group in self.priority_backlog_groups.items():
                lines.append(
                    f"| {priority} | {group['completed']} | {group['open']} | {group['next_item'] or 'None'} |"
                )
            lines.append("")
        lines.extend(
            [
                "## Next backlog item",
                "",
                self.next_backlog_item or "None",
                "",
                "## Active blockers",
                "",
            ]
        )
        if self.active_blockers:
            lines.extend(f"- {blocker}" for blocker in self.active_blockers)
        else:
            lines.append("None")
        return "\n".join(lines)


def analyze_project(root: str | Path) -> ProjectReport:
    """Analyze a project R checkout and summarize backlog readiness."""
    root_path = Path(root)
    readme_text = _read_text(root_path / "README.md")
    missing_features_text = _read_text(root_path / "status" / "missing-features.md")
    stuck_text = _read_text(root_path / "status" / "stuck.md")

    completed = 0
    open_items: list[str] = []
    priority_groups: dict[str, dict[str, object]] = {}
    current_priority: str | None = None
    for line in missing_features_text.splitlines():
        priority_match = _PRIORITY_HEADING_RE.match(line)
        if priority_match:
            current_priority = priority_match.group("priority")
            priority_groups.setdefault(current_priority, {"completed": 0, "open": 0, "next_item": None})
            continue
        match = _CHECKBOX_RE.match(line)
        if not match:
            continue
        group = None
        if current_priority is not None:
            group = priority_groups.setdefault(current_priority, {"completed": 0, "open": 0, "next_item": None})
        if match.group("mark").strip().lower() == "x":
            completed += 1
            if group is not None:
                group["completed"] = int(group["completed"]) + 1
        else:
            item_text = match.group("text")
            open_items.append(item_text)
            if group is not None:
                group["open"] = int(group["open"]) + 1
                if group["next_item"] is None:
                    group["next_item"] = item_text

    blockers = _active_blockers(stuck_text)
    return ProjectReport(
        project_name=_project_name(readme_text, root_path),
        completed_backlog_items=completed,
        open_backlog_items=len(open_items),
        next_backlog_item=open_items[0] if open_items else None,
        has_active_blockers=bool(blockers),
        active_blockers=blockers,
        priority_backlog_groups=priority_groups,
    )


def _project_name(readme_text: str, root_path: Path) -> str:
    for line in readme_text.splitlines():
        match = _HEADING_RE.match(line)
        if match:
            return match.group("title")
    return root_path.name


def _active_blockers(stuck_text: str) -> list[str]:
    in_active_section = False
    blockers: list[str] = []
    for line in stuck_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            in_active_section = stripped.lower() == "## active blockers"
            continue
        if not in_active_section or not stripped.startswith("- "):
            continue
        item = stripped[2:].strip()
        if item and not item.lower().startswith("none"):
            blockers.append(item)
    return blockers


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

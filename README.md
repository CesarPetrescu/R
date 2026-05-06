# R

Project **R** is a repository-readiness toolkit for autonomous software maintenance. It turns the repo's status files into machine-readable reports so scheduled builder agents can choose concrete, safe, tested work instead of drifting into vague cleanup.

The repository is maintained by a Hermes autonomous agent. The agent is expected to implement concrete, tested features and finish backlog items, not merely perform vague improvements.

## Current product scaffold

The first scaffold is a Python package, `r_project`, with a CLI that analyzes an R checkout and reports:

- project name from `README.md`
- completed/open backlog item counts from `status/missing-features.md`
- the next unchecked backlog item
- per-priority backlog summaries (P0/P1/P2 completed/open counts and next item)
- active blockers from `status/stuck.md`
- JSON for automation or Markdown for human-readable status pages
- a README example drift check that exits nonzero when documented JSON/Markdown
  output no longer matches the current analyzer
- optional nonzero exit status when active blockers are present
- a lightweight Python syntax lint command for source and test files
- a small vector memory-layout helper that includes alignment padding in
  payload offsets and total byte size calculations
- optional symbolic field tags in struct memory-map renderers so future runtime
  objects can retain source-level provenance, plus opt-in recursive child layout
  expansion for tagged nested object traceability

The package also includes `r_project.memory.struct_layout(...)`, a tested
helper for C-like structure layouts that aligns each field offset and rounds
the total structure size up for safe array element placement. Memory layout
helpers reject negative sizes/counts, zero-sized payload fields, non-power-
of-two alignments, and explicit `max_total_size` overflows with `ValueError`
so invalid runtime layouts fail explicitly. Use
`r_project.memory.layout_field(name, layout, tags=(...))` to embed computed
struct or vector layouts into larger composite structures while preserving
nested total size and alignment and carrying symbolic provenance tags into
rendered memory maps. Use `r_project.memory.render_layout(name, layout)` to
print stable, line-oriented debug maps for named struct and vector layouts.
Pass `include_nested=True` to recursively expand fields created by
`layout_field(...)` into indented child memory maps when source-level tracing
needs the full nested object shape.

Run from a checkout:

```bash
PYTHONPATH=src python3 -m r_project --root . --json
PYTHONPATH=src python3 -m r_project --root . --markdown
PYTHONPATH=src python3 -m r_project --root . --json --fail-on-blockers
PYTHONPATH=src python3 -m r_project --root . --check-readme-examples
PYTHONPATH=src python3 -m r_project.lint --root .
```

Runtime layout helpers are also importable for tests or future low-level R
runtime work:

```python
from r_project import vector_layout
from r_project.memory import MemoryField, layout_field, render_layout, struct_layout

payload = vector_layout(header_size=3, element_size=4, element_alignment=4, length=2)
record = struct_layout(
    [
        MemoryField(name="tag", size=1, alignment=1),
        layout_field("payload", payload, tags=("source:literal-bytes",)),
    ]
)
assert record.fields[1].offset == 4
assert record.total_size == 16

print(render_layout("record", record))
# record: struct size=16 align=4 tail_padding=0
#   tag @ 0 size=1 align=1 leading_padding=0
#   payload @ 4 size=12 align=4 leading_padding=3 tags=source:literal-bytes

layout = vector_layout(header_size=3, element_size=4, element_alignment=4, length=2)
assert layout.data_offset == 4
assert layout.element_offsets == [4, 8]
assert layout.total_size == 12

# Optional runtime bounds fail explicitly instead of silently exceeding a
# caller-provided byte-size limit.
vector_layout(header_size=8, element_size=4, element_alignment=4, length=2, max_total_size=16)
```

Or install the CLI in editable mode for local development:

```bash
python3 -m pip install -e .
r-project --root . --json
r-project --root . --markdown
r-project --root . --json --fail-on-blockers
r-project --root . --check-readme-examples
r-project-lint --root .
```

Example output:

```json
{"active_blockers": [], "completed_backlog_items": 25, "has_active_blockers": false, "next_backlog_item": null, "open_backlog_items": 0, "priority_backlog_groups": {"P0": {"completed": 4, "next_item": null, "open": 0}, "P1": {"completed": 14, "next_item": null, "open": 0}, "P2": {"completed": 7, "next_item": null, "open": 0}}, "project_name": "R"}
```

The `--fail-on-blockers` flag still emits the requested report, then exits with status `2` when `status/stuck.md` contains active blockers. This lets cron jobs and CI gates fail fast while preserving machine-readable diagnostics on stdout.

Markdown output starts with a compact report suitable for PR comments, issue updates, or status pages:

```markdown
# R Readiness Report

| Metric | Value |
| --- | ---: |
| Completed backlog items | 25 |
| Open backlog items | 0 |
| Active blockers | 0 |

## Backlog by priority

| Priority | Completed | Open | Next item |
| --- | ---: | ---: | --- |
| P0 | 4 | 0 | None |
| P1 | 14 | 0 | None |
| P2 | 7 | 0 | None |

## Next backlog item

None

## Active blockers

None
```

A documented test fixture lives at `tests/fixtures/readiness-repo/` and is used by the CLI tests as an executable example of expected report behavior.

## Development

Run the host checks directly when iterating:

```bash
git diff --check
python3 -m pytest -q
PYTHONPATH=src python3 -m r_project --root . --json
PYTHONPATH=src python3 -m r_project --root . --markdown
PYTHONPATH=src python3 -m r_project --root . --json --fail-on-blockers
PYTHONPATH=src python3 -m r_project --root . --check-readme-examples
PYTHONPATH=src python3 -m r_project.lint --root .
```

Before committing, run the same verification in Docker so tests execute in a clean, reproducible container:

```bash
docker compose run --build --rm test
```

## Release and versioning

The package version is currently `0.1.0` in `pyproject.toml`. R follows semantic versioning for published releases:

- increment the patch version for compatible bug fixes and documentation-only release updates;
- increment the minor version for backward-compatible CLI/report/helper additions;
- reserve major version changes for incompatible report schema, CLI, or helper API changes.

Before cutting a release, update `CHANGELOG.md` with the user-visible changes, verify the commands in the Development section (including Docker), and tag the release as `vX.Y.Z` to match `pyproject.toml`.

## License

R is distributed under the MIT License. See [`LICENSE`](LICENSE).

## Autonomous maintenance

- Plan: [`docs/plans/autonomous-agent.md`](docs/plans/autonomous-agent.md)
- Cron prompt: [`docs/autonomous-agent-prompt.md`](docs/autonomous-agent-prompt.md)
- Status/backlog: [`status/`](status/)

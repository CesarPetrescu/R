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
  objects can retain source-level provenance, opt-in recursive child layout
  expansion for tagged nested object traceability, optional half-open byte
  span summaries for quick runtime overlap checks, recursive flattened byte
  spans for fully qualified nested range comparisons, span filtering by
  qualified names and tags for narrowed diagnostics, a stable overlap
  detector for intersecting runtime ranges, Markdown overlap reports for
  human-readable runtime diagnostics, grouped overlap reports by shared
  provenance tag or qualified-name prefix, compact grouped overlap totals
  for larger trace dashboards, and Markdown grouped-total tables for PR
  comments and dashboards

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
needs the full nested object shape. Pass `include_spans=True` to append
half-open `span=start..end` ranges, call `layout.byte_spans()` to get
structured `ByteSpan` records, use `flatten_byte_spans(name, layout)` to
produce fully qualified parent/child spans with absolute offsets for nested
diagnostics, call `leaf_byte_spans(...)` to suppress parent container spans
when callers need leaf-only diagnostics, call `filter_byte_spans(...)` to
narrow flattened spans by qualified names and provenance tags before overlap
checks, pass spans to
`find_overlapping_byte_spans(...)` to identify runtime range intersections
while excluding endpoint-only touching ranges, call
`render_byte_span_overlaps(...)` to format those intersections as stable
Markdown for PR comments and trace reports, or use
`group_byte_span_overlaps(...)`/`render_grouped_byte_span_overlaps(...)` to
summarize larger diagnostics by shared provenance tag or qualified-name prefix.
Use `group_byte_span_overlap_totals(...)` when dashboards need compact overlap
counts and total intersecting bytes per group instead of full pair rows, and
`render_grouped_byte_span_overlap_totals(...)` when those totals should be
formatted as stable Markdown tables for PR comments or dashboards.

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
from r_project.memory import ByteSpan, MemoryField, filter_byte_spans, find_overlapping_byte_spans, flatten_byte_spans, group_byte_span_overlap_totals, group_byte_span_overlaps, layout_field, leaf_byte_spans, render_byte_span_overlaps, render_grouped_byte_span_overlap_totals, render_grouped_byte_span_overlaps, render_layout, struct_layout

payload = vector_layout(header_size=3, element_size=4, element_alignment=4, length=2)
record = struct_layout(
    [
        MemoryField(name="tag", size=1, alignment=1),
        layout_field("payload", payload, tags=("source:literal-bytes",)),
    ]
)
assert record.fields[1].offset == 4
assert record.total_size == 16

print(render_layout("record", record, include_spans=True))
# record: struct size=16 align=4 tail_padding=0
#   tag @ 0 size=1 align=1 leading_padding=0 span=0..1
#   payload @ 4 size=12 align=4 leading_padding=3 tags=source:literal-bytes span=4..16
assert [(span.name, span.start, span.end) for span in record.byte_spans()] == [
    ("tag", 0, 1),
    ("payload", 4, 16),
]
assert [(span.name, span.start, span.end) for span in flatten_byte_spans("record", record)] == [
    ("record.tag", 0, 1),
    ("record.payload", 4, 16),
    ("record.payload.header", 4, 7),
    ("record.payload.element[0]", 8, 12),
    ("record.payload.element[1]", 12, 16),
]

assert [(span.name, span.start, span.end) for span in filter_byte_spans(leaf_byte_spans(flatten_byte_spans("record", record)), name_prefix="record.payload.", tags_all=("source:literal-bytes",))] == [
    ("record.payload.header", 4, 7),
    ("record.payload.element[0]", 8, 12),
    ("record.payload.element[1]", 12, 16),
]

left = flatten_byte_spans("left", payload, base_offset=16)
right = flatten_byte_spans("right", vector_layout(header_size=0, element_size=4, element_alignment=4, length=1), base_offset=20)
assert [(overlap.left.name, overlap.right.name, overlap.start, overlap.end) for overlap in find_overlapping_byte_spans(left + right)] == [
    ("left.element[1]", "right.element[0]", 20, 24),
]
assert render_byte_span_overlaps(left + right) == "\n".join(
    [
        "# Byte Span Overlaps",
        "",
        "| Left span | Right span | Overlap | Size |",
        "| --- | --- | ---: | ---: |",
        "| left.element[1] (20..24) | right.element[0] (20..24) | 20..24 | 4 |",
    ]
)

tagged_spans = [
    ByteSpan("left.value", 0, 8, tags=("source:literal", "runtime:left")),
    ByteSpan("right.value", 4, 12, tags=("source:literal", "runtime:right")),
    ByteSpan("scratch", 6, 10),
]
assert list(group_byte_span_overlaps(tagged_spans, by="tag")) == ["source:literal", "untagged"]
assert group_byte_span_overlap_totals(tagged_spans, by="tag")["untagged"].total_overlap_size == 6
assert render_grouped_byte_span_overlap_totals(tagged_spans, by="tag") == "\n".join(
    [
        "# Byte Span Overlap Totals by Tag",
        "",
        "| Group | Overlaps | Total overlap bytes |",
        "| --- | ---: | ---: |",
        "| source:literal | 1 | 4 |",
        "| untagged | 2 | 6 |",
    ]
)
assert render_grouped_byte_span_overlaps(tagged_spans, by="tag") == "\n".join(
    [
        "# Byte Span Overlaps by Tag",
        "",
        "## source:literal",
        "",
        "| Left span | Right span | Overlap | Size |",
        "| --- | --- | ---: | ---: |",
        "| left.value (0..8) | right.value (4..12) | 4..8 | 4 |",
        "",
        "## untagged",
        "",
        "| Left span | Right span | Overlap | Size |",
        "| --- | --- | ---: | ---: |",
        "| left.value (0..8) | scratch (6..10) | 6..8 | 2 |",
        "| right.value (4..12) | scratch (6..10) | 6..10 | 4 |",
    ]
)

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
{"active_blockers": [], "completed_backlog_items": 34, "has_active_blockers": false, "next_backlog_item": null, "open_backlog_items": 0, "priority_backlog_groups": {"P0": {"completed": 4, "next_item": null, "open": 0}, "P1": {"completed": 23, "next_item": null, "open": 0}, "P2": {"completed": 7, "next_item": null, "open": 0}}, "project_name": "R"}
```

The `--fail-on-blockers` flag still emits the requested report, then exits with status `2` when `status/stuck.md` contains active blockers. This lets cron jobs and CI gates fail fast while preserving machine-readable diagnostics on stdout.

Markdown output starts with a compact report suitable for PR comments, issue updates, or status pages:

```markdown
# R Readiness Report

| Metric | Value |
| --- | ---: |
| Completed backlog items | 34 |
| Open backlog items | 0 |
| Active blockers | 0 |

## Backlog by priority

| Priority | Completed | Open | Next item |
| --- | ---: | ---: | --- |
| P0 | 4 | 0 | None |
| P1 | 23 | 0 | None |
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

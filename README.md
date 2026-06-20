# R

R is an automation showcase for building interpreted Rust inside C. The star of the repo is `runtime/rustic.c`: a compact C-hosted interpreter for a Rust-like expression language. The surrounding Python package keeps the autonomous maintenance workflow measurable, testable, and safe.

## At a glance

| Area | What lives here |
| --- | --- |
| Runtime | `runtime/rustic.c`, a C interpreter for Rust-like integer expressions, blocks, loops, arrays, functions, recursion, and checked diagnostics. |
| Tests | `tests/`, pytest fixtures, and Docker verification that compile and exercise the C runtime. |
| Automation | [`automations/`](automations/) and [`docs/automation-index.md`](docs/automation-index.md), the worker/runbook surfaces for the autonomous showcase. |
| Status | `status/`, the backlog and blocker files read by the reporting CLI. |

## What this repo is

R has two connected parts:

1. **The product:** interpreted Rust inside C, focused on `runtime/` and C runtime behavior.
2. **The showcase:** a Hermes worker repeatedly chooses real interpreter work, writes tests, verifies locally and in Docker, opens PRs, and grows the runtime safely.

Python is support tooling only. It powers pytest helpers, readiness reports, documentation drift checks, release guards, and memory-layout utilities used by the automation workflow.

## Runtime capabilities

The interpreter currently covers a practical Rust-like expression slice:

- arithmetic, precedence, comparisons, boolean `!`, `&&`, and `||`;
- `let` bindings, assignment, statement sequencing, lexical blocks, `if`/`else`, `while`, `break`, and `continue`;
- `match` expressions with integer arms and `_` defaults;
- arrays with checked indexing plus helpers such as `len`, `set`, `push`, `sum`, `count`, `find`, `difference`, `drop`, `take`, `window_sum`, `chunk_sum`, `rotate`, `prefix_sum`, `adjacent_diff`, `median`, `variance_sum`, `mode`, histogram helpers, threshold/outlier run helpers, ranking helpers, and clamp/weighted-score helpers;
- named functions, first-class function references, nested calls, recursion, and call-local parameter bindings;
- stable diagnostics for undefined identifiers, invalid loop control, division by zero, malformed comparisons, bad arity, unmatched parentheses, unclosed blocks, and runaway programs that hit the interpreter step budget.

Host tests compile the runtime with `cc -std=c99 -Wall -Wextra -Werror` and exercise the behavior end to end.

## Quick start

Run the main checks from a checkout:

```bash
python3 -m pip install -e .
python3 -m pytest -q
PYTHONPATH=src python3 -m r_project --root . --json
PYTHONPATH=src python3 -m r_project --root . --markdown
PYTHONPATH=src python3 -m r_project --root . --json --fail-on-blockers
PYTHONPATH=src python3 -m r_project.lint --root .
```

Or use the installed console scripts:

```bash
r-project --root . --json
r-project --root . --markdown
r-project --root . --json --fail-on-blockers
r-project-lint --root .
```

Before committing, run the clean-container verification:

```bash
docker compose run --build --rm test
```

## Readiness reports

The CLI turns `status/` into JSON or Markdown that can be pasted into PRs, issues, dashboards, or release gates.

```json
{"active_blockers": [], "completed_backlog_items": 168, "has_active_blockers": false, "next_backlog_item": null, "open_backlog_items": 0, "priority_backlog_groups": {"P0": {"completed": 4, "next_item": null, "open": 0}, "P1": {"completed": 104, "next_item": null, "open": 0}, "P2": {"completed": 60, "next_item": null, "open": 0}}, "project_name": "R"}
```

```markdown
# R Readiness Report

| Metric | Value |
| --- | ---: |
| Completed backlog items | 168 |
| Open backlog items | 0 |
| Active blockers | 0 |

## Backlog by priority

| Priority | Completed | Open | Next item |
| --- | ---: | ---: | --- |
| P0 | 4 | 0 | None |
| P1 | 104 | 0 | None |
| P2 | 60 | 0 | None |

## Next backlog item

None

## Active blockers

None
```

`--fail-on-blockers` still emits the requested report, then exits with status `2` when `status/stuck.md` contains active blockers. That makes cron jobs and CI gates fail fast while preserving machine-readable diagnostics on stdout.

The README and dashboard examples are drift-checked. Useful guards:

```bash
PYTHONPATH=src python3 -m r_project --root . --check-readme-examples
PYTHONPATH=src python3 -m r_project --root . --generate-readme-examples
PYTHONPATH=src python3 -m r_project --root . --write-readme-examples --dry-run-readme-examples
PYTHONPATH=src python3 -m r_project --root . --check-readme-examples --readme-examples-path README.md
PYTHONPATH=src python3 -m r_project --root . --check-readme-examples --readme-examples-path docs/usage-examples.md
PYTHONPATH=src python3 -m r_project --root . --check-readme-examples --readme-examples-path docs/dashboard-index.md
PYTHONPATH=src python3 -m r_project --root . --check-readme-examples --readme-examples-path docs/automation-index.md
PYTHONPATH=src python3 -m r_project --root . --check-readme-schema-examples --readme-schema-path docs/dashboard-index.md
PYTHONPATH=src python3 -m r_project --root . --check-readme-schema-examples --readme-schema-path docs/automation-index.md
```

Standalone checked examples live in [`docs/usage-examples.md`](docs/usage-examples.md), [`docs/dashboard-index.md`](docs/dashboard-index.md), and [`docs/automation-index.md`](docs/automation-index.md).

## Memory layout helpers

`r_project.memory` provides tested helpers for C-like layouts: `struct_layout`, `vector_layout`, nested `layout_field(...)` values, byte-span flattening/filtering, and Markdown renderers for overlap diagnostics. These helpers reject invalid sizes, counts, alignments, and configured overflow limits explicitly instead of silently producing unsafe layouts.

Minimal example:

```python
from r_project import vector_layout
from r_project.memory import MemoryField, layout_field, render_layout, struct_layout

payload = vector_layout(header_size=3, element_size=4, element_alignment=4, length=2)
record = struct_layout([
    MemoryField(name="tag", size=1, alignment=1),
    layout_field("payload", payload, tags=("source:literal-bytes",)),
])

assert record.fields[1].offset == 4
assert record.total_size == 16
print(render_layout("record", record, include_spans=True))
```

## Memory overlap demo JSON Schemas

Dashboard consumers that validate memory-overlap demo JSON can inspect the schema surface without reading source:

```bash
r-project --memory-overlap-demo-schema
```

The compact README schema contract is drift-checked by `r-project --root . --check-readme-schema-examples`:

```json
{"$schema": "https://json-schema.org/draft/2020-12/schema", "$defs": {"memoryOverlapTotalsDemo": {"required": ["by", "totals"], "totals_item": {"required": ["group", "overlap_count", "total_overlap_size"]}}, "memoryThresholdDemo": {"required": ["by", "max_overlap_count", "max_total_overlap_size", "violations"], "violations_item": {"required": ["group", "overlap_count", "total_overlap_size", "max_overlap_count", "max_total_overlap_size", "exceeded"]}}}}
```

Use these commands to check or refresh the schema fence:

```bash
PYTHONPATH=src python3 -m r_project --root . --check-memory-overlap-demo-schema
PYTHONPATH=src python3 -m r_project --root . --check-readme-schema-examples
PYTHONPATH=src python3 -m r_project --root . --write-readme-schema-examples --dry-run-readme-schema-examples
PYTHONPATH=src python3 -m r_project --root . --check-readme-schema-examples --readme-schema-path README.md
PYTHONPATH=src python3 -m r_project --root . --check-readme-schema-examples --readme-schema-path docs/dashboard-schema.md
```

The standalone dashboard schema page is [`docs/dashboard-schema.md`](docs/dashboard-schema.md).

## Development workflow

Use TDD for runtime behavior changes:

1. add or update a failing pytest fixture;
2. confirm the targeted test fails for the expected reason;
3. implement the smallest runtime/tooling change;
4. run the targeted test, the full host suite, readiness reports, and Docker.

Required pre-PR verification:

```bash
git diff --check
python3 -m pytest -q
PYTHONPATH=src python3 -m r_project --root . --json
PYTHONPATH=src python3 -m r_project --root . --markdown
PYTHONPATH=src python3 -m r_project --root . --json --fail-on-blockers
docker compose run --build --rm test
```

## Release and versioning

The package version is currently `0.1.0` in `pyproject.toml`. R follows semantic versioning for published releases:

- increment the patch version for compatible bug fixes and documentation-only release updates;
- increment the minor version for backward-compatible CLI/report/helper additions;
- reserve major version changes for incompatible report schema, CLI, or helper API changes.

Before cutting a release, update `CHANGELOG.md` with user-visible changes, run the development and Docker checks, and tag the release as `vX.Y.Z` to match `pyproject.toml`. Release automation can run:

```bash
PYTHONPATH=src python3 -m r_project --root . --check-changelog-version
PYTHONPATH=src python3 -m r_project --root . --check-release-tag v0.1.0 --docker-verified
PYTHONPATH=src python3 -m r_project --root . --json --check-release-tag v0.1.0 --docker-verified
```

More release surfaces live in [`docs/release-index.md`](docs/release-index.md), [`docs/release-checklist.md`](docs/release-checklist.md), and [`docs/release-examples.md`](docs/release-examples.md).

## Autonomous maintenance

- Automation home: [`automations/`](automations/)
- Interpreted Rust inside C showcase: [`automations/interpreted-rust-in-c.md`](automations/interpreted-rust-in-c.md)
- Combined automation index: [`docs/automation-index.md`](docs/automation-index.md)
- Dashboard docs: [`docs/dashboard-index.md`](docs/dashboard-index.md), [`docs/dashboard-automation-index.md`](docs/dashboard-automation-index.md)
- Plan: [`docs/plans/autonomous-agent.md`](docs/plans/autonomous-agent.md)
- Cron prompt: [`docs/autonomous-agent-prompt.md`](docs/autonomous-agent-prompt.md)
- Status/backlog: [`status/`](status/)

## License

R is distributed under the GNU Affero General Public License v3.0 or later (`AGPL-3.0-or-later`). See [`LICENSE`](LICENSE).

# R Current State

Last updated: 2026-05-07

## Repository

- Path: `/root/hermes-workspace/R`
- Remote: `git@github.com-r:CesarPetrescu/R.git`
- Branch: `main`
- Product direction: repository-readiness toolkit for autonomous software maintenance.
- Current implementation: tested Python scaffold with `r_project` analyzer and installable `r-project`/`r-project-lint` CLIs, including per-priority backlog summaries, README example drift checks/generation/writing, vector and struct memory-layout helpers, nested layout renderers, byte-span flattening/filtering/leaf helpers, overlap detectors, grouped overlap reports/totals/threshold helpers, fixture-backed Markdown and JSON CLI demos, JSON Schema definitions, compact README schema docs/examples, an on-demand schema fixture drift check, release/versioning notes, a release tag checklist guard with JSON summary output, and AGPL-3.0-or-later licensing.
- Test environment: Dockerized verification via `Dockerfile` and `docker-compose.yml` service `test`.
- Example fixture: `tests/fixtures/readiness-repo/` documents expected report behavior and backs CLI tests.

## Implemented behavior

- `r_project.report.analyze_project(root)` reads a checkout and returns backlog counts, per-priority backlog groups, the next unchecked item, and active blocker status.
- `ProjectReport.to_markdown()` formats readiness data as GitHub-flavored Markdown for human status pages.
- `python3 -m r_project --root <path> --json` emits the report as stable JSON for cron/agent consumption.
- `python3 -m r_project --root <path> --markdown` emits the report as Markdown for PR comments, issue updates, and status pages.
- `python3 -m pip install -e .` installs an editable `r-project` console script for local development.
- `python3 -m r_project --root <path> --json --fail-on-blockers` emits the selected report and exits with status 2 when active blockers exist.
- `python3 -m r_project --root <path> --check-readme-examples` compares README JSON/Markdown examples against current generated output and exits with status 1 plus drift diagnostics when they differ.
- `python3 -m r_project --root <path> --generate-readme-examples` emits copy-paste-ready JSON and Markdown fenced blocks from the current analyzer output so README examples can be refreshed without hand-copying multiple commands.
- `python3 -m r_project --root <path> --write-readme-examples` rewrites the README JSON and Markdown example fences in place from current analyzer output so agents can refresh documented examples without manual copying.
- `python3 -m r_project --root <path> --write-readme-examples --dry-run-readme-examples` prints the README content that would be written by the README example writer without modifying `README.md`, so agents can preview regenerated JSON/Markdown fences before side effects.
- `python3 -m r_project.lint --root <path>` and installed `r-project-lint --root <path>` run a lightweight Python syntax lint over `src/` and `tests/`.
- `r_project.vector_layout(...)` calculates aligned vector payload offsets, stride, and total size so header and trailing padding are represented consistently; invalid negative values, zero element sizes/alignments, non-power-of-two element alignments, and optional `max_total_size` overflows raise `ValueError`.
- `r_project.memory.struct_layout(fields)` computes C-like structure offsets with per-field alignment and tail padding so arrays of structures remain aligned; invalid field sizes/alignments, non-power-of-two field alignments, and optional `max_total_size` overflows raise `ValueError`.
- `r_project.memory.layout_field(name, layout)` converts computed struct/vector layouts into `MemoryField` values so nested runtime objects preserve child total sizes and alignment when embedded in larger structures.
- `r_project.memory.render_layout(name, layout)` renders named struct/vector layouts as stable, line-oriented debug memory maps with offsets, padding, sizes, alignment, and optional symbolic field tags/provenance metadata. Pass `include_nested=True` to recursively include embedded child struct/vector layouts for full source-level traceability. Pass `include_spans=True` to append half-open byte ranges for quick overlap diagnostics.
- `r_project.memory.flatten_byte_spans(name, layout)` returns fully qualified parent and nested child `ByteSpan` records with absolute half-open ranges and inherited provenance tags so runtime overlap checks can compare nested object memory ranges directly.
- `r_project.memory.filter_byte_spans(spans, ...)` preserves input ordering while narrowing flattened spans by optional name prefix, name substring, required tags, and any-tag predicates before overlap checks or reports.
- `r_project.memory.leaf_byte_spans(spans)` preserves input ordering while suppressing parent container spans that strictly contain another provided span, so overlap reports can focus on concrete leaf fields or vector parts.
- `r_project.memory.find_overlapping_byte_spans(spans)` returns stable pairwise `ByteSpanOverlap` intersections for half-open ranges, excluding endpoint-only touching ranges.
- `r_project.memory.render_byte_span_overlaps(spans)` formats span overlaps as stable Markdown with an explicit empty state for PR comments, trace logs, and status reports.
- `r_project.memory.group_byte_span_overlaps(spans, by="tag")` groups intersections by shared provenance tags, with unshared/untagged intersections under `untagged`; `by="name_prefix"` groups by qualified-name prefix pairs for larger runtime diagnostics.
- `r_project.memory.group_byte_span_overlap_totals(spans, ...)` returns compact per-group overlap counts and total intersecting bytes so dashboards can summarize large grouped diagnostics without rendering every pair.
- `r_project.memory.find_grouped_byte_span_overlap_total_violations(spans, ...)` returns grouped total budget violations for dashboard gates that enforce maximum overlap counts or intersecting bytes.
- `r_project.memory.render_grouped_byte_span_overlap_threshold_violations(spans, ...)` formats grouped total budget violations as stable Markdown tables for PR comments, trace logs, and dashboard gates.
- `python3 -m r_project --memory-threshold-demo` emits fixture-backed Markdown threshold-violation demo output so documentation, PR comments, and Docker verification can exercise a stable runtime diagnostics surface.
- `python3 -m r_project --memory-threshold-demo --json` emits the same threshold-violation demo as stable JSON so dashboards and agent checks can consume the fixture without parsing Markdown.
- `python3 -m r_project --memory-threshold-demo --memory-overlap-max-count <n> --memory-overlap-max-bytes <n>` overrides the demo's preset grouped overlap-count and intersecting-byte budgets in Markdown or JSON output.
- `python3 -m r_project --memory-threshold-demo --memory-overlap-group-by name_prefix --memory-overlap-prefix-depth 2` emits fixture-backed Markdown grouped threshold violations scoped by qualified-name prefix depth for dashboard gates.
- `python3 -m r_project --memory-threshold-demo --json --memory-overlap-group-by name_prefix --memory-overlap-prefix-depth 2` emits the same scoped threshold violations as stable JSON.
- `python3 -m r_project --memory-overlap-totals-demo` emits fixture-backed Markdown grouped overlap totals so documentation, PR comments, and Docker verification can exercise compact non-violation diagnostics.
- `python3 -m r_project --memory-overlap-totals-demo --json` emits the same grouped overlap totals as stable JSON so dashboards and agent checks can consume compact summary fixtures without parsing Markdown.
- `python3 -m r_project --memory-overlap-totals-demo --memory-overlap-group-by name_prefix --memory-overlap-prefix-depth 2` emits fixture-backed Markdown grouped overlap totals scoped by qualified-name prefix depth for dashboard summaries.
- `python3 -m r_project --memory-overlap-totals-demo --json --memory-overlap-group-by name_prefix --memory-overlap-prefix-depth 2` emits the same scoped grouped overlap totals as stable JSON.
- `python3 -m r_project --memory-overlap-demo-schema` emits JSON Schema definitions for the memory threshold and grouped-total demo JSON payloads so dashboard consumers can validate fields without reading source.
- `python3 -m r_project --root <path> --check-memory-overlap-demo-schema` compares the stored schema fixture against current generated schema output and exits with status 1 plus drift diagnostics when they differ.
- `README.md` documents compact JSON Schema examples for the memory-overlap totals and threshold demo JSON payloads so dashboard consumers can discover required fields from the docs as well as the CLI.
- `python3 -m r_project --root <path> --check-changelog-version` compares `pyproject.toml` package version metadata with README and CHANGELOG mentions so release automation can catch stale documented version notes before tagging.
- `python3 -m r_project --root <path> --check-release-tag vX.Y.Z --docker-verified` checks that a candidate release tag matches the `pyproject.toml` version, Docker verification evidence is present, and the git working tree is clean before publishing; use `--skip-git-clean-check` only for copied container contexts without `.git`. Add `--json` to emit a machine-readable release checklist summary with `tag_matches_version`, `docker_verified`, `git_clean`, and overall `ready` fields for release automation.
- Add `--memory-overlap-name-prefix <prefix>` or one or more `--memory-overlap-tag <tag>` flags to the fixture-backed memory threshold and grouped-total demos to filter spans before overlap totals or threshold violations are calculated.
- `r_project.memory.render_grouped_byte_span_overlap_totals(spans, ...)` formats compact grouped overlap totals as stable Markdown tables for PR comments, trace logs, and dashboards.
- `r_project.memory.render_grouped_byte_span_overlaps(spans, ...)` formats those grouped intersections as stable Markdown sections for PR comments, trace logs, and status reports.
- `StructLayout.byte_spans()` and `VectorLayout.byte_spans()` return `ByteSpan` records with half-open `[start, end)` ranges so runtime diagnostics can compare object memory ranges without parsing renderer text.
- Tests compare README JSON and Markdown report examples with the current CLI output so documented examples do not drift when report fields or counts change.
- `README.md` documents the current `0.1.0` semantic-versioning release policy and `CHANGELOG.md` records unreleased user-visible changes.
- `LICENSE` declares GNU Affero General Public License v3.0 or later (`AGPL-3.0-or-later`) terms so distributed and network-served modified versions remain open-source.

## Verified commands

```bash
git diff --check
python3 -m pytest -q
PYTHONPATH=src python3 -m r_project --root . --json
PYTHONPATH=src python3 -m r_project --root . --markdown
PYTHONPATH=src python3 -m r_project --root . --json --fail-on-blockers
PYTHONPATH=src python3 -m r_project --root . --check-readme-examples
PYTHONPATH=src python3 -m r_project --root . --generate-readme-examples
PYTHONPATH=src python3 -m r_project --root . --write-readme-examples --dry-run-readme-examples
PYTHONPATH=src python3 -m r_project --root . --write-readme-examples
PYTHONPATH=src python3 -m r_project --memory-threshold-demo
PYTHONPATH=src python3 -m r_project --memory-threshold-demo --json
PYTHONPATH=src python3 -m r_project --memory-threshold-demo --memory-overlap-max-count 2 --memory-overlap-max-bytes 6
PYTHONPATH=src python3 -m r_project --memory-threshold-demo --json --memory-overlap-max-count 2 --memory-overlap-max-bytes 6
PYTHONPATH=src python3 -m r_project --memory-threshold-demo --memory-overlap-group-by name_prefix --memory-overlap-prefix-depth 2
PYTHONPATH=src python3 -m r_project --memory-threshold-demo --json --memory-overlap-group-by name_prefix --memory-overlap-prefix-depth 2
PYTHONPATH=src python3 -m r_project --memory-overlap-totals-demo
PYTHONPATH=src python3 -m r_project --memory-overlap-totals-demo --json
PYTHONPATH=src python3 -m r_project --memory-overlap-totals-demo --memory-overlap-group-by name_prefix --memory-overlap-prefix-depth 2
PYTHONPATH=src python3 -m r_project --memory-overlap-totals-demo --json --memory-overlap-group-by name_prefix --memory-overlap-prefix-depth 2
PYTHONPATH=src python3 -m r_project --memory-overlap-totals-demo --memory-overlap-name-prefix left.
PYTHONPATH=src python3 -m r_project --memory-threshold-demo --json --memory-overlap-tag source:literal --memory-overlap-max-count 0
PYTHONPATH=src python3 -m r_project --memory-overlap-demo-schema
PYTHONPATH=src python3 -m r_project --root . --check-memory-overlap-demo-schema
PYTHONPATH=src python3 -m r_project --root . --check-changelog-version
PYTHONPATH=src python3 -m r_project --root . --check-release-tag v0.1.0 --docker-verified
PYTHONPATH=src python3 -m r_project --root . --json --check-release-tag v0.1.0 --docker-verified
PYTHONPATH=src python3 -m r_project.lint --root .
docker compose run --build --rm test
```

## Operating rule

The autonomous agent must turn this into a real, tested project by finishing concrete backlog items each run. It should not stop at vague improvements when code can be created safely.

Scheduled R runs are PR-first and reviewer-gated: changes must be made on `ai/r/*` branches, pushed with `/usr/local/bin/r-bot-git-push`, opened/updated as PRs to `main`, reviewed by the AI reviewer, and merged to `main` by r-coder only when `AI_REVIEW:CLEAR`, clean/mergeable state, and local Docker verification are all present.

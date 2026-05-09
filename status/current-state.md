# R Current State

Last updated: 2026-05-09

## Repository

- Path: `/root/hermes-workspace/R`
- Remote: `git@github.com-r:CesarPetrescu/R.git`
- Branch: `main`
- Product direction: automation showcase for building and presenting interpreted Rust inside C; repository-readiness tooling remains support infrastructure for proving the autonomous loop works safely.
- Current implementation: tiny C-hosted Rust-like expression interpreter under `runtime/`, tested by a compiled C host fixture with bindings, sequencing, assignment/mutation, parenthesized expression support, equality and ordering comparisons that return boolean integers, block expressions with nested lexical scopes, conditional `if`/`else` expressions with branch-local scopes, `while` loop statements that re-evaluate conditions while preserving outer mutations, and `fn`-like named function declarations/calls with scoped argument bindings, plus a Python `r_project` analyzer and installable `r-project`/`r-project-lint` CLIs, including per-priority readiness reports, README/example/schema drift guards and writers, dashboard and release automation docs with Docker-covered guards, release automation index link/command row generation and writer dry-runs with configurable preview-version command generation plus named profile-section guards, dashboard automation index link/command row generation and writer dry-runs with configurable preview-variant command generation, dashboard example fixture row generation and writer dry-runs derived from `docs/dashboard-index.md`, release section writer matrix row generation/writing, memory-layout helpers with overlap diagnostics/demos/schemas, release checklist guards/fixtures, lightweight linting, Docker verification, and AGPL-3.0-or-later licensing.
- Test environment: Dockerized verification via `Dockerfile` and `docker-compose.yml` service `test`.
- Example fixture: `tests/fixtures/readiness-repo/` documents expected report behavior and backs CLI tests.

## Implemented behavior

- `runtime/include/rustic.h` and `runtime/rustic.c` expose `rustic_eval_expression(...)`, a C-hosted Rust-like integer expression evaluator with whitespace skipping, `+`, `*`, multiplication precedence, parenthesized expressions that override precedence, `let` bindings, identifier lookup, semicolon-separated expression-statement sequencing that returns the final expression value, assignment/mutation of existing bindings, equality and ordering comparisons (`==`, `!=`, `<`, `<=`, `>`, `>=`) that return `1` for true and `0` for false, block expressions with nested lexical scopes and final-expression values, conditional `if`/`else` expressions that evaluate only the selected branch while preserving branch-local scopes, `while` loop statements that mutate existing outer bindings across iterations and skip non-selected bodies, `fn`-like named function declarations and calls that bind evaluated arguments in call-local scope and return the function body's final expression, undefined-identifier errors for reads, assignment targets, and unknown functions, unmatched-parenthesis errors, unclosed-block errors, malformed comparison/equality diagnostics, wrong-argument-count diagnostics, and stable parse-error status messages; `tests/fixtures/rustic_expression_driver.c` demonstrates the API end to end.
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
- Add `--readme-examples-path docs/usage-examples.md` to README JSON/Markdown example drift checks and writer/dry-run modes when dashboard-ready report examples live in a standalone README-style Markdown file under `--root`; absolute paths and `..` escapes are rejected before writer modes can modify files outside `--root`.
- `docs/usage-examples.md` stores standalone dashboard-ready JSON and Markdown report examples that are kept in sync by host tests and the Docker harness via `--readme-examples-path docs/usage-examples.md`.
- `docs/dashboard-index.md` stores a standalone dashboard landing page with checked readiness report fences and checked compact memory-overlap schema fences, linking `docs/usage-examples.md` and `docs/dashboard-schema.md` for consumers that need one entry point.
- Add `--readme-examples-section` to report example checks and writers, or `--readme-schema-section` to compact schema checks and writers, when a dashboard Markdown file contains multiple independently named readiness/schema snippets and only one section should be checked or refreshed.
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
- `python3 -m r_project --root <path> --check-readme-schema-examples` compares the README compact memory-overlap JSON Schema example against current generated schema output and exits with status 1 plus drift diagnostics when it differs.
- `python3 -m r_project --root <path> --write-readme-schema-examples` rewrites the README compact memory-overlap JSON Schema example fence in place from current generated schema output; add `--dry-run-readme-schema-examples` to print the refreshed README without modifying it. Add `--readme-schema-path docs/dashboard-schema.md` to the check or writer commands when the README-style schema section lives in an alternate Markdown document under the project root.
- `docs/dashboard-schema.md` stores standalone dashboard-ready compact memory-overlap JSON Schema examples that are kept in sync by host tests and the Docker verification harness via `--readme-schema-path docs/dashboard-schema.md`.
- The `docs/dashboard-index.md` schema section is also kept in sync by host tests and Docker verification via `--readme-schema-path docs/dashboard-index.md`.
- `README.md` documents compact JSON Schema examples for the memory-overlap totals and threshold demo JSON payloads so dashboard consumers can discover required fields from the docs as well as the CLI.
- `python3 -m r_project --root <path> --check-changelog-version` compares `pyproject.toml` package version metadata with README and CHANGELOG mentions so release automation can catch stale documented version notes before tagging.
- `python3 -m r_project --root <path> --check-release-tag vX.Y.Z --docker-verified` checks that a candidate release tag matches the `pyproject.toml` version, Docker verification evidence is present, and the git working tree is clean before publishing; use `--skip-git-clean-check` only for copied container contexts without `.git`. Add `--json` to emit a machine-readable release checklist summary with `tag_matches_version`, `docker_verified`, `git_clean`, and overall `ready` fields for release automation.
- `python3 -m r_project --root <path> --check-release-tag-fixture` compares the stored release checklist JSON fixture against current generated checklist output and exits with status 1 plus drift diagnostics when they differ.
- `python3 -m r_project --root <path> --write-release-tag-fixture` rewrites the release checklist JSON fixture from current generated checklist output; add `--dry-run-release-tag-fixture` to print the refreshed fixture without modifying files.
- Add `--release-tag-fixture-version X.Y.Z` to `--check-release-tag-fixture` or `--write-release-tag-fixture` to verify or preview a frozen release checklist fixture for a future package version without editing `pyproject.toml` first.
- Add `--release-tag-fixture-path docs/release/checklist.json` to `--check-release-tag-fixture` or `--write-release-tag-fixture` when external release automation stores a frozen checklist JSON file under another root-relative path; absolute paths and `..` escapes are rejected before writer modes can modify files outside `--root`.
- `python3 -m r_project --root <path> --check-release-examples --release-examples-path docs/release-examples.md` compares the release checklist JSON example fence in a README-style Markdown doc against current generated checklist output and exits with status 1 plus drift diagnostics when it differs.
- `python3 -m r_project --root <path> --write-release-examples --dry-run-release-examples --release-examples-path docs/release-examples.md` previews a refreshed release checklist JSON example fence without modifying the Markdown doc; omit the dry-run flag to patch the fence in place. Add `--release-examples-version X.Y.Z` to the checker or writer when docs need to preview a future tag before `pyproject.toml` changes.
- `docs/release-examples.md` stores a checked README-style release checklist JSON example for release dashboards that need embedded snippets alongside the docs-path JSON fixture.
- `docs/release-checklist.md` documents the external release checklist fixture workflow, `docs/release/checklist.json` stores a checked docs-path release checklist fixture that Docker verifies with `--release-tag-fixture-path docs/release/checklist.json`, and `docs/release-index.md` links those release fixture docs with the version/tag guard commands for release automation consumers.
- `docs/automation-index.md` is a combined automation navigation page that links dashboard readiness/schema docs with release readiness fixtures, embeds checked readiness report, compact memory-overlap schema, and release checklist examples via alternate README-style path guards, and records the guard commands plus Docker harness needed before publishing automation-facing docs.
- Docker verification dry-runs the scoped release example writer against `docs/automation-index.md` and its `Embedded release checklist example` section so in-place refresh capability for combined automation docs is exercised in the clean-container harness.
- `tests/fixtures/automation-index-release-smoke.md` is an executable smoke fixture for the scoped automation-index release writer; host tests prove dry-run refreshes replace only the release checklist fence while preserving the surrounding embedded readiness and memory-overlap schema examples.
- `tests/fixtures/release-examples-future-version-smoke.md` is an executable current-version release checklist snippet used by host tests and Docker to prove `--release-examples-version` dry-runs can preview future tags without mutating current-version docs.
- `python3 -m r_project --root <path> --check-release-example-fixtures` audits `docs/release-example-fixtures.md` and exits nonzero when a listed release-example smoke fixture command is missing equivalent `docker-compose.yml` harness coverage.
- `python3 -m r_project --root <path> --check-release-example-sections` audits `docs/release-example-sections.md` and exits nonzero when a registered Markdown release checklist section command is missing equivalent `docker-compose.yml` harness coverage.
- `python3 -m r_project --root <path> --check-release-section-writer-matrix` audits `docs/release-section-writer-matrix.md` and exits nonzero when a registered release checklist section is missing current-version or configurable future-version writer dry-run coverage, or when a matrix command is missing equivalent `docker-compose.yml` harness coverage. Add `--release-section-writer-matrix-version X.Y.Z` to validate a future preview target other than the default `0.2.0`.
- `python3 -m r_project --root <path> --check-automation-index-links` audits `docs/automation-index.md` and exits nonzero when the combined automation navigation page omits a standalone dashboard or release automation surface link.
- `python3 -m r_project --root <path> --check-automation-index-commands` audits `docs/automation-index.md` fenced `r-project` commands and exits nonzero when any documented automation command is missing equivalent `docker-compose.yml` clean-container harness coverage.
- `python3 -m r_project --root <path> --check-automation-command-fixtures` audits `docs/automation-command-fixtures.md` table rows and exits nonzero when any indexed split-doc automation command is missing equivalent `docker-compose.yml` clean-container harness coverage.
- `python3 -m r_project --root <path> --check-dashboard-automation-index` audits `docs/dashboard-automation-index.md` and exits nonzero when the dashboard-only automation entry point omits a dashboard surface link, has no documented `r-project` commands, or documents commands missing equivalent `docker-compose.yml` clean-container harness coverage.
- `python3 -m r_project --root <path> --generate-dashboard-automation-index` emits dashboard automation index surface-link rows and Docker-covered command lines from the built-in dashboard surface registry so new dashboard docs can preview exact additions. Add `--dashboard-automation-index-variant <label>` to generate dashboard section-writer matrix and dashboard automation guard commands for a named preview profile instead of the default `compact` profile.
- `python3 -m r_project --root <path> --write-dashboard-automation-index --dry-run-dashboard-automation-index` previews the `docs/dashboard-automation-index.md` content that would result from appending any missing generated dashboard links and commands; omitting the dry-run flag appends those missing rows once. Add `--dashboard-automation-index-variant <label>` to preview or append named dashboard preview-profile command rows.
- `python3 -m r_project --root <path> --generate-dashboard-example-fixtures` emits `docs/dashboard-example-fixtures.md` table rows derived from `docs/dashboard-index.md` commands so new dashboard index snippets can be registered without hand-copying command cells.
- `python3 -m r_project --root <path> --write-dashboard-example-fixtures --dry-run-dashboard-example-fixtures` previews the dashboard fixture registry content that would result from appending any missing dashboard-index-derived rows; omitting the dry-run flag appends those missing rows once.
- `python3 -m r_project --root <path> --check-dashboard-example-fixtures` audits `docs/dashboard-example-fixtures.md` table rows and exits nonzero when any indexed dashboard readiness/schema command is missing equivalent `docker-compose.yml` clean-container harness coverage or when the registry omits a dashboard-index command.
- `docs/dashboard-section-writer-matrix.md` maps every dashboard fixture registry check command to a corresponding README/schema writer dry-run, and `python3 -m r_project --root <path> --check-dashboard-section-writer-matrix` exits nonzero when a registry row lacks writer coverage or when a matrix command is missing from the Docker harness. Add `--dashboard-section-writer-matrix-variant <label>` to require variant-labeled matrix rows for every dashboard writer command before publishing variant-specific dashboard docs.
- `python3 -m r_project --root <path> --generate-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant <label>` emits Markdown table rows derived from `docs/dashboard-example-fixtures.md` so new dashboard preview variants can copy exact writer dry-run rows into the matrix before running the guard.
- `python3 -m r_project --root <path> --generate-release-section-writer-matrix --release-section-writer-matrix-version <version>` emits Markdown table rows derived from `docs/release-example-sections.md` so release docs can copy exact current-version and future-version writer dry-run rows into the matrix before running the guard.
- `python3 -m r_project --root <path> --write-release-section-writer-matrix --dry-run-release-section-writer-matrix --release-section-writer-matrix-version <version>` previews the `docs/release-section-writer-matrix.md` content that would result from appending any missing registry-derived current/future writer rows; omitting the dry-run flag appends those missing rows once.
- `python3 -m r_project --root <path> --check-release-automation-index` audits `docs/release-automation-index.md` and exits nonzero when the release-only automation entry point omits a release surface link, has no documented `r-project` commands, or documents commands missing equivalent `docker-compose.yml` clean-container harness coverage.
- `python3 -m r_project --root <path> --generate-release-automation-index` emits release automation index surface-link rows and Docker-covered command lines from the built-in release surface registry so new release docs can preview exact additions. Add `--release-automation-index-version X.Y.Z` to generate non-default release preview commands for release examples and release-section writer matrix coverage.
- `python3 -m r_project --root <path> --write-release-automation-index --dry-run-release-automation-index` previews the `docs/release-automation-index.md` content that would result from appending any missing generated release links and commands; omitting the dry-run flag appends those missing rows once. Add `--release-automation-index-version X.Y.Z` to preview or append non-default release preview command rows. Add `--release-automation-index-profile-section 'Heading'` when release automation docs need a named profile block whose preview-version commands can be generated, written, and guarded independently in the same document.
- `python3 -m r_project --root <path> --write-dashboard-section-writer-matrix --dry-run-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant <label>` previews the `docs/dashboard-section-writer-matrix.md` content that would result from appending any missing registry-derived variant rows; omitting the dry-run flag appends those missing rows once.
- `python3 -m r_project --root <path> --check-release-examples-path-safety` audits release example Markdown path override safety by proving absolute paths and `..` escapes are rejected before future checker/writer modes can touch files outside `--root`.
- `docs/release-example-fixtures.md` indexes release-example smoke fixtures and the Docker commands that exercise them so future release-doc fixture additions remain auditable from one page.
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
PYTHONPATH=src python3 -m r_project --root . --check-readme-examples --readme-examples-path README.md
PYTHONPATH=src python3 -m r_project --root . --write-readme-examples --dry-run-readme-examples --readme-examples-path README.md
PYTHONPATH=src python3 -m r_project --root . --check-readme-examples --readme-examples-path docs/usage-examples.md
PYTHONPATH=src python3 -m r_project --root . --write-readme-examples --dry-run-readme-examples --readme-examples-path docs/usage-examples.md
PYTHONPATH=src python3 -m r_project --root . --check-readme-examples --readme-examples-path docs/dashboard-index.md
PYTHONPATH=src python3 -m r_project --root . --write-readme-examples --dry-run-readme-examples --readme-examples-path docs/automation-index.md --readme-examples-section 'Embedded readiness report example'
PYTHONPATH=src python3 -m r_project --root . --check-readme-schema-examples --readme-schema-path docs/dashboard-index.md
PYTHONPATH=src python3 -m r_project --root . --write-readme-schema-examples --dry-run-readme-schema-examples --readme-schema-path docs/automation-index.md --readme-schema-section 'Embedded memory-overlap schema example'
PYTHONPATH=src python3 -m r_project --root . --check-readme-examples --readme-examples-path docs/automation-index.md
PYTHONPATH=src python3 -m r_project --root . --check-readme-schema-examples --readme-schema-path docs/automation-index.md
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
PYTHONPATH=src python3 -m r_project --root . --check-readme-schema-examples
PYTHONPATH=src python3 -m r_project --root . --write-readme-schema-examples --dry-run-readme-schema-examples
PYTHONPATH=src python3 -m r_project --root . --check-readme-schema-examples --readme-schema-path README.md
PYTHONPATH=src python3 -m r_project --root . --check-readme-schema-examples --readme-schema-path docs/dashboard-schema.md
PYTHONPATH=src python3 -m r_project --root . --check-changelog-version
PYTHONPATH=src python3 -m r_project --root . --check-release-tag v0.1.0 --docker-verified
PYTHONPATH=src python3 -m r_project --root . --json --check-release-tag v0.1.0 --docker-verified
PYTHONPATH=src python3 -m r_project --root . --check-release-tag-fixture
PYTHONPATH=src python3 -m r_project --root . --write-release-tag-fixture --dry-run-release-tag-fixture
PYTHONPATH=src python3 -m r_project --root . --write-release-tag-fixture
PYTHONPATH=src python3 -m r_project --root . --write-release-tag-fixture --dry-run-release-tag-fixture --release-tag-fixture-version 0.2.0
PYTHONPATH=src python3 -m r_project --root . --write-release-tag-fixture --dry-run-release-tag-fixture --release-tag-fixture-path tests/fixtures/release-tag-checklist.json
PYTHONPATH=src python3 -m r_project --root . --check-release-tag-fixture --release-tag-fixture-path docs/release/checklist.json
PYTHONPATH=src python3 -m r_project --root . --check-release-examples --release-examples-path docs/release-examples.md
PYTHONPATH=src python3 -m r_project --root . --check-release-examples --release-examples-path docs/automation-index.md --release-examples-section 'Embedded release checklist example'
PYTHONPATH=src python3 -m r_project --root . --write-release-examples --dry-run-release-examples --release-examples-path docs/automation-index.md --release-examples-section 'Embedded release checklist example'
PYTHONPATH=src python3 -m r_project --root . --write-release-examples --dry-run-release-examples --release-examples-path tests/fixtures/automation-index-release-smoke.md --release-examples-section 'Embedded release checklist example'
PYTHONPATH=src python3 -m r_project --root . --write-release-examples --dry-run-release-examples --release-examples-path docs/release-examples.md
PYTHONPATH=src python3 -m r_project --root . --write-release-examples --dry-run-release-examples --release-examples-version 0.2.0 --release-examples-path docs/release-examples.md
PYTHONPATH=src python3 -m r_project --root . --write-release-examples --dry-run-release-examples --release-examples-version 0.2.0 --release-examples-path tests/fixtures/release-examples-future-version-smoke.md
PYTHONPATH=src python3 -m r_project --root . --check-release-example-fixtures
PYTHONPATH=src python3 -m r_project --root . --check-release-example-sections
PYTHONPATH=src python3 -m r_project --root . --check-release-section-writer-matrix
PYTHONPATH=src python3 -m r_project --root . --check-release-section-writer-matrix --release-section-writer-matrix-version 0.2.0
PYTHONPATH=src python3 -m r_project --root . --generate-release-section-writer-matrix --release-section-writer-matrix-version 0.2.0
PYTHONPATH=src python3 -m r_project --root . --write-release-section-writer-matrix --dry-run-release-section-writer-matrix --release-section-writer-matrix-version 0.2.0
PYTHONPATH=src python3 -m r_project --root . --check-release-examples-path-safety
PYTHONPATH=src python3 -m r_project --root . --generate-release-automation-index
PYTHONPATH=src python3 -m r_project --root . --generate-release-automation-index --release-automation-index-version 0.3.0
PYTHONPATH=src python3 -m r_project --root . --generate-release-automation-index --release-automation-index-version 0.3.0 --release-automation-index-profile-section 'Release 0.3.0 preview profile'
PYTHONPATH=src python3 -m r_project --root . --write-release-automation-index --dry-run-release-automation-index
PYTHONPATH=src python3 -m r_project --root . --write-release-automation-index --dry-run-release-automation-index --release-automation-index-version 0.3.0
PYTHONPATH=src python3 -m r_project --root . --write-release-automation-index --dry-run-release-automation-index --release-automation-index-version 0.3.0 --release-automation-index-profile-section 'Release 0.3.0 preview profile'
PYTHONPATH=src python3 -m r_project --root . --check-release-automation-index
PYTHONPATH=src python3 -m r_project --root . --check-release-automation-index --release-automation-index-version 0.3.0
PYTHONPATH=src python3 -m r_project --root . --check-release-automation-index --release-automation-index-version 0.3.0 --release-automation-index-profile-section 'Release 0.3.0 preview profile'
PYTHONPATH=src python3 -m r_project --root . --check-automation-index-links
PYTHONPATH=src python3 -m r_project --root . --check-automation-index-commands
PYTHONPATH=src python3 -m r_project --root . --check-automation-command-fixtures
PYTHONPATH=src python3 -m r_project --root . --generate-dashboard-automation-index
PYTHONPATH=src python3 -m r_project --root . --generate-dashboard-automation-index --dashboard-automation-index-variant expanded
PYTHONPATH=src python3 -m r_project --root . --write-dashboard-automation-index --dry-run-dashboard-automation-index
PYTHONPATH=src python3 -m r_project --root . --write-dashboard-automation-index --dry-run-dashboard-automation-index --dashboard-automation-index-variant expanded
PYTHONPATH=src python3 -m r_project --root . --check-dashboard-automation-index
PYTHONPATH=src python3 -m r_project --root . --check-dashboard-automation-index --dashboard-automation-index-variant expanded
PYTHONPATH=src python3 -m r_project --root . --generate-dashboard-example-fixtures
PYTHONPATH=src python3 -m r_project --root . --write-dashboard-example-fixtures --dry-run-dashboard-example-fixtures
PYTHONPATH=src python3 -m r_project --root . --check-dashboard-example-fixtures
PYTHONPATH=src python3 -m r_project --root . --check-dashboard-section-writer-matrix
PYTHONPATH=src python3 -m r_project --root . --check-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant compact
PYTHONPATH=src python3 -m r_project --root . --check-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant expanded
PYTHONPATH=src python3 -m r_project --root . --generate-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant compact
PYTHONPATH=src python3 -m r_project --root . --generate-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant expanded
PYTHONPATH=src python3 -m r_project --root . --write-dashboard-section-writer-matrix --dry-run-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant compact
PYTHONPATH=src python3 -m r_project --root . --write-dashboard-section-writer-matrix --dry-run-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant expanded
PYTHONPATH=src python3 -m r_project.lint --root .
docker compose run --build --rm test
```

## Operating rule

The autonomous agent must turn this into a real, tested project by finishing concrete backlog items each run. It should not stop at vague improvements when code can be created safely.

Scheduled R runs are PR-first and reviewer-gated: changes must be made on `ai/r/*` branches, pushed with `/usr/local/bin/r-bot-git-push`, opened/updated as PRs to `main`, reviewed by the AI reviewer, and merged to `main` by r-coder only when `AI_REVIEW:CLEAR`, clean/mergeable state, and local Docker verification are all present.

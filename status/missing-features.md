# R Missing Features

Prioritized backlog for autonomous implementation.

## P0 — make the repo real

- [x] Choose and document a concrete product direction for R based on repo/user context.
- [x] Create the first buildable source scaffold.
- [x] Add the first automated test suite.
- [x] Add build/lint/test commands and record them in `status/current-state.md`.

## P1 — implementation depth

- [x] Implement the first useful end-to-end feature.
- [x] Add CLI or API entry points, depending on the chosen product direction.
- [x] Add fixtures/examples for expected behavior.
- [x] Implement markdown output for human-readable reports.
- [x] Add CLI option to fail with a nonzero exit code when active blockers exist.
- [x] Add backlog priority grouping so reports summarize P0/P1/P2 progress separately.
- [x] Package the CLI for editable installs and document `pip install -e .` usage.
- [x] Add vector memory-layout padding helper for issue-driven runtime work.
- [x] Add documented memory-layout errors for invalid vector and struct alignments.
- [x] Add optional memory-layout overflow-limit checks for explicit runtime size bounds.
- [x] Add object-layout helpers for nesting struct/vector layouts into composite runtime objects.
- [x] Add named object-layout renderers for debugging composite runtime memory maps.
- [x] Add symbolic field tags or provenance metadata to composite runtime memory maps.
- [x] Add tagged nested-layout renderers that recursively include child struct/vector memory maps.
- [x] Add symbolic byte-span summaries for rendered layouts and overlap diagnostics.
- [x] Add recursive byte-span flattener for nested layouts so overlap checks can compare fully qualified child ranges.
- [x] Add layout overlap detector that consumes flattened byte spans and reports intersecting runtime ranges.
- [x] Add layout overlap reporter/renderer for human-readable overlap diagnostics.
- [x] Add span-filtering helpers for flattened byte spans so runtime diagnostics can narrow overlap reports by qualified names and provenance tags.
- [x] Add leaf-only byte-span helpers so diagnostics can suppress parent container ranges before overlap reports.
- [x] Add grouped byte-span overlap reports by shared provenance tag or qualified-name prefix for larger runtime diagnostics.
- [x] Add grouped byte-span overlap totals so compact dashboards can consume counts and intersecting-byte totals without full reports.
- [x] Add compact grouped byte-span overlap total renderers for dashboard and PR-comment Markdown tables.
- [x] Add grouped byte-span overlap threshold helpers so dashboards can flag overlap-count or intersecting-byte budget violations.
- [x] Add Markdown threshold violation renderers so PR comments can show which grouped byte-span totals exceed dashboard budgets.
- [x] Add fixture-backed CLI/demo output for memory-layout threshold violation examples.
- [x] Add structured JSON output for the memory-threshold demo so runtime diagnostics have machine-readable CLI fixtures.
- [x] Add fixture-backed grouped overlap totals CLI/demo output in Markdown and JSON so dashboards can consume compact non-violation summaries.
- [x] Add CLI options to emit fixture-backed grouped overlap totals by qualified-name prefix depth for scoped dashboard summaries.
- [x] Add fixture-backed grouped overlap threshold violation CLI output by qualified-name prefix depth for scoped dashboard gates.
- [x] Add CLI flags for custom memory-overlap threshold budgets so dashboard gates can tune overlap-count and intersecting-byte limits.
- [x] Add CLI filters that let memory-overlap demos narrow fixture spans by qualified-name prefix or provenance tag before totals/threshold calculations.
- [x] Add a compact JSON schema description for memory-overlap demo outputs so dashboard consumers can validate fields without reading source.
- [x] Start the interpreted Rust inside C showcase with a tiny C-hosted Rust-like expression interpreter fixture.
- [x] Extend the C-hosted Rust-like interpreter with `let` bindings and identifier lookup, backed by a C host fixture that evaluates `let x = 2 + 3; x * 4` to `20` and reports undefined identifiers.
- [x] Extend the C-hosted Rust-like interpreter with expression-statement sequencing so multiple semicolon-separated expressions preserve the final value.
- [x] Extend the C-hosted Rust-like interpreter with assignment/mutation support so existing bindings can be updated and undefined assignment targets fail explicitly.

## P2 — project quality

- [x] Improve README with real usage examples.
- [x] Add release/versioning notes.
- [x] Add license file.
- [x] Add type-checking or linting command once the toolchain choice is stable.
- [x] Dockerize the test/verification harness so autonomous runs validate in a clean container.
- [x] Add tests that enforce README report examples stay in sync with current CLI output.
- [x] Add a CLI check that reports README JSON/Markdown example drift on demand.
- [x] Add a CLI generator that emits README JSON/Markdown example fences from the current report on demand.
- [x] Add a CLI check that reports memory-overlap demo JSON Schema fixture drift on demand.
- [x] Add a README example writer that patches generated JSON/Markdown example fences into README.md automatically.
- [x] Add a README example writer dry-run mode so agents can preview patched README content before modifying README.md.
- [x] Add a CHANGELOG/version drift guard so release automation can verify documented user-visible version notes before tagging.
- [x] Add compact README JSON Schema docs/examples for memory-overlap demo dashboard consumers.
- [x] Add a release tag checklist command so release automation can verify tag names, Docker evidence, and clean git state before publishing.
- [x] Add release-tag checklist JSON output so external release automation can consume machine-readable dry-run summaries.
- [x] Add schema-specific README drift checks for compact memory-overlap JSON Schema docs.
- [x] Add release-tag checklist fixture drift tests for external release automation that depends on frozen JSON summaries.
- [x] Add a release checklist fixture writer so release automation can refresh frozen JSON summaries without manual copying.
- [x] Add a README schema example writer so compact memory-overlap JSON Schema docs can be refreshed automatically.
- [x] Add a release checklist fixture writer verification mode that can target future package versions once release automation starts preparing non-current tags.
- [x] Add a schema writer verification mode that can refresh alternate README paths if dashboard docs move out of the main README.
- [x] Add a release checklist fixture writer path override if external release automation stores frozen summaries outside `tests/fixtures/`.
- [x] Add a README report example writer/checker path override if dashboard-ready usage examples move into standalone docs.
- [x] Add a standalone usage-example document backed by README report example checks for dashboard consumers.
- [x] Add a standalone dashboard schema document backed by README schema example checks for dashboard consumers.
- [x] Add a dashboard release/readiness index document backed by report and schema drift checks for dashboard consumers.
- [x] Add standalone release checklist fixture docs backed by a checked external fixture path for release automation consumers.
- [x] Add a release readiness index that links release checklist fixture docs with version/tag guard commands for release automation consumers.
- [x] Add a combined dashboard/release automation index so consumers have one docs entry point across readiness reports, schema examples, and release fixtures.
- [x] Add standalone release checklist examples backed by a README-style drift guard for release automation consumers.
- [x] Add a release checklist example future-version flag so Markdown release docs can preview a non-current tag before `pyproject.toml` changes.
- [x] Add embedded automation-index readiness and schema examples backed by alternate README-style drift checks for combined dashboard/release automation consumers.
- [x] Add an embedded automation-index release checklist example backed by a scoped README-style release drift check for combined automation consumers.
- [x] Add a scoped release-example writer smoke test for `docs/automation-index.md` so Docker verification previews in-place release snippet refreshes for combined automation docs.
- [x] Add a release-docs smoke fixture that verifies the scoped automation-index writer output preserves surrounding readiness/schema examples unchanged.
- [x] Add a compact future-version release example dry-run smoke fixture so preview mode proves current-version docs stay unchanged.
- [x] Add a standalone release-example fixture index so release smoke fixtures and Docker coverage can be audited from one page.
- [x] Add a release-example fixture index guard so Docker coverage drift is caught automatically when fixture rows change.
- [x] Add a release automation docs guard that validates `docs/automation-index.md` links every standalone dashboard and release automation surface.
- [x] Add an automation docs command index guard that verifies every `r-project` command documented in `docs/automation-index.md` is represented in Docker verification.
- [x] Add a release examples path safety audit guard so Markdown release example path override checks stay enforced in host and Docker verification.
- [x] Add an automation command fixture index so future split automation command docs stay auditable against Docker verification.
- [x] Add a release example section registry so future release docs can embed multiple independently named checklist snippets in one Markdown file.
- [x] Add a release section writer matrix so current-version and future-version release snippet writers stay covered for every registered release section.
- [x] Add a dashboard automation fixture registry so future dashboard docs split readiness/schema examples across multiple independently checked Markdown sections.
- [x] Add a dashboard section writer matrix so readiness and schema example writers can target independently named Markdown sections.
- [x] Add a configurable release-section writer matrix preview version so future release docs can audit non-`0.2.0` dry-run targets.
- [x] Add a dashboard section writer matrix guard so readiness/schema writer dry-runs stay covered for every dashboard fixture registry row.
- [x] Add a configurable dashboard-section writer matrix preview mode so variant-specific dashboard docs can be audited against Docker coverage.
- [x] Add a dashboard section writer matrix row generator so new variant-specific dashboard docs can preview registry-derived writer rows before appending them.
- [x] Add a dashboard section writer matrix row writer so new variant-specific dashboard docs can safely append generated writer rows after preview.
- [x] Add a release section writer matrix row generator so release docs can preview registry-derived current/future writer rows before appending them.
- [x] Add a release section writer matrix row writer so release docs can safely append generated current/future writer rows after preview.
- [x] Add a dashboard automation index guard so future dashboard-only automation docs must link every dashboard surface and keep documented commands covered in Docker.
- [x] Add a dashboard example fixture row writer so dashboard-index commands can safely append missing registry rows after preview.
- [x] Add a dashboard automation index row writer so dashboard-only docs can safely append missing link/command rows after preview.
- [x] Add a release automation index row writer so release-only docs can safely append missing link/command rows after preview.
- [x] Add a release automation index preview-version selector so release-only docs can generate and dry-run non-default release preview profiles.
- [x] Add a dashboard automation index variant selector so dashboard-only docs can generate, dry-run, and guard multiple named preview profiles beyond default command rows.
- [x] Add release automation index named profile sections so multiple release preview versions can be generated, written, and guarded independently in one document.

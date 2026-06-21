# Changelog

All notable user-visible changes to R are tracked here. Releases should follow the semantic versioning policy documented in `README.md` and use tags that match `pyproject.toml`.

## Unreleased

- Added `threshold_run_signal_density_delta(array, min, max)` and `outlier_run_signal_density_delta(array, min, max)` normalized threshold-run balance helpers to the C-hosted Rustic interpreter, with direct, composed, diagnostic, and looped cleanup fixture coverage.
- Added `count(array, value)` value-frequency helper support to the C-hosted Rustic interpreter, with loop-built, rebuilt, and function-returned collection showcase fixtures plus non-array, non-integer, and wrong-argument diagnostics.
- Added `sum(array)` compact array summary support to the C-hosted Rustic interpreter, with loop-built, rebuilt, and function-returned collection showcase fixtures plus non-array and wrong-argument diagnostics.
- Added `push(array, value)` bounded append-style construction to the C-hosted Rustic interpreter, with loop-built collection showcase fixtures and diagnostics for non-array, non-integer, and full-array cases.
- Added `match`-style expression dispatch to the C-hosted Rustic interpreter, with fixture coverage for selected integer arms, default arms, skipped unselected arms, and loop-control inside matched arms.
- Added `break`/`continue` loop-control semantics to the C-hosted Rustic interpreter, with fixture coverage for early loop exits and skipped iterations.
- Added release/versioning policy notes for the current `0.1.0` package.
- Switched Project R from MIT to GNU Affero General Public License v3.0 or later (`AGPL-3.0-or-later`) so distributed and network-served modified versions remain open-source.
- Added `r-project-lint` and `python -m r_project.lint` syntax-check commands for source/test files.
- Documented and enforced memory-layout validation for non-power-of-two alignments.
- Added `layout_field(...)` for embedding computed struct/vector layouts into larger composite runtime structures.
- Added `render_layout(...)` for stable named memory-map debugging of struct and vector layouts.
- Added optional symbolic field tags/provenance metadata to struct memory-map rendering.
- Added recursive flattened byte spans for fully qualified nested memory range diagnostics.
- Added `find_overlapping_byte_spans(...)` for pairwise runtime memory-range overlap diagnostics.
- Added `render_byte_span_overlaps(...)` for stable Markdown overlap diagnostics with an explicit empty state.
- Added `leaf_byte_spans(...)` for suppressing parent container ranges in leaf-only overlap diagnostics.
- Added grouped byte-span overlap helpers and Markdown renderers for shared provenance tags and qualified-name prefix pairs.
- Added Markdown threshold violation tables for grouped byte-span overlap dashboard budgets.
- Added memory-threshold demo CLI flags for custom overlap-count and intersecting-byte dashboard budgets.
- Added `--check-changelog-version` so release automation can catch README/CHANGELOG version drift against `pyproject.toml` before tagging.
- Added `--check-release-tag` so release automation can verify candidate tag names, Docker verification evidence, and clean git state before publishing.
- Added JSON output for `--check-release-tag` so release automation can consume machine-readable checklist summaries before publishing.
- Added `--check-release-tag-fixture` and `tests/fixtures/release-tag-checklist.json` so release automation can detect frozen checklist JSON drift.
- Added `--write-release-tag-fixture` and `--dry-run-release-tag-fixture` so release automation can refresh or preview frozen release checklist JSON fixtures without manual copying.
- Added `docs/release-index.md` as a release readiness entry point linking fixture docs, checked JSON, and version/tag guard commands.
- Added `--check-release-examples`/`--write-release-examples` plus `docs/release-examples.md` so release dashboards can verify and refresh README-style release checklist JSON snippets.
- Added `--release-examples-version` so release docs can preview future README-style checklist snippets before `pyproject.toml` changes.
- Added `docs/release-example-fixtures.md` and Docker dry-run coverage so release-example smoke fixtures are auditable from one index.

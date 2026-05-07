# Changelog

All notable user-visible changes to R are tracked here. Releases should follow the semantic versioning policy documented in `README.md` and use tags that match `pyproject.toml`.

## Unreleased

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

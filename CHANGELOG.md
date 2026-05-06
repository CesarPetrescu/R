# Changelog

All notable user-visible changes to R are tracked here. Releases should follow the semantic versioning policy documented in `README.md` and use tags that match `pyproject.toml`.

## Unreleased

- Added release/versioning policy notes for the current `0.1.0` package.
- Added MIT license metadata for Project R contributors.
- Added `r-project-lint` and `python -m r_project.lint` syntax-check commands for source/test files.
- Documented and enforced memory-layout validation for non-power-of-two alignments.
- Added `layout_field(...)` for embedding computed struct/vector layouts into larger composite runtime structures.
- Added `render_layout(...)` for stable named memory-map debugging of struct and vector layouts.
- Added optional symbolic field tags/provenance metadata to struct memory-map rendering.
- Added recursive flattened byte spans for fully qualified nested memory range diagnostics.
- Added `find_overlapping_byte_spans(...)` for pairwise runtime memory-range overlap diagnostics.
- Added `render_byte_span_overlaps(...)` for stable Markdown overlap diagnostics with an explicit empty state.

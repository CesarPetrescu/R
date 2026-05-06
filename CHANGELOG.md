# Changelog

All notable user-visible changes to R are tracked here. Releases should follow the semantic versioning policy documented in `README.md` and use tags that match `pyproject.toml`.

## Unreleased

- Added release/versioning policy notes for the current `0.1.0` package.
- Added MIT license metadata for Project R contributors.
- Added `r-project-lint` and `python -m r_project.lint` syntax-check commands for source/test files.
- Documented and enforced memory-layout validation for non-power-of-two alignments.
- Added `layout_field(...)` for embedding computed struct/vector layouts into larger composite runtime structures.

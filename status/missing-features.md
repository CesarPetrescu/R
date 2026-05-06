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

## P2 — project quality

- [x] Improve README with real usage examples.
- [x] Add release/versioning notes.
- [x] Add license file.
- [x] Add type-checking or linting command once the toolchain choice is stable.
- [x] Dockerize the test/verification harness so autonomous runs validate in a clean container.
- [x] Add tests that enforce README report examples stay in sync with current CLI output.
- [x] Add a CLI check that reports README JSON/Markdown example drift on demand.

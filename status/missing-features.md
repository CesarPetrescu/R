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

## P2 — project quality

- [x] Improve README with real usage examples.
- [x] Add release/versioning notes.
- [x] Add license file.
- [x] Add type-checking or linting command once the toolchain choice is stable.
- [x] Dockerize the test/verification harness so autonomous runs validate in a clean container.
- [x] Add tests that enforce README report examples stay in sync with current CLI output.
- [x] Add a CLI check that reports README JSON/Markdown example drift on demand.

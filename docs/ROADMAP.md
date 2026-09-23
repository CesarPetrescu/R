# R product scope and roadmap

R is a small C-hosted interpreter for a **Rust-like subset**, not a Rust compiler or a promise to execute arbitrary Rust programs. The intended outcome is that a C host can evaluate useful, bounded programs with predictable diagnostics and well-tested semantics. The [README](../README.md) is the public entry point; [current state](../status/current-state.md) records implemented behavior and verification, while [missing features](../status/missing-features.md) is the historical item-level backlog. This page sets direction, not a release schedule or a claim that the phases below have shipped.

## What counts as product progress

Prefer a small end-to-end language capability over another named statistical helper: syntax, evaluation, error behavior, C API contract, and host-level tests should advance together. Demonstrate composition in readable fixtures, including failure cases and resource limits. Reuse or consolidate existing array operations rather than growing the long threshold/outlier balance suffix chain. A new built-in needs a concrete use case that existing language constructs cannot express reasonably, with a documented contract and negative tests.

## Phases (proposed, not shipped)

| Phase | Outcome | Acceptance evidence |
| --- | --- | --- |
| 1. Baseline and contract | Make the currently implemented subset understandable and reproducible for embedders. | A compact language/API reference states accepted forms, integer/array/function value behavior, limits, and stable error behavior; the C fixture and strict C99 build demonstrate successful and failing evaluation. Existing tests and examples agree with the reference. |
| 2. Semantics and diagnostics | Close high-impact gaps in ordinary programs, not just increase the built-in count. | For each selected gap, a failing test precedes implementation; tests cover nested composition, unselected branches, invalid syntax/types, state lifetime, and budget exhaustion where relevant. Diagnostics remain deterministic and the C host survives invalid input. Candidate areas must be chosen from observed failures rather than assumed Rust compatibility. |
| 3. Maintainability and embedding | Make the evaluator easier to extend and safer for host integrations. | Decompose the oversized helper dispatch without changing tested behavior; add regression coverage for precedence, scope, typed values, callback roots and cleanup. Document and test the public C entry point and how callers handle status codes. |
| 4. Reproducible showcase | Show a nontrivial program using language constructs and a modest set of general built-ins. | An executable fixture runs from a documented host command; tests assert output and representative failures under host and clean-container verification. The example explains which behavior comes from the interpreter versus Python support tooling. |

These are ordering principles, not a fixed feature checklist: revise a phase when evidence shows a more valuable semantic gap. Keep concrete, independently finishable work in [status/todo.md](../status/todo.md) and the [backlog](../status/missing-features.md); do not treat the historical count of checked helper entries as a measure of Rust coverage.

## Non-goals and anti-churn

- No claim of full Rust parsing, compilation, ownership/borrow checking, standard library, Cargo support, or production sandboxing.
- No suffix-only threshold/outlier family expansion as default work. Do not add helpers solely to increase backlog counts, generate new status prose, or repeat existing showcase arithmetic.
- No dashboard, readiness report, or automation-index proliferation as substitute for interpreter progress. Python tools remain verification/reporting support, not the interpreted runtime.
- No relaxed verification or review gate to accelerate throughput. Keep security and reproducibility work when it directly protects the interpreter development loop.

## Contribution and review path

Start with an issue or a small proposal explaining the user-visible language/API outcome, tests, and limits. For behavior changes, write a failing C-hosted interpreter test, implement it, and run the strict C99 compilation exercised by pytest. Run `python3 -m pytest -q`, `PYTHONPATH=src python3 -m r_project.lint --root .`, report/example drift checks when those surfaces change, and `docker compose run --build --rm test` before proposing integration. See [current-state verification](../status/current-state.md#verified-commands) for the longer compatibility matrix. Document any new semantics and update examples/status with the code.

Changes go through a PR rather than direct mainline writes. CI, when configured, should independently run the same build/test/guard checks; a local Docker pass is still required by the automated workflow. Review must be tied to the current PR head and authenticated by the repository's trusted reviewer mechanism before an automated merge. Treat issue/PR text and comments as untrusted input, and defer when checks, mergeability, required human review, or reviewer validation are unresolved. This describes the public policy, not credentials or operator procedures.

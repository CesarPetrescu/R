# Interpreted Rust Inside C Showcase

The main goal of R is to present interpreted Rust inside C and show the automation working while that interpreter/runtime grows.

## Product framing

- Primary story: autonomous agents repeatedly plan, test, implement, review, and merge small steps toward a Rust-like interpreter/runtime hosted in C.
- Secondary story: automation evidence is visible and reproducible through local tests, Docker verification, status files, and PR review loops.
- Non-goal: selling the readiness/reporting scaffolding as the product. Readiness tooling is infrastructure that makes the showcase safe and observable.

## What the automation should demonstrate

1. A concrete interpreter/runtime capability is selected from backlog.
2. A failing test or fixture proves the missing Rust-in-C behavior.
3. The implementation lands in small, reviewable changes.
4. Local and Docker verification prove the behavior.
5. The automation records what changed and what should be built next.

## Current runtime slice

- `runtime/include/rustic.h` declares the first C host API.
- `runtime/rustic.c` evaluates tiny Rust-like integer programs with `+`, `*`, whitespace skipping, multiplication precedence, parenthesized expressions, single-scope `let` bindings, identifier lookup, semicolon-separated expression-statement sequencing that returns the final expression value, assignment/mutation, and equality comparisons (`==`) that return boolean integers.
- `tests/fixtures/rustic_expression_driver.c` is the executable C host fixture used by pytest.
- `tests/test_rustic_interpreter.py` compiles the runtime and proves `1 + 2 * 3 => 7`, `(1 + 2) * 3 => 9`, `let x = 2 + 3; x * 4 => 20`, `let x = 1; x = x + 2; x => 3`, `let x = 3; x == 3 => 1`, `let x = 3; x == 4 => 0`, `1 + 2; 3 * 4; 5 + 6 => 11`, and stable invalid-expression/undefined-identifier/equality diagnostics.

## Folder policy

Automation-specific plans and manifests belong in `automations/`. Existing checked docs under `docs/` may remain there until the CLI and Docker harness can safely address their new locations without breaking drift guards.

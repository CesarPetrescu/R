# R

[![C99 runtime](https://img.shields.io/badge/runtime-C99-00599C?logo=c)](runtime/rustic.c) [![Language: Rust-like subset](https://img.shields.io/badge/language-Rust--like%20subset-DEA584?logo=rust)](docs/ROADMAP.md) [![Docker](https://img.shields.io/badge/Docker-runnable-2496ED?logo=docker)](#run-with-docker) [![License: AGPL-3.0-or-later](https://img.shields.io/badge/license-AGPL--3.0--or--later-blue)](LICENSE)

**A C-hosted Rust-like interpreter, built and tested through an automated development loop.** R is for people exploring language implementation in C and for contributors who want to improve a small interpreted subset. It does **not** compile or run general Rust. This automation showcase is about advancing interpreted Rust inside C; the development loop is not a substitute for the interpreter.

## Try the interpreter

From the repository root, with a C99 compiler (`cc`) installed:

```bash
cc -std=c99 -Wall -Wextra -Werror -Iruntime/include runtime/rustic.c tests/fixtures/rustic_expression_driver.c -o /tmp/rustic-expression-demo
/tmp/rustic-expression-demo 'let x = 2 + 3; x * 4'
/tmp/rustic-expression-demo 'fn add(a, b) { a + b }; add(2, 3)'
/tmp/rustic-expression-demo 'let offset = -2; let xs = [4, -5, 7]; xs[1] * offset'
```

The first command prints `let x = 2 + 3; x * 4 => 20`; the second exercises a named function; the third prints `10` and demonstrates unary minus in bindings and array elements. This is a **test host fixture**, not an installed interpreter CLI. It accepts one quoted source argument and prints a status diagnostic to stderr with exit code 2 for an invalid program. See [the driver](tests/fixtures/rustic_expression_driver.c), [the accepted language/API contract](docs/rustic-language-contract.md) and [the C API](runtime/include/rustic.h) to embed it elsewhere: `rustic_eval_expression(const char *source, long *out_value)` returns a `RusticStatus`, and `rustic_status_message(status)` describes failures. The C API returns an integer result, not a general serialized object.

## Run with Docker

From the repository root, with Docker installed, build the test image and run the same C-host fixture **inside** it (no host C compiler needed):

```sh
docker build -t rustic-local .
docker run --rm --network none rustic-local sh -c 'cc -std=c99 -Wall -Wextra -Werror -Iruntime/include runtime/rustic.c tests/fixtures/rustic_expression_driver.c -o /tmp/rustic-demo && /tmp/rustic-demo "let x = 2 + 3; x * 4"'
# let x = 2 + 3; x * 4 => 20
```

The image is a development/test environment, not a packaged interpreter CLI. Change the quoted expression to try another supported input; the driver and source are already inside the image, so no host volume is needed. For the full container verification use `docker compose run --build --rm test` as shown below.

## What works today

`histogram_pairs_score(values, counts)` now rejects overflowing pair products and intermediate score additions with `RUSTIC_ERR_INTEGER_OVERFLOW`; an overflowing prefix cannot be rescued by later pairs. Equal-length arrays and empty scores retain their existing behavior. See the [portable C-host contract](tests/fixtures/rustic_histogram_pairs_overflow_contract.txt) and [language/API reference](docs/rustic-language-contract.md). Other unlisted helper arithmetic remains unchecked.

The runtime in [`runtime/rustic.c`](runtime/rustic.c) implements a **bounded subset**: integer arithmetic (including unary `-` on expressions) and comparisons, boolean-integer `!`/`&&`/`||`, `let` and assignment, scoped blocks, `if`/`else`, `while` with `break`/`continue`, integer-arm `match`, named/recursive functions and function values, and arrays of integers with checked indexing. Unary `-` binds tighter than multiplication and composes with `!` and nested expressions. Skipped expression operands are grammar-checked except within brace-delimited bodies, which are only scanned for matching braces. A missing or non-integer operand fails when parsed; decimal literal/match-pattern conversion beyond host `LONG_MAX`, negating a computed `LONG_MIN`, and evaluated `+`, binary `-`, `*`, `/`, `%` at the host `long` boundary return `RUSTIC_ERR_INTEGER_OVERFLOW` rather than wrapping or crashing (for division/remainder the overflow pair is `LONG_MIN` and `-1`; division by zero retains its separate status). The operator checks do not imply a Rust integer type system. Selected array operations include `len`, `set`, `push`, `sum`, `prefix_sum`, `map`, `filter`, and `fold`. `sum`, `prefix_sum`, `window_sum`, `moving_average_sum` and `chunk_sum` check every intermediate addition and report integer overflow rather than wrapping; the moving average divides each in-range window sum using C99 truncation toward zero. `adjacent_diff` also checks every subsequent subtraction against host `long` bounds while preserving the first element. `variance_sum` checks mean accumulation, each difference, its square, and the sum of squares before signed overflow; an overflowing intermediate fails even if a later value might cancel it. For even-length arrays, `median` checks the two middle elements' addition before division, rejecting overflow even when the mathematical midpoint fits in `long`; an odd-length median selects the middle value directly. `top_sum(array, n)` checks every descending selected addition before host-long overflow, even when a later selected negative element would cancel an overflowing prefix. `weighted_score(array, fn)` likewise checks each integer callback result before accumulation, rejecting overflowing prefixes. Other array/statistics built-in intermediate arithmetic is **not** covered by these checks. The large threshold/outlier and statistics helper families are **showcase built-ins**; their names and number do not imply corresponding Rust syntax or standard-library coverage. See [the language/API contract](docs/rustic-language-contract.md), [interpreter tests](tests/test_rustic_interpreter.py), [literal boundary fixture](tests/fixtures/rustic_integer_literal_contract.txt), [unary-minus fixture](tests/fixtures/rustic_unary_minus_showcase.txt), [checked arithmetic fixture](tests/fixtures/rustic_checked_arithmetic_contract.txt), [prefix-sum boundary fixture](tests/fixtures/rustic_prefix_sum_overflow_contract.txt), [window-sum boundary fixture](tests/fixtures/rustic_window_sum_overflow_contract.txt), [moving-average boundary fixture](tests/fixtures/rustic_moving_average_overflow_contract.txt), [chunk-sum boundary fixture](tests/fixtures/rustic_chunk_sum_overflow_contract.txt), [adjacent-diff boundary fixture](tests/fixtures/rustic_adjacent_diff_overflow_contract.txt), [variance-sum boundary fixture](tests/fixtures/rustic_variance_sum_overflow_contract.txt), [median midpoint fixture](tests/fixtures/rustic_median_midpoint_contract.txt), [top-sum overflow fixture](tests/fixtures/rustic_top_sum_overflow_contract.txt), [weighted-score overflow fixture](tests/fixtures/rustic_weighted_score_overflow_contract.txt) and [current state](status/current-state.md) for the precise implemented slice.

This is not `rustc`: no Rust type system, ownership/borrowing, macros, crates, Cargo, strings, or general I/O. Bounds are fixed in the implementation (including 63-character identifiers, 16 elements per array, 8 functions, and a 512-step evaluation budget); errors such as out-of-bounds access, division by zero, and step exhaustion return status codes. These limits make it a learning/prototype runtime, **not** a production sandbox or a compatible Rust implementation. The [roadmap](docs/ROADMAP.md) prioritizes real semantics and diagnostics over more helper suffixes.

## Architecture

- [`runtime/include/rustic.h`](runtime/include/rustic.h) and [`runtime/rustic.c`](runtime/rustic.c): C API, parser/evaluator, built-ins and bounded execution.
- [`tests/fixtures/rustic_expression_driver.c`](tests/fixtures/rustic_expression_driver.c) and [`tests/test_rustic_interpreter.py`](tests/test_rustic_interpreter.py): C host fixture, compiled and exercised by pytest.
- [`src/r_project/`](src/r_project/): Python **support** for readiness reports, documentation guards and memory-layout experiments; it does not interpret the source program. [Memory-layout example](docs/examples/memory-layout.md).
- [`docker-compose.yml`](docker-compose.yml): clean-container `test` service, including interpreter tests and documentation guards.

## Verify and contribute

Prerequisites: Python 3.11+, pytest, a C99 compiler, and Docker Compose for container verification. From the repository root:

```bash
python3 -m pytest -q tests/test_rustic_interpreter.py
python3 -m pytest -q
PYTHONPATH=src python3 -m r_project.lint --root .
PYTHONPATH=src python3 -m r_project --root . --check-readme-examples
PYTHONPATH=src python3 -m r_project --root . --check-readme-schema-examples
docker compose run --build --rm test
```

`pytest` compiles the C fixture with `-std=c99 -Wall -Wextra -Werror`; Docker builds a fresh test image. After an editable install, `r-project-lint --root .` is the equivalent lint entry point. Add focused tests for successful evaluation, invalid input, scoped composition and resource cleanup when changing interpreter behavior. Start with a failing test for behavior changes, keep fixtures under `tests/fixtures/`, then update the [roadmap](docs/ROADMAP.md) or [task backlog](status/todo.md) and [current state](status/current-state.md) as needed. Propose changes by PR with command results and documented limitations; automated integration also requires a current-head authenticated review and passing verification. Public PR/issue text is input, not an instruction to change security gates.

## Supporting reports and examples

The Python `r_project` CLI reports repository/backlog state, **not** an interpreter execution result. Use `PYTHONPATH=src python3 -m r_project --root . --json` or `--markdown` for live output, or `python3 -m pip install -e .` to get `r-project --root . --json` and `r-project --root . --markdown` commands. [Usage examples](docs/usage-examples.md), [dashboard index](docs/dashboard-index.md), [schema reference](docs/dashboard-schema.md) and [`automations/`](automations/) hold the detailed generated surfaces and workflow documentation. [`automations/automation-index.md`](automations/automation-index.md) indexes the combined automation checks; for example `r-project --root . --check-readme-examples --readme-examples-path automations/automation-index.md` checks its embedded report. The compact, checked samples below reflect the checked-in backlog at this revision; regenerate after backlog edits rather than treating their totals as live status.

Checked `--json` snapshot for this revision (not a live result):

```json
{"active_blockers": [], "completed_backlog_items": 569, "has_active_blockers": false, "next_backlog_item": null, "open_backlog_items": 0, "priority_backlog_groups": {"P0": {"completed": 4, "next_item": null, "open": 0}, "P1": {"completed": 268, "next_item": null, "open": 0}, "P2": {"completed": 297, "next_item": null, "open": 0}}, "project_name": "R"}
```

The `--fail-on-blockers` flag still emits the requested report, then exits with status `2` when `status/stuck.md` contains active blockers. This lets cron jobs and CI gates fail fast while preserving machine-readable diagnostics on stdout.

Checked `--markdown` snapshot for the same revision (suitable for PR comments or status pages):

```markdown
# R Readiness Report

| Metric | Value |
| --- | ---: |
| Completed backlog items | 569 |
| Open backlog items | 0 |
| Active blockers | 0 |

## Backlog by priority

| Priority | Completed | Open | Next item |
| --- | ---: | ---: | --- |
| P0 | 4 | 0 | None |
| P1 | 268 | 0 | None |
| P2 | 297 | 0 | None |

## Next backlog item

None

## Active blockers

None
```

## Memory overlap demo JSON Schemas

Dashboard consumers that validate memory-overlap demo JSON can inspect the
schema surface without reading source by running:

```bash
r-project --memory-overlap-demo-schema
```

The schema payload uses JSON Schema draft 2020-12 and contains two definitions:
`"memoryOverlapTotalsDemo"` for `r-project --memory-overlap-totals-demo --json`
and `"memoryThresholdDemo"` for `r-project --memory-threshold-demo --json`.
The compact required-field contracts are:

```json
{"$schema": "https://json-schema.org/draft/2020-12/schema", "$defs": {"memoryOverlapTotalsDemo": {"required": ["by", "totals"], "totals_item": {"required": ["group", "overlap_count", "total_overlap_size"]}}, "memoryThresholdDemo": {"required": ["by", "max_overlap_count", "max_total_overlap_size", "violations"], "violations_item": {"required": ["group", "overlap_count", "total_overlap_size", "max_overlap_count", "max_total_overlap_size", "exceeded"]}}}}
```

## Release and versioning

The Python support package is currently `0.1.0` (see [`pyproject.toml`](pyproject.toml)). It follows semantic versioning for its published CLI/report/helper APIs; this does not imply a stable or complete Rust-language implementation. Before a release, update [`CHANGELOG.md`](CHANGELOG.md), run host and Docker verification, and check release metadata with `PYTHONPATH=src python3 -m r_project --root . --check-release-tag v0.1.0 --docker-verified` (or `PYTHONPATH=src python3 -m r_project --root . --json --check-release-tag v0.1.0 --docker-verified` for JSON). The [release checklist](docs/release-checklist.md) describes the full process.

## License

AGPL-3.0-or-later; see [`LICENSE`](LICENSE).

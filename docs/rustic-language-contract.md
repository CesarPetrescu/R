# Rustic language and C-host contract

Rustic is a bounded Rust-*like* expression interpreter, not `rustc`. The public entry point is `runtime/include/rustic.h`; `runtime/rustic.c` owns parsing and evaluation. The strict-C99 [host driver](../tests/fixtures/rustic_expression_driver.c), [direct C API fixture](../tests/fixtures/rustic_api_contract_driver.c), [literal contract fixture](../tests/fixtures/rustic_integer_literal_contract.txt) and [checked arithmetic fixture](../tests/fixtures/rustic_checked_arithmetic_contract.txt) are executable reference cases. Python is test/report tooling, not the interpreter.

## Accepted forms

- Decimal nonnegative integer literals up to the host C `LONG_MAX`; unary `-` and `!`; `+`, `-`, `*`, `/`, `%`, parentheses, comparisons, and short-circuit `&&`/`||` (boolean integers `0`/`1`). Arithmetic precedence follows the parser's expression grammar; unary operators bind before multiplication.
- `let name = expr;`, assignment to an existing binding, semicolon-separated statements, scoped `{ ... }` blocks, `if condition { ... } else { ... }`, `while condition { ... }` with `break;`/`continue;`, and integer-pattern `match expr { 0 => expr, _ => expr }`. Match patterns are nonnegative decimal literals or `_`; arms use commas. Skipped expression operands (including unselected match arms) consume expression grammar without evaluating values, but **skipped blocks** (including unselected `if`/`else` and `while` bodies) are scanned for balanced braces, not checked for valid statements: `if 0 { 1 + * } else { 7 }` returns `7`. Selected blocks do parse their statements. Match *patterns* are parsed and range-checked even after an earlier arm matches.
- Named `fn` declarations, recursive calls and function values; arrays of integer elements (`[1, 2]`) with checked `xs[index]`, plus selected bounded built-ins such as `len`, `push`, `map` and `fold`. Arrays and functions are runtime values but the public entry point returns only `long`—end a program with an integer expression. See interpreter tests for callback and temporary lifetime behavior.

## Embedding and failures

```c
#include "rustic.h"
long result = 0;
RusticStatus status = rustic_eval_expression("let x = 2 + 3; x * 4", &result);
/* status == RUSTIC_OK, result == 20 */
/* on failure, use rustic_status_message(status); do not use result */
```

Pass a NUL-terminated source and a non-NULL output pointer. Every call starts with fresh interpreter state. On success, `RUSTIC_OK` writes the final integer to `*out_value`. On failure, the output is **not updated** and the status describes the failure; `NULL` arguments return `RUSTIC_ERR_EXPECTED_INTEGER`. The host fixture prints `source => result` on success and `message: source` to stderr with exit code `2` on failure. The enum names and messages are in the [C header](../runtime/include/rustic.h) and implementation; do not infer a source position from a status code.

Decimal digits beyond `LONG_MAX` (including inside bindings and match-arm patterns) return `RUSTIC_ERR_INTEGER_OVERFLOW` / `integer overflow` rather than silently clamping. The `-` prefix is a separate unary operator, so `-(LONG_MAX+1)` as a decimal token also fails literal conversion; negating a *computed* `LONG_MIN` has the same status. Evaluated `+`, binary `-` and `*` also reject a result outside the host C `long` range. `/` and `%` reject `LONG_MIN` with divisor `-1` with the same overflow status; a zero divisor still returns `RUSTIC_ERR_DIVISION_BY_ZERO`. In-range division truncates toward zero and the remainder follows the C99 signed-integer rule. `sum(array)` checks every intermediate addition in input order; even a later negative element cannot rescue an overflowing prefix. Its empty-array result is `0`. Other array/statistics built-in intermediate arithmetic is not yet checked. An error leaves the C API output untouched. Skipped expression operands such as `0 && (LONG_MAX + 1)` are consumed without performing arithmetic; `0 && (1 + *)` still rejects malformed expression syntax, while skipped `{ ... }` blocks are only scanned for balanced braces and can contain malformed statements. See the [sum contract fixture](../tests/fixtures/rustic_sum_overflow_contract.txt) for host-portable boundaries, composition, invalid arguments and lazy branches.

## Runnable host examples

From the repository root (choose any writable output path):

```sh
cc -std=c99 -Wall -Wextra -Werror -Iruntime/include runtime/rustic.c tests/fixtures/rustic_expression_driver.c -o /tmp/rustic-demo
/tmp/rustic-demo 'let x = 2 + 3; x * 4'  # => 20
/tmp/rustic-demo '0 && 999999999999999999999999999999999999'  # => 0 (not evaluated)
/tmp/rustic-demo '999999999999999999999999999999999999'  # exit 2: integer overflow
/tmp/rustic-demo '9223372036854775807 + 1'  # exit 2: integer overflow on 64-bit long hosts
/tmp/rustic-demo 'match 0 { 999999999999999999999999999999 => 1, _ => 2 }'  # exit 2: integer overflow
/tmp/rustic-demo 'let xs = [1, 2]; xs[2]'  # exit 2: array index out of bounds
```

The first oversized digits exceed `LONG_MAX` on normal 32/64-bit hosts; the checked arithmetic example uses a 64-bit boundary. The pytest fixtures construct exact boundaries from `sizeof(long)` for portability. A Docker-backed host run is in the [README](../README.md#run-with-docker).

## Resource boundaries and exclusions

The implementation caps identifiers at 63 characters, arrays at 16 elements and 64 live slots, named functions at 8, bindings at 1024, and evaluation at 512 steps. Overflowing a bound or running out of steps returns a status rather than broadening the sandbox guarantee. No Rust type checker, ownership/borrowing, strings, crates, I/O or general Rust compatibility is offered. Invalid input can be reported by the host without killing the host process; the fixed budget is not a security isolation boundary.

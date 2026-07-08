# R

Project **R** is an automation showcase for an automated worker building interpreted Rust inside C.

The core artifact is `runtime/rustic.c`: a C-hosted Rust-like interpreter. The Hermes worker is part of the showcase: it repeatedly chooses real interpreter work, writes tests, verifies in Docker, opens reviewed PRs, and grows the runtime safely.

Automation-facing material is collected under [`automations/`](automations/) as the proper home for worker workflow docs and verification surfaces. Older checked docs under `docs/` remain as executable verification inputs until their commands are migrated behind the automation folder.

## What this repo is

R has two connected parts:

1. **The product:** a small Rust-like interpreter implemented in C under `runtime/`.
2. **The showcase:** an automated Hermes worker keeps improving that interpreter through tested pull requests.

The point is not to sell generic repository-readiness tooling. The point is to show an autonomous worker repeatedly choosing real interpreter work, writing tests, verifying locally and in Docker, opening PRs, getting review, and safely growing interpreted Rust inside C.

## Why Python is here

Python is support tooling only. It exists because it is convenient for the worker and tests:

- `tests/` uses pytest to compile and exercise the C interpreter.
- `src/r_project/` contains small reporting/checking helpers for the autonomous workflow.
- docs/status guard commands help the worker avoid stale examples and unsafe releases.

The core runtime remains C. New product work should focus on `runtime/rustic.c`, its C API, language features, diagnostics, and interpreter tests.

## License

R is licensed under the GNU Affero General Public License v3.0 or later (`AGPL-3.0-or-later`). See `LICENSE` for the full text.

## Interpreter runtime

The first Rust-in-C runtime slice lives under `runtime/`. It exposes a tiny C API,
`rustic_eval_expression(...)`, that parses and evaluates Rust-like integer
programs such as `1 + 2 * 3`, `(1 + 2) * 3`, `10 - 3 + 2 * 4`,
`let x = 2 + 3; x * 4`,
`1 + 2; 3 * 4; 5 + 6`, `let x = 1; x = x + 2; x`,
`!0`, `!(2 < 1)`,
`let x = 3; x == 3`, `let x = 3; x != 4`, `1 + 2 < 2 * 2`,
`{ let x = 2; x + 1 }`,
`if 1 < 2 { let x = 3; x + 4 } else { missing }`,
`let i = 0; let total = 0; while i < 4 { total = total + i; i = i + 1; }; total`,
`fn add(a, b) { a + b }; add(2, 3)`,
`fn add(a, b) { a + b }; let op = add; op(2, 3)`,
`fn inc(x) { x + 1 }; fn choose() { inc }; let f = choose(); f(6)`,
`fn add(a, b) { a + b }; fn twice(x) { add(x, x) }; twice(add(2, 3))`,
`let n = 0; let total = 0; while n < 10 { n = n + 1; if n == 4 { break; } else { total = total + n; } }; total`,
`let n = 0; let total = 0; while n < 5 { n = n + 1; if n == 3 { continue; } else { total = total + n; } }; total`,
`let n = 2; match n { 1 => 10, 2 => 20, _ => 99 }`,
`[1, 2 + 3, 9][1]`, `let xs = [3, 5, 8]; xs[0] + xs[2]`,
`len([1, 2, 3])`, `let xs = [3, 5, 8]; len(xs) + xs[len(xs) - 1]`,
`let xs = [0, 0, 0]; let i = 0; while i < len(xs) { xs = set(xs, i, i + 1); i = i + 1; }; xs[0] + xs[1] + xs[2]`,
`let xs = []; let i = 0; while i < 4 { xs = push(xs, i + 1); i = i + 1; }; sum(xs)`,
`count([1, 2, 1, 3], 1)`, `find([4, 5, 4], 5)`, `contains_any([1, 2, 3], [9, 2])`, `intersection_count([1, 2, 3], [2, 3])`, `sum(difference([1, 2, 3], [2]))`, `sum(drop(range(6), 3))`, `sum(window_sum(range(6), 3))`, `chunk_count(range(8), 3)`, `sum(chunk_sum(range(8), 3))`, `rotate(range(4), 1)[0]`, `rotate_right(range(4), 1)[0]`, `prefix_sum([2, 3, 5])[2]`, `sum(adjacent_diff(prefix_sum([2, 3, 5])))`, `sum(moving_average_sum(prefix_sum([2, 3, 5]), 2))`, `median([9, 1, 5, 3])`, `variance_sum([1, 2, 3])`, `mode([2, 1, 2, 1])`, `unique_count([3, 1, 3, 2])`, `sum(histogram_count([2, 2, 1, 3, 3, 3]))`, `sum(histogram_values([3, 1, 3, 2]))`, `frequency_score([3, 1, 3], 3)`, `histogram_pairs_score(histogram_values([3, 1, 3]), histogram_count([3, 1, 3]))`, `histogram_distance_score(histogram_values([3, 1, 3]), histogram_count([3, 1, 3]), [3, 1])`, `histogram_within_distance(histogram_values([3, 1, 3]), histogram_count([3, 1, 3]), [3, 1], 1)`, `threshold_count([1, 3, 5, 7], 3, 6)`, `threshold_all([3, 5, 6], 3, 6)`, `outlier_count([1, 3, 5, 7], 3, 6)`, `threshold_window_count([3, 4, 5, 7, 3], 3, 6, 3)`, `outlier_score([1, 3, 8, 5], 3, 6)`, `threshold_run_count([3, 4, 7, 3, 5, 9, 4], 3, 6)`, `outlier_streak([1, 3, 8, 9, 5, 10], 3, 6)`, `threshold_run_score([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)`, `outlier_run_count([1, 3, 8, 9, 5, 10], 3, 6)`, `sum(threshold_run_lengths([3, 4, 7, 3, 5, 6, 9, 4], 3, 6))`, `sum(outlier_run_lengths([1, 3, 8, 9, 5, 10], 3, 6))`, `threshold_run_length_score([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)`, `outlier_run_length_score([1, 3, 8, 9, 5, 10], 3, 6)`, `threshold_longest_run([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)`, `threshold_shortest_run([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)`, `outlier_shortest_run([1, 3, 8, 9, 5, 10], 3, 6)`, `outlier_longest_run([1, 3, 8, 9, 5, 10], 3, 6)`, `threshold_run_delta([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)`, `outlier_run_delta([1, 3, 8, 9, 10, 5, 0], 3, 6)`, `threshold_run_ratio_score([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)`, `outlier_run_ratio_score([1, 3, 8, 9, 10, 5, 0], 3, 6)`, `threshold_run_contrast([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)`, `outlier_run_contrast([1, 3, 8, 9, 10, 5, 0], 3, 6)`, `threshold_run_contrast_delta([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)`, `outlier_run_contrast_delta([1, 3, 8, 9, 10, 5, 0], 3, 6)`, `threshold_run_signal_score([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)`, `outlier_run_signal_score([1, 3, 8, 9, 10, 5, 0], 3, 6)`, `threshold_run_signal_density([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)`, `outlier_run_signal_density([1, 8, 9, 3, 0, 1], 3, 6)`, `threshold_run_signal_density_delta([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)`, `outlier_run_signal_density_delta([1, 8, 9, 3, 0, 1], 3, 6)`, `threshold_run_signal_density_ratio([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)`, `outlier_run_signal_density_ratio([1, 8, 9, 3, 0, 1], 3, 6)`, `threshold_run_signal_density_gap([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)`, `outlier_run_signal_density_gap([1, 8, 9, 3, 0, 1], 3, 6)`, `threshold_run_signal_density_band([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)`, `outlier_run_signal_density_band([1, 8, 9, 3, 0, 1], 3, 6)`, `threshold_run_signal_density_band_ratio([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)`, `outlier_run_signal_density_band_ratio([1, 8, 9, 3, 0, 1], 3, 6)`, `threshold_run_signal_density_band_gap([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)`, `threshold_run_signal_density_band_gap_ratio([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)`, `threshold_run_signal_density_band_span([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)`, `threshold_run_signal_density_band_span_ratio([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)`, `threshold_run_signal_density_band_span_gap([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)`, `threshold_run_signal_density_band_span_gap_ratio([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)`, `threshold_run_signal_density_band_span_gap_delta([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)`, `threshold_run_signal_density_band_span_gap_delta_ratio([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)`, `threshold_run_signal_density_band_span_gap_delta_balance([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)`, `threshold_run_signal_density_band_span_gap_delta_balance_ratio([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)`, `threshold_run_signal_density_band_span_gap_delta_balance_delta([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)`, `threshold_run_signal_density_band_span_gap_delta_balance_count([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)`, `threshold_run_signal_density_band_span_gap_delta_balance_drift([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)`, `threshold_run_signal_density_band_span_gap_delta_balance_spread([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)`, `outlier_run_signal_density_band_span_gap_delta_balance_delta([1, 8, 9, 3, 0, 1], 3, 6)`, `outlier_run_signal_density_band_span_gap_delta_balance_count([1, 8, 9, 3, 0, 1], 3, 6)`, `outlier_run_signal_density_band_span_gap_delta_balance_drift([1, 8, 9, 3, 0, 1], 3, 6)`, `outlier_run_signal_density_band_span_gap_delta_balance_spread([1, 8, 9, 3, 0, 1], 3, 6)`, `threshold_run_signal_density_band_span_gap_delta_balance_mass([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)`, `threshold_run_signal_density_band_span_gap_delta_balance_load([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)`, `threshold_run_signal_density_band_span_gap_delta_balance_flux([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)`, `threshold_run_signal_density_band_span_gap_delta_balance_wave([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)`, `threshold_run_signal_density_band_span_gap_delta_balance_peak([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)`, `outlier_run_signal_density_band_span_gap_delta_balance_mass([1, 8, 9, 3, 0, 1], 3, 6)`, `outlier_run_signal_density_band_span_gap_delta_balance_load([1, 8, 9, 3, 0, 1], 3, 6)`, `outlier_run_signal_density_band_span_gap_delta_balance_flux([1, 8, 9, 3, 0, 1], 3, 6)`, `outlier_run_signal_density_band_span_gap_delta_balance_wave([1, 8, 9, 3, 0, 1], 3, 6)`, `outlier_run_signal_density_band_span_gap_delta_balance_peak([1, 8, 9, 3, 0, 1], 3, 6)`, `outlier_run_signal_density_band_gap([1, 8, 9, 3, 0, 1], 3, 6)`, `outlier_run_signal_density_band_gap_ratio([1, 8, 9, 3, 0, 1], 3, 6)`, `outlier_run_signal_density_band_span([1, 8, 9, 3, 0, 1], 3, 6)`, `outlier_run_signal_density_band_span_ratio([1, 8, 9, 3, 0, 1], 3, 6)`, `outlier_run_signal_density_band_span_gap([1, 8, 9, 3, 0, 1], 3, 6)`, `outlier_run_signal_density_band_span_gap_ratio([1, 8, 9, 3, 0, 1], 3, 6)`, `outlier_run_signal_density_band_span_gap_delta([1, 8, 9, 3, 0, 1], 3, 6)`, `outlier_run_signal_density_band_span_gap_delta_ratio([1, 8, 9, 3, 0, 1], 3, 6)`, `outlier_run_signal_density_band_span_gap_delta_balance([1, 8, 9, 3, 0, 1], 3, 6)`, `fn square(x) { x * x }; weighted_score([1, 2, 3], square)`,  `nth_sorted([9, 1, 5, 3], 2)`, `sum(top_count([5, 1, 9, 3], 3))`, `rank_of([9, 1, 5, 3], 5)`, `top_sum([5, 1, 9, 3], 2)`, `sum(clamp([9, 1, 5, 3], 2, 6))`, `fn even(x) { x % 2 == 0 }; partition_count(range(7), even)`, `equals([1, 2], [1, 2])`, `starts_with([1, 2, 3], [1, 2])`, `any([1, 2, 3], 2)`, `all([4, 4, 4], 4)`, `min([3, 1, 4])`, `max([3, 1, 4])`, `range(4)[2]`, `sum(range(5))`, `sum(repeat(4, 3))`, `sum(concat([1, 2], [3, 4]))`, `reverse(range(4))[0]`, `sum(take(range(6), 3))`, `sort([3, 1, 2])[0]`, `sum(dedup([3, 1, 3, 2, 1]))`, `fn double(x) { x * 2 }; sum(map(range(6), double))`, `fn even(x) { x % 2 == 0 }; sum(filter(range(7), even))`, `fn weight(i, x) { (i + 1) * x }; sum(map_indexed([3, 4, 5], weight))`, `fn odd_index(i, x) { i % 2 == 1 }; sum(filter_indexed([10, 20, 30, 40], odd_index))`, `fn add(x, y) { x + y }; sum(zip_with([1, 2, 3], [10, 20, 30], add))`, `fn add(acc, x) { acc + x }; fold(range(6), 0, add)`,
`fn even(n) { if n == 0 { 1 } else { if n % 2 == 0 { even(n - 2) } else { 0 } } }; even(8)`,
`1 < 2 && 3 < 4`, `0 || 5 == 5`,
and `fn countdown(n) { if n == 0 { 7 } else { countdown(n - 1) } }; countdown(3)`,
`fn triangle(n) { if n == 0 { 0 } else { n + triangle(n - 1) } }; triangle(5)`,
`fn factorial(n) { if n == 0 { 1 } else { n * factorial(n - 1) } }; factorial(5)`,
`let n = 1; let total = 0; while n <= 10 { if n % 3 == 0 { total = total + n } else { 0 }; n = n + 1; }; total`,
`let n = 96; let steps = 0; while n > 1 { n = n / 2; steps = steps + 1; }; steps`,
and `20 / 5 + 3 * 2` from a C
host fixture. Recent signal-density band helpers also include `threshold_run_signal_density_band_span_gap_delta_balance_seed(array, min, max)` and `outlier_run_signal_density_band_span_gap_delta_balance_seed(array, min, max)` for matching-mass plus shortest-run seed pressure on top of the balance-petal score. The evaluator supports `+`, `-`, `*`, `/`, `%`, unary boolean negation `!`,
multiplicative precedence, parenthesized expressions, `let` bindings, identifier lookup,
semicolon-separated expression-statement sequencing that returns the final
expression value, assignment/mutation of existing bindings, equality and ordering comparisons
(`==`, `!=`, `<`, `<=`, `>`, `>=`) that return `1` for true and `0` for false,
short-circuiting boolean conjunction/disjunction (`&&`, `||`) for compound guards, block expressions with
nested lexical scopes, conditional `if`/`else` expressions that evaluate only the selected branch,
`while` loop statements that re-evaluate their condition while preserving outer mutations,
`break` statements for early loop exits and `continue` statements for skipping to the next iteration,
`match` expressions with integer arms and `_` defaults for multi-way expression dispatch,
array literals with integer elements, checked indexing, `len(...)` length inspection, `set(array, index, value)` bounded rebuilds, `push(array, value)` bounded append-style construction, `sum(array)` compact summaries, `count(array, value)` value-frequency counts, `find(array, value)` first-index lookup, `contains_any(left, right)` cross-array membership checks, `intersection_count(left, right)` distinct cross-array intersection counts, `difference(left, right)` bounded left-minus-right array construction, `drop(array, n)` bounded prefix removal, `window_sum(array, n)` bounded sliding-window sums, `chunk_count(array, n)` fixed-size group counts, `chunk_sum(array, n)` fixed-size group sums, `rotate(array, n)` bounded left rotations, `rotate_right(array, n)` bounded right rotations, `prefix_sum(array)` cumulative sums, `adjacent_diff(array)` adjacent integer deltas, `moving_average_sum(array, n)` integer sliding-window averages, `median(array)` sorted midpoint summaries, `variance_sum(array)` summed squared distance from the integer mean, `mode(array)` most-frequent value selection with smallest-value tie behavior, `unique_count(array)` distinct-value counts, `histogram_count(array)` sorted distinct-value frequency arrays, `histogram_values(array)` sorted distinct-value arrays, `frequency_score(array, value)` value-frequency scores, `histogram_pairs_score(values, counts)` weighted-frequency validation scores, `histogram_distance_score(values, counts, expected)` absolute frequency-distance scoring, `histogram_within_distance(values, counts, expected, limit)` thresholded frequency-distance validation, `threshold_count(array, min, max)` inclusive range counts, `threshold_all(array, min, max)` all-values threshold validation, `outlier_count(array, min, max)` out-of-range counts, `threshold_window_count(array, min, max, n)` fully in-range sliding-window counts, `outlier_score(array, min, max)` summed distance outside inclusive bounds, `threshold_run_count(array, min, max)` contiguous in-range run counts, `outlier_streak(array, min, max)` maximum consecutive out-of-range streak lengths, `threshold_run_score(array, min, max)` sum-of-squared in-range run length scoring, `outlier_run_count(array, min, max)` contiguous out-of-range run counts, `threshold_run_lengths(array, min, max)` in-range run-length arrays, `outlier_run_lengths(array, min, max)` out-of-range run-length arrays, `threshold_run_length_score(array, min, max)` sum-of-squared in-range run-length scoring, `outlier_run_length_score(array, min, max)` sum-of-squared out-of-range run-length scoring, `threshold_longest_run(array, min, max)` longest in-range run extrema, `threshold_shortest_run(array, min, max)` shortest in-range run extrema, `outlier_shortest_run(array, min, max)` shortest out-of-range run extrema, `outlier_longest_run(array, min, max)` longest out-of-range run extrema, `threshold_run_delta(array, min, max)` and `outlier_run_delta(array, min, max)` longest-minus-shortest run balance scores, `threshold_run_ratio_score(array, min, max)` and `outlier_run_ratio_score(array, min, max)` run-mass-minus-run-count continuity scores, `threshold_run_signal_score(array, min, max)` and `outlier_run_signal_score(array, min, max)` combined contrast-delta continuity scores, `threshold_run_signal_density(array, min, max)` and `outlier_run_signal_density(array, min, max)` signal-score densities normalized by matching run mass, `threshold_run_signal_density_delta(array, min, max)` and `outlier_run_signal_density_delta(array, min, max)` normalized signal-density minus run-balance scores, `threshold_run_signal_density_ratio(array, min, max)` and `outlier_run_signal_density_ratio(array, min, max)` signal-density delta minus matching-run-count contrast scores, `threshold_run_signal_density_gap(array, min, max)` and `outlier_run_signal_density_gap(array, min, max)` signal-density-ratio minus transition-balance gap scores, `threshold_transition_count(array, min, max)` and `outlier_transition_count(array, min, max)` adjacent range-state transition counts, `threshold_transition_score(array, min, max)` and `outlier_transition_score(array, min, max)` neighboring run-length-weighted transition scores, `threshold_transition_density(array, min, max)` and `outlier_transition_density(array, min, max)` matching-mass-normalized transition densities, `threshold_transition_balance(array, min, max)` and `outlier_transition_balance(array, min, max)` transition-density-vs-continuity balance scores, `threshold_run_contrast(array, min, max)` and `outlier_run_contrast(array, min, max)` continuity-vs-transition-balance contrast scores, `threshold_run_contrast_delta(array, min, max)` and `outlier_run_contrast_delta(array, min, max)` contrast-minus-run-delta scores, `weighted_score(array, fn)` callback-backed scalar scoring, `nth_sorted(array, n)` zero-based sorted order statistics, `top_count(array, n)` descending top-N arrays, `rank_of(array, value)` sorted-rank lookup, `top_sum(array, n)` descending top-N sums, `clamp(array, min, max)` bounded distribution shaping, `partition_count(array, fn)` callback-backed partition counts, `equals(left, right)` exact array comparisons, `starts_with(array, prefix)` prefix comparisons, `any(array, value)`/`all(array, value)` membership predicates, `min(array)`/`max(array)` bounds helpers, `range(n)` bounded `0..n-1` array construction, `repeat(value, n)` bounded repeated-value construction, `concat(array, array)` bounded array concatenation, `reverse(array)` ordering, `take(array, n)` bounded prefix slicing, `sort(array)` ascending ordering, `dedup(array)` first-occurrence duplicate removal, `map(array, fn)`/`filter(array, fn)` transformation helpers, `map_indexed(array, fn)`/`filter_indexed(array, fn)` `(index, value)` callback helpers, `zip_with(array, array, fn)` pairwise composition, and `fold(array, initial, fn)` reductions for small collection-style programs,
`fn`-like named function declarations/calls with call-local parameter bindings,
block-local function declarations that can use visible lexical bindings without leaking outside their block,
first-class function references that can be bound with `let`, returned from helpers, and called through local names,
function composition, recursive calls for countdown-style programs, remainder-based divisibility guards,
a fixed interpreter step budget that returns a stable `step limit exceeded`
diagnostic for runaway loops or recursion instead of hanging the C host, and stable undefined-identifier, loop-control-outside-loop, division-by-zero, malformed-comparison, wrong-argument-count,
unmatched-parenthesis, and unclosed-block diagnostics. The pytest suite
compiles that C runtime with `cc -std=c99 -Wall -Wextra -Werror` so the showcase
proves end-to-end interpreted expressions, grouping, bindings, sequencing, mutation,
subtraction, integer division, remainder arithmetic, boolean negation, boolean comparison results, scoped block evaluation, conditional branch selection,
array literals with integer elements, checked indexing, `len(...)` array length inspection, bounded `set(...)` array rebuilds with non-array/non-integer/out-of-bounds diagnostics, bounded `push(...)` array appends with non-array/non-integer/full-array diagnostics, `sum(...)` array summaries with non-array/wrong-argument diagnostics, `count(...)` value-frequency counts with non-array/non-integer/wrong-argument diagnostics, `find(...)` first-index lookup with not-found `-1`, empty-array behavior, and non-array/non-integer/wrong-argument diagnostics, `contains_any(...)` cross-array membership checks with empty-array behavior and non-array/wrong-argument diagnostics, `intersection_count(...)` distinct cross-array intersection counts with duplicate suppression, empty-array behavior, and non-array/wrong-argument diagnostics, `difference(...)` bounded left-minus-right arrays with empty-array behavior, composition support, non-array/wrong-argument diagnostics, `drop(...)` bounded prefix removal with empty-array behavior, `window_sum(...)` bounded sliding-window sums with empty-array/short-window behavior, invalid-size diagnostics, composition support, and array-slot cleanup regressions, `chunk_count(...)` fixed-size group counts, `chunk_sum(...)` fixed-size group sums, `rotate(...)` bounded left rotations, `rotate_right(...)` bounded right rotations, `prefix_sum(...)` cumulative sums, and `adjacent_diff(...)` adjacent deltas with empty-array behavior, invalid argument diagnostics, composition support, and array-slot cleanup regressions, `partition_count(...)` callback-backed partition counts with empty-array behavior, composition support, invalid callback diagnostics, and array-slot cleanup regressions, `equals(...)` exact array comparisons and `starts_with(...)` prefix comparisons with empty-prefix behavior and non-array/wrong-argument diagnostics, `any(...)`/`all(...)` membership predicates with non-array/non-integer/wrong-argument diagnostics, `min(...)`/`max(...)` bounds helpers with non-array/empty-array/wrong-argument diagnostics, `range(...)` array construction with non-integer/wrong-argument/bounded-cap diagnostics, `repeat(...)` repeated-value array construction with non-integer/wrong-argument/bounded-cap diagnostics, `concat(...)` array concatenation with non-array/wrong-argument/bounded-cap diagnostics, `reverse(...)` array ordering, `take(...)` bounded prefix slicing, `sort(...)` ascending ordering, `dedup(...)` duplicate removal, with array-slot cleanup regressions, `map(...)` array transformations and `filter(...)` array selections with function-argument diagnostics and slot-cleanup regressions, `map_indexed(...)` and `filter_indexed(...)` indexed callback helpers with function-argument diagnostics and slot-cleanup regressions, `zip_with(...)` pairwise array composition with shortest-length behavior, function-argument diagnostics, nested-composition argument root preservation, and slot-cleanup regressions, `fold(...)` array reductions with callback arity diagnostics and slot-cleanup regressions, named function calls/argument binding, block-local helper functions with lexical binding visibility and non-leakage,
first-class function references bound with `let`, returned from helpers, and called through local names,
nested call composition,
recursive countdowns, recursive divisibility guards, recursive triangular-number and factorial showcase fixtures,
loop arithmetic showcase fixtures for `%` divisibility filtering and `/` quotient accumulation,
compound boolean guard showcase fixtures with short-circuited skipped operands,
comparison-heavy loop showcase fixtures combining nested blocks, block-local helpers, function-valued bindings, comparisons, and compound boolean guards,
array reshaping/statistics showcase fixtures combining `chunk_count(...)`, `chunk_sum(...)`, `rotate(...)`, `rotate_right(...)`, `drop(...)`, `take(...)`, `window_sum(...)`, `prefix_sum(...)`, `adjacent_diff(...)`, `median(...)`, `variance_sum(...)`, `mode(...)`, `unique_count(...)`, `histogram_count(...)`, `histogram_values(...)`, `frequency_score(...)`, `histogram_pairs_score(...)`, `histogram_distance_score(...)`, `histogram_within_distance(...)`, `threshold_count(...)`, `threshold_all(...)`, `outlier_count(...)`, `threshold_window_count(...)`, `outlier_score(...)`, `threshold_run_count(...)`, `outlier_streak(...)`, `threshold_run_score(...)`, `outlier_run_count(...)`, `threshold_run_lengths(...)`, `outlier_run_lengths(...)`, `threshold_run_length_score(...)`, `outlier_run_length_score(...)`, `threshold_longest_run(...)`, `threshold_shortest_run(...)`, `outlier_shortest_run(...)`, `outlier_longest_run(...)`, `threshold_run_delta(...)`, `outlier_run_delta(...)`, `threshold_run_ratio_score(...)`, `outlier_run_ratio_score(...)`, `threshold_transition_count(...)`, `outlier_transition_count(...)`, `threshold_transition_score(...)`, `outlier_transition_score(...)`, `threshold_transition_density(...)`, `outlier_transition_density(...)`, `threshold_transition_balance(...)`, `outlier_transition_balance(...)`, `threshold_run_contrast(...)`, `outlier_run_contrast(...)`, `threshold_run_contrast_delta(...)`, `outlier_run_contrast_delta(...)`, `threshold_run_signal_score(...)`, `outlier_run_signal_score(...)`, `threshold_run_signal_density(...)`, `outlier_run_signal_density(...)`, `threshold_run_signal_density_delta(...)`, `outlier_run_signal_density_delta(...)`, `threshold_run_signal_density_ratio(...)`, `outlier_run_signal_density_ratio(...)`, `threshold_run_signal_density_gap(...)`, `outlier_run_signal_density_gap(...)`, `threshold_run_signal_density_band(...)`, `outlier_run_signal_density_band(...)`, `threshold_run_signal_density_band_ratio(...)`, `outlier_run_signal_density_band_ratio(...)`, `threshold_run_signal_density_band_gap(...)`, `outlier_run_signal_density_band_gap(...)`, `threshold_run_signal_density_band_gap_ratio(...)`, `outlier_run_signal_density_band_gap_ratio(...)`, `threshold_run_signal_density_band_span(...)`, `outlier_run_signal_density_band_span(...)`, `threshold_run_signal_density_band_span_ratio(...)`, `outlier_run_signal_density_band_span_ratio(...)`, `threshold_run_signal_density_band_span_gap(...)`, `outlier_run_signal_density_band_span_gap(...)`, `threshold_run_signal_density_band_span_gap_ratio(...)`, `outlier_run_signal_density_band_span_gap_ratio(...)`, `threshold_run_signal_density_band_span_gap_delta(...)`, `threshold_run_signal_density_band_span_gap_delta_ratio(...)`, `outlier_run_signal_density_band_span_gap_delta(...)`, `outlier_run_signal_density_band_span_gap_delta_ratio(...)`, `weighted_score(...)`, `nth_sorted(...)`, `top_count(...)`, `rank_of(...)`, `top_sum(...)`, and `clamp(...)`,
array ordering/comparison showcase fixtures for exact equality and prefix comparisons over sorted/deduped compositions,
and runaway loop/recursion
safety before larger statement forms or runtime objects are added. Recent signal-density band helpers also include `threshold_run_signal_density_band_span_gap_delta_balance_seed(array, min, max)` and `outlier_run_signal_density_band_span_gap_delta_balance_seed(array, min, max)` for matching-mass plus shortest-run seed pressure on top of the balance-petal score.

The package also includes `r_project.memory.struct_layout(...)`, a tested
helper for C-like structure layouts that aligns each field offset and rounds
the total structure size up for safe array element placement. Memory layout
helpers reject negative sizes/counts, zero-sized payload fields, non-power-
of-two alignments, and explicit `max_total_size` overflows with `ValueError`
so invalid runtime layouts fail explicitly. Use
`r_project.memory.layout_field(name, layout, tags=(...))` to embed computed
struct or vector layouts into larger composite structures while preserving
nested total size and alignment and carrying symbolic provenance tags into
rendered memory maps. Use `r_project.memory.render_layout(name, layout)` to
print stable, line-oriented debug maps for named struct and vector layouts.
Pass `include_nested=True` to recursively expand fields created by
`layout_field(...)` into indented child memory maps when source-level tracing
needs the full nested object shape. Pass `include_spans=True` to append
half-open `span=start..end` ranges, call `layout.byte_spans()` to get
structured `ByteSpan` records, use `flatten_byte_spans(name, layout)` to
produce fully qualified parent/child spans with absolute offsets for nested
diagnostics, call `leaf_byte_spans(...)` to suppress parent container spans
when callers need leaf-only diagnostics, call `filter_byte_spans(...)` to
narrow flattened spans by qualified names and provenance tags before overlap
checks, pass spans to
`find_overlapping_byte_spans(...)` to identify runtime range intersections
while excluding endpoint-only touching ranges, call
`render_byte_span_overlaps(...)` to format those intersections as stable
Markdown for PR comments and trace reports, or use
`group_byte_span_overlaps(...)`/`render_grouped_byte_span_overlaps(...)` to
summarize larger diagnostics by shared provenance tag or qualified-name prefix.
Use `group_byte_span_overlap_totals(...)` when dashboards need compact overlap
counts and total intersecting bytes per group instead of full pair rows, call
`find_grouped_byte_span_overlap_total_violations(...)` to flag groups whose
compact totals exceed overlap-count or intersecting-byte budgets, call
`render_grouped_byte_span_overlap_threshold_violations(...)` to format those
budget failures as stable Markdown for PR comments or dashboard gates, and
`render_grouped_byte_span_overlap_totals(...)` when compact totals should be
formatted as stable Markdown tables for PR comments or dashboards.

Run from a checkout:

```bash
PYTHONPATH=src python3 -m r_project --root . --json
PYTHONPATH=src python3 -m r_project --root . --markdown
PYTHONPATH=src python3 -m r_project --root . --json --fail-on-blockers
PYTHONPATH=src python3 -m r_project --root . --check-readme-examples
PYTHONPATH=src python3 -m r_project --root . --generate-readme-examples
PYTHONPATH=src python3 -m r_project --root . --write-readme-examples --dry-run-readme-examples
PYTHONPATH=src python3 -m r_project --root . --check-readme-examples --readme-examples-path README.md
PYTHONPATH=src python3 -m r_project --root . --write-readme-examples --dry-run-readme-examples --readme-examples-path README.md
PYTHONPATH=src python3 -m r_project --root . --check-readme-examples --readme-examples-path docs/usage-examples.md
PYTHONPATH=src python3 -m r_project --root . --write-readme-examples --dry-run-readme-examples --readme-examples-path docs/usage-examples.md
PYTHONPATH=src python3 -m r_project --root . --check-readme-examples --readme-examples-path docs/dashboard-index.md
PYTHONPATH=src python3 -m r_project --root . --write-readme-examples --dry-run-readme-examples --readme-examples-path docs/automation-index.md --readme-examples-section 'Embedded readiness report example'
PYTHONPATH=src python3 -m r_project --root . --check-readme-schema-examples --readme-schema-path docs/dashboard-index.md
PYTHONPATH=src python3 -m r_project --root . --write-readme-schema-examples --dry-run-readme-schema-examples --readme-schema-path docs/automation-index.md --readme-schema-section 'Embedded memory-overlap schema example'
PYTHONPATH=src python3 -m r_project --root . --check-readme-examples --readme-examples-path docs/automation-index.md
PYTHONPATH=src python3 -m r_project --root . --check-readme-schema-examples --readme-schema-path docs/automation-index.md
PYTHONPATH=src python3 -m r_project --root . --write-readme-examples
PYTHONPATH=src python3 -m r_project --memory-threshold-demo
PYTHONPATH=src python3 -m r_project --memory-threshold-demo --json
PYTHONPATH=src python3 -m r_project --memory-threshold-demo --memory-overlap-max-count 2 --memory-overlap-max-bytes 6
PYTHONPATH=src python3 -m r_project --memory-threshold-demo --json --memory-overlap-max-count 2 --memory-overlap-max-bytes 6
PYTHONPATH=src python3 -m r_project --memory-threshold-demo --memory-overlap-group-by name_prefix --memory-overlap-prefix-depth 2
PYTHONPATH=src python3 -m r_project --memory-threshold-demo --json --memory-overlap-group-by name_prefix --memory-overlap-prefix-depth 2
PYTHONPATH=src python3 -m r_project --memory-overlap-totals-demo
PYTHONPATH=src python3 -m r_project --memory-overlap-totals-demo --json
PYTHONPATH=src python3 -m r_project --memory-overlap-totals-demo --memory-overlap-group-by name_prefix --memory-overlap-prefix-depth 2
PYTHONPATH=src python3 -m r_project --memory-overlap-totals-demo --json --memory-overlap-group-by name_prefix --memory-overlap-prefix-depth 2
PYTHONPATH=src python3 -m r_project --memory-overlap-totals-demo --memory-overlap-name-prefix left.
PYTHONPATH=src python3 -m r_project --memory-threshold-demo --json --memory-overlap-tag source:literal --memory-overlap-max-count 0
PYTHONPATH=src python3 -m r_project --memory-overlap-demo-schema
PYTHONPATH=src python3 -m r_project --root . --check-memory-overlap-demo-schema
PYTHONPATH=src python3 -m r_project --root . --check-readme-schema-examples
PYTHONPATH=src python3 -m r_project --root . --write-readme-schema-examples --dry-run-readme-schema-examples
PYTHONPATH=src python3 -m r_project --root . --write-readme-schema-examples
PYTHONPATH=src python3 -m r_project --root . --check-readme-schema-examples --readme-schema-path README.md
PYTHONPATH=src python3 -m r_project --root . --check-readme-schema-examples --readme-schema-path docs/dashboard-schema.md
PYTHONPATH=src python3 -m r_project --root . --check-changelog-version
PYTHONPATH=src python3 -m r_project --root . --check-release-tag v0.1.0 --docker-verified
PYTHONPATH=src python3 -m r_project --root . --json --check-release-tag v0.1.0 --docker-verified
PYTHONPATH=src python3 -m r_project --root . --check-release-tag-fixture
PYTHONPATH=src python3 -m r_project --root . --write-release-tag-fixture --dry-run-release-tag-fixture
PYTHONPATH=src python3 -m r_project --root . --write-release-tag-fixture
PYTHONPATH=src python3 -m r_project --root . --write-release-tag-fixture --dry-run-release-tag-fixture --release-tag-fixture-version 0.2.0
PYTHONPATH=src python3 -m r_project --root . --write-release-tag-fixture --dry-run-release-tag-fixture --release-tag-fixture-path tests/fixtures/release-tag-checklist.json
PYTHONPATH=src python3 -m r_project --root . --check-release-tag-fixture --release-tag-fixture-path docs/release/checklist.json
PYTHONPATH=src python3 -m r_project --root . --check-release-examples --release-examples-path docs/release-examples.md
PYTHONPATH=src python3 -m r_project --root . --check-release-examples --release-examples-path docs/automation-index.md --release-examples-section 'Embedded release checklist example'
PYTHONPATH=src python3 -m r_project --root . --write-release-examples --dry-run-release-examples --release-examples-path docs/automation-index.md --release-examples-section 'Embedded release checklist example'
PYTHONPATH=src python3 -m r_project --root . --write-release-examples --dry-run-release-examples --release-examples-path tests/fixtures/automation-index-release-smoke.md --release-examples-section 'Embedded release checklist example'
PYTHONPATH=src python3 -m r_project --root . --write-release-examples --dry-run-release-examples --release-examples-path docs/release-examples.md
PYTHONPATH=src python3 -m r_project --root . --write-release-examples --dry-run-release-examples --release-examples-version 0.2.0 --release-examples-path docs/release-examples.md
PYTHONPATH=src python3 -m r_project --root . --write-release-examples --dry-run-release-examples --release-examples-version 0.2.0 --release-examples-path tests/fixtures/release-examples-future-version-smoke.md
PYTHONPATH=src python3 -m r_project --root . --check-release-example-fixtures
PYTHONPATH=src python3 -m r_project --root . --check-release-example-sections
PYTHONPATH=src python3 -m r_project --root . --check-release-section-writer-matrix
PYTHONPATH=src python3 -m r_project --root . --check-release-section-writer-matrix --release-section-writer-matrix-version 0.2.0
PYTHONPATH=src python3 -m r_project --root . --generate-release-section-writer-matrix --release-section-writer-matrix-version 0.2.0
PYTHONPATH=src python3 -m r_project --root . --write-release-section-writer-matrix --dry-run-release-section-writer-matrix --release-section-writer-matrix-version 0.2.0
PYTHONPATH=src python3 -m r_project --root . --check-release-examples-path-safety
PYTHONPATH=src python3 -m r_project --root . --generate-release-automation-index
PYTHONPATH=src python3 -m r_project --root . --generate-release-automation-index --release-automation-index-version 0.3.0
PYTHONPATH=src python3 -m r_project --root . --generate-release-automation-index --release-automation-index-version 0.3.0 --release-automation-index-profile-section 'Release 0.3.0 preview profile'
PYTHONPATH=src python3 -m r_project --root . --write-release-automation-index --dry-run-release-automation-index
PYTHONPATH=src python3 -m r_project --root . --write-release-automation-index --dry-run-release-automation-index --release-automation-index-version 0.3.0
PYTHONPATH=src python3 -m r_project --root . --write-release-automation-index --dry-run-release-automation-index --release-automation-index-version 0.3.0 --release-automation-index-profile-section 'Release 0.3.0 preview profile'
PYTHONPATH=src python3 -m r_project --root . --check-release-automation-index
PYTHONPATH=src python3 -m r_project --root . --check-release-automation-index --release-automation-index-version 0.3.0
PYTHONPATH=src python3 -m r_project --root . --check-release-automation-index --release-automation-index-version 0.3.0 --release-automation-index-profile-section 'Release 0.3.0 preview profile'
PYTHONPATH=src python3 -m r_project --root . --check-automation-index-links
PYTHONPATH=src python3 -m r_project --root . --check-automation-index-commands
PYTHONPATH=src python3 -m r_project --root . --check-automation-command-fixtures
PYTHONPATH=src python3 -m r_project --root . --generate-dashboard-automation-index
PYTHONPATH=src python3 -m r_project --root . --generate-dashboard-automation-index --dashboard-automation-index-variant expanded
PYTHONPATH=src python3 -m r_project --root . --write-dashboard-automation-index --dry-run-dashboard-automation-index
PYTHONPATH=src python3 -m r_project --root . --write-dashboard-automation-index --dry-run-dashboard-automation-index --dashboard-automation-index-variant expanded
PYTHONPATH=src python3 -m r_project --root . --check-dashboard-automation-index
PYTHONPATH=src python3 -m r_project --root . --check-dashboard-automation-index --dashboard-automation-index-variant expanded
PYTHONPATH=src python3 -m r_project --root . --generate-dashboard-example-fixtures
PYTHONPATH=src python3 -m r_project --root . --write-dashboard-example-fixtures --dry-run-dashboard-example-fixtures
PYTHONPATH=src python3 -m r_project --root . --check-dashboard-example-fixtures
PYTHONPATH=src python3 -m r_project --root . --check-dashboard-section-writer-matrix
PYTHONPATH=src python3 -m r_project --root . --check-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant compact
PYTHONPATH=src python3 -m r_project --root . --check-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant expanded
PYTHONPATH=src python3 -m r_project --root . --generate-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant compact
PYTHONPATH=src python3 -m r_project --root . --generate-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant expanded
PYTHONPATH=src python3 -m r_project --root . --write-dashboard-section-writer-matrix --dry-run-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant compact
PYTHONPATH=src python3 -m r_project --root . --write-dashboard-section-writer-matrix --dry-run-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant expanded
PYTHONPATH=src python3 -m r_project.lint --root .
```

Runtime layout helpers are also importable for tests or future low-level R
runtime work:

```python
from r_project import vector_layout
from r_project.memory import ByteSpan, MemoryField, filter_byte_spans, find_grouped_byte_span_overlap_total_violations, find_overlapping_byte_spans, flatten_byte_spans, group_byte_span_overlap_totals, group_byte_span_overlaps, layout_field, leaf_byte_spans, render_byte_span_overlaps, render_grouped_byte_span_overlap_threshold_violations, render_grouped_byte_span_overlap_totals, render_grouped_byte_span_overlaps, render_layout, struct_layout

payload = vector_layout(header_size=3, element_size=4, element_alignment=4, length=2)
record = struct_layout(
    [
        MemoryField(name="tag", size=1, alignment=1),
        layout_field("payload", payload, tags=("source:literal-bytes",)),
    ]
)
assert record.fields[1].offset == 4
assert record.total_size == 16

print(render_layout("record", record, include_spans=True))
# record: struct size=16 align=4 tail_padding=0
#   tag @ 0 size=1 align=1 leading_padding=0 span=0..1
#   payload @ 4 size=12 align=4 leading_padding=3 tags=source:literal-bytes span=4..16
assert [(span.name, span.start, span.end) for span in record.byte_spans()] == [
    ("tag", 0, 1),
    ("payload", 4, 16),
]
assert [(span.name, span.start, span.end) for span in flatten_byte_spans("record", record)] == [
    ("record.tag", 0, 1),
    ("record.payload", 4, 16),
    ("record.payload.header", 4, 7),
    ("record.payload.element[0]", 8, 12),
    ("record.payload.element[1]", 12, 16),
]

assert [(span.name, span.start, span.end) for span in filter_byte_spans(leaf_byte_spans(flatten_byte_spans("record", record)), name_prefix="record.payload.", tags_all=("source:literal-bytes",))] == [
    ("record.payload.header", 4, 7),
    ("record.payload.element[0]", 8, 12),
    ("record.payload.element[1]", 12, 16),
]

left = flatten_byte_spans("left", payload, base_offset=16)
right = flatten_byte_spans("right", vector_layout(header_size=0, element_size=4, element_alignment=4, length=1), base_offset=20)
assert [(overlap.left.name, overlap.right.name, overlap.start, overlap.end) for overlap in find_overlapping_byte_spans(left + right)] == [
    ("left.element[1]", "right.element[0]", 20, 24),
]
assert render_byte_span_overlaps(left + right) == "\n".join(
    [
        "# Byte Span Overlaps",
        "",
        "| Left span | Right span | Overlap | Size |",
        "| --- | --- | ---: | ---: |",
        "| left.element[1] (20..24) | right.element[0] (20..24) | 20..24 | 4 |",
    ]
)

tagged_spans = [
    ByteSpan("left.value", 0, 8, tags=("source:literal", "runtime:left")),
    ByteSpan("right.value", 4, 12, tags=("source:literal", "runtime:right")),
    ByteSpan("scratch", 6, 10),
]
assert list(group_byte_span_overlaps(tagged_spans, by="tag")) == ["source:literal", "untagged"]
assert find_grouped_byte_span_overlap_total_violations(
    tagged_spans,
    by="tag",
    max_overlap_count=1,
    max_total_overlap_size=4,
)["untagged"].total_overlap_size == 6
assert render_grouped_byte_span_overlap_totals(tagged_spans, by="tag") == "\n".join(
    [
        "# Byte Span Overlap Totals by Tag",
        "",
        "| Group | Overlaps | Total overlap bytes |",
        "| --- | ---: | ---: |",
        "| source:literal | 1 | 4 |",
        "| untagged | 2 | 6 |",
    ]
)
assert render_grouped_byte_span_overlap_threshold_violations(
    tagged_spans,
    by="tag",
    max_overlap_count=1,
    max_total_overlap_size=4,
) == "\n".join(
    [
        "# Byte Span Overlap Threshold Violations by Tag",
        "",
        "| Group | Overlaps | Max overlaps | Total overlap bytes | Max overlap bytes | Violations |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
        "| untagged | 2 | 1 | 6 | 4 | overlap count, total overlap bytes |",
    ]
)
assert render_grouped_byte_span_overlaps(tagged_spans, by="tag") == "\n".join(
    [
        "# Byte Span Overlaps by Tag",
        "",
        "## source:literal",
        "",
        "| Left span | Right span | Overlap | Size |",
        "| --- | --- | ---: | ---: |",
        "| left.value (0..8) | right.value (4..12) | 4..8 | 4 |",
        "",
        "## untagged",
        "",
        "| Left span | Right span | Overlap | Size |",
        "| --- | --- | ---: | ---: |",
        "| left.value (0..8) | scratch (6..10) | 6..8 | 2 |",
        "| right.value (4..12) | scratch (6..10) | 6..10 | 4 |",
    ]
)

layout = vector_layout(header_size=3, element_size=4, element_alignment=4, length=2)
assert layout.data_offset == 4
assert layout.element_offsets == [4, 8]
assert layout.total_size == 12

# Optional runtime bounds fail explicitly instead of silently exceeding a
# caller-provided byte-size limit.
vector_layout(header_size=8, element_size=4, element_alignment=4, length=2, max_total_size=16)
```

Or install the CLI in editable mode for local development:

```bash
python3 -m pip install -e .
r-project --root . --json
r-project --root . --markdown
r-project --root . --json --fail-on-blockers
r-project --root . --check-readme-examples
r-project --root . --generate-readme-examples
r-project --root . --write-readme-examples --dry-run-readme-examples
r-project --root . --check-readme-examples --readme-examples-path README.md
r-project --root . --write-readme-examples --dry-run-readme-examples --readme-examples-path README.md
r-project --root . --check-readme-examples --readme-examples-path docs/usage-examples.md
r-project --root . --write-readme-examples --dry-run-readme-examples --readme-examples-path docs/usage-examples.md
r-project --root . --check-readme-examples --readme-examples-path docs/dashboard-index.md
r-project --root . --write-readme-examples --dry-run-readme-examples --readme-examples-path docs/automation-index.md --readme-examples-section 'Embedded readiness report example'
r-project --root . --check-readme-schema-examples --readme-schema-path docs/dashboard-index.md
r-project --root . --write-readme-schema-examples --dry-run-readme-schema-examples --readme-schema-path docs/automation-index.md --readme-schema-section 'Embedded memory-overlap schema example'
r-project --root . --check-readme-examples --readme-examples-path docs/automation-index.md
r-project --root . --check-readme-schema-examples --readme-schema-path docs/automation-index.md
r-project --root . --write-readme-examples
r-project --memory-threshold-demo
r-project --memory-threshold-demo --json
r-project --memory-threshold-demo --memory-overlap-max-count 2 --memory-overlap-max-bytes 6
r-project --memory-threshold-demo --json --memory-overlap-max-count 2 --memory-overlap-max-bytes 6
r-project --memory-threshold-demo --memory-overlap-group-by name_prefix --memory-overlap-prefix-depth 2
r-project --memory-threshold-demo --json --memory-overlap-group-by name_prefix --memory-overlap-prefix-depth 2
r-project --memory-overlap-totals-demo
r-project --memory-overlap-totals-demo --json
r-project --memory-overlap-totals-demo --memory-overlap-group-by name_prefix --memory-overlap-prefix-depth 2
r-project --memory-overlap-totals-demo --json --memory-overlap-group-by name_prefix --memory-overlap-prefix-depth 2
r-project --memory-overlap-totals-demo --memory-overlap-name-prefix left.
r-project --memory-threshold-demo --json --memory-overlap-tag source:literal --memory-overlap-max-count 0
r-project --memory-overlap-demo-schema
r-project --root . --check-memory-overlap-demo-schema
r-project --root . --check-readme-schema-examples
r-project --root . --write-readme-schema-examples --dry-run-readme-schema-examples
r-project --root . --write-readme-schema-examples
r-project --root . --check-readme-schema-examples --readme-schema-path README.md
r-project --root . --check-readme-schema-examples --readme-schema-path docs/dashboard-schema.md
r-project --root . --check-changelog-version
r-project --root . --check-release-tag v0.1.0 --docker-verified
r-project --root . --json --check-release-tag v0.1.0 --docker-verified
r-project --root . --check-release-tag-fixture
r-project --root . --write-release-tag-fixture --dry-run-release-tag-fixture
r-project --root . --write-release-tag-fixture
r-project --root . --write-release-tag-fixture --dry-run-release-tag-fixture --release-tag-fixture-version 0.2.0
r-project --root . --write-release-tag-fixture --dry-run-release-tag-fixture --release-tag-fixture-path tests/fixtures/release-tag-checklist.json
r-project --root . --check-release-tag-fixture --release-tag-fixture-path docs/release/checklist.json
r-project --root . --check-release-examples --release-examples-path docs/release-examples.md
r-project --root . --check-release-examples --release-examples-path docs/automation-index.md --release-examples-section 'Embedded release checklist example'
r-project --root . --write-release-examples --dry-run-release-examples --release-examples-path docs/automation-index.md --release-examples-section 'Embedded release checklist example'
r-project --root . --write-release-examples --dry-run-release-examples --release-examples-path tests/fixtures/automation-index-release-smoke.md --release-examples-section 'Embedded release checklist example'
r-project --root . --write-release-examples --dry-run-release-examples --release-examples-path docs/release-examples.md
r-project --root . --write-release-examples --dry-run-release-examples --release-examples-version 0.2.0 --release-examples-path docs/release-examples.md
r-project --root . --write-release-examples --dry-run-release-examples --release-examples-version 0.2.0 --release-examples-path tests/fixtures/release-examples-future-version-smoke.md
r-project --root . --check-release-example-fixtures
r-project --root . --check-release-example-sections
r-project --root . --check-release-section-writer-matrix
r-project --root . --check-release-section-writer-matrix --release-section-writer-matrix-version 0.2.0
r-project --root . --generate-release-section-writer-matrix --release-section-writer-matrix-version 0.2.0
r-project --root . --write-release-section-writer-matrix --dry-run-release-section-writer-matrix --release-section-writer-matrix-version 0.2.0
r-project --root . --check-release-examples-path-safety
r-project --root . --generate-release-automation-index
r-project --root . --generate-release-automation-index --release-automation-index-version 0.3.0
r-project --root . --generate-release-automation-index --release-automation-index-version 0.3.0 --release-automation-index-profile-section 'Release 0.3.0 preview profile'
r-project --root . --write-release-automation-index --dry-run-release-automation-index
r-project --root . --write-release-automation-index --dry-run-release-automation-index --release-automation-index-version 0.3.0
r-project --root . --write-release-automation-index --dry-run-release-automation-index --release-automation-index-version 0.3.0 --release-automation-index-profile-section 'Release 0.3.0 preview profile'
r-project --root . --check-release-automation-index
r-project --root . --check-release-automation-index --release-automation-index-version 0.3.0
r-project --root . --check-release-automation-index --release-automation-index-version 0.3.0 --release-automation-index-profile-section 'Release 0.3.0 preview profile'
r-project --root . --check-automation-index-links
r-project --root . --check-automation-index-commands
r-project --root . --check-automation-command-fixtures
r-project --root . --generate-dashboard-automation-index
r-project --root . --generate-dashboard-automation-index --dashboard-automation-index-variant expanded
r-project --root . --write-dashboard-automation-index --dry-run-dashboard-automation-index
r-project --root . --write-dashboard-automation-index --dry-run-dashboard-automation-index --dashboard-automation-index-variant expanded
r-project --root . --check-dashboard-automation-index
r-project --root . --check-dashboard-automation-index --dashboard-automation-index-variant expanded
r-project --root . --generate-dashboard-example-fixtures
r-project --root . --write-dashboard-example-fixtures --dry-run-dashboard-example-fixtures
r-project --root . --check-dashboard-example-fixtures
r-project --root . --check-dashboard-section-writer-matrix
r-project --root . --check-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant compact
r-project --root . --check-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant expanded
r-project --root . --generate-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant compact
r-project --root . --generate-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant expanded
r-project --root . --write-dashboard-section-writer-matrix --dry-run-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant compact
r-project --root . --write-dashboard-section-writer-matrix --dry-run-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant expanded
r-project-lint --root .
```

Example output:

```json
{"active_blockers": [], "completed_backlog_items": 350, "has_active_blockers": false, "next_backlog_item": null, "open_backlog_items": 0, "priority_backlog_groups": {"P0": {"completed": 4, "next_item": null, "open": 0}, "P1": {"completed": 254, "next_item": null, "open": 0}, "P2": {"completed": 92, "next_item": null, "open": 0}}, "project_name": "R"}
```

The `--fail-on-blockers` flag still emits the requested report, then exits with status `2` when `status/stuck.md` contains active blockers. This lets cron jobs and CI gates fail fast while preserving machine-readable diagnostics on stdout.

Markdown output starts with a compact report suitable for PR comments, issue updates, or status pages:

```markdown
# R Readiness Report

| Metric | Value |
| --- | ---: |
| Completed backlog items | 350 |
| Open backlog items | 0 |
| Active blockers | 0 |

## Backlog by priority

| Priority | Completed | Open | Next item |
| --- | ---: | ---: | --- |
| P0 | 4 | 0 | None |
| P1 | 254 | 0 | None |
| P2 | 92 | 0 | None |

## Next backlog item

None

## Active blockers

None
```

A documented test fixture lives at `tests/fixtures/readiness-repo/` and is used by the CLI tests as an executable example of expected report behavior.

If report examples move into another README-style Markdown file, pass a
root-relative path to the same checker or writer, for example:

```bash
r-project --root . --check-readme-examples --readme-examples-path docs/usage-examples.md
r-project --root . --write-readme-examples --readme-examples-path docs/usage-examples.md
```

The repository also keeps those examples in
[`docs/usage-examples.md`](docs/usage-examples.md), which is checked in host
tests and the Docker verification harness so external dashboard docs can depend
on a stable standalone Markdown surface. When a Markdown dashboard page contains
multiple readiness snippets, add `--readme-examples-section 'Heading text'` to
check or refresh only the named section's JSON and Markdown fences. [`docs/dashboard-index.md`](docs/dashboard-index.md)
links those readiness examples with the checked schema examples and is also
verified by host tests and Docker as a dashboard landing page. [`docs/dashboard-example-fixtures.md`](docs/dashboard-example-fixtures.md)
indexes those dashboard example guard commands against Docker coverage so future
split dashboard docs stay auditable. [`docs/dashboard-section-writer-matrix.md`](docs/dashboard-section-writer-matrix.md)
proves each indexed dashboard readiness/schema surface has a Docker-covered writer dry-run and can preview or append variant-labeled writer rows from the fixture registry.
[`docs/dashboard-automation-index.md`](docs/dashboard-automation-index.md)
keeps dashboard-only automation links and commands auditable against Docker coverage and can be refreshed with generated link/command rows before publishing new dashboard surfaces.
[`docs/automation-index.md`](docs/automation-index.md)
embeds checked readiness and compact schema examples while linking the dashboard
and release automation surfaces from one combined index. [`docs/automation-command-fixtures.md`](docs/automation-command-fixtures.md)
indexes the combined automation commands and Docker harness coverage so future
split-doc command lists stay auditable.

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

Use the on-demand drift guard to ensure the stored fixture still matches current
CLI output before publishing dashboard integrations:

```bash
r-project --root . --check-memory-overlap-demo-schema
```

Run the README-specific guard when editing the compact schema example in this
section:

```bash
r-project --root . --check-readme-schema-examples
```

Preview or apply a refreshed compact schema example directly from current CLI
output with:

```bash
r-project --root . --write-readme-schema-examples --dry-run-readme-schema-examples
r-project --root . --write-readme-schema-examples
```

If dashboard-facing schema docs move into another README-style Markdown file,
pass a root-relative path to the same checker or writer, for example:

```bash
r-project --root . --check-readme-schema-examples --readme-schema-path docs/dashboard-schema.md
r-project --root . --write-readme-schema-examples --readme-schema-path docs/dashboard-schema.md
```

When one dashboard Markdown file contains multiple schema snippets, add
`--readme-schema-section 'Heading text'` so the checker or writer targets only
the first JSON fence under that named heading.

The repository also keeps those compact schema examples in
[`docs/dashboard-schema.md`](docs/dashboard-schema.md), which is checked in host
tests and the Docker verification harness so external dashboard docs can depend
on a stable standalone schema surface. [`docs/dashboard-index.md`](docs/dashboard-index.md)
combines the checked readiness report fences and compact schema fence in one
landing page for dashboard consumers.

## Development

Run the host checks directly when iterating:

```bash
git diff --check
python3 -m pytest -q
PYTHONPATH=src python3 -m r_project --root . --json
PYTHONPATH=src python3 -m r_project --root . --markdown
PYTHONPATH=src python3 -m r_project --root . --json --fail-on-blockers
PYTHONPATH=src python3 -m r_project --root . --check-readme-examples
PYTHONPATH=src python3 -m r_project --root . --generate-readme-examples
PYTHONPATH=src python3 -m r_project --root . --write-readme-examples --dry-run-readme-examples
PYTHONPATH=src python3 -m r_project --root . --check-readme-examples --readme-examples-path README.md
PYTHONPATH=src python3 -m r_project --root . --write-readme-examples --dry-run-readme-examples --readme-examples-path README.md
PYTHONPATH=src python3 -m r_project --root . --check-readme-examples --readme-examples-path docs/usage-examples.md
PYTHONPATH=src python3 -m r_project --root . --write-readme-examples --dry-run-readme-examples --readme-examples-path docs/usage-examples.md
PYTHONPATH=src python3 -m r_project --root . --check-readme-examples --readme-examples-path docs/dashboard-index.md
PYTHONPATH=src python3 -m r_project --root . --write-readme-examples --dry-run-readme-examples --readme-examples-path docs/automation-index.md --readme-examples-section 'Embedded readiness report example'
PYTHONPATH=src python3 -m r_project --root . --check-readme-schema-examples --readme-schema-path docs/dashboard-index.md
PYTHONPATH=src python3 -m r_project --root . --write-readme-schema-examples --dry-run-readme-schema-examples --readme-schema-path docs/automation-index.md --readme-schema-section 'Embedded memory-overlap schema example'
PYTHONPATH=src python3 -m r_project --root . --check-readme-examples --readme-examples-path docs/automation-index.md
PYTHONPATH=src python3 -m r_project --root . --check-readme-schema-examples --readme-schema-path docs/automation-index.md
PYTHONPATH=src python3 -m r_project --root . --write-readme-examples
PYTHONPATH=src python3 -m r_project --memory-threshold-demo
PYTHONPATH=src python3 -m r_project --memory-threshold-demo --json
PYTHONPATH=src python3 -m r_project --memory-threshold-demo --memory-overlap-max-count 2 --memory-overlap-max-bytes 6
PYTHONPATH=src python3 -m r_project --memory-threshold-demo --json --memory-overlap-max-count 2 --memory-overlap-max-bytes 6
PYTHONPATH=src python3 -m r_project --memory-threshold-demo --memory-overlap-group-by name_prefix --memory-overlap-prefix-depth 2
PYTHONPATH=src python3 -m r_project --memory-threshold-demo --json --memory-overlap-group-by name_prefix --memory-overlap-prefix-depth 2
PYTHONPATH=src python3 -m r_project --memory-overlap-totals-demo
PYTHONPATH=src python3 -m r_project --memory-overlap-totals-demo --json
PYTHONPATH=src python3 -m r_project --memory-overlap-totals-demo --memory-overlap-group-by name_prefix --memory-overlap-prefix-depth 2
PYTHONPATH=src python3 -m r_project --memory-overlap-totals-demo --json --memory-overlap-group-by name_prefix --memory-overlap-prefix-depth 2
PYTHONPATH=src python3 -m r_project --memory-overlap-totals-demo --memory-overlap-name-prefix left.
PYTHONPATH=src python3 -m r_project --memory-threshold-demo --json --memory-overlap-tag source:literal --memory-overlap-max-count 0
PYTHONPATH=src python3 -m r_project --memory-overlap-demo-schema
PYTHONPATH=src python3 -m r_project --root . --check-memory-overlap-demo-schema
PYTHONPATH=src python3 -m r_project --root . --check-readme-schema-examples
PYTHONPATH=src python3 -m r_project --root . --write-readme-schema-examples --dry-run-readme-schema-examples
PYTHONPATH=src python3 -m r_project --root . --write-readme-schema-examples
PYTHONPATH=src python3 -m r_project --root . --check-readme-schema-examples --readme-schema-path README.md
PYTHONPATH=src python3 -m r_project --root . --check-readme-schema-examples --readme-schema-path docs/dashboard-schema.md
PYTHONPATH=src python3 -m r_project --root . --check-changelog-version
PYTHONPATH=src python3 -m r_project --root . --check-release-tag v0.1.0 --docker-verified
PYTHONPATH=src python3 -m r_project --root . --json --check-release-tag v0.1.0 --docker-verified
PYTHONPATH=src python3 -m r_project --root . --check-release-tag-fixture
PYTHONPATH=src python3 -m r_project --root . --write-release-tag-fixture --dry-run-release-tag-fixture
PYTHONPATH=src python3 -m r_project --root . --write-release-tag-fixture
PYTHONPATH=src python3 -m r_project --root . --write-release-tag-fixture --dry-run-release-tag-fixture --release-tag-fixture-version 0.2.0
PYTHONPATH=src python3 -m r_project --root . --write-release-tag-fixture --dry-run-release-tag-fixture --release-tag-fixture-path tests/fixtures/release-tag-checklist.json
PYTHONPATH=src python3 -m r_project --root . --check-release-tag-fixture --release-tag-fixture-path docs/release/checklist.json
PYTHONPATH=src python3 -m r_project --root . --check-release-examples --release-examples-path docs/release-examples.md
PYTHONPATH=src python3 -m r_project --root . --check-release-examples --release-examples-path docs/automation-index.md --release-examples-section 'Embedded release checklist example'
PYTHONPATH=src python3 -m r_project --root . --write-release-examples --dry-run-release-examples --release-examples-path docs/automation-index.md --release-examples-section 'Embedded release checklist example'
PYTHONPATH=src python3 -m r_project --root . --write-release-examples --dry-run-release-examples --release-examples-path tests/fixtures/automation-index-release-smoke.md --release-examples-section 'Embedded release checklist example'
PYTHONPATH=src python3 -m r_project --root . --write-release-examples --dry-run-release-examples --release-examples-path docs/release-examples.md
PYTHONPATH=src python3 -m r_project --root . --write-release-examples --dry-run-release-examples --release-examples-version 0.2.0 --release-examples-path docs/release-examples.md
PYTHONPATH=src python3 -m r_project --root . --write-release-examples --dry-run-release-examples --release-examples-version 0.2.0 --release-examples-path tests/fixtures/release-examples-future-version-smoke.md
PYTHONPATH=src python3 -m r_project --root . --check-release-example-fixtures
PYTHONPATH=src python3 -m r_project --root . --check-release-example-sections
PYTHONPATH=src python3 -m r_project --root . --check-release-section-writer-matrix
PYTHONPATH=src python3 -m r_project --root . --check-release-section-writer-matrix --release-section-writer-matrix-version 0.2.0
PYTHONPATH=src python3 -m r_project --root . --generate-release-section-writer-matrix --release-section-writer-matrix-version 0.2.0
PYTHONPATH=src python3 -m r_project --root . --write-release-section-writer-matrix --dry-run-release-section-writer-matrix --release-section-writer-matrix-version 0.2.0
PYTHONPATH=src python3 -m r_project --root . --check-release-examples-path-safety
PYTHONPATH=src python3 -m r_project --root . --generate-release-automation-index
PYTHONPATH=src python3 -m r_project --root . --generate-release-automation-index --release-automation-index-version 0.3.0
PYTHONPATH=src python3 -m r_project --root . --generate-release-automation-index --release-automation-index-version 0.3.0 --release-automation-index-profile-section 'Release 0.3.0 preview profile'
PYTHONPATH=src python3 -m r_project --root . --write-release-automation-index --dry-run-release-automation-index
PYTHONPATH=src python3 -m r_project --root . --write-release-automation-index --dry-run-release-automation-index --release-automation-index-version 0.3.0
PYTHONPATH=src python3 -m r_project --root . --write-release-automation-index --dry-run-release-automation-index --release-automation-index-version 0.3.0 --release-automation-index-profile-section 'Release 0.3.0 preview profile'
PYTHONPATH=src python3 -m r_project --root . --check-release-automation-index
PYTHONPATH=src python3 -m r_project --root . --check-release-automation-index --release-automation-index-version 0.3.0
PYTHONPATH=src python3 -m r_project --root . --check-release-automation-index --release-automation-index-version 0.3.0 --release-automation-index-profile-section 'Release 0.3.0 preview profile'
PYTHONPATH=src python3 -m r_project --root . --check-automation-index-links
PYTHONPATH=src python3 -m r_project --root . --check-automation-index-commands
PYTHONPATH=src python3 -m r_project --root . --check-automation-command-fixtures
PYTHONPATH=src python3 -m r_project --root . --generate-dashboard-automation-index
PYTHONPATH=src python3 -m r_project --root . --generate-dashboard-automation-index --dashboard-automation-index-variant expanded
PYTHONPATH=src python3 -m r_project --root . --write-dashboard-automation-index --dry-run-dashboard-automation-index
PYTHONPATH=src python3 -m r_project --root . --write-dashboard-automation-index --dry-run-dashboard-automation-index --dashboard-automation-index-variant expanded
PYTHONPATH=src python3 -m r_project --root . --check-dashboard-automation-index
PYTHONPATH=src python3 -m r_project --root . --check-dashboard-automation-index --dashboard-automation-index-variant expanded
PYTHONPATH=src python3 -m r_project --root . --generate-dashboard-example-fixtures
PYTHONPATH=src python3 -m r_project --root . --write-dashboard-example-fixtures --dry-run-dashboard-example-fixtures
PYTHONPATH=src python3 -m r_project --root . --check-dashboard-example-fixtures
PYTHONPATH=src python3 -m r_project --root . --check-dashboard-section-writer-matrix
PYTHONPATH=src python3 -m r_project --root . --check-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant compact
PYTHONPATH=src python3 -m r_project --root . --check-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant expanded
PYTHONPATH=src python3 -m r_project --root . --generate-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant compact
PYTHONPATH=src python3 -m r_project --root . --generate-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant expanded
PYTHONPATH=src python3 -m r_project --root . --write-dashboard-section-writer-matrix --dry-run-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant compact
PYTHONPATH=src python3 -m r_project --root . --write-dashboard-section-writer-matrix --dry-run-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant expanded
PYTHONPATH=src python3 -m r_project.lint --root .
```

Before committing, run the same verification in Docker so tests execute in a clean, reproducible container:

```bash
docker compose run --build --rm test
```

## Release and versioning

The package version is currently `0.1.0` in `pyproject.toml`. R follows semantic versioning for published releases:

- increment the patch version for compatible bug fixes and documentation-only release updates;
- increment the minor version for backward-compatible CLI/report/helper additions;
- reserve major version changes for incompatible report schema, CLI, or helper API changes.

Before cutting a release, update `CHANGELOG.md` with the user-visible changes, verify the commands in the Development section (including Docker), and tag the release as `vX.Y.Z` to match `pyproject.toml`. External release automation can run `r-project --root . --json --check-release-tag v0.1.0 --docker-verified` to get a machine-readable checklist with `tag_matches_version`, `docker_verified`, `git_clean`, and overall `ready` fields before publishing. If automation relies on the frozen checklist fixture, run `r-project --root . --check-release-tag-fixture` to confirm `tests/fixtures/release-tag-checklist.json` still matches current CLI output, or `r-project --root . --write-release-tag-fixture --dry-run-release-tag-fixture` to preview a refreshed fixture before writing it with `r-project --root . --write-release-tag-fixture`. Add `--release-tag-fixture-version X.Y.Z` to either fixture command when preparing or validating a future-version checklist before `pyproject.toml` is bumped. Add `--release-tag-fixture-path docs/release/checklist.json` when external release automation stores its frozen checklist under another root-relative path.

The standalone [`docs/release-checklist.md`](docs/release-checklist.md) page documents that external fixture-path workflow and the checked [`docs/release/checklist.json`](docs/release/checklist.json) fixture for release automation consumers. [`docs/release-examples.md`](docs/release-examples.md) keeps a checked README-style release checklist JSON fence for dashboards that need embedded snippets. Add `--release-examples-version X.Y.Z` to the release example checker or writer when release docs need to preview a non-current tag before `pyproject.toml` changes. [`docs/release-example-fixtures.md`](docs/release-example-fixtures.md) indexes the release-example smoke fixtures and Docker commands that exercise them; run `r-project --root . --check-release-example-fixtures` to verify every indexed fixture command has matching Docker harness coverage. [`docs/release-example-sections.md`](docs/release-example-sections.md) registers independently checked release checklist Markdown sections; run `r-project --root . --check-release-example-sections` to verify every registered section command has matching Docker harness coverage. [`docs/release-section-writer-matrix.md`](docs/release-section-writer-matrix.md) maps those registered sections to current-version and configurable future-version writer dry-runs; run `r-project --root . --check-release-section-writer-matrix` to verify the matrix covers each section and Docker exercises every writer command, add `--release-section-writer-matrix-version X.Y.Z` when release docs need a different future preview target, run `r-project --root . --generate-release-section-writer-matrix --release-section-writer-matrix-version X.Y.Z` to emit registry-derived current/future writer rows before appending them to the matrix, or run `r-project --root . --write-release-section-writer-matrix --dry-run-release-section-writer-matrix --release-section-writer-matrix-version X.Y.Z` to preview safe append/idempotence updates before omitting the dry-run flag. [`docs/release-automation-index.md`](docs/release-automation-index.md) keeps release-only automation links and commands auditable against Docker coverage and can be refreshed with generated link/command rows before publishing new release surfaces. [`docs/dashboard-example-fixtures.md`](docs/dashboard-example-fixtures.md) indexes independently checked dashboard readiness/schema docs; run `r-project --root . --check-dashboard-example-fixtures` to verify every indexed dashboard command has matching Docker harness coverage. Run `r-project --root . --check-automation-index-links` to verify [`docs/automation-index.md`](docs/automation-index.md) links every standalone dashboard and release automation surface before publishing combined automation docs. Run `r-project --root . --check-automation-command-fixtures` to verify [`docs/automation-command-fixtures.md`](docs/automation-command-fixtures.md) keeps split-doc automation commands covered by Docker. [`docs/release-index.md`](docs/release-index.md) links those release fixture docs with the version/tag guard commands as a single release readiness entry point. [`docs/automation-index.md`](docs/automation-index.md) combines the dashboard readiness/schema docs and release readiness docs as one automation navigation page.

## License

R is distributed under the GNU Affero General Public License v3.0 or later (`AGPL-3.0-or-later`). See [`LICENSE`](LICENSE).

## Autonomous maintenance

- Automation home: [`automations/`](automations/)
- Interpreted Rust inside C showcase: [`automations/interpreted-rust-in-c.md`](automations/interpreted-rust-in-c.md)
- Plan: [`docs/plans/autonomous-agent.md`](docs/plans/autonomous-agent.md)
- Cron prompt: [`docs/autonomous-agent-prompt.md`](docs/autonomous-agent-prompt.md)
- Status/backlog: [`status/`](status/)

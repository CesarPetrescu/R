# R TODO

Select work by user-visible interpreter outcomes in [the product roadmap](../docs/ROADMAP.md), not by the number of checked helper entries. The historical [backlog](missing-features.md) records completed work but is not a mandate to continue balance suffixes. Complete a concrete, testable implementation package when safe; report a blocker rather than manufacture a low-value task.

## Next recommended tasks

1. Test whether invalid statements in unselected `if`/`else` and zero-iteration `while` blocks are silently accepted (`if 0 { 1 + * } else { 7 }` currently returns `7`); decide and document the supported grammar, then close the gap test-first without evaluating effects in skipped bodies. Cover nested blocks, scope, malformed statements, and step limits.
2. Audit another observed arithmetic or semantic failure in an ordinary composed program; use a portable boundary or host-level RED/GREEN fixture, invalid input and C API output-preservation tests where applicable.
3. Split the oversized `parse_factor` helper-dispatch chain without changing interpreter behavior; preserve existing helper outputs, diagnostic ordering and temporary-array cleanup in regression tests.
4. Add a repository CI workflow through an authorized maintainer with the required permission; verify the strict C-host tests, documentation guards and container test service without claiming CI exists before it runs.

## Recently completed roadmap outcomes
- Checked `outlier_score(array, min, max)` distance subtractions and nonnegative accumulation against host-`long` overflow. A portable 22-row fixture covers both sides, reversed bounds, valid boundaries, lazy paths, diagnostics, composition and repeated cleanup; the C API preserves output on failure.

- Checked `histogram_distance_score` and `histogram_within_distance` before the frequency subtraction, absolute-value conversion, left-to-right score addition, and missing-expected-element increment. A portable 24-row fixture covers the host-long limits, compositions, lazy paths, diagnostics and repeated temporary cleanup; both functions preserve C API output on failure. The distance-limit predicate does not silently turn overflow into a boolean.
- Checked `histogram_pairs_score(values, counts)` per-pair multiplication and left-to-right sum before signed overflow. A portable 20-row fixture covers both boundaries, a later-cancelled prefix, empty/mismatched arrays, composed and skipped paths, and 65-iteration cleanup; the C API output stays unchanged on error.
- Checked `weighted_score(array, fn)` callback-result additions before signed overflow, with positive/negative host-long boundaries and a later-cancelled prefix. The portable 16-row fixture covers valid and invalid callbacks, nested temporary arrays, lazy branches and 65-iteration cleanup; the C API output is unchanged on error.
- Checked `top_sum(array, n)` selected additions after descending sort before signed overflow. The portable 20-row fixture covers both host-long bounds, a later-cancelled prefix, zero/empty/count edges, function/nested temporary composition, lazy paths, diagnostics and 65-iteration cleanup; the C API retains its previous output on error.

- Checked `median(array)` even-length midpoint addition before C signed-overflow UB. The sorted middle pair must have an in-range host-`long` sum before division (even when its mathematical midpoint would fit); odd-length arrays return their middle element. A portable 20-row host fixture covers both overflow directions, signed truncation, composition, skipped paths, invalid arguments and 65-iteration cleanup; the C API output is unchanged on failure.

- Checked `variance_sum(array)` mean accumulation, signed delta, square and sum-of-squares accumulation before host-long overflow. A portable 21-row host fixture covers positive/negative bounds, composition, skipped branches, invalid arguments and 65-iteration temporary cleanup; the C API preserves output on failure. The even-length `median` arithmetic was checked in a subsequent work package.
- Checked each `adjacent_diff(array)` subtraction against host-long bounds before evaluation; the first element is copied without subtraction. A portable 17-row host fixture covers both overflow directions, zero/one-element arrays, nested temporaries, skipped paths, invalid arguments, 65-iteration cleanup and unchanged C API output.
- Checked `chunk_sum(array, n)` additions per chunk before signed-overflow UB; a portable 18-row host fixture covers boundary values, partial and independent chunks, nested temporaries, lazy paths, invalid arguments, repeated cleanup and unchanged C API output.
- Checked every `moving_average_sum(array, n)` intermediate window addition before division, including positive/negative overflow that would otherwise wrap to an apparently valid mean. A portable 17-row host fixture covers boundaries, truncation, nested temporaries, skipped branches, diagnostics and repeated cleanup; the C API preserves output on error.
- Checked every `window_sum(array, n)` intermediate addition, including positive/negative boundaries and later cancellation in overlapping windows; preserved C API output on failure. A portable 17-row fixture exercises composition, lazy paths, diagnostics and 65-iteration temporary cleanup.
- Checked every `prefix_sum(array)` intermediate addition before computing it, including positive/negative boundaries and a later-cancelled prefix; C API output remains unchanged on error. A portable 14-row host fixture covers composition, lazy branches, invalid arguments and repeated temporary cleanup.
- Documented the accepted Rustic language/C API subset with executable success/error host examples in `docs/rustic-language-contract.md`; `strtol` overflow in evaluated literals and match-arm patterns reports `RUSTIC_ERR_INTEGER_OVERFLOW`. The grammar-only skip path does not evaluate literal magnitude. Checked expression operators are described below; helper-internal arithmetic remains a separate task.
- Checked host-`long` arithmetic for evaluated expression operators, including the `LONG_MIN / -1` and `% -1` crash cases; added boundary cases, composed positive/negative host examples and C API output-preservation checks. Helper-internal arithmetic is not checked.
- Checked every `sum(array)` intermediate addition in array order with an overflow status, preserving the C API output on error; other built-in arithmetic remains unchecked.

## Every-run checklist

- [ ] Inspect branch/status and checkout ownership first; sync clean, unowned `main` with a fast-forward pull, or use an isolated worktree. Never switch, reset, or stash another worker's shared checkout.
- [ ] Read README, roadmap, plan, prompt, and all `status/` files
- [ ] Ideate candidate roadmap-completion tasks
- [ ] Choose the highest-impact finishable work package
- [ ] Write failing tests first for behavior changes
- [ ] Implement the selected work package fully enough to close backlog items
- [ ] Run verification
- [ ] Update status/backlog with completed and overflow ideas
- [ ] Commit verified changes only on a focused `ai/r/*` branch, push through the authorized bot wrapper, and open/update a PR against `main`; never push directly to `main`.
- [ ] Before any merge, require the exact-current-head authenticated reviewer verifier (`/usr/local/bin/r-verify-ai-review <pr-number>`, exit 0 and JSON `"ok": true`), clean mergeability, required checks and local Docker evidence; leave the PR open if any gate is missing.

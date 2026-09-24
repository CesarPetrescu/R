# R TODO

Select work by user-visible interpreter outcomes in [the product roadmap](../docs/ROADMAP.md), not by the number of checked helper entries. The historical [backlog](missing-features.md) records completed work but is not a mandate to continue balance suffixes. Complete a concrete, testable implementation package when safe; report a blocker rather than manufacture a low-value task.

## Next recommended tasks

1. Continue the built-in arithmetic safety audit beyond checked `sum` and `prefix_sum`: demonstrate overflow in `window_sum([LONG_MAX, 1], 2)` with a portable RED C-host fixture, then propagate `RUSTIC_ERR_INTEGER_OVERFLOW` and check nested temporary-array lifetime. Expression operators and these two helpers do **not** protect other built-in internals.
2. Pick another observed semantic or diagnostic gap in ordinary composed programs and close it test-first, including invalid input, scope/lifetime and budget cases where relevant. Do not assume full Rust compatibility.
3. Split the oversized `parse_factor` helper-dispatch chain without changing interpreter behavior; preserve existing helper outputs, diagnostic ordering and temporary-array cleanup in regression tests.
4. Add a repository CI workflow through an authorized maintainer with the required permission; verify the strict C-host tests, documentation guards and container test service without claiming CI exists before it runs.

## Recently completed roadmap outcomes

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

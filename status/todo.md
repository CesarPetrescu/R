# R TODO

Select work by user-visible interpreter outcomes in [the product roadmap](../docs/ROADMAP.md), not by the number of checked helper entries. The historical [backlog](missing-features.md) records completed work but is not a mandate to continue balance suffixes. Complete a concrete, testable implementation package when safe; report a blocker rather than manufacture a low-value task.

## Next recommended tasks

1. Specify the accepted Rustic subset and C API contract with runnable positive/negative host examples, explicit integer/array/function semantics and fixed resource bounds; compare the reference against existing tests.
2. Audit C `long` literal conversion and arithmetic overflow using explicit host examples (including beyond-`LONG_MAX` input), then define/test a deterministic C API diagnostic without assuming full Rust integer semantics. Unary negation of `LONG_MIN` is covered; other operations are not.
3. Pick another observed semantic or diagnostic gap in ordinary composed programs and close it test-first, including invalid input, scope/lifetime and budget cases where relevant. Do not assume full Rust compatibility.
4. Split the oversized `parse_factor` helper-dispatch chain without changing interpreter behavior; preserve existing helper outputs, diagnostic ordering and temporary-array cleanup in regression tests.
5. Add a repository CI workflow through an authorized maintainer with the required permission; verify the strict C-host tests, documentation guards and container test service without claiming CI exists before it runs.

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

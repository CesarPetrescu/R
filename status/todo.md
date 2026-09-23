# R TODO

Select work by user-visible interpreter outcomes in [the product roadmap](../docs/ROADMAP.md), not by the number of checked helper entries. The historical [backlog](missing-features.md) records completed work but is not a mandate to continue balance suffixes. Complete a concrete, testable implementation package when safe; report a blocker rather than manufacture a low-value task.

## Next recommended tasks

1. Specify the accepted Rustic subset and C API contract with runnable positive/negative host examples, explicit integer/array/function semantics and fixed resource bounds; compare the reference against existing tests.
2. Pick one observed semantic or diagnostic gap in ordinary composed programs and close it test-first, including invalid input, scope/lifetime and budget cases where relevant. Do not assume full Rust compatibility.
3. Split the oversized `parse_factor` helper-dispatch chain without changing interpreter behavior; preserve existing helper outputs, diagnostic ordering and temporary-array cleanup in regression tests.
4. Add a repository CI workflow through an authorized maintainer with the required permission; verify the strict C-host tests, documentation guards and container test service without claiming CI exists before it runs.

## Every-run checklist

- [ ] Pull latest `main` with `git checkout main && git pull --ff-only`
- [ ] Read README, plan, prompt, and all `status/` files
- [ ] Ideate candidate roadmap-completion tasks
- [ ] Choose the highest-impact finishable work package
- [ ] Write failing tests first for behavior changes
- [ ] Implement the selected work package fully enough to close backlog items
- [ ] Run verification
- [ ] Update status/backlog with completed and overflow ideas
- [ ] Commit and push verified changes

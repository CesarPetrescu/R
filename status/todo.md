# R TODO

The autonomous agent should complete concrete implementation work every run, not vague improvements.

## Next recommended tasks

1. Add CI workflow once the builder GitHub App has `workflows` permission, or ask a maintainer to push `.github/workflows/ci.yml`.
2. Split the oversized `parse_factor` helper-dispatch chain into smaller generated or table-driven units without changing interpreter behavior; preserve the checked helper-chain outputs and strict diagnostics.
3. Continue extending the Rustic interpreter with a bounded, test-first product-depth helper family after the balance-whole helpers; select the next identifier-safe suffix (for example `piece`) after checking the 63-character Rustic identifier cap, with acceptance coverage for direct/edge behavior, invalid arguments, the composed showcase, and 65-iteration cleanup diagnostics.

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

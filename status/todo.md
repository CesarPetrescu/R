# R TODO

The autonomous agent should complete concrete implementation work every run, not vague improvements.

## Next recommended tasks

1. Add CI workflow once the builder GitHub App has `workflows` permission, or ask a maintainer to push `.github/workflows/ci.yml`.
2. Continue extending the Rustic interpreter with a bounded, test-first product-depth helper family after the balance-assure helpers; next candidate `balance-check` is identifier-safe (62/60 characters for threshold/outlier) and should preserve direct/edge, invalid-argument, showcase, and cleanup diagnostics.
3. Split the oversized `parse_factor` helper-dispatch chain into smaller generated or table-driven units without changing interpreter behavior.

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

# R TODO

The autonomous agent should complete concrete implementation work every run, not vague improvements.

## Next recommended tasks

1. Add CI workflow once the builder GitHub App has `workflows` permission, or ask a maintainer to push `.github/workflows/ci.yml`.
2. Add a dashboard automation surface link/command guard extension if future dashboard docs add new standalone surfaces beyond `docs/dashboard-section-writer-matrix.md`.
3. Add a dashboard variant-specific writer applicator if dashboard docs need a safe in-place mode that appends generated variant rows to `docs/dashboard-section-writer-matrix.md` after preview.

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

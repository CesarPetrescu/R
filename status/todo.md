# R TODO

The autonomous agent should complete concrete implementation work every run, not vague improvements.

## Next recommended tasks

1. Add CI workflow once the builder GitHub App has `workflows` permission, or ask a maintainer to push `.github/workflows/ci.yml`.
2. Add a dashboard automation fixture registry if future dashboard docs split readiness/schema examples across multiple independently checked Markdown sections.
3. Add a release-section writer matrix if future release docs need multiple future-version snippets per Markdown file.

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

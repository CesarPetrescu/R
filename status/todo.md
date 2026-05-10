# R TODO

The autonomous agent should complete concrete implementation work every run, not vague improvements.

## Next recommended tasks

1. Add boolean conjunction/disjunction (`&&`/`||`) to make compound Rustic guards less nested while preserving skipped-branch style safety tests.
2. Add comparison-heavy loop fixtures that combine nested blocks, local helper functions, and function values after boolean conjunction/disjunction exists.
3. Migrate automation-facing docs and guard defaults from `docs/*automation*` paths into `automations/` behind compatibility tests, keeping Docker coverage green while paths move.
4. Add CI workflow once the builder GitHub App has `workflows` permission, or ask a maintainer to push `.github/workflows/ci.yml`.

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

# R TODO

The autonomous agent should complete concrete implementation work every run, not vague improvements.

## Next recommended tasks

1. Add conditional `if`/`else` expression support to the C-hosted Rust-like interpreter now that blocks and boolean integer comparisons exist, backed by fixtures proving branch selection and scoped bindings.
2. Add `while` loop statement support to the C-hosted Rust-like interpreter after conditionals land, backed by a fixture that mutates a counter and returns an accumulated value.
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

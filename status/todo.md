# R TODO

The autonomous agent should complete concrete implementation work every run, not vague improvements.

## Next recommended tasks

1. Add another concrete Rustic product-depth helper pair that extends the signal-density band family beyond `threshold_run_signal_density_band_span_gap_delta_balance_shard(...)`, choosing names within the 63-character Rustic identifier cap, with empty/single-element/no-match behavior, invalid argument diagnostics, composition fixtures, and array-slot cleanup. Safe next candidate suffix: `gravel` (threshold helper length 63); avoid `granite`/`obsidian`/`citrine`/`emerald`/`sapphire`/`crystal` because they exceed the Rustic identifier cap.
2. Migrate automation-facing docs and guard defaults from `docs/*automation*` paths into `automations/` behind compatibility tests, keeping Docker coverage green while paths move.
3. Add CI workflow once the builder GitHub App has `workflows` permission, or ask a maintainer to push `.github/workflows/ci.yml`.

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

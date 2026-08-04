# Automations

This folder is the canonical home for automation-facing material in R.

R's main goal is to showcase automation working while it builds and presents interpreted Rust inside C. The readiness CLI, drift checks, Docker harness, PR workflow, and checked docs are support systems for that showcase; they are not the thing being sold as the product.

## Contents

- `interpreted-rust-in-c.md` — product/showcase direction for the Rust-in-C interpreter work.
- `public-github-trust-boundary.md` — deterministic owner/bot intake and authenticated-review requirements for public issues and pull requests.
- Canonical automation indexes and command fixtures now live here:
  - `automations/automation-index.md`
  - `automations/dashboard-automation-index.md`
  - `automations/release-automation-index.md`
  - `automations/automation-command-fixtures.md`
- Existing executable supporting docs remain under `docs/` until their checked commands can migrate safely:
  - `docs/dashboard-example-fixtures.md`
  - `docs/dashboard-section-writer-matrix.md`
  - `docs/release-example-fixtures.md`
  - `docs/release-example-sections.md`
  - `docs/release-section-writer-matrix.md`
- Legacy compatibility copies of the four moved indexes remain under `docs/`; pass the corresponding `--*-path docs/...` override when validating one explicitly.

## Rule for future work

New automation plans, manifests, and showcase orchestration docs should start in `automations/`. Only keep files under `docs/` when they are executable checked fixtures that current CLI tests or Docker verification still address by path.

# Automations

This folder is the canonical home for automation-facing material in R.

R's main goal is to showcase automation working while it builds and presents interpreted Rust inside C. The readiness CLI, drift checks, Docker harness, PR workflow, and checked docs are support systems for that showcase; they are not the thing being sold as the product.

## Contents

- `interpreted-rust-in-c.md` — product/showcase direction for the Rust-in-C interpreter work.
- Existing executable automation docs currently live under `docs/` and are linked here until their checked commands can migrate safely:
  - `docs/automation-index.md`
  - `docs/dashboard-automation-index.md`
  - `docs/release-automation-index.md`
  - `docs/automation-command-fixtures.md`
  - `docs/dashboard-example-fixtures.md`
  - `docs/dashboard-section-writer-matrix.md`
  - `docs/release-example-fixtures.md`
  - `docs/release-example-sections.md`
  - `docs/release-section-writer-matrix.md`

## Rule for future work

New automation plans, manifests, and showcase orchestration docs should start in `automations/`. Only keep files under `docs/` when they are executable checked fixtures that current CLI tests or Docker verification still address by path.

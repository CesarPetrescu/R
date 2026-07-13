# R Autonomous Agent Plan

> **For Hermes:** Operating specification for recurring autonomous development on `/root/hermes/r-shared/workspace`.

**Goal:** Build project R aggressively and safely by finishing concrete backlog items each run. R's product direction is an automation showcase for interpreted Rust inside C: the agent should use the readiness tooling to make autonomous progress observable, but the interpreter/runtime demonstration is the main product story. The automation must not stop at vague "improvements" when implementation work is possible.

**Architecture:** A Hermes cron job runs in `/root/hermes/r-shared/workspace`. Each run pulls first, reads `status/`, ideates concrete product/backlog-completion tasks, evaluates impact/safety/testability, chooses the highest-impact finishable work package, researches with official docs/web/man pages as needed, creates or reuses an `ai/r/*` branch, implements with tests first when behavior changes, verifies locally including Docker, pushes the branch, opens/updates a PR, obtains or confirms AI reviewer verdict, and may merge to `main` only when the reviewer has cleared the PR and it is safe/mergeable.

## Operating Principles

1. **Finish things:** Treat unchecked backlog as a queue to complete, not suggestions.
2. **Concrete implementation over polish:** Prefer shipping working features, tests, and tooling over generic cleanup or status-only edits.
3. **TDD for behavior:** Write failing tests first for behavior changes, then implement, then verify.
4. **Autonomous ideation:** If the repo is empty or underspecified, create a concrete product direction in `status/current-state.md` and `status/missing-features.md`, implement the first useful scaffold, and keep moving. Do not ask questions during cron runs.
5. **Research when unsure:** Prefer official docs; use `man` pages for local commands, C/POSIX/libc/system details, or when web docs are unavailable. Record findings in `status/research.md`.
6. **No secrets:** Never commit private keys, tokens, `.env`, or host-specific credentials.
7. **PR-first version control:** Start with `git checkout main && git pull --ff-only`; make verified changes on `ai/r/*` branches, push with `/usr/local/bin/r-bot-git-push`, and open/update PRs. Do not push directly to `main`.
8. **Reviewer-gated merge:** r-coder may merge to `main` only after an AI reviewer verdict of `AI_REVIEW:CLEAR`, clean/mergeable PR state, and recorded local Docker verification. Never merge if human review is required or changes are requested.

## Per-run Algorithm

1. Sync: `git checkout main && git pull --ff-only`; inspect `git status --short`.
2. Read `README.md`, `docs/plans/autonomous-agent.md`, and every file under `status/`.
3. Ideate several candidate work packages that would move R toward a complete, useful project.
4. Think/evaluate: impact, safety, dependencies, testability, verification cost.
5. Choose the highest-impact work package that can be completed and verified now.
6. If behavior changes, use TDD: add failing tests, confirm RED, implement, confirm GREEN.
7. Run project verification, including Docker verification when a Docker harness exists. For R specifically, `docker compose run --build --rm test` is mandatory before any push so tests execute in a clean reproducible container.
8. Update status/backlog, including overflow ideas with concrete acceptance tests.
9. Commit verified changes on an `ai/r/*` branch and push using `/usr/local/bin/r-bot-git-push`.
10. Open or update a PR against `main`; make sure an AI reviewer pass occurs.
11. If the PR has `AI_REVIEW:CLEAR`, is clean/mergeable, and verification evidence is present, r-coder may squash merge it to `main` if GitHub permits and it is safe.
12. Report compactly: ideation, selected work package, branch, PR, reviewer verdict, merge result, backlog items completed, tests, verification, commit/push, blockers, next item.

## Verification

Use the best available project verification. Initially, before code exists:

```bash
git diff --check
```

As soon as a language/toolchain exists, replace/extend this with real build, lint, and test commands in `status/current-state.md`. For R, Docker verification is required before committing and pushing:

```bash
docker compose run --build --rm test
```

## Stop Conditions

Stop without pushing broken work if tests fail and the fix is not safe, push auth is missing, the tree has unexpected user changes, or implementation requires unsafe host actions. Record blockers in `status/stuck.md`. Do not merge if the AI reviewer has not cleared the PR, the PR is not clean/mergeable, local Docker verification is missing, a human-mandatory marker is present, or a human explicitly requested no merge.

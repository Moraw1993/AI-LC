# Working on AI-LC

This checkout contains the framework implementation. Learning workspace instructions
are packaged in `src/ailearn/resources/AGENTS.md`; `ailearn init` installs those instructions
for the learner. Do not treat framework development as learner mastery evidence.

Maintain the provider-independent boundary: Python owns validation, graph handling,
evidence gates, scheduling and persistence; the external harness owns reasoning, teaching,
fresh exercise generation and independent semantic assessment. Keep Master plus the five
specialist roles. Shared policy lives in common.md. Never add a static exercise bank.

Read docs/architecture.md and CONTRIBUTING.md before architectural changes. Preserve existing
workspace files, validate cross-domain dependencies, use transactional state writes and
fail clearly on corrupt or unsupported data. Do not execute learner code without a real
external sandbox. Hints, exposure and self-reports do not establish mastery.

Verify changes with `uv run pytest`, `uv run ruff check .`,
`uv run ruff format --check .` and `uv build`. Domain or instruction changes must remain
included in the wheel. Keep README, architecture and authoring guidance consistent with
actual CLI behavior. This checkout is exclusively for framework development. Conduct
learning sessions in separate workspaces outside this repository; packaged learner
instructions are product resources, not instructions to conduct learning here.

## Mandatory development workflow

- Start every change from up-to-date `origin/develop` on its own branch. Use `feat/`,
  `fix/`, `docs/`, `test/`, or `chore/` plus a descriptive name. Never develop directly
  on develop or main. The one-time empty bootstrap commit only establishes the base.
- Make several small, descriptive, thematic commits when appropriate. Stage explicit
  files, inspect staged changes and run `python scripts/check_repository.py --staged`.
- Every implementation finishes with testing and review by an independent agent that
  did not implement the change. The reviewer must examine the final revision, run
  applicable checks and report findings and results. Fix failures and obtain a new
  independent check of any corrective implementation before merging.
- After an independent PASS and passing CI, create/update the PR targeting develop
  and merge using a merge commit to preserve the thematic commit history. Record the
  tested commit SHA, reviewer result and validation in the PR. Do not bypass failures.
- Only a release PR from `release/vX.Y.Z` may target main. It must originate from develop,
  match the package version, pass independent review and CI, and create an annotated
  `vX.Y.Z` tag on the merged main commit. No ordinary changes or direct development
  commits on main. Do not publish a release merely to complete a development task.
- Never commit plans.md, local audit reports, test temporary directories, learning
  state, caches, environments, build outputs, credentials or large generated files.
  The repository check rejects source files over 1 MiB; exceptions require an explicit
  user decision before changing the limit/policy. Keep uv.lock as a reproducibility file.
- Keep the checkout on a new work branch for ongoing changes, not an integration branch.

See CONTRIBUTING.md for commands, release procedure and GitHub protection requirements.

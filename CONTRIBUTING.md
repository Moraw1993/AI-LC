# Development workflow

This repository is the implementation workspace for AI-LC. Learner sessions, learning
plans, personal artifacts and learning state belong in a separate directory outside it.
Domain packs and agent templates under src are product resources and remain versioned.

## Branches and commits

`develop` is the integration branch. `main` contains releases only. Every change starts
on its own branch from current develop, including documentation and configuration changes.

```sh
git fetch origin
git switch -c feat/descriptive-name origin/develop
```

Use feat/, fix/, docs/, test/ or chore/ as appropriate. Break work into small thematic
commits describing the actual change; several commits per implementation are expected
when they help review. Stage explicit paths rather than blindly adding the whole directory.

```sh
git add src/ailearn/engine.py tests/test_lifecycle.py
git diff --cached
python scripts/check_repository.py --staged
git commit -m "fix: require core evidence before transfer assessment"
```

The initial empty develop commit is the one-time bootstrap base. The initial implementation
is reviewed and integrated through its own branch and PR. A local empty main base is
reserved for the first release; publishing main is not part of development bootstrap.

## Independent review and PR

1. Implement and run the relevant checks.
2. Ask an independent agent that did not implement the change to inspect the final
   revision and run tests. Record its PASS/FAIL, tested SHA, commands and findings.
3. Fix failures. Corrective code must receive an independent check before integration.
4. Push the work branch and open a PR targeting develop. Include independent review
   results and validation using the PR template. Wait for CI to pass.
5. Merge the PR using a merge commit so thematic commits remain visible. Update the
   local develop tracking ref, then start subsequent work on another branch from develop.

```sh
uv sync --locked
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv build
python scripts/check_repository.py
```

Run independent checks again when new implementation changes invalidate the reviewed
revision. The agent must report honestly; a PR checkbox alone is not proof of review.

## Releases

Only a release PR from `release/vX.Y.Z` may target main. Create it from develop, update
the package version and lockfile, describe release changes, then obtain independent
review and passing CI. Merge into main and tag that exact merged commit:

```sh
git fetch origin
git switch main
git merge --ff-only origin/main
git tag -a vX.Y.Z -m "AI-LC X.Y.Z"
git push origin vX.Y.Z
```

Replace X.Y.Z with the release version, matching pyproject.toml. Do not move published
tags. Do not release as a side effect of routine development. For the first release,
publish the reserved empty main base before opening the release PR; no implementation
reaches main except through that PR. Publishing a GitHub release or PyPI package is a
separate explicit release action.

## Repository hygiene

Commit source, maintainable product docs, tests, configuration and uv.lock. Do not commit
plans.md, temporary test folders, one-off audit/verification reports, caches, environments,
learner state, credentials, distribution archives, generated media or datasets. Keep
large files in external storage. scripts/check_repository.py rejects forbidden paths and
tracked/staged files larger than 1 MiB. The check reads Git objects, including staged
content, rather than guessing from working-tree file sizes.

## Enforcement boundaries

CI checks tracked files and PR routing. A release PR must be named release/vX.Y.Z,
match the package version and include the current origin/develop commit. CI cannot prove
that an independent agent actually reviewed a change; the PR must retain its report.

GitHub branch protection must require PRs and these status checks on develop and main:
repository-policy and all test matrix jobs. Disable force pushes and branch deletion,
and disallow bypasses where the account plan permits. Require review approval if a
separate reviewer account is available. These repository files do not themselves enable
GitHub branch protection or restrict repository administrators. Tag creation after a
release merge is a required release step, not an automatic action in this version.

## Native release artifacts

Development uses uv; release users do not. `uv run python scripts/build_native.py`
builds a PyInstaller executable for the current platform and writes its SHA256 file.
The native-release PR workflow builds all supported platform assets and smoke-tests
packaged domains, neutral configuration and installers. Require all native jobs before
integration. On an annotated release tag matching the package version, the same workflow
publishes a GitHub release only after native checks and verification that the tagged
commit belongs to main. Publishing this release workflow requires explicit release
authorization; ordinary feature merges never create tags or releases.

Installer verification can use `-ReleaseDirectory dist -Version vX.Y.Z -NoModifyPath`
on Windows, or `RELEASE_DIRECTORY`, `VERSION`, `AILEARN_INSTALL_ROOT`, `AILEARN_BIN_DIR`
on Unix. These support offline validation without changing the actual user installation.

If publication fails after an annotated main tag was created, do not move the tag.
The native-release workflow supports a manual `release_tag` input. Run it from the
reviewed workflow revision with the existing tag; it checks out that immutable release,
rebuilds/tests every native asset, fetches and validates the actual annotated remote tag
object and verifies main ancestry before publishing. This also avoids actions/checkout
projecting a tag name onto a commit-only local ref. Never publish unchecked artifacts.

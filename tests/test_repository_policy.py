"""Repository gates protect artifacts and the release-only main branch."""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "repository_policy", Path(__file__).parents[1] / "scripts/check_repository.py"
)
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


def test_forbidden_artifacts():
    for path in [
        "plans.md",
        ".test-tmp-review/state.json",
        ".uv-cache/data.py",
        "audit/output.json",
        "audiot/results.txt",
        "dist-final/package.whl",
        "secrets/.env",
        "docs/verification.md",
        "data/huge.parquet",
    ]:
        assert policy.forbidden(path), path
    for path in [
        "src/ailearn/engine.py",
        "uv.lock",
        "docs/architecture.md",
        "src/ailearn/resources/agents/assessor.md",
        ".env.example",
    ]:
        assert not policy.forbidden(path), path


def test_develop_and_release_routing():
    assert not policy.check_pr("develop", "feat/review-scheduling", "0.1.0")
    assert policy.check_pr("develop", "main", "0.1.0")
    assert policy.check_pr("main", "feat/review-scheduling", "0.1.0")
    assert policy.check_pr("main", "release/v0.2.0", "0.1.0")

"""Harness configuration must preserve user policy and learner state."""

import tomllib

import pytest

from ailearn.cli import main
from ailearn.harness import configure_codex


def test_neutral_codex_config_preserves_user_files(tmp_path):
    (tmp_path / "AGENTS.md").write_text("User instructions", "utf-8")
    codex = tmp_path / ".codex"
    codex.mkdir()
    (codex / "config.toml").write_text('sandbox_mode = "read-only"', "utf-8")
    assert main(["--workspace", str(tmp_path), "config", "--harness", "codex"]) == 0
    before = (tmp_path / ".ai-learning" / "bootstrap.json").read_bytes()
    configure_codex(tmp_path)
    assert (tmp_path / ".ai-learning" / "bootstrap.json").read_bytes() == before
    assert not (tmp_path / ".ai-learning" / "state.json").exists()
    assert (tmp_path / "AGENTS.md").read_text() == "User instructions"
    assert (codex / "config.toml").read_text() == 'sandbox_mode = "read-only"'
    assert (tmp_path / ".agents/skills/ai-lc-master/SKILL.md").is_file()
    learner_instructions = (tmp_path / ".ai-learning/AGENTS.md").read_text("utf-8")
    assert "Conversation stages and transitions" in learner_instructions
    assert "Do not begin diagnosis before that approval" in learner_instructions
    assert "Ordinary checks" in learner_instructions
    assert "Master owns learner communication" in learner_instructions
    assert "reviewed and approved the course overview" in learner_instructions
    assessor = tomllib.loads((codex / "agents/assessor.toml").read_text("utf-8"))
    assert assessor["name"] == "assessor"
    assert assessor["model_reasoning_effort"] == "low"
    assert "formal checkpoints" in assessor["description"]
    assert "ordinary lesson" in assessor["developer_instructions"]


def test_conflicting_rules_fail_before_bootstrap(tmp_path):
    rules = tmp_path / ".codex/rules/ai-lc.rules"
    rules.parent.mkdir(parents=True)
    rules.write_text("User policy", "utf-8")
    with pytest.raises(ValueError, match="preserved"):
        configure_codex(tmp_path)
    assert rules.read_text() == "User policy"
    assert not (tmp_path / ".ai-learning").exists()


def test_conflicting_assessor_is_preserved_and_fails_before_bootstrap(tmp_path):
    assessor = tmp_path / ".codex/agents/assessor.toml"
    assessor.parent.mkdir(parents=True)
    assessor.write_text('name = "assessor"\n# Learner-owned configuration\n', "utf-8")
    with pytest.raises(ValueError, match="existing Codex agent differs; preserved"):
        configure_codex(tmp_path)
    assert "Learner-owned" in assessor.read_text("utf-8")
    assert not (tmp_path / ".ai-learning").exists()


def test_redirected_codex_directory_rejected(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (tmp_path / ".codex").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlink permission unavailable")
    with pytest.raises(ValueError, match="redirected"):
        configure_codex(tmp_path)
    assert not list(outside.iterdir())

"""Conservative Codex projection; never loosen the sandbox or execute learner code."""

import os
import tempfile
from pathlib import Path

from ailearn.store import Store

RULES = "\n".join(
    [
        "# AI-LC: allow deterministic reads only; writes retain normal approval policy.",
        *[
            f'prefix_rule(pattern = ["ailearn", "{command}"], decision = "allow")'
            for command in ("--version", "sources", "schema", "status", "doctor", "plan")
        ],
        "",
    ]
)

ASSESSOR_AGENT = '''name = "assessor"
description = "AI-LC Assessor for formal checkpoints; never grade ordinary lesson turns."
model_reasoning_effort = "low"
developer_instructions = """
Assess only a completed AI-LC evidence checkpoint explicitly routed to the Assessor.
Never handle ordinary lesson replies or formative checks.
Use the submitted task, learner artifact, rubric, hint log, and sensor outputs. Do not use
Teacher confidence or coaching assumptions. Return concise, dimension-level Evidence JSON
and honest confidence. Do not assign mastery; AI-LC deterministic gates decide progression.
Never invent learner responses, artifacts, sensor results, or evidence. If the submitted
material is incomplete or ambiguous, request clarification instead of filling gaps.
"""
'''


def configure_codex(workspace: Path) -> None:
    workspace = workspace.resolve()
    destination = workspace / ".codex" / "rules" / "ai-lc.rules"
    assessor = workspace / ".codex" / "agents" / "assessor.toml"
    for path in (
        destination.parent.parent,
        destination.parent,
        destination,
        assessor.parent,
        assessor,
    ):
        if path.is_symlink() or path.is_junction():
            raise ValueError(f"Codex integration path cannot be redirected: {path}")
    if destination.exists() and destination.read_text("utf-8") != RULES:
        raise ValueError(f"existing Codex rules differ; preserved: {destination}")
    if assessor.exists() and assessor.read_text("utf-8") != ASSESSOR_AGENT:
        raise ValueError(f"existing Codex agent differs; preserved: {assessor}")
    # Preflight before bootstrap; user-owned Codex config and agents stay untouched.
    Store(workspace).bootstrap()
    for path, content, prefix in (
        (destination, RULES, ".ai-lc-rules-"),
        (assessor, ASSESSOR_AGENT, ".ai-lc-assessor-"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            continue
        fd, name = tempfile.mkstemp(prefix=prefix, dir=path.parent)
        stage = Path(name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(content)
            # Exclusive publication does not replace a concurrent user file.
            if os.name == "nt":
                # Windows rename is atomic and fails if the destination exists.
                # Hard-link creation can be denied by the restricted sandbox token.
                stage.rename(path)
            else:
                os.link(stage, path)
        finally:
            stage.unlink(missing_ok=True)

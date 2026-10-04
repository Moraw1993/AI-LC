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
            for command in ("--version", "domains", "sources", "schema", "status", "doctor", "plan")
        ],
        "",
    ]
)


def configure_codex(workspace: Path) -> None:
    workspace = workspace.resolve()
    destination = workspace / ".codex" / "rules" / "ai-lc.rules"
    for path in (destination.parent.parent, destination.parent, destination):
        if path.is_symlink() or path.is_junction():
            raise ValueError(f"Codex rules path cannot be redirected: {path}")
    if destination.exists() and destination.read_text("utf-8") != RULES:
        raise ValueError(f"existing Codex rules differ; preserved: {destination}")
    # Preflight before bootstrap; user-owned Codex config.toml and rules stay untouched.
    Store(workspace).bootstrap()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        fd, name = tempfile.mkstemp(prefix=".ai-lc-rules-", dir=destination.parent)
        stage = Path(name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(RULES)
            # Exclusive publication does not replace a concurrent user file.
            if os.name == "nt":
                # Windows rename is atomic and fails if the destination exists.
                # Hard-link creation can be denied by the restricted sandbox token.
                stage.rename(destination)
            else:
                os.link(stage, destination)
        finally:
            stage.unlink(missing_ok=True)

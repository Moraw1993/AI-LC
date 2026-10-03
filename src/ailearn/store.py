"""Atomic snapshots with an exclusive writer lock; no implicit data repair."""

import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from importlib.resources import files
from pathlib import Path

from ailearn.graph import Graph
from ailearn.models import Config, Snapshot, now


class Store:
    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()
        self.root = self.workspace / ".ai-learning"
        if self.root.is_symlink() or self.root.is_junction():
            raise ValueError("workspace state directory must not be a symlink or junction")

    def load(self) -> Snapshot:
        if not self.root.exists():
            raise ValueError("workspace is not initialized; run ailearn init")
        state = Snapshot.model_validate_json((self.root / "state.json").read_text("utf-8"))
        graph = Graph(state.domains)
        if state.config.domain not in graph.domains:
            raise ValueError("configured domain is missing")
        if set(state.knowledge) - set(graph.nodes):
            raise ValueError("unknown competency in learner state")
        return state

    @contextmanager
    def transaction(self):
        if not self.root.is_dir():
            raise ValueError("workspace is not initialized; run ailearn init")
        lock = self.root / "write.lock"
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise ValueError(
                f"workspace is locked: {lock}. Wait for the active writer. If it crashed, "
                "verify no writer is running before removing write.lock; no automatic recovery."
            ) from exc
        try:
            with os.fdopen(fd, "w", encoding="ascii") as stream:
                stream.write(str(os.getpid()))
            state = self.load()
            yield state
            self.save(state)
        finally:
            lock.unlink()

    def save(self, state: Snapshot):
        # Publishing one authoritative file makes evidence+state+history one transaction.
        fd, name = tempfile.mkstemp(prefix="state-", suffix=".tmp", dir=self.root)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(state.model_dump_json(indent=2))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.root / "state.json")
        finally:
            Path(name).unlink(missing_ok=True)

    def init(self, config: Config, domains: list) -> bool:
        if self.root.exists():
            state = self.load()
            if state.config != config:
                raise ValueError("workspace already exists with different configuration")
            return False
        graph = Graph(domains)
        if config.domain not in graph.domains:
            raise ValueError(f"unknown domain: {config.domain}")
        self.workspace.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=".ai-learning-init-", dir=self.workspace))
        try:
            (stage / "agents").mkdir()
            for resource in files("ailearn").joinpath("resources/agents").iterdir():
                if resource.name.endswith(".md"):
                    (stage / "agents" / resource.name).write_text(
                        resource.read_text("utf-8"), "utf-8"
                    )
            state = Snapshot(
                config=config,
                domains=domains,
                history=[{"event": "initialization", "timestamp": now().isoformat()}],
            )
            (stage / "state.json").write_text(state.model_dump_json(indent=2), "utf-8")
            (stage / "AGENTS.md").write_text(
                files("ailearn").joinpath("resources/AGENTS.md").read_text("utf-8"), "utf-8"
            )
            stage.rename(self.root)
        finally:
            if stage.exists():
                shutil.rmtree(stage)
        # Exclusive creation preserves pre-existing harness instructions.
        try:
            with (self.workspace / "AGENTS.md").open("x", encoding="utf-8") as stream:
                stream.write((self.root / "AGENTS.md").read_text("utf-8"))
        except FileExistsError:
            pass
        return True

    def export(self) -> dict:
        return self.load().model_dump(mode="json")


def dumps(value) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False)

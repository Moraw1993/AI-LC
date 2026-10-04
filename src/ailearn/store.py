"""Atomic snapshots with an exclusive writer lock; no implicit data repair."""

import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from importlib.resources import files
from pathlib import Path

from ailearn.graph import Graph
from ailearn.models import Bootstrap, Config, Intake, LearningProfile, Snapshot, now


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
        if state.intake is not None:
            profile = state.intake.profile
            if (
                profile.domain,
                profile.target,
                profile.depth,
                profile.learner,
                profile.working_style,
            ) != (
                state.config.domain,
                state.config.target,
                state.config.depth,
                state.config.learner,
                state.config.preferences,
            ):
                raise ValueError("learning profile differs from course configuration")
            closure = graph.closure(graph.domains[profile.domain].targets[profile.target])
            if not set(profile.diagnostic_competencies) <= set(closure):
                raise ValueError("invalid diagnostic competencies in learning profile")
            if state.intake.baseline is not None:
                from ailearn.onboarding import complete_intake

                baseline = state.intake.baseline
                check = state.model_copy(deep=True)
                check.intake.baseline = None
                complete_intake(check, baseline)
        return state

    def bootstrap_state(self) -> Bootstrap:
        return Bootstrap.model_validate_json((self.root / "bootstrap.json").read_text("utf-8"))

    def active(self) -> "Store":
        if (self.root / "state.json").is_file():
            return self  # Existing v0.1 workspaces remain readable without rewriting.
        bootstrap = self.bootstrap_state()
        if not bootstrap.active_workspace:
            return self
        destination = (self.workspace / bootstrap.active_workspace).resolve()
        if not destination.is_relative_to(self.workspace) or destination == self.workspace:
            raise ValueError("active workspace must remain inside the learning hub")
        course = Store(destination)
        if not (course.root / "state.json").is_file():
            raise ValueError(
                "active course snapshot is missing; preserve files and restore a backup"
            )
        course.load()  # An active course cannot silently turn back into neutral onboarding.
        return course

    def _install_skills(self) -> None:
        resources = files("ailearn").joinpath("resources/skills")
        pending = []
        for skill in resources.iterdir():
            destination = self.workspace / ".agents" / "skills" / skill.name / "SKILL.md"
            # Never follow an existing redirected skills directory or replace user files.
            for parent in destination.parents:
                if parent == self.workspace:
                    break
                if parent.is_symlink() or parent.is_junction():
                    raise ValueError(f"skills directory cannot be redirected: {parent}")
            content = skill.joinpath("SKILL.md").read_text("utf-8")
            if destination.is_symlink():
                raise ValueError(f"skill file cannot be redirected: {destination}")
            if destination.exists() and destination.read_text("utf-8") != content:
                raise ValueError(f"existing skill preserved; conflicting file: {destination}")
            pending.append((destination, content))
        for destination, content in pending:
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists():
                with destination.open("x", encoding="utf-8") as stream:
                    stream.write(content)

    def bootstrap(self) -> bool:
        """Install the Master entrypoint without selecting domain, target or curriculum."""
        if self.root.exists():
            if (self.root / "state.json").exists():
                self.load()
            else:
                self.bootstrap_state()
            self._install_commands(self.root)
            self._install_skills()
            return False
        self.workspace.mkdir(parents=True, exist_ok=True)
        self._install_skills()
        stage = Path(tempfile.mkdtemp(prefix=".ai-learning-init-", dir=self.workspace))
        try:
            self._resources(stage)
            (stage / "bootstrap.json").write_text(Bootstrap().model_dump_json(indent=2), "utf-8")
            stage.rename(self.root)
        finally:
            if stage.exists():
                shutil.rmtree(stage)
        self._root_instructions()
        return True

    def configure(self, profile: LearningProfile, domains: list) -> "Store":
        profile = LearningProfile.model_validate(profile.model_dump())
        graph = Graph(domains)
        if profile.domain not in graph.domains:
            raise ValueError(f"unknown domain: {profile.domain}; provide a custom pack")
        path = graph.closure(graph.domains[profile.domain].targets[profile.target])
        if not set(profile.diagnostic_competencies) <= set(path):
            raise ValueError("diagnostic competencies must belong to the selected goal closure")
        with self._lock():
            bootstrap = self.bootstrap_state()
            destination = self.workspace / "workspaces" / profile.workspace_name
            if destination.resolve() != destination or not destination.resolve().is_relative_to(
                self.workspace
            ):
                raise ValueError("course destination cannot be redirected")
            course = Store(destination)
            course.init(
                Config(
                    learner=profile.learner,
                    domain=profile.domain,
                    target=profile.target,
                    depth=profile.depth,
                    preferences=profile.working_style,
                ),
                domains,
                Intake(profile=profile),
            )
            bootstrap.active_workspace = destination.relative_to(self.workspace).as_posix()
            self._atomic(self.root / "bootstrap.json", bootstrap.model_dump_json(indent=2))
        return course

    def _resources(self, stage: Path) -> None:
        self._install_commands(stage)
        (stage / "agents").mkdir()
        for resource in files("ailearn").joinpath("resources/agents").iterdir():
            if resource.name.endswith(".md"):
                (stage / "agents" / resource.name).write_text(resource.read_text("utf-8"), "utf-8")
        (stage / "AGENTS.md").write_text(
            files("ailearn").joinpath("resources/AGENTS.md").read_text("utf-8"), "utf-8"
        )

    def _install_commands(self, root: Path) -> None:
        directory = root / "commands"
        destination = directory / "ailearn.py"
        if directory.is_symlink() or directory.is_junction() or destination.is_symlink():
            raise ValueError("local command path cannot be redirected")
        content = files("ailearn").joinpath("resources/commands/ailearn.py").read_text("utf-8")
        if destination.exists():
            if destination.read_text("utf-8") != content:
                raise ValueError("existing local command differs; preserved")
            return
        directory.mkdir(exist_ok=True)
        with destination.open("x", encoding="utf-8") as stream:
            stream.write(content)

    def _root_instructions(self) -> None:
        try:
            with (self.workspace / "AGENTS.md").open("x", encoding="utf-8") as stream:
                stream.write((self.root / "AGENTS.md").read_text("utf-8"))
        except FileExistsError:
            pass

    @contextmanager
    def _lock(self):
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
            yield
        finally:
            lock.unlink()

    @contextmanager
    def transaction(self):
        with self._lock():
            state = self.load()
            yield state
            self.save(state)

    def save(self, state: Snapshot):
        # Publishing one authoritative file makes evidence+state+history one transaction.
        self._atomic(self.root / "state.json", state.model_dump_json(indent=2))

    def _atomic(self, destination: Path, content: str) -> None:
        fd, name = tempfile.mkstemp(prefix="state-", suffix=".tmp", dir=self.root)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, destination)
        finally:
            Path(name).unlink(missing_ok=True)

    def init(self, config: Config, domains: list, intake: Intake | None = None) -> bool:
        if self.root.exists():
            state = self.load()
            if state.config != config:
                raise ValueError("workspace already exists with different configuration")
            if intake is not None and (
                state.intake is None or state.intake.profile != intake.profile
            ):
                raise ValueError("workspace already exists with a different learning profile")
            if intake is not None and state.domains != domains:
                raise ValueError("workspace already exists with different domain packs")
            return False
        graph = Graph(domains)
        if config.domain not in graph.domains:
            raise ValueError(f"unknown domain: {config.domain}")
        self.workspace.mkdir(parents=True, exist_ok=True)
        self._install_skills()
        stage = Path(tempfile.mkdtemp(prefix=".ai-learning-init-", dir=self.workspace))
        try:
            self._resources(stage)
            state = Snapshot(
                config=config,
                domains=domains,
                intake=intake,
                history=[{"event": "initialization", "timestamp": now().isoformat()}],
            )
            (stage / "state.json").write_text(state.model_dump_json(indent=2), "utf-8")
            stage.rename(self.root)
        finally:
            if stage.exists():
                shutil.rmtree(stage)
        self._root_instructions()
        return True

    def export(self) -> dict:
        return self.load().model_dump(mode="json")


def dumps(value) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False)

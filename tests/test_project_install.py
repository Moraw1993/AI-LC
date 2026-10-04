import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from domain_fixtures import load_test_domains

from ailearn import installer
from ailearn.cli import main
from ailearn.models import Config
from ailearn.store import Store

SOURCE = Path(__file__).resolve().parents[1]


@pytest.fixture
def project(tmp_path, monkeypatch):
    # Exercise the real installer/launcher with existing dependencies, no network in unit tests.
    def populate(stage, source):
        runtime = stage / "runtime"
        runtime.mkdir()
        shutil.copytree(
            source / "src/ailearn",
            runtime / "ailearn",
            ignore=shutil.ignore_patterns("__pycache__"),
        )
        for module_name in [
            "pydantic",
            "pydantic_core",
            "yaml",
            "annotated_types",
            "typing_inspection",
            "typing_extensions",
        ]:
            module = __import__(module_name)
            path = Path(module.__file__)
            if path.name == "__init__.py":
                shutil.copytree(
                    path.parent,
                    runtime / path.parent.name,
                    ignore=shutil.ignore_patterns("__pycache__"),
                )
            else:
                shutil.copy2(path, runtime / path.name)

    monkeypatch.setattr(installer, "populate_runtime", populate)
    return tmp_path / "learning project with spaces"


def command(project, *args, cwd=None):
    return subprocess.run(
        [sys.executable, "-I", str(project / ".ai-learning/commands/ailearn.py"), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def test_project_install_no_global_tool_and_idempotency(project):
    project.mkdir()
    (project / "AGENTS.md").write_text("User guidance", "utf-8")
    assert installer.install(project, SOURCE)
    assert (project / "AGENTS.md").read_text("utf-8") == "User guidance"
    launcher = project / ".ai-learning/commands/ailearn.py"
    assert launcher.is_file()
    assert (project / ".ai-lc/runtime/ailearn/cli.py").is_file()
    before = (project / ".ai-learning/bootstrap.json").read_bytes()
    assert not installer.install(project, SOURCE)
    assert before == (project / ".ai-learning/bootstrap.json").read_bytes()
    assert not list(project.glob(".ai-lc-install-*"))
    status = command(project, "status", cwd=project.parent)
    assert status.returncode == 0, status.stderr
    assert json.loads(status.stdout)["phase"] == "intent-discovery"
    schema = command(project, "schema", "LearningProfile")
    assert schema.returncode == 0, schema.stderr
    assert "target" in json.loads(schema.stdout)["required"]


def test_course_launcher_inherits_runtime_and_binds_course(project):
    from test_onboarding import profile

    installer.install(project, SOURCE)
    course = Store(project).configure(profile(), load_test_domains())
    output = command(course.workspace, "status", cwd=project.parent)
    assert output.returncode == 0, output.stderr
    status = json.loads(output.stdout)
    assert status["workspace"] == str(course.workspace)
    assert status["intake"]["profile"]["agent_name"] == "Ada"
    assert installer.install(project, SOURCE) is False
    assert Store(project).active().workspace == course.workspace


def test_install_failure_preserves_existing_project(project, monkeypatch):
    project.mkdir()
    keep = project / "notes.md"
    keep.write_text("Learner notes", "utf-8")

    def fail(stage, _):
        (stage / "temporary.py").write_text("pass", "utf-8")
        raise OSError("simulated pip failure")

    monkeypatch.setattr(installer, "populate_runtime", fail)
    with pytest.raises(OSError, match="pip failure"):
        installer.install(project, SOURCE)
    assert keep.read_text("utf-8") == "Learner notes"
    assert not (project / ".ai-lc").exists()
    assert not list(project.glob(".ai-lc-install-*"))


def test_corrupt_runtime_manifest_and_python_mismatch(project):
    installer.install(project, SOURCE)
    manifest = project / ".ai-lc/installation.json"
    expected = json.loads(manifest.read_text("utf-8"))
    for malformed in ["broken JSON", "[]", '{"format": 99}']:
        manifest.write_text(malformed, "utf-8")
        assert command(project, "doctor").returncode == 2
        with pytest.raises((OSError, ValueError)):
            installer.install(project, SOURCE)
    expected["python"] = [0, 0]
    manifest.write_text(json.dumps(expected), "utf-8")
    output = command(project, "status")
    assert output.returncode == 2
    assert "Python major/minor" in output.stderr


def test_existing_runtime_and_local_command_never_overwritten(project):
    project.mkdir()
    (project / ".ai-lc").mkdir()
    artifact = project / ".ai-lc/user.txt"
    artifact.write_text("keep", "utf-8")
    with pytest.raises(OSError):
        installer.install(project, SOURCE)
    assert artifact.read_text("utf-8") == "keep"
    command_path = project / ".ai-learning/commands/ailearn.py"
    Store(project).bootstrap()
    command_path.write_text("# custom command", "utf-8")
    with pytest.raises(ValueError, match="preserved"):
        Store(project).bootstrap()
    assert command_path.read_text("utf-8") == "# custom command"


def test_install_preserves_existing_legacy_snapshot(project):
    Store(project).init(Config(domain="statistics"), load_test_domains())
    before = (project / ".ai-learning/state.json").read_bytes()
    installer.install(project, SOURCE)
    assert (project / ".ai-learning/state.json").read_bytes() == before
    assert command(project, "doctor").returncode == 0


def test_schemas_available_without_a_learning_workspace(tmp_path, capsys):
    for model in ["Domain", "Evidence", "Exercise", "Baseline", "Snapshot"]:
        assert main(["--workspace", str(tmp_path), "schema", model]) == 0
        assert json.loads(capsys.readouterr().out)["title"] == model


def test_cleanup_rejects_a_redirected_target(tmp_path):
    with pytest.raises(ValueError, match="escaped"):
        installer.remove_created(tmp_path, tmp_path / "different")


def test_framework_checkout_cannot_become_a_learning_project():
    with pytest.raises(ValueError, match="outside the framework"):
        installer.install(SOURCE, SOURCE)


def test_pip_setup_only_targets_project_and_does_not_modify_global_python(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(installer.venv.EnvBuilder, "create", lambda _, path: path.mkdir())
    monkeypatch.setattr(installer.subprocess, "run", lambda args, **kw: seen.append(args))
    installer.populate_runtime(tmp_path, SOURCE)
    assert "--target" in seen[0]
    assert seen[0][seen[0].index("--target") + 1] == str(tmp_path / "runtime")
    assert seen[0][0].startswith(str(tmp_path / "bootstrap-venv"))
    assert not (tmp_path / "bootstrap-venv").exists()

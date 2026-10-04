"""Standard-library bootstrap for a project-owned runtime and Codex instructions."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import venv
from pathlib import Path


def fingerprint(source: Path) -> str:
    package = source / "src" / "ailearn"
    if not (source / "pyproject.toml").is_file() or not package.is_dir():
        raise ValueError("source must be an AI-LC checkout with pyproject.toml and src/ailearn")
    digest = hashlib.sha256()
    paths = [source / "pyproject.toml", *sorted(package.rglob("*"))]
    for path in paths:
        if path.is_file() and "__pycache__" not in path.parts:
            digest.update(path.relative_to(source).as_posix().encode())
            digest.update(b"\0" + path.read_bytes())
    return digest.hexdigest()


def populate_runtime(stage: Path, source: Path) -> None:
    """Use temporary pip, installing every dependency under the project only."""
    environment = stage / "bootstrap-venv"
    venv.EnvBuilder(with_pip=True).create(environment)
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    subprocess.run(
        [
            str(python),
            "-I",
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-warn-script-location",
            "--target",
            str(stage / "runtime"),
            str(source),
        ],
        check=True,
    )
    remove_created(environment, stage)


def remove_created(path: Path, parent: Path) -> None:
    if path.resolve().parent != parent.resolve():
        raise ValueError("temporary cleanup target escaped its expected directory")
    shutil.rmtree(path)


def bootstrap_project(runtime: Path, workspace: Path) -> None:
    script = (
        "import sys; sys.path.insert(0, sys.argv[1]); "
        "from ailearn.cli import main; "
        "raise SystemExit(main(['--workspace', sys.argv[2], 'init']))"
    )
    subprocess.run([sys.executable, "-I", "-c", script, str(runtime), str(workspace)], check=True)


def install(workspace: Path, source: Path) -> bool:
    if sys.version_info < (3, 12):  # noqa: UP036 - bootstrap runs before package installation
        raise ValueError("AI-LC requires Python 3.12 or newer")
    workspace, source = workspace.resolve(), source.resolve()
    if workspace == source:
        raise ValueError("install into a learning project outside the framework checkout")
    expected = {"format": 1, "python": list(sys.version_info[:2]), "source": fingerprint(source)}
    destination = workspace / ".ai-lc"
    if destination.is_symlink() or destination.is_junction():
        raise ValueError("project runtime directory cannot be redirected")
    if destination.exists():
        manifest = json.loads((destination / "installation.json").read_text("utf-8"))
        if manifest != expected:
            raise ValueError("existing installation differs; preserved. Use a separate project")
        if not (destination / "runtime/ailearn/cli.py").is_file():
            raise ValueError(
                "local runtime is incomplete; preserve project files and restore a backup"
            )
        bootstrap_project(destination / "runtime", workspace)
        return False
    workspace.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".ai-lc-install-", dir=workspace))
    try:
        populate_runtime(stage, source)
        (stage / "installation.json").write_text(json.dumps(expected, indent=2), "utf-8")
        # Validate/bootstrap before publishing runtime. Learner snapshots are never reset.
        bootstrap_project(stage / "runtime", workspace)
        stage.rename(destination)
    finally:
        if stage.exists():
            remove_created(stage, workspace)
    return True


def main(argv: list[str] | None = None, *, source: Path) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    try:
        created = install(args.workspace, source)
        print("Project installation ready." if created else "Project installation preserved.")
        print("Local command: python .ai-learning/commands/ailearn.py status")
        print("Open the project in Codex and invoke $ai-lc-master.")
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"AI-LC installation: {exc}", file=sys.stderr)
        return 2

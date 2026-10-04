"""Run the project's AI-LC runtime, including from a nested course or another cwd."""

import json
import sys
from pathlib import Path


def launch() -> int:
    workspace = Path(__file__).resolve().parents[2]
    try:
        home = next(
            directory / ".ai-lc"
            for directory in (workspace, *workspace.parents)
            if (directory / ".ai-lc").exists()
        )
        if home.is_symlink() or home.is_junction():
            raise ValueError("project runtime directory cannot be redirected")
        manifest = json.loads((home / "installation.json").read_text("utf-8"))
        if not isinstance(manifest, dict) or manifest.get("format") != 1:
            raise ValueError("unsupported or corrupt project installation manifest")
        if manifest.get("python") != list(sys.version_info[:2]):
            raise ValueError("use the Python major/minor version used for project installation")
        runtime = home / "runtime"
        if runtime.is_symlink() or runtime.is_junction():
            raise ValueError("project runtime directory cannot be redirected")
        if not (runtime / "ailearn/cli.py").is_file():
            raise ValueError("project runtime is incomplete; restore a backup")
        sys.path.insert(0, str(runtime))
        from ailearn.cli import main

        return main(["--workspace", str(workspace), *sys.argv[1:]])
    except (StopIteration, OSError, ValueError, ImportError) as exc:
        message = str(exc) or "project runtime is missing; run AI-LC install.py for this project"
        print(f"AI-LC local command: {message}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(launch())

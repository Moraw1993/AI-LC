"""Check staged/tracked Git objects and development/release PR routing."""

import argparse
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path, PurePosixPath

MAX_BYTES = 1024 * 1024
LOCAL_DIRS = {
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".uv-cache",
    ".ai-learning",
    ".ai-lc",
    ".smoke",
    ".wheel-venv",
    ".tool-bin",
    ".tool-store",
    "audit",
    "audits",
    "audiot",
    "learning",
    "artifacts",
    "reports",
    "build",
    ".cache",
    ".mypy_cache",
    "htmlcov",
}
LOCAL_FILES = {"plans.md", "docs/plan-review.md", "docs/verification.md", ".coverage"}
GENERATED_SUFFIXES = (
    ".whl",
    ".zip",
    ".tar.gz",
    ".parquet",
    ".feather",
    ".pkl",
    ".pickle",
    ".npy",
    ".npz",
    ".mp3",
    ".mp4",
    ".wav",
    ".log",
    ".tmp",
)


def git(*arguments: str) -> bytes:
    return subprocess.check_output(["git", *arguments], stderr=subprocess.PIPE)


def forbidden(path: str) -> bool:
    lower = path.lower()
    parts = PurePosixPath(lower).parts
    if lower in LOCAL_FILES or lower.endswith(GENERATED_SUFFIXES):
        return True
    if any(p in LOCAL_DIRS or p.startswith((".test-tmp", ".ai-lc-install-")) for p in parts[:-1]):
        return True
    if parts[0].startswith("dist") and len(parts) > 1:
        return True
    name = parts[-1]
    return name == ".env" or (name.startswith(".env.") and name != ".env.example")


def check_files(staged: bool) -> list[str]:
    command = (
        ("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z")
        if staged
        else ("ls-files", "-z")
    )
    paths = [p.decode("utf-8") for p in git(*command).split(b"\0") if p]
    errors = []
    for path in paths:
        if forbidden(path):
            errors.append(f"Forbidden repository artifact: {path}")
        size = int(git("cat-file", "-s", f":{path}"))
        if size > MAX_BYTES:
            errors.append(f"File exceeds 1 MiB: {path} ({size} bytes)")
    return errors


def check_pr(base: str, head: str, version: str) -> list[str]:
    if base == "develop":
        if not re.fullmatch(r"(?:feat|fix|docs|test|chore)/[a-z0-9][a-z0-9._/-]*", head):
            return ["PRs to develop require a descriptive feat/fix/docs/test/chore work branch."]
    elif base == "main":
        match = re.fullmatch(r"release/v(\d+\.\d+\.\d+)", head)
        if not match or match[1] != version:
            return ["PRs to main require release/vX.Y.Z matching the package version."]
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", "origin/develop", "HEAD"],
            capture_output=True,
            check=False,
        )
        if result.returncode:
            return ["Release branch must include the current origin/develop commit."]
    else:
        return [f"Unsupported integration target: {base}"]
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged", action="store_true")
    parser.add_argument("--base", default=os.getenv("GITHUB_BASE_REF", ""))
    parser.add_argument("--head", default=os.getenv("GITHUB_HEAD_REF", ""))
    args = parser.parse_args(argv)
    try:
        errors = check_files(args.staged)
        if args.base:
            version = tomllib.loads(Path("pyproject.toml").read_text("utf-8"))["project"]["version"]
            errors += check_pr(args.base, args.head, version)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print(f"Repository check could not run: {exc}", file=sys.stderr)
        return 2
    for error in errors:
        print(error, file=sys.stderr)
    if not errors:
        print("OK: repository files and applicable PR policy.")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

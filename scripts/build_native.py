"""Build a self-contained executable on its target OS, then verify packaged resources."""

import hashlib
import platform
import subprocess
import sys
from pathlib import Path

from ailearn import __version__


def main() -> None:
    machine = platform.machine().lower()
    arch = {"amd64": "x64", "x86_64": "x64", "arm64": "arm64", "aarch64": "arm64"}.get(machine)
    system = {"Windows": "windows", "Linux": "linux", "Darwin": "macos"}.get(platform.system())
    if not arch or not system:
        raise SystemExit("Unsupported release platform")
    name = f"ailearn-{system}-{arch}"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onefile",
            "--name",
            name,
            "--paths",
            "src",
            "--collect-all",
            "ailearn",
            "--specpath",
            "build",
            "scripts/native_entry.py",
        ],
        check=True,
    )
    binary = Path("dist") / (name + (".exe" if system == "windows" else ""))
    result = subprocess.check_output([str(binary.resolve()), "--version"], text=True).strip()
    if result != __version__:
        raise SystemExit("Binary version mismatch")
    subprocess.run([str(binary.resolve()), "domains"], check=True, stdout=subprocess.DEVNULL)
    binary.with_name(binary.name + ".sha256").write_text(
        hashlib.sha256(binary.read_bytes()).hexdigest() + "  " + binary.name + "\n", "utf-8"
    )


if __name__ == "__main__":
    main()

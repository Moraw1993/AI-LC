"""Install AI-LC into a learning project without a global tool or uv."""

import sys
from pathlib import Path

if sys.version_info < (3, 12):  # noqa: UP036 - installer also handles unsupported interpreters
    print("AI-LC installation requires Python 3.12 or newer", file=sys.stderr)
    raise SystemExit(2)

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from ailearn.installer import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(source=Path(__file__).resolve().parent))

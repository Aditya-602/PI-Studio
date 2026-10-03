from __future__ import annotations

import os
import subprocess
import sys


def main() -> int:
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name",
        "PI-Studio",
        "--windowed",
        "--onedir",
        "--clean",
        "--noconfirm",
        "main.py",
    ]
    return subprocess.call(cmd, env={**os.environ, "PYTHONPATH": os.getcwd()})


if __name__ == "__main__":
    raise SystemExit(main())

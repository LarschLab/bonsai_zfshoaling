from __future__ import annotations

import importlib.util
import platform
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    if importlib.util.find_spec("PyInstaller") is None:
        print(
            "PyInstaller is not installed. Create a clean build environment and run:\n"
            "  cd calibrationApp\n"
            "  python -m pip install -r requirements-roi-editor-build.txt",
            file=sys.stderr,
        )
        return 2

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        "DishROIEditor",
        str(root / "roi_editor_launcher.py"),
    ]
    print("Building a dependency-isolated application bundle...")
    completed = subprocess.run(command, cwd=root, check=False)
    if completed.returncode == 0:
        name = "DishROIEditor.app" if platform.system() == "Darwin" else "DishROIEditor"
        print(f"Build complete. Distributable output: {root / 'dist' / name}")
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())

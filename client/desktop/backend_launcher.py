"""Entry point for the PyInstaller-bundled Watchtower backend.

PyInstaller runs this as a top-level script, so we import the package's
``main()`` here (which uses proper relative imports internally).
"""
import sys
from pathlib import Path

# Ensure the bundled package is importable.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from watchtower.api import main  # noqa: E402

if __name__ == "__main__":
    main()

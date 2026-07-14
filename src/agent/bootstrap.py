"""Ensure the `agent` package is importable in the active interpreter."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def ensure_agent_importable() -> None:
    """Add src/ to sys.path when running from a checkout without a working editable install."""
    if importlib.util.find_spec("agent") is not None:
        return

    src = project_root() / "src"
    if (src / "agent").is_dir():
        src_str = str(src)
        if src_str not in sys.path:
            sys.path.insert(0, src_str)

    if importlib.util.find_spec("agent") is None:
        raise ModuleNotFoundError("agent")


def install_instructions() -> str:
    root = project_root()
    return (
        "Catalogsmith is not installed in this Python environment.\n\n"
        "From the project root, run:\n"
        f'  cd "{root}"\n'
        "  .\\.venv\\Scripts\\Activate.ps1\n"
        '  .\\scripts\\repair-venv.ps1\n\n'
        "Then start the app with:\n"
        "  catalogsmith-serve\n"
        "  # or\n"
        "  python -m agent\n"
    )

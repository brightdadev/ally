"""
Workspace mapping and structural inspection skill for Ally.
Author: Bright da dev
"""
from pathlib import Path
from app.state import STATE


def get_project_tree(max_depth: int = 2) -> str:
    root = STATE.root.resolve()
    lines = [f"{root.name}/"]
    ignored = {".git", "__pycache__", ".venv", "venv", ".egg-info", "dist", "build"}

    def _walk(path: Path, prefix: str, depth: int):
        if depth > max_depth:
            return
        try:
            entries = sorted(path.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
            filtered = [e for e in entries if e.name not in ignored]
            for i, entry in enumerate(filtered):
                connector = "└── " if i == len(filtered) - 1 else "├── "
                lines.append(f"{prefix}{connector}{entry.name}{'/' if entry.is_dir() else ''}")
                if entry.is_dir():
                    ext = "    " if i == len(filtered) - 1 else "│   "
                    _walk(entry, prefix + ext, depth + 1)
        except Exception:
            pass

    _walk(root, "", 1)
    return "\n".join(lines)
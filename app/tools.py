"""
Filesystem tools for Ally with directory sandbox enforcement.
Author: Bright da dev
"""
from pathlib import Path
from app.state import STATE


def _resolve(path: str) -> Path:
    root = STATE.root.resolve()
    p = Path(path)
    target = (root / p).resolve() if not p.is_absolute() else p.resolve()

    try:
        target.relative_to(root)
    except ValueError:
        raise PermissionError(f"Access denied: '{path}' escapes project root '{root}'")

    return target


def read_file(path: str) -> str:
    try:
        return _resolve(path).read_text(encoding="utf-8")
    except Exception as e:
        return f"ERROR: {e}"


def write_file(path: str, content: str) -> str:
    try:
        p = _resolve(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"OK wrote {p} ({len(content)} chars)"
    except Exception as e:
        return f"ERROR: {e}"


def patch_file(path: str, old: str, new: str) -> str:
    try:
        p = _resolve(path)
        if not p.is_file():
            return f"ERROR: file {p} does not exist"
        text = p.read_text(encoding="utf-8")
        if old not in text:
            return f"ERROR: old text not found in {p}"
        p.write_text(text.replace(old, new, 1), encoding="utf-8")
        return f"OK patched {p}"
    except Exception as e:
        return f"ERROR: {e}"


def delete_file(path: str) -> str:
    try:
        p = _resolve(path)
        if not p.is_file():
            return f"ERROR: file {p} does not exist"
        p.unlink()
        return f"OK deleted {p}"
    except Exception as e:
        return f"ERROR: {e}"


def list_dir(path: str = ".") -> str:
    try:
        p = _resolve(path)
        if not p.is_dir():
            return f"ERROR: directory {p} does not exist"
        entries = sorted(p.iterdir())
        return "\n".join(f"{'d' if e.is_dir() else 'f'} {e.name}" for e in entries)
    except Exception as e:
        return f"ERROR: {e}"

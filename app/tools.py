"""
Filesystem and terminal execution tools for Ally with sandbox and console isolation.
Author: Bright da dev
Version: 1.1.0
"""
import sys
import subprocess
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


def run_command(command: str, timeout: int = 30) -> str:
    """
    Execute terminal command with strict console isolation.
    Uses CREATE_NO_WINDOW and DEVNULL stdin to prevent console mode corruption and mouse escape leaks.
    """
    root = STATE.root.resolve()
    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = subprocess.CREATE_NO_WINDOW

    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=str(root),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            creationflags=creation_flags,
            timeout=max(1, min(timeout, 120)),
        )
        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()
        exit_code = proc.returncode

        output_parts = [f"Exit Code: {exit_code}"]
        if stdout:
            if len(stdout) > 4000:
                stdout = stdout[:4000] + "\n... [output truncated for brevity]"
            output_parts.append(f"STDOUT:\n{stdout}")
        if stderr:
            if len(stderr) > 2000:
                stderr = stderr[:2000] + "\n... [stderr truncated for brevity]"
            output_parts.append(f"STDERR:\n{stderr}")
        if not stdout and not stderr:
            output_parts.append("(Command produced no console output)")

        return "\n\n".join(output_parts)
    except subprocess.TimeoutExpired:
        return f"ERROR: Command timed out after {timeout} seconds."
    except Exception as e:
        return f"ERROR: Failed to execute command: {e}"
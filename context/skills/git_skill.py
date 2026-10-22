"""
Git repository inspection skill for Ally.
Author: Bright da dev
"""
import subprocess
from app.state import STATE


def get_git_status() -> str:
    try:
        res = subprocess.run(
            ["git", "status", "--short", "--branch"],
            cwd=str(STATE.root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res.returncode != 0:
            return f"Git notice: {res.stderr.strip() or 'Not a git repository'}"
        return res.stdout.strip() or "Working tree clean. No uncommitted changes."
    except Exception as e:
        return f"ERROR running git: {e}"
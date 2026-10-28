"""
Filesystem tools with persistent background server manager and live error capture.
Author: Bright da dev
"""
import fnmatch
import os
import re
import subprocess
import threading
import time
from pathlib import Path
from app.state import STATE

DEFAULT_IGNORES = [
    ".env", ".env.*", "*.env",
    "node_modules", "node_modules/*",
    "__pycache__", "*.pyc",
    ".git", ".git/*",
    ".venv", ".venv/*", "venv", "venv/*",
    "dist", "dist/*", "build", "build/*",
    ".ally", ".ally/*",
]

COMMAND_BLACKLIST = {
    "format", "shutdown", "rmdir /s /q c:", "del /f /s /q c:",
    "mkfs", "dd", ":(){ :|:& };:"
}

URL_REGEX = re.compile(r"https?://(?:localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\]):\d+(?:/[^\s]*)?", re.IGNORECASE)

# Persistent background server registry: pid -> {proc, cmd, url, logs}
ACTIVE_SERVERS = {}


def get_ignore_patterns() -> list[str]:
    patterns = list(DEFAULT_IGNORES)
    ignore_file = STATE.root / ".allyignore"
    if ignore_file.is_file():
        try:
            lines = ignore_file.read_text(encoding="utf-8").splitlines()
            for line in lines:
                clean = line.strip()
                if clean and not clean.startswith("#"):
                    patterns.append(clean)
                    if clean.endswith("/"):
                        patterns.append(f"{clean}*")
        except Exception:
            pass
    return patterns


def is_ignored(path: Path) -> bool:
    try:
        rel_path = path.resolve().relative_to(STATE.root.resolve()).as_posix()
    except ValueError:
        return True

    patterns = get_ignore_patterns()
    for pat in patterns:
        clean_pat = pat.rstrip("/")
        if fnmatch.fnmatch(rel_path, pat) or fnmatch.fnmatch(path.name, pat):
            return True
        if rel_path.startswith(f"{clean_pat}/") or rel_path == clean_pat:
            return True
    return False


def _resolve(path: str) -> Path:
    root = STATE.root.resolve()
    p = Path(path)
    target = (root / p).resolve() if not p.is_absolute() else p.resolve()

    try:
        target.relative_to(root)
    except ValueError:
        raise PermissionError(f"Access denied: '{path}' escapes project root '{root}'")

    if is_ignored(target):
        raise PermissionError(f"Access denied: '{path}' is blocked by .allyignore")

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
        entries = [e for e in sorted(p.iterdir()) if not is_ignored(e)]
        return "\n".join(f"{'d' if e.is_dir() else 'f'} {e.name}" for e in entries)
    except Exception as e:
        return f"ERROR: {e}"


def _kill_process_tree(pid: int):
    try:
        subprocess.run(f"taskkill /F /T /PID {pid}", shell=True, capture_output=True)
    except Exception:
        pass


def _background_log_reader(proc, log_buffer: list):
    """Continuously reads stdout and stderr into a rolling buffer of 200 lines."""
    for line in iter(proc.stdout.readline, ""):
        if not line:
            break
        log_buffer.append(line.rstrip())
        if len(log_buffer) > 200:
            log_buffer.pop(0)


def run_command(command: str, timeout: int = 30) -> str:
    """
    Executes a command. Persistent dev servers are launched in background,
    kept alive, and inspected for live preview URLs and early crash traces.
    """
    cmd_clean = command.strip()
    cmd_lower = cmd_clean.lower()

    for blocked in COMMAND_BLACKLIST:
        if blocked in cmd_lower:
            return f"ERROR: Command '{cmd_clean}' is blocked by security policy."

    is_server = any(k in cmd_lower for k in ["run dev", "start", "serve", "vite", "nodemon", "watch", "http.server"])

    if is_server:
        try:
            proc = subprocess.Popen(
                cmd_clean,
                cwd=str(STATE.root),
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            log_buffer = []
            reader_thread = threading.Thread(target=_background_log_reader, args=(proc, log_buffer), daemon=True)
            reader_thread.start()

            # Inspect startup output for 4 seconds
            time.sleep(4)

            # 1. Did the server crash on boot? (Capture exact error)
            if proc.poll() is not None:
                output = "\n".join(log_buffer)
                return f"[Server Failed to Start - Exit Code: {proc.returncode}]\n--- ERROR OUTPUT ---\n{output}"

            # 2. Server is alive! Scan for Preview URL
            startup_text = "\n".join(log_buffer)
            url_match = URL_REGEX.search(startup_text)
            preview_url = url_match.group(0) if url_match else None

            # Register in active servers (KEEPS IT ALIVE)
            ACTIVE_SERVERS[proc.pid] = {
                "proc": proc,
                "cmd": cmd_clean,
                "url": preview_url,
                "logs": log_buffer,
            }

            resp = [
                f"[Server Running in Background - PID: {proc.pid}]",
                f"PREVIEW URL: {preview_url}" if preview_url else "Status: Running (Scanning for URL...)",
                "--- STARTUP LOGS ---",
                startup_text if startup_text else "(Server started cleanly with zero initial logs)"
            ]
            return "\n".join(resp)

        except Exception as e:
            return f"ERROR launching background server: {e}"

    # Standard short commands (git, tsc, npm test, etc.)
    safe_timeout = min(timeout, 60)
    try:
        proc = subprocess.Popen(
            cmd_clean,
            cwd=str(STATE.root),
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            stdout, stderr = proc.communicate(timeout=safe_timeout)
            parts = [f"Exit Code: {proc.returncode}"]
            if stdout:
                parts.append(f"--- STDOUT ---\n{stdout.strip()}")
            if stderr:
                parts.append(f"--- STDERR ---\n{stderr.strip()}")
            if not stdout and not stderr:
                parts.append("(Command produced no output)")
            return "\n".join(parts)
        except subprocess.TimeoutExpired:
            _kill_process_tree(proc.pid)
            return f"ERROR: Command '{cmd_clean}' timed out after {safe_timeout}s and was forcibly terminated."
    except Exception as e:
        return f"ERROR running command: {e}"


def get_server_logs(pid: int = None) -> str:
    """Retrieve live stdout/stderr logs from a running server."""
    if not ACTIVE_SERVERS:
        return "Notice: No background servers are currently running."

    target_pid = pid or list(ACTIVE_SERVERS.keys())[-1]
    server = ACTIVE_SERVERS.get(target_pid)
    if not server:
        return f"ERROR: No server found with PID {target_pid}."

    logs = "\n".join(server["logs"][-50:])
    status = "Active" if server["proc"].poll() is None else f"Exited (Code: {server['proc'].poll()})"
    return f"[Server PID {target_pid} - Status: {status}]\n--- RECENT LOGS ---\n{logs}"


def stop_server(pid: int = None) -> str:
    """Cleanly stops a running background dev server by PID."""
    if not ACTIVE_SERVERS:
        return "Notice: No background servers are currently running."

    target_pid = pid or list(ACTIVE_SERVERS.keys())[-1]
    server = ACTIVE_SERVERS.pop(target_pid, None)
    if not server:
        return f"ERROR: No active server found with PID {target_pid}."

    _kill_process_tree(target_pid)
    return f"OK: Stopped server '{server['cmd']}' (PID: {target_pid})."


def list_servers() -> str:
    """Lists all active background servers and their preview URLs."""
    if not ACTIVE_SERVERS:
        return "No background servers are currently running."

    lines = []
    for pid, s in list(ACTIVE_SERVERS.items()):
        is_alive = s["proc"].poll() is None
        status = "ONLINE" if is_alive else f"EXITED ({s['proc'].poll()})"
        url = s["url"] or "No URL detected"
        lines.append(f"- PID {pid} [{status}]: {s['cmd']} -> {url}")
    return "\n".join(lines)
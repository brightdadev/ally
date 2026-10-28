"""
Security and context defense for Ally (.allyignore).
Author: Bright da dev
Version: 1.1.0
"""
import fnmatch
from pathlib import Path
from typing import List, Optional
from app.state import STATE

# Mandatory built-in security patterns: secrets, keys, and massive bloat
DEFAULT_IGNORE_PATTERNS = [
    ".env*",
    "*.env",
    ".ssh",
    ".ssh/*",
    "*id_rsa*",
    "*.pem",
    "*.key",
    "*.pfx",
    "*.cert",
    "*.crt",
    "node_modules",
    "node_modules/*",
    ".git",
    ".git/*",
    "__pycache__",
    "__pycache__/*",
    ".venv",
    ".venv/*",
    "venv",
    "venv/*",
    ".cache",
    ".cache/*",
    ".expo",
    ".expo/*",
    "AppData",
    "AppData/*",
    "dist",
    "dist/*",
    "build",
    "build/*",
    "*.pyc",
    ".DS_Store",
]


def load_ignore_patterns(root: Optional[Path] = None) -> List[str]:
    target_root = (root or STATE.root).resolve()
    patterns = list(DEFAULT_IGNORE_PATTERNS)
    ignore_file = target_root / ".allyignore"

    if ignore_file.is_file():
        try:
            for line in ignore_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)
        except Exception:
            pass

    return patterns


def is_ignored(path: Path | str, root: Optional[Path] = None) -> bool:
    target_root = (root or STATE.root).resolve()
    p = Path(path)
    full_path = (target_root / p).resolve() if not p.is_absolute() else p.resolve()

    try:
        rel_str = str(full_path.relative_to(target_root)).replace("\\", "/")
    except ValueError:
        # Outside project boundary is always ignored/blocked
        return True

    name = full_path.name
    parts = full_path.parts

    patterns = load_ignore_patterns(target_root)
    for pattern in patterns:
        clean_pat = pattern.replace("\\", "/").rstrip("/")
        # Check against file name
        if fnmatch.fnmatch(name, clean_pat):
            return True
        # Check against relative path
        if fnmatch.fnmatch(rel_str, clean_pat) or fnmatch.fnmatch(rel_str, f"{clean_pat}/*"):
            return True
        # Check if any parent folder matches
        for part in parts:
            if fnmatch.fnmatch(part, clean_pat):
                return True

    return False


def create_default_allyignore(root: Optional[Path] = None):
    target_root = (root or STATE.root).resolve()
    ignore_file = target_root / ".allyignore"
    if not ignore_file.exists():
        content = """# Ally Ignore File (.allyignore)
# Prevents sensitive credentials from reaching the Gemini API and filters workspace bloat.

# Credentials & Secrets (CRITICAL)
.env*
*.env
.ssh/
*id_rsa*
*.pem
*.key
*.pfx
*.cert
*.crt

# Dependency & Cache Bloat
node_modules/
__pycache__/
.venv/
venv/
.cache/
.expo/
dist/
build/
AppData/
"""
        ignore_file.write_text(content, encoding="utf-8")
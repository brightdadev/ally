"""
Autonomous project memory manager for Ally (.ally/memory.md).
Author: Bright da dev
"""
import json
from pathlib import Path
from typing import Optional
from app.state import STATE


def get_memory_file(root: Optional[Path] = None) -> Path:
    target_root = (root or STATE.root).resolve()
    return target_root / ".ally" / "memory.md"


def _detect_workspace_stack(root: Path) -> str:
    """Auto-detect workspace technology stack from project manifest files."""
    stack_items = []

    # Node.js / JavaScript / TypeScript
    pkg_json = root / "package.json"
    if pkg_json.is_file():
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
            name = data.get("name", root.name)
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            key_libs = []
            for lib in ["react", "vite", "next", "vue", "typescript", "tailwindcss", "svelte", "express", "framer-motion", "lucide-react"]:
                if lib in deps:
                    key_libs.append(lib)
            libs_str = f" ({', '.join(key_libs)})" if key_libs else ""
            stack_items.append(f"Node.js app '{name}'{libs_str}")
        except Exception:
            stack_items.append("Node.js workspace")

    # Python
    if (root / "pyproject.toml").is_file() or (root / "requirements.txt").is_file():
        stack_items.append("Python environment")

    # Rust
    if (root / "Cargo.toml").is_file():
        stack_items.append("Rust workspace")

    # Go
    if (root / "go.mod").is_file():
        stack_items.append("Go module")

    return "; ".join(stack_items) if stack_items else "Standard codebase"


def ensure_memory(root: Optional[Path] = None) -> str:
    """Ensure .ally/memory.md exists, auto-generating it if absent."""
    target_root = (root or STATE.root).resolve()
    mem_file = get_memory_file(target_root)

    if mem_file.is_file():
        try:
            return mem_file.read_text(encoding="utf-8")
        except Exception:
            return ""

    # Auto-initialize memory bank on first workspace encounter
    try:
        mem_file.parent.mkdir(parents=True, exist_ok=True)
        detected_stack = _detect_workspace_stack(target_root)
        initial_content = f"""# Project Memory: {target_root.name}

> Maintained autonomously by Ally.
> Initialized on first workspace entry.

## Workspace Architecture
- **Project Root**: `{target_root.name}`
- **Identified Stack**: {detected_stack}

## Active Decisions & Milestones
- Workspace memory initialized autonomously by Ally.
"""
        mem_file.write_text(initial_content, encoding="utf-8")
        return initial_content
    except Exception:
        return ""


def read_memory(root: Optional[Path] = None) -> str:
    return ensure_memory(root)


def record_decision(decision: str, category: str = "Architecture", root: Optional[Path] = None) -> str:
    target_root = (root or STATE.root).resolve()
    mem_file = get_memory_file(target_root)
    mem_file.parent.mkdir(parents=True, exist_ok=True)

    header = ""
    if not mem_file.is_file():
        header = f"# Project Memory: {target_root.name}\n\n> Maintained autonomously by Ally.\n\n"

    entry = f"\n### [{category}] Decision\n- {decision.strip()}\n"

    try:
        current = mem_file.read_text(encoding="utf-8") if mem_file.is_file() else header
        mem_file.write_text(current + entry, encoding="utf-8")
        return f"OK: Recorded decision into {mem_file.name}"
    except Exception as e:
        return f"ERROR recording decision: {e}"
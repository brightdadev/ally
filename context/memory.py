"""
Project memory manager for Ally (.ally/memory.md).
Author: Bright da dev
"""
from pathlib import Path
from typing import Optional
from app.state import STATE


def get_memory_file(root: Optional[Path] = None) -> Path:
    target_root = (root or STATE.root).resolve()
    return target_root / ".ally" / "memory.md"


def read_memory(root: Optional[Path] = None) -> str:
    mem_file = get_memory_file(root)
    if mem_file.is_file():
        try:
            return mem_file.read_text(encoding="utf-8")
        except Exception as e:
            return f"ERROR reading memory: {e}"
    return ""


def record_decision(decision: str, category: str = "Architecture", root: Optional[Path] = None) -> str:
    mem_file = get_memory_file(root)
    mem_file.parent.mkdir(parents=True, exist_ok=True)

    header = ""
    if not mem_file.is_file():
        header = "# Project Memory\n\n> Maintained autonomously by Ally (Author: Bright da dev)\n\n"

    entry = f"\n### [{category}] Decision\n- {decision.strip()}\n"

    try:
        current = mem_file.read_text(encoding="utf-8") if mem_file.is_file() else header
        mem_file.write_text(current + entry, encoding="utf-8")
        return f"OK: Recorded decision into {mem_file.name}"
    except Exception as e:
        return f"ERROR recording decision: {e}"
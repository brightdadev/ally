"""
Step-by-step project preparation wizard for Ally.
Author: Bright da dev
"""
from pathlib import Path


def is_project_prepped(root: Path) -> bool:
    """Check if the target directory has a project brief."""
    return (root / "project.md").is_file()


def prep_project(
    root: Path,
    project_name: str,
    objective: str,
    tech_stack: str,
    conventions: str = "",
) -> Path:
    """
    Generate project.md and initialize .ally/memory.md in the project root.
    """
    root = root.resolve()
    brief_path = root / "project.md"
    memory_dir = root / ".ally"
    memory_path = memory_dir / "memory.md"

    # 1. Generate project.md
    brief_content = f"""# Project Brief: {project_name}

> Initialized by Ally (Author: Bright da dev)

## Objective
{objective}

## Tech Stack & Runtime
{tech_stack}

## Engineering Standards & Constraints
{conventions or "- Maintain clean, modular architecture.\n- Test before committing.\n- Defensive error handling."}
"""
    brief_path.write_text(brief_content, encoding="utf-8")

    # 2. Initialize project memory
    memory_dir.mkdir(parents=True, exist_ok=True)
    if not memory_path.exists():
        initial_memory = f"""# Project Memory: {project_name}

> Maintained autonomously by Ally.

## Current Phase
Initial Setup & Architecture.

## Key Decisions
- Project brief established via Ally project_prep.

## Active Conventions
- Sandboxed execution enforced.
"""
        memory_path.write_text(initial_memory, encoding="utf-8")

    return brief_path

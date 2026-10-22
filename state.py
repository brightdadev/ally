"""
State management module for Ally.
Author: Bright da dev
"""
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AllyState:
    root: Path = field(default_factory=Path.cwd)
    project_brief: str = ""
    mode: str = "plan"          # plan | accept | auto
    model: str = "gemini-2.5-flash"


STATE = AllyState()

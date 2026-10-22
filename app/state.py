"""
Runtime state container for Ally with dynamic model resolution.
Author: Bright da dev
"""
from dataclasses import dataclass, field
from pathlib import Path
from app.model.router import ROUTER


@dataclass
class AllyState:
    root: Path = field(default_factory=Path.cwd)
    project_brief: str = ""
    mode: str = "accept"        # plan | accept | auto
    model: str = field(default_factory=ROUTER.get_default_model)
    username: str = "developer"

    @property
    def available_models(self) -> list[str]:
        """Dynamically fetched from app/model/models.json."""
        return ROUTER.list_models()


STATE = AllyState()

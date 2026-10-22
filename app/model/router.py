"""
Dynamic Model Router and Registry for Ally.
Author: Bright da dev
"""
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

CONFIG_PATH = Path(__file__).parent / "models.json"


@dataclass
class ModelSpec:
    id: str
    name: str
    description: str
    tier: str


class ModelRouter:
    def __init__(self, config_path: Path = CONFIG_PATH):
        self.config_path = config_path
        self._models: Dict[str, ModelSpec] = {}
        self._default_model: str = "gemini-3.7-flash"
        self.reload()

    def reload(self) -> None:
        """Dynamically loads or reloads models.json from disk."""
        if not self.config_path.is_file():
            raise FileNotFoundError(f"Model configuration missing: {self.config_path}")

        data = json.loads(self.config_path.read_text(encoding="utf-8"))
        self._default_model = data.get("default_model", "gemini-3.7-flash")
        self._models.clear()

        for item in data.get("models", []):
            spec = ModelSpec(
                id=item["id"],
                name=item["name"],
                description=item.get("description", ""),
                tier=item.get("tier", "standard"),
            )
            self._models[spec.id] = spec

    def list_models(self) -> List[str]:
        """Return list of valid model IDs."""
        return list(self._models.keys())

    def get_default_model(self) -> str:
        return self._default_model

    def get_model(self, model_id: str) -> Optional[ModelSpec]:
        return self._models.get(model_id)

    def resolve(self, model_id: str) -> str:
        """
        Validate and resolve a model ID.
        Falls back to default if invalid model is requested.
        """
        if model_id in self._models:
            return model_id
        return self._default_model


ROUTER = ModelRouter()

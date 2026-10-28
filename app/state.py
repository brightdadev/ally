"""
Runtime state container for Ally with token usage analytics.
Author: Bright da dev
"""
from dataclasses import dataclass, field
from pathlib import Path
from app.model.router import ROUTER


@dataclass
class TokenTracker:
    prompt_tokens: int = 0
    candidate_tokens: int = 0
    total_tokens: int = 0
    total_requests: int = 0
    key1_requests: int = 0
    key2_requests: int = 0

    def add(self, prompt: int, candidate: int, total: int, key_index: int = 1):
        self.prompt_tokens += prompt
        self.candidate_tokens += candidate
        self.total_tokens += total
        self.total_requests += 1
        if key_index == 1:
            self.key1_requests += 1
        else:
            self.key2_requests += 1


@dataclass
class AllyState:
    root: Path = field(default_factory=Path.cwd)
    project_brief: str = ""
    mode: str = "auto"
    model: str = field(default_factory=ROUTER.get_default_model)
    username: str = "developer"
    active_key_index: int = 1
    tokens: TokenTracker = field(default_factory=TokenTracker)

    @property
    def available_models(self) -> list[str]:
        return ROUTER.list_models()


STATE = AllyState()

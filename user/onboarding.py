"""
Global user onboarding, identity, and dual API key management for Ally.
Author: Bright da dev
Version: 1.1.0
"""
import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path

CONFIG_DIR = Path.home() / ".ally"
PROFILE_FILE = CONFIG_DIR / "user_profile.json"


def _get_system_username() -> str:
    try:
        return os.getlogin() or Path.home().name
    except Exception:
        return "bright"


@dataclass
class UserProfile:
    username: str = ""
    role: str = "Lead Developer / Architect"
    default_model: str = "gemini-3.6-flash"
    default_mode: str = "auto"
    api_key_1: str = ""
    api_key_2: str = ""
    active_key_index: int = 1

    def __post_init__(self):
        if not self.username or self.username == "developer":
            self.username = _get_system_username()


def get_profile_path() -> Path:
    return PROFILE_FILE


def profile_exists() -> bool:
    return PROFILE_FILE.is_file()


def load_profile() -> UserProfile:
    if not profile_exists():
        return UserProfile()
    try:
        data = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
        k1 = data.get("api_key_1") or data.get("global_api_key", "")
        k2 = data.get("api_key_2", "")
        uname = data.get("username", "")
        if not uname or uname == "developer":
            uname = _get_system_username()

        return UserProfile(
            username=uname,
            role=data.get("role", "Lead Developer / Architect"),
            default_model=data.get("default_model", "gemini-3.6-flash"),
            default_mode=data.get("default_mode", "auto"),
            api_key_1=k1,
            api_key_2=k2,
            active_key_index=data.get("active_key_index", 1),
        )
    except Exception:
        return UserProfile()


def save_profile(profile: UserProfile) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    # Always preserve existing keys if the incoming profile object didn't populate them
    if profile_exists():
        try:
            existing = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
            if not profile.api_key_1 and existing.get("api_key_1"):
                profile.api_key_1 = existing["api_key_1"]
            if not profile.api_key_2 and existing.get("api_key_2"):
                profile.api_key_2 = existing["api_key_2"]
        except Exception:
            pass
    PROFILE_FILE.write_text(json.dumps(asdict(profile), indent=2), encoding="utf-8")
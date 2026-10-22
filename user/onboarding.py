"""
Global user onboarding and dual API key management for Ally.
Author: Bright da dev
"""
import json
from dataclasses import dataclass, asdict
from pathlib import Path

CONFIG_DIR = Path.home() / ".ally"
PROFILE_FILE = CONFIG_DIR / "user_profile.json"


@dataclass
class UserProfile:
    username: str = "developer"
    default_model: str = "gemini-3.6-flash"
    default_mode: str = "accept"
    api_key_1: str = ""
    api_key_2: str = ""
    active_key_index: int = 1


def get_profile_path() -> Path:
    return PROFILE_FILE


def profile_exists() -> bool:
    return PROFILE_FILE.is_file()


def load_profile() -> UserProfile:
    if not profile_exists():
        return UserProfile()
    try:
        data = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
        # Backwards compatibility check
        k1 = data.get("api_key_1") or data.get("global_api_key", "")
        k2 = data.get("api_key_2", "")
        return UserProfile(
            username=data.get("username", "developer"),
            default_model=data.get("default_model", "gemini-3.6-flash"),
            default_mode=data.get("default_mode", "accept"),
            api_key_1=k1,
            api_key_2=k2,
            active_key_index=data.get("active_key_index", 1),
        )
    except Exception:
        return UserProfile()


def save_profile(profile: UserProfile) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    PROFILE_FILE.write_text(json.dumps(asdict(profile), indent=2), encoding="utf-8")
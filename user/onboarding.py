"""
Global user onboarding and profile management for Ally.
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
    default_model: str = "gemini-2.5-flash"
    default_mode: str = "accept"
    global_api_key: str = ""


def get_profile_path() -> Path:
    return PROFILE_FILE


def profile_exists() -> bool:
    return PROFILE_FILE.is_file()


def load_profile() -> UserProfile:
    """Load user profile from ~/.ally/user_profile.json or return defaults."""
    if not profile_exists():
        return UserProfile()
    try:
        data = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
        return UserProfile(
            username=data.get("username", "developer"),
            default_model=data.get("default_model", "gemini-2.5-flash"),
            default_mode=data.get("default_mode", "accept"),
            global_api_key=data.get("global_api_key", ""),
        )
    except Exception:
        return UserProfile()


def save_profile(profile: UserProfile) -> None:
    """Persist user profile globally to ~/.ally/user_profile.json."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    PROFILE_FILE.write_text(json.dumps(asdict(profile), indent=2), encoding="utf-8")

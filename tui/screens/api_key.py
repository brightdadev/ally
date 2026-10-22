"""
API Key Setup Modal for Ally.
Author: Bright da dev
"""
import os
from pathlib import Path
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label
from user.onboarding import load_profile, save_profile
from app.state import STATE


class ApiKeyModal(ModalScreen[bool]):
    CSS = """
    ApiKeyModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }
    #api-dialog {
        width: 68;
        height: auto;
        border: thick #00d2ff;
        background: #141b24;
        padding: 1 2;
    }
    .title {
        text-style: bold;
        color: #00d2ff;
        text-align: center;
        margin-bottom: 1;
    }
    .hint {
        color: #8b9bb4;
        margin-bottom: 1;
    }
    .field-label {
        color: #e6edf3;
        margin-top: 1;
    }
    #api-buttons {
        margin-top: 1;
        align: right middle;
    }
    """

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Gemini API Key Required", classes="title"),
            Label("Get your free Gemini API key from: https://aistudio.google.com", classes="hint"),
            Label("Paste your GEMINI_API_KEY below:", classes="field-label"),
            Input(placeholder="AIzaSy...", password=True, id="input-api-key"),
            Horizontal(
                Button("Save & Start Ally", variant="primary", id="btn-save-key"),
                id="api-buttons",
            ),
            id="api-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save-key":
            key = self.query_one("#input-api-key", Input).value.strip()
            if not key:
                return

            # 1. Set in active runtime
            os.environ["GEMINI_API_KEY"] = key

            # 2. Write to local .env in project root
            env_file = STATE.root / ".env"
            env_file.write_text(f"GEMINI_API_KEY={key}\n", encoding="utf-8")

            # 3. Save globally in user profile
            profile = load_profile()
            profile.global_api_key = key
            save_profile(profile)

            self.dismiss(True)
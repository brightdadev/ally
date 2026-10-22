"""
Dual API Key Configuration Modal for Ally.
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
        width: 70;
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
        prof = load_profile()
        yield Vertical(
            Label("Dual Gemini API Key Management", classes="title"),
            Label("Configure up to 2 keys. Key 2 acts as automatic quota failover.", classes="hint"),
            Label("Primary API Key (Key 1 - Required):", classes="field-label"),
            Input(value=prof.api_key_1, placeholder="AIzaSy... (Key 1)", password=True, id="input-key-1"),
            Label("Backup API Key (Key 2 - Optional Quota Failover):", classes="field-label"),
            Input(value=prof.api_key_2, placeholder="AIzaSy... (Key 2)", password=True, id="input-key-2"),
            Horizontal(
                Button("Save Keys & Continue", variant="primary", id="btn-save-keys"),
                id="api-buttons",
            ),
            id="api-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save-keys":
            k1 = self.query_one("#input-key-1", Input).value.strip()
            k2 = self.query_one("#input-key-2", Input).value.strip()

            if not k1 and not k2:
                return

            profile = load_profile()
            profile.api_key_1 = k1
            profile.api_key_2 = k2
            save_profile(profile)

            # Update active runtime env
            if k1:
                os.environ["GEMINI_API_KEY"] = k1
                STATE.active_key_index = 1
            elif k2:
                os.environ["GEMINI_API_KEY"] = k2
                STATE.active_key_index = 2

            # Write to local .env
            env_file = STATE.root / ".env"
            env_lines = []
            if k1:
                env_lines.append(f"GEMINI_API_KEY_1={k1}")
                env_lines.append(f"GEMINI_API_KEY={k1}")
            if k2:
                env_lines.append(f"GEMINI_API_KEY_2={k2}")
            env_file.write_text("\n".join(env_lines) + "\n", encoding="utf-8")

            self.dismiss(True)
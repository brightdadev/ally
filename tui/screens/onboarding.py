"""
First-run Onboarding Modal for Ally.
Author: Bright da dev
"""
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select
from user.onboarding import UserProfile, save_profile
from app.model.router import ROUTER
from app.state import STATE


class OnboardingModal(ModalScreen[bool]):
    CSS = """
    OnboardingModal {
        align: center middle;
    }
    #dialog {
        width: 65;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    .title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
        text-align: center;
    }
    .field-label {
        margin-top: 1;
        color: $text;
    }
    #btn-container {
        margin-top: 1;
        align: right middle;
    }
    """

    def compose(self) -> ComposeResult:
        model_options = [(m, m) for m in ROUTER.list_models()]
        mode_options = [("Human-in-the-loop (accept)", "accept"), ("Read-only (plan)", "plan"), ("Autonomous (auto)", "auto")]

        yield Vertical(
            Label("Welcome to Ally - System Setup", classes="title"),
            Label("Author: Bright da dev", classes="field-label"),
            Label("Developer Name / Handle:", classes="field-label"),
            Input(value=STATE.username, id="input-username"),
            Label("Default Model:", classes="field-label"),
            Select(model_options, value=STATE.model, id="select-model"),
            Label("Default Mode:", classes="field-label"),
            Select(mode_options, value=STATE.mode, id="select-mode"),
            Horizontal(
                Button("Save Profile", variant="primary", id="btn-save"),
                id="btn-container",
            ),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            username = self.query_one("#input-username", Input).value.strip() or "developer"
            model = self.query_one("#select-model", Select).value
            mode = self.query_one("#select-mode", Select).value

            STATE.username = username
            STATE.model = str(model)
            STATE.mode = str(mode)

            profile = UserProfile(username=username, default_model=str(model), default_mode=str(mode))
            save_profile(profile)
            self.dismiss(True)
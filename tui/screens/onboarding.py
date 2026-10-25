"""
Compact Pure-Black Onboarding Profile Modal.
Author: Bright da dev
"""
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select
from user.onboarding import UserProfile, save_profile, load_profile
from app.model.router import ROUTER
from app.state import STATE


class OnboardingModal(ModalScreen[bool]):
    CSS = """
    OnboardingModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.85);
    }
    #dialog {
        width: 60;
        height: auto;
        border: solid #1f1f1f;
        background: #000000;
        padding: 1 2;
    }
    .title {
        text-style: bold;
        color: #ffffff;
        text-align: center;
        margin-bottom: 1;
    }
    .field-label {
        color: #777777;
        margin-top: 1;
    }
    #btn-container {
        margin-top: 1;
        align: right middle;
    }
    """

    def compose(self) -> ComposeResult:
        prof = load_profile()
        model_options = [(m, m) for m in ROUTER.list_models()]
        mode_options = [("Human-in-the-loop (accept)", "accept"), ("Read-only (plan)", "plan"), ("Autonomous (auto)", "auto")]

        yield Vertical(
            Label("Developer Profile", classes="title"),
            Label("Handle / Username:", classes="field-label"),
            Input(value=prof.username, id="input-username"),
            Label("Default Model:", classes="field-label"),
            Select(model_options, value=STATE.model, id="select-model"),
            Label("Default Operating Mode:", classes="field-label"),
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
            model = str(self.query_one("#select-model", Select).value)
            mode = str(self.query_one("#select-mode", Select).value)

            STATE.username = username
            STATE.model = model
            STATE.mode = mode

            prof = load_profile()
            prof.username = username
            prof.default_model = model
            prof.default_mode = mode
            save_profile(prof)
            self.dismiss(True)
"""
Quota Exhaustion and Model Switcher Modal.
Author: Bright da dev
"""
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Select
from app.model.router import ROUTER
from app.state import STATE


class QuotaModal(ModalScreen[str]):
    CSS = """
    QuotaModal {
        align: center middle;
    }
    #quota-dialog {
        width: 60;
        height: auto;
        border: thick $error;
        background: $surface;
        padding: 1 2;
    }
    .alert-title {
        text-style: bold;
        color: $error;
        text-align: center;
        margin-bottom: 1;
    }
    .message {
        color: $text;
        margin-bottom: 1;
    }
    #quota-actions {
        margin-top: 1;
        align: right middle;
    }
    """

    def __init__(self, current_model: str):
        super().__init__()
        self.current_model = current_model

    def compose(self) -> ComposeResult:
        options = [(m, m) for m in ROUTER.list_models() if m != self.current_model]
        if not options:
            options = [(m, m) for m in ROUTER.list_models()]

        yield Vertical(
            Label("API Quota / Rate-Limit Triggered", classes="alert-title"),
            Label(f"Model '{self.current_model}' hit its quota limit. Select an alternate model to continue:", classes="message"),
            Select(options, value=options[0][1], id="select-new-model"),
            Horizontal(
                Button("Switch & Continue", variant="error", id="btn-switch"),
                id="quota-actions",
            ),
            id="quota-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-switch":
            new_model = str(self.query_one("#select-new-model", Select).value)
            STATE.model = new_model
            self.dismiss(new_model)
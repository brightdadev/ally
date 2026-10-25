"""
Compact Pure-Black Model Selector Modal with Zero Leaked Colors.
Author: Bright da dev
"""
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Select
from app.model.router import ROUTER
from app.state import STATE


class ModelSelectModal(ModalScreen[str]):
    CSS = """
    ModelSelectModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.9);
    }
    #model-dialog {
        width: 58;
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
    .message {
        color: #777777;
        margin-bottom: 1;
    }
    #model-actions {
        margin-top: 1;
        align: right middle;
    }
    """

    def __init__(self, current_model: str, is_quota_alert: bool = False):
        super().__init__()
        self.current_model = current_model
        self.is_quota_alert = is_quota_alert

    def compose(self) -> ComposeResult:
        options = [(m, m) for m in ROUTER.list_models()]
        title_text = "API Quota Limit Reached" if self.is_quota_alert else "Select Active Model"
        msg_text = (
            f"Model '{self.current_model}' reached its limit. Choose another model:"
            if self.is_quota_alert
            else "Choose a Gemini model from your catalog:"
        )

        yield Vertical(
            Label(title_text, classes="title"),
            Label(msg_text, classes="message"),
            Select(options, value=self.current_model, id="select-active-model"),
            Horizontal(
                Button("Cancel", variant="default", id="btn-cancel"),
                Button("Select Model", variant="primary", id="btn-select"),
                id="model-actions",
            ),
            id="model-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-select":
            chosen = str(self.query_one("#select-active-model", Select).value)
            STATE.model = chosen
            self.dismiss(chosen)
        elif event.button.id == "btn-cancel":
            self.dismiss("")
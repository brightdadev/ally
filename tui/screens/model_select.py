"""
Context-Aware Model Selection Modal.
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
        background: rgba(0, 0, 0, 0.7);
    }
    #model-dialog {
        width: 60;
        height: auto;
        border: thick #00d2ff;
        background: #141b24;
        padding: 1 2;
    }
    #model-dialog.quota-alert {
        border: thick #ff4757;
    }
    .title {
        text-style: bold;
        color: #00d2ff;
        text-align: center;
        margin-bottom: 1;
    }
    .title.quota-title {
        color: #ff4757;
    }
    .message {
        color: #e6edf3;
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
        dialog_class = "quota-alert" if self.is_quota_alert else ""
        title_class = "title quota-title" if self.is_quota_alert else "title"

        title_text = "API Quota Limit Reached" if self.is_quota_alert else "Select Active Model"
        msg_text = (
            f"Model '{self.current_model}' hit an API quota/rate limit. Select another model to continue:"
            if self.is_quota_alert
            else "Choose a Gemini model from your catalog:"
        )
        btn_variant = "error" if self.is_quota_alert else "primary"
        btn_text = "Switch & Retry" if self.is_quota_alert else "Select Model"

        yield Vertical(
            Label(title_text, classes=title_class),
            Label(msg_text, classes="message"),
            Select(options, value=self.current_model, id="select-active-model"),
            Horizontal(
                Button("Cancel", variant="default", id="btn-cancel"),
                Button(btn_text, variant=btn_variant, id="btn-select"),
                id="model-actions",
            ),
            id="model-dialog",
            classes=dialog_class,
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-select":
            chosen = str(self.query_one("#select-active-model", Select).value)
            STATE.model = chosen
            self.dismiss(chosen)
        elif event.button.id == "btn-cancel":
            self.dismiss("")
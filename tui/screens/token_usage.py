"""
Token Usage Analytics Modal for Ally (Pure Black Edition).
Author: Bright da dev
"""
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static
from app.state import STATE


class TokenUsageModal(ModalScreen[bool]):
    CSS = """
    TokenUsageModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.85);
    }
    #usage-dialog {
        width: 65;
        height: auto;
        border: solid #222222;
        background: #000000;
        padding: 1 2;
    }
    .title {
        text-style: bold;
        color: #ffffff;
        text-align: center;
        margin-bottom: 1;
    }
    .metric-row {
        height: 1;
        margin-bottom: 1;
    }
    .metric-label {
        width: 32;
        color: #666666;
    }
    .metric-val {
        color: #00ff66;
        text-style: bold;
    }
    .section-header {
        color: #888888;
        margin-top: 1;
        margin-bottom: 1;
    }
    #usage-buttons {
        margin-top: 1;
        align: right middle;
    }
    """

    def compose(self) -> ComposeResult:
        t = STATE.tokens
        yield Vertical(
            Label("Token Consumption & API Key Metrics", classes="title"),
            Horizontal(Label("Requests Completed:", classes="metric-label"), Static(str(t.total_requests), classes="metric-val"), classes="metric-row"),
            Horizontal(Label("Prompt Tokens:", classes="metric-label"), Static(f"{t.prompt_tokens:,}", classes="metric-val"), classes="metric-row"),
            Horizontal(Label("Completion Tokens:", classes="metric-label"), Static(f"{t.candidate_tokens:,}", classes="metric-val"), classes="metric-row"),
            Horizontal(Label("Total Token Volume:", classes="metric-label"), Static(f"{t.total_tokens:,}", classes="metric-val"), classes="metric-row"),
            Label("--- Dual Key Distribution ---", classes="section-header"),
            Horizontal(Label("Primary Key (1) Requests:", classes="metric-label"), Static(str(t.key1_requests), classes="metric-val"), classes="metric-row"),
            Horizontal(Label("Backup Key (2) Requests:", classes="metric-label"), Static(str(t.key2_requests), classes="metric-val"), classes="metric-row"),
            Horizontal(Label("Active Key Index:", classes="metric-label"), Static(f"Key #{STATE.active_key_index}", classes="metric-val"), classes="metric-row"),
            Horizontal(
                Button("Close", variant="default", id="btn-close"),
                id="usage-buttons",
            ),
            id="usage-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(True)
"""
Token Usage Analytics Modal for Ally.
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
        background: rgba(0, 0, 0, 0.7);
    }
    #usage-dialog {
        width: 65;
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
    .metric-row {
        height: 1;
        margin-bottom: 1;
    }
    .metric-label {
        width: 32;
        color: #8b9bb4;
    }
    .metric-val {
        color: #00ff88;
        text-style: bold;
    }
    #usage-buttons {
        margin-top: 1;
        align: right middle;
    }
    """

    def compose(self) -> ComposeResult:
        t = STATE.tokens
        yield Vertical(
            Label("Ally Token Analytics & Key Usage", classes="title"),
            Horizontal(Label("Total Requests Completed:", classes="metric-label"), Static(str(t.total_requests), classes="metric-val"), classes="metric-row"),
            Horizontal(Label("Prompt Tokens Ingested:", classes="metric-label"), Static(f"{t.prompt_tokens:,}", classes="metric-val"), classes="metric-row"),
            Horizontal(Label("Completion Tokens Generated:", classes="metric-label"), Static(f"{t.candidate_tokens:,}", classes="metric-val"), classes="metric-row"),
            Horizontal(Label("Total Token Consumption:", classes="metric-label"), Static(f"[bold cyan]{t.total_tokens:,}[/]", classes="metric-val"), classes="metric-row"),
            Label("--- Dual API Key Distribution ---", classes="metric-label"),
            Horizontal(Label("Requests on Primary Key (1):", classes="metric-label"), Static(str(t.key1_requests), classes="metric-val"), classes="metric-row"),
            Horizontal(Label("Requests on Backup Key (2):", classes="metric-label"), Static(str(t.key2_requests), classes="metric-val"), classes="metric-row"),
            Horizontal(Label("Currently Active Key:", classes="metric-label"), Static(f"Key #{STATE.active_key_index}", classes="metric-val"), classes="metric-row"),
            Horizontal(
                Button("Close", variant="primary", id="btn-close"),
                id="usage-buttons",
            ),
            id="usage-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(True)
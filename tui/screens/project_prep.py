"""
Project Preparation Wizard Modal for Ally.
Author: Bright da dev
"""
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label
from user.project_prep import prep_project
from app.state import STATE


class ProjectPrepModal(ModalScreen[bool]):
    CSS = """
    ProjectPrepModal {
        align: center middle;
    }
    #prep-dialog {
        width: 70;
        height: auto;
        border: thick $success;
        background: $surface;
        padding: 1 2;
    }
    .title {
        text-style: bold;
        color: $success;
        margin-bottom: 1;
        text-align: center;
    }
    .field-label {
        margin-top: 1;
        color: $text;
    }
    #prep-buttons {
        margin-top: 1;
        align: right middle;
    }
    """

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Ally Project Preparation Wizard", classes="title"),
            Label("Project Name:", classes="field-label"),
            Input(value=STATE.root.name, id="prep-name"),
            Label("Primary Objective / Brief:", classes="field-label"),
            Input(placeholder="What is this system building?", id="prep-objective"),
            Label("Tech Stack & Dependencies:", classes="field-label"),
            Input(placeholder="e.g., Python 3.14, Textual, Google GenAI", id="prep-stack"),
            Label("Engineering Constraints:", classes="field-label"),
            Input(placeholder="e.g., Sandboxed, no external databases", id="prep-conventions"),
            Horizontal(
                Button("Cancel", variant="default", id="btn-cancel"),
                Button("Initialize Project", variant="success", id="btn-init"),
                id="prep-buttons",
            ),
            id="prep-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-init":
            name = self.query_one("#prep-name", Input).value.strip() or STATE.root.name
            objective = self.query_one("#prep-objective", Input).value.strip() or "General development."
            stack = self.query_one("#prep-stack", Input).value.strip() or "Python"
            conventions = self.query_one("#prep-conventions", Input).value.strip()

            prep_project(STATE.root, name, objective, stack, conventions)
            brief_file = STATE.root / "project.md"
            if brief_file.is_file():
                STATE.project_brief = brief_file.read_text(encoding="utf-8")
            self.dismiss(True)
        elif event.button.id == "btn-cancel":
            self.dismiss(False)
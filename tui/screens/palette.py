"""
Theme Palette Selector Modal with Live Theme Inheritance.
Author: Bright da dev
"""
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Select
from tui.theme import THEMES
from user.onboarding import load_profile, save_profile


class ThemePaletteModal(ModalScreen[str]):
    CSS = """
    ThemePaletteModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.9);
    }
    #palette-dialog {
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
    .hint {
        color: #666666;
        margin-bottom: 1;
    }
    #palette-actions {
        margin-top: 1;
        align: right middle;
    }
    """

    def compose(self) -> ComposeResult:
        prof = load_profile()
        options = [(v["name"], k) for k, v in THEMES.items()]
        current = prof.accent_theme if prof.accent_theme in THEMES else "cobalt"

        yield Vertical(
            Label("Accent Theme Palette", classes="title"),
            Label("All UI colors outside pure black will adapt to this theme:", classes="hint"),
            Select(options, value=current, id="select-theme"),
            Horizontal(
                Button("Cancel", variant="default", id="btn-cancel"),
                Button("Apply Theme", variant="primary", id="btn-apply"),
                id="palette-actions",
            ),
            id="palette-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-apply":
            selected = str(self.query_one("#select-theme", Select).value)
            prof = load_profile()
            prof.accent_theme = selected
            save_profile(prof)
            self.dismiss(selected)
        elif event.button.id == "btn-cancel":
            self.dismiss("")
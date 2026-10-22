"""
Modernized Textual Terminal User Interface for Ally.
Author: Bright da dev
"""
import asyncio
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from textual.app import App, ComposeResult
from textual.widgets import Input, RichLog, Static, Header, Footer
from textual.containers import Vertical, Horizontal
from textual.binding import Binding

from app import agent
from app.state import STATE
from app.model.router import ROUTER
from user.onboarding import profile_exists, load_profile
from tui.screens import OnboardingModal, ProjectPrepModal, QuotaModal


class AllyApp(App):
    CSS = """
    Screen {
        layout: vertical;
        background: $background;
    }
    #top-bar {
        height: 1;
        background: $boost;
        padding: 0 1;
    }
    .badge {
        margin-right: 2;
        text-style: bold;
    }
    #log {
        height: 1fr;
        border: round $primary;
        background: $surface;
        padding: 0 1;
    }
    #prompt-bar {
        height: 3;
        margin-top: 0;
    }
    """

    BINDINGS = [
        Binding("ctrl+o", "open_onboarding", "Onboarding"),
        Binding("ctrl+p", "open_prep", "Project Prep"),
        Binding("ctrl+m", "switch_model", "Change Model"),
        Binding("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.chat = None
        self._approval_future = None
        self._busy = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Horizontal(
            Static(f"[cyan]User:[/] {STATE.username}", id="badge-user", classes="badge"),
            Static(f"[green]Model:[/] {STATE.model}", id="badge-model", classes="badge"),
            Static(f"[yellow]Mode:[/] {STATE.mode.upper()}", id="badge-mode", classes="badge"),
            Static(f"[dim]Root:[/] {STATE.root.name}", id="badge-root", classes="badge"),
            id="top-bar",
        )
        yield RichLog(id="log", wrap=True, markup=True)
        yield Vertical(
            Input(placeholder="Ask Ally anything, or type /help... (Ctrl+P: Prep, Ctrl+M: Model)", id="prompt"),
            id="prompt-bar",
        )
        yield Footer()

    def on_mount(self):
        self.query_one("#prompt").focus()

        # Load user profile if present
        if profile_exists():
            prof = load_profile()
            STATE.username = prof.username
            STATE.model = prof.default_model
            STATE.mode = prof.default_mode
            self._refresh_status()
        else:
            self.action_open_onboarding()

        self._boot()

    def _boot(self):
        log = self.query_one("#log", RichLog)
        if not os.environ.get("GEMINI_API_KEY"):
            log.write("[bold red]GEMINI_API_KEY not found.[/]")
            log.write("[yellow]Please add GEMINI_API_KEY to your .env file and restart.[/]")
            return

        try:
            self.chat = agent.new_chat()
            log.write(f"[bold green]Ally v1.0.1 Ready.[/] [dim]Engine authored by Bright da dev[/dim]")
            log.write(f"[cyan]Active Model:[/] [bold]{STATE.model}[/] | [yellow]Mode:[/] [bold]{STATE.mode}[/]")
            log.write("[dim]Press [bold]Ctrl+P[/] for Project Prep Wizard, or type [bold]/help[/] for commands.[/dim]\n")
        except Exception as e:
            log.write(f"[red]Boot initialization failed: {e}[/]")

    def _refresh_status(self):
        self.query_one("#badge-user", Static).update(f"[cyan]User:[/] {STATE.username}")
        self.query_one("#badge-model", Static).update(f"[green]Model:[/] {STATE.model}")
        self.query_one("#badge-mode", Static).update(f"[yellow]Mode:[/] {STATE.mode.upper()}")
        self.query_one("#badge-root", Static).update(f"[dim]Root:[/] {STATE.root.name}")

    def action_open_onboarding(self):
        def _on_closed(saved: bool):
            if saved:
                self._refresh_status()
                self._reset_chat("Profile updated.")
        self.push_screen(OnboardingModal(), _on_closed)

    def action_open_prep(self):
        def _on_closed(prepped: bool):
            if prepped:
                self._refresh_status()
                self._reset_chat("Project brief and memory initialized.")
        self.push_screen(ProjectPrepModal(), _on_closed)

    def action_switch_model(self):
        def _on_switched(new_model: str):
            if new_model:
                STATE.model = new_model
                self._refresh_status()
                self._reset_chat(f"Switched model to {new_model}.")
        self.push_screen(QuotaModal(STATE.model), _on_switched)

    def _reset_chat(self, msg: str = ""):
        log = self.query_one("#log", RichLog)
        try:
            self.chat = agent.new_chat()
            if msg:
                log.write(f"[green]{msg}[/]")
        except Exception as e:
            log.write(f"[red]Chat reset failed: {e}[/]")

    async def request_approval(self, name: str, args: dict) -> bool:
        log = self.query_one("#log", RichLog)
        path = args.get("path", "?")
        if name == "write_file":
            body = args.get("content", "")
            preview = body[:600] + ("\n... (truncated)" if len(body) > 600 else "")
            log.write(f"[yellow bold]WRITE FILE:[/] {path}\n[dim]{preview}[/]")
        elif name == "patch_file":
            log.write(f"[yellow bold]PATCH FILE:[/] {path}\n[dim]--- OLD ---\n{args.get('old','')[:300]}\n--- NEW ---\n{args.get('new','')[:300]}[/]")
        elif name == "delete_file":
            log.write(f"[red bold]DELETE FILE:[/] {path}")
        else:
            log.write(f"[yellow bold]{name}:[/] {args}")

        log.write("[bold yellow]Approve this change? (y/n)[/]")
        self._approval_future = asyncio.get_running_loop().create_future()
        return await self._approval_future

    async def on_input_submitted(self, event: Input.Submitted):
        text = event.value.strip()
        event.input.value = ""
        if not text:
            return

        if self._approval_future and not self._approval_future.done():
            self._approval_future.set_result(text.lower() in ("y", "yes"))
            return

        log = self.query_one("#log", RichLog)

        if text.startswith("/"):
            self._handle_command(text, log)
            return

        if self.chat is None:
            log.write("[red]Ally not initialized. Check GEMINI_API_KEY in .env.[/]")
            return

        if self._busy:
            log.write("[yellow]Ally is currently executing. Please wait...[/]")
            return

        log.write(f"\n[bold cyan]{STATE.username}:[/] {text}")
        log.write("[bold green]Ally:[/]")

        def _stream(chunk: str):
            log.write(chunk)

        self._busy = True
        try:
            await agent.run_turn(self.chat, text, _stream, self.request_approval)
        except agent.QuotaException:
            log.write("[bold red][!] Quota / Rate-limit exceeded on current model.[/]")
            self.action_switch_model()
        except Exception as e:
            log.write(f"[red]Execution error: {e}[/]")
        finally:
            self._busy = False

    def _handle_command(self, text: str, log: RichLog):
        parts = text.split(maxsplit=1)
        cmd = parts[0]
        arg = parts[1] if len(parts) > 1 else ""

        if cmd == "/help":
            log.write(
                "[bold cyan]Available Commands:[/]\n"
                "  /prep            Open the step-by-step Project Prep Wizard\n"
                "  /model <name>    Switch active model on the fly\n"
                "  /models          List all dynamically loaded models from models.json\n"
                "  /plan            Set mode to read-only planning\n"
                "  /accept          Set mode to human-in-the-loop approval\n"
                "  /auto            Set mode to autonomous writing\n"
                "  /status          Display active state and loaded brief\n"
                "  /reset           Restart chat session with fresh context\n"
                "  /quit            Exit application"
            )
        elif cmd == "/prep":
            self.action_open_prep()
        elif cmd == "/models":
            log.write(f"[cyan]Loaded models in catalog:[/] {', '.join(ROUTER.list_models())}")
        elif cmd == "/model":
            if not arg:
                log.write(f"Active model: {STATE.model}")
                return
            if arg in ROUTER.list_models():
                STATE.model = arg
                self._refresh_status()
                self._reset_chat(f"Switched model to {arg}.")
            else:
                log.write(f"[red]Unknown model '{arg}'. Available: {ROUTER.list_models()}[/]")
        elif cmd in ("/plan", "/accept", "/auto"):
            STATE.mode = cmd[1:]
            self._refresh_status()
            log.write(f"[green]Mode updated to {STATE.mode.upper()}[/]")
        elif cmd == "/status":
            log.write(f"User: {STATE.username} | Mode: {STATE.mode} | Model: {STATE.model} | Root: {STATE.root}")
        elif cmd == "/reset":
            self._reset_chat("Session context reset.")
        elif cmd == "/quit":
            self.exit()
        else:
            log.write(f"[red]Unknown command '{cmd}'. Type /help for options.[/]")


def run():
    AllyApp().run()


if __name__ == "__main__":
    run()
"""
Terminal-Native IDE for Ally.
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
from textual.widgets import (
    Input, RichLog, Static, Header, Footer, DirectoryTree, Label
)
from textual.containers import Vertical, Horizontal
from textual.binding import Binding

from app import agent
from app.state import STATE
from app.model.router import ROUTER
from user.onboarding import profile_exists, load_profile
from tui.screens import OnboardingModal, ProjectPrepModal, ModelSelectModal, ApiKeyModal


class WorkspaceTree(DirectoryTree):
    def filter_paths(self, paths):
        ignored = {".git", "__pycache__", ".venv", "venv", ".egg-info", "dist", "build"}
        return [p for p in paths if p.name not in ignored]


class AllyApp(App):
    CSS = """
    Screen {
        layout: vertical;
        background: #0f141c;
    }
    #ide-layout {
        height: 1fr;
        layout: horizontal;
    }
    #sidebar {
        width: 32;
        background: #141b24;
        border-right: solid #2a3749;
    }
    #sidebar.hidden {
        display: none;
    }
    #sidebar-header {
        height: 2;
        background: #1c2633;
        color: #00d2ff;
        text-style: bold;
        padding: 0 1;
        content-align: center middle;
    }
    #file-tree {
        height: 1fr;
        background: transparent;
        padding: 0 1;
    }
    #main-panel {
        width: 1fr;
        height: 1fr;
        layout: vertical;
    }
    #top-breadcrumbs {
        height: 1;
        background: #18222f;
        padding: 0 1;
        border-bottom: solid #2a3749;
    }
    .badge {
        margin-right: 2;
        text-style: bold;
    }
    #log {
        height: 1fr;
        background: #0d1117;
        border: none;
        padding: 0 1;
    }
    #prompt-container {
        height: 3;
        background: #161f2c;
        border-top: solid #00d2ff;
        padding: 0 1;
    }
    #prompt {
        background: transparent;
        border: none;
    }
    """

    BINDINGS = [
        Binding("f1", "show_help", "Help", priority=True),
        Binding("f2", "switch_model", "Model Select", priority=True),
        Binding("f3", "open_prep", "Project Prep", priority=True),
        Binding("ctrl+b", "toggle_sidebar", "Toggle Explorer", priority=True),
        Binding("ctrl+k", "open_api_key", "API Key"),
        Binding("ctrl+o", "open_onboarding", "Profile"),
        Binding("ctrl+q", "quit", "Quit", priority=True),
    ]

    def __init__(self):
        super().__init__()
        self.chat = None
        self._approval_future = None
        self._busy = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Horizontal(
            Vertical(
                Label("PROJECT EXPLORER", id="sidebar-header"),
                WorkspaceTree(str(STATE.root), id="file-tree"),
                id="sidebar",
            ),
            Vertical(
                Horizontal(
                    Static(f"[cyan]User:[/] {STATE.username}", id="badge-user", classes="badge"),
                    Static(f"[green]Model (F2):[/] {STATE.model}", id="badge-model", classes="badge"),
                    Static(f"[yellow]Mode:[/] {STATE.mode.upper()}", id="badge-mode", classes="badge"),
                    Static(f"[dim]Root:[/] {STATE.root.name}", id="badge-root", classes="badge"),
                    id="top-breadcrumbs",
                ),
                RichLog(id="log", wrap=True, markup=True),
                Vertical(
                    Input(placeholder="Type prompt or command (/help, /prep, /key)... [F2: Model, Ctrl+B: Explorer]", id="prompt"),
                    id="prompt-container",
                ),
                id="main-panel",
            ),
            id="ide-layout",
        )
        yield Footer()

    def on_mount(self):
        self.query_one("#prompt").focus()

        # 1. Load global profile if available
        if profile_exists():
            prof = load_profile()
            STATE.username = prof.username
            STATE.model = prof.default_model
            STATE.mode = prof.default_mode
            if prof.global_api_key and not os.environ.get("GEMINI_API_KEY"):
                os.environ["GEMINI_API_KEY"] = prof.global_api_key
            self._refresh_status()

        # 2. Check for API key; if missing, launch ApiKeyModal immediately
        if not os.environ.get("GEMINI_API_KEY"):
            self.action_open_api_key()
        else:
            self._boot()

    def _boot(self):
        log = self.query_one("#log", RichLog)
        if not os.environ.get("GEMINI_API_KEY"):
            return

        try:
            self.chat = agent.new_chat()
            log.write(f"[bold green]Ally Terminal IDE v1.0.1 Online.[/] [dim]Engine by Bright da dev[/dim]")
            log.write(f"[cyan]Model:[/] [bold]{STATE.model}[/] | [yellow]Mode:[/] [bold]{STATE.mode}[/] | [bold]Root:[/] {STATE.root.name}")
            log.write("[dim]Shortcuts: [bold]F2[/]: Select Model | [bold]F3[/]: Project Prep | [bold]Ctrl+K[/]: Set API Key | [bold]Ctrl+B[/]: Explorer[/dim]\n")
        except Exception as e:
            log.write(f"[red]Chat init error: {e}[/]")

    def _refresh_status(self):
        self.query_one("#badge-user", Static).update(f"[cyan]User:[/] {STATE.username}")
        self.query_one("#badge-model", Static).update(f"[green]Model (F2):[/] {STATE.model}")
        self.query_one("#badge-mode", Static).update(f"[yellow]Mode:[/] {STATE.mode.upper()}")
        self.query_one("#badge-root", Static).update(f"[dim]Root:[/] {STATE.root.name}")

    def action_toggle_sidebar(self):
        sidebar = self.query_one("#sidebar")
        sidebar.toggle_class("hidden")

    def action_open_api_key(self):
        def _on_key_set(saved: bool):
            if saved:
                log = self.query_one("#log", RichLog)
                log.write("[bold green]GEMINI_API_KEY configured successfully.[/]")
                self._boot()
        self.push_screen(ApiKeyModal(), _on_key_set)

    def action_switch_model(self):
        def _on_switched(new_model: str):
            if new_model:
                STATE.model = new_model
                self._refresh_status()
                self._reset_chat(f"Active model set to {new_model}.")
        self.push_screen(ModelSelectModal(STATE.model, is_quota_alert=False), _on_switched)

    def action_open_prep(self):
        def _on_closed(prepped: bool):
            if prepped:
                self._refresh_status()
                self._reset_chat("Project brief and memory initialized.")
                tree = self.query_one("#file-tree", WorkspaceTree)
                tree.reload()
        self.push_screen(ProjectPrepModal(), _on_closed)

    def action_open_onboarding(self):
        def _on_closed(saved: bool):
            if saved:
                self._refresh_status()
                self._reset_chat("Profile preferences applied.")
        self.push_screen(OnboardingModal(), _on_closed)

    def action_show_help(self):
        log = self.query_one("#log", RichLog)
        log.write(
            "[bold cyan]Ally IDE Keyboard & Slash Commands:[/]\n"
            "  [bold]F1[/]              Display command guide\n"
            "  [bold]F2[/]              Open Model Selection\n"
            "  [bold]F3[/]              Open Project Prep Wizard\n"
            "  [bold]Ctrl+K[/]          Configure GEMINI_API_KEY\n"
            "  [bold]Ctrl+B[/]          Toggle Project Explorer Sidebar\n"
            "  [bold]Ctrl+O[/]          Edit Developer Profile\n"
            "  [bold]Ctrl+Q[/]          Quit Ally\n"
            "  /key              Set Gemini API key\n"
            "  /model <name>     Switch active model\n"
            "  /models           List available catalog models\n"
            "  /plan             Set mode to read-only planning\n"
            "  /accept           Set mode to human-in-the-loop approval\n"
            "  /auto             Set mode to autonomous writing\n"
            "  /reset            Reset chat conversation"
        )

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected):
        prompt = self.query_one("#prompt", Input)
        rel_path = event.path.relative_to(STATE.root)
        prompt.value = f"{prompt.value} @{rel_path} ".strip() + " "
        prompt.focus()

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
            log.write(f"[yellow bold]WRITE:[/] {path}\n[dim]{preview}[/]")
        elif name == "patch_file":
            log.write(f"[yellow bold]PATCH:[/] {path}\n[dim]--- OLD ---\n{args.get('old','')[:300]}\n--- NEW ---\n{args.get('new','')[:300]}[/]")
        elif name == "delete_file":
            log.write(f"[red bold]DELETE:[/] {path}")
        else:
            log.write(f"[yellow bold]{name}:[/] {args}")

        log.write("[bold yellow]Approve this modification? (y/n)[/]")
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
            log.write("[red]Ally not initialized. Press Ctrl+K to enter your GEMINI_API_KEY.[/]")
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
            tree = self.query_one("#file-tree", WorkspaceTree)
            tree.reload()
        except agent.QuotaException:
            log.write("[bold red][!] Quota / Rate-limit reached for current model.[/]")
            def _on_switched(new_model: str):
                if new_model:
                    STATE.model = new_model
                    self._refresh_status()
                    self._reset_chat(f"Switched model to {new_model}.")
            self.push_screen(ModelSelectModal(STATE.model, is_quota_alert=True), _on_switched)
        except Exception as e:
            log.write(f"[red]Execution error: {e}[/]")
        finally:
            self._busy = False

    def _handle_command(self, text: str, log: RichLog):
        parts = text.split(maxsplit=1)
        cmd = parts[0]
        arg = parts[1] if len(parts) > 1 else ""

        if cmd == "/help":
            self.action_show_help()
        elif cmd == "/key":
            self.action_open_api_key()
        elif cmd == "/prep":
            self.action_open_prep()
        elif cmd == "/models":
            log.write(f"[cyan]Loaded models:[/] {', '.join(ROUTER.list_models())}")
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
            log.write(f"[red]Unknown command '{cmd}'. Type /help or press F1.[/]")


def run():
    AllyApp().run()


if __name__ == "__main__":
    run()
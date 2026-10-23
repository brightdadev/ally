"""
Terminal-Native IDE for Ally v1.0.4.
Author: Bright da dev
"""
import asyncio
import os
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from rich.markdown import Markdown
from rich.panel import Panel

from textual.app import App, ComposeResult
from textual.widgets import (
    Input, RichLog, Static, Header, Footer, DirectoryTree, Label
)
from textual.containers import Vertical, Horizontal
from textual.binding import Binding
from textual import work

from app import agent
from app.state import STATE
from app.model.router import ROUTER
from user.onboarding import profile_exists, load_profile
from tui.screens import (
    OnboardingModal,
    ProjectPrepModal,
    ModelSelectModal,
    ApiKeyModal,
    TokenUsageModal,
)


def format_clean_error(err: Exception, current_model: str) -> Panel:
    err_str = str(err)
    err_lower = err_str.lower()

    if "429" in err_str or "resource_exhausted" in err_lower:
        limit_note = ""
        if "limit: 20" in err_str:
            limit_note = " (20 requests/day free-tier limit)"
        elif "limit:" in err_str:
            try:
                val = err_str.split("limit:")[1].split(",")[0].strip()
                limit_note = f" (limit: {val})"
            except Exception:
                pass

        body = (
            f"[bold red]Quota Limit Reached for {current_model}[/]{limit_note}\n\n"
            f"[dim yellow]Action:[/] Press [bold cyan]F2[/] to switch model, or [bold cyan]Ctrl+K[/] to add a Backup API Key (Key 2)."
        )
        return Panel(body, title="[bold red]API Quota (429)[/]", border_style="red", padding=(1, 2))

    if "503" in err_str or "unavailable" in err_lower:
        body = (
            f"[bold red]Google Servers Overloaded (503)[/]\n\n"
            f"Model [bold]{current_model}[/] is currently experiencing high demand on Google's side.\n"
            f"[dim yellow]Action:[/] Retry in a few seconds or press [bold cyan]F2[/] to switch models."
        )
        return Panel(body, title="[bold red]Service Unavailable (503)[/]", border_style="red", padding=(1, 2))

    if "10053" in err_str:
        body = (
            "[bold yellow]Connection Reset by Host[/]\n\n"
            "The local socket connection dropped. Session has been automatically reconnected."
        )
        return Panel(body, title="[bold yellow]Network Reset[/]", border_style="yellow", padding=(1, 2))

    clean_msg = err_str
    if "'message':" in err_str:
        try:
            clean_msg = err_str.split("'message':")[1].split("',")[0].strip(" '\"")
        except Exception:
            clean_msg = err_str[:140]
    else:
        clean_msg = err_str[:140]

    body = f"[bold red]API Notice:[/] {clean_msg}"
    return Panel(body, title="[bold red]Execution Notice[/]", border_style="red", padding=(1, 2))


class WorkspaceTree(DirectoryTree):
    def filter_paths(self, paths):
        ignored = {".git", "__pycache__", ".venv", "venv", ".egg-info", "dist", "build"}
        return [p for p in paths if p.name not in ignored]


class AllyApp(App):
    TITLE = "Ally"
    SUB_TITLE = "Terminal IDE v1.0.4"

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
        width: 28;
        background: #141b24;
        border-right: solid #2a3749;
    }
    #sidebar.hidden {
        display: none;
    }
    #process-panel {
        width: 38;
        background: #141b24;
        border-left: solid #2a3749;
    }
    #process-panel.hidden {
        display: none;
    }
    .panel-header {
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
    #process-log {
        height: 1fr;
        background: transparent;
        padding: 0 1;
        color: #8b9bb4;
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
    #badge-status {
        color: #00ff88;
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
        Binding("f4", "open_usage", "Token Usage", priority=True),
        Binding("ctrl+b", "toggle_sidebar", "Explorer", priority=True),
        Binding("ctrl+p", "toggle_process", "Process Box", priority=True),
        Binding("ctrl+k", "open_api_key", "API Keys"),
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
                Label("PROJECT EXPLORER", classes="panel-header"),
                WorkspaceTree(str(STATE.root), id="file-tree"),
                id="sidebar",
            ),
            Vertical(
                Horizontal(
                    Static("[bold green]● READY[/]", id="badge-status", classes="badge"),
                    Static(f"[cyan]User:[/] {STATE.username}", id="badge-user", classes="badge"),
                    Static(f"[green]Model (F2):[/] {STATE.model}", id="badge-model", classes="badge"),
                    Static(f"[yellow]Mode:[/] {STATE.mode.upper()}", id="badge-mode", classes="badge"),
                    Static(f"[magenta]Key:[/] #{STATE.active_key_index}", id="badge-key", classes="badge"),
                    Static(f"[dim]Root:[/] {STATE.root.name}", id="badge-root", classes="badge"),
                    id="top-breadcrumbs",
                ),
                RichLog(id="log", wrap=True, markup=True),
                Vertical(
                    Input(placeholder="Type prompt or command (/help, /prep, /usage, /key)... [F4: Usage, F2: Model, Ctrl+B: Explorer]", id="prompt"),
                    id="prompt-container",
                ),
                id="main-panel",
            ),
            Vertical(
                Label("PROCESS MONITOR", classes="panel-header"),
                RichLog(id="process-log", wrap=True, markup=True),
                id="process-panel",
            ),
            id="ide-layout",
        )
        yield Footer()

    def on_mount(self):
        self.query_one("#prompt").focus()

        if profile_exists():
            prof = load_profile()
            STATE.username = prof.username
            if prof.default_model in ROUTER.list_models():
                STATE.model = prof.default_model
            else:
                STATE.model = ROUTER.get_default_model()
            STATE.mode = prof.default_mode
            if prof.api_key_1 and not os.environ.get("GEMINI_API_KEY"):
                os.environ["GEMINI_API_KEY"] = prof.api_key_1
            self._refresh_status()

        self._log_process("System booted. Ready.")

        if not os.environ.get("GEMINI_API_KEY") and not agent.get_active_key():
            self.action_open_api_key()
        else:
            self._boot()

    def _boot(self):
        log = self.query_one("#log", RichLog)
        if not os.environ.get("GEMINI_API_KEY") and not agent.get_active_key():
            return

        try:
            agent.reset_client()
            self.chat = agent.new_chat()
            log.write(f"[bold green]Ally Terminal IDE v1.0.4 Online.[/] [dim]Engine by Bright da dev[/dim]")
            log.write(f"[cyan]Model:[/] [bold]{STATE.model}[/] | [yellow]Mode:[/] [bold]{STATE.mode}[/] | [magenta]Active Key:[/] #{STATE.active_key_index}")
            log.write("[dim]Shortcuts: [bold]F2[/]: Model Select | [bold]F3[/]: Project Prep | [bold]F4[/]: Token Usage | [bold]Ctrl+K[/]: Set 2 Keys[/dim]\n")
            self._log_process(f"Session active: {STATE.model} (Key #{STATE.active_key_index})")
        except Exception as e:
            log.write(format_clean_error(e, STATE.model))
            self._log_process("[red]Boot error[/]")

    def _refresh_status(self):
        self.query_one("#badge-user", Static).update(f"[cyan]User:[/] {STATE.username}")
        self.query_one("#badge-model", Static).update(f"[green]Model (F2):[/] {STATE.model}")
        self.query_one("#badge-mode", Static).update(f"[yellow]Mode:[/] {STATE.mode.upper()}")
        self.query_one("#badge-key", Static).update(f"[magenta]Key:[/] #{STATE.active_key_index}")
        self.query_one("#badge-root", Static).update(f"[dim]Root:[/] {STATE.root.name}")

    def _set_activity(self, state: str):
        badge = self.query_one("#badge-status", Static)
        if state == "thinking":
            badge.update("[bold magenta]⠋ THINKING...[/]")
        elif state == "streaming":
            badge.update("[bold cyan]● STREAMING...[/]")
        elif state == "executing":
            badge.update("[bold yellow]⚙ EXECUTING...[/]")
        else:
            badge.update("[bold green]● READY[/]")

    def _log_process(self, message: str):
        plog = self.query_one("#process-log", RichLog)
        timestamp = datetime.now().strftime("%H:%M:%S")
        clean_msg = message[:30] + ("..." if len(message) > 30 else "")
        plog.write(f"[dim]{timestamp}[/] {clean_msg}")

    def action_toggle_sidebar(self):
        self.query_one("#sidebar").toggle_class("hidden")

    def action_toggle_process(self):
        self.query_one("#process-panel").toggle_class("hidden")

    def action_open_api_key(self):
        def _on_key_set(saved: bool):
            if saved:
                log = self.query_one("#log", RichLog)
                log.write("[bold green]Dual API Keys updated successfully.[/]")
                self._log_process("API Keys updated.")
                self._boot()
        self.push_screen(ApiKeyModal(), _on_key_set)

    def action_open_usage(self):
        self.push_screen(TokenUsageModal())

    def action_switch_model(self):
        def _on_switched(new_model: str):
            if new_model:
                STATE.model = new_model
                self._refresh_status()
                self._reset_chat(f"Active model set to {new_model}.")
                self._log_process(f"Switched to {new_model}")
        self.push_screen(ModelSelectModal(STATE.model, is_quota_alert=False), _on_switched)

    def action_open_prep(self):
        def _on_closed(prepped: bool):
            if prepped:
                self._refresh_status()
                self._reset_chat("Project brief and memory initialized.")
                tree = self.query_one("#file-tree", WorkspaceTree)
                tree.reload()
                self._log_process("Project prep executed.")
        self.push_screen(ProjectPrepModal(), _on_closed)

    def action_open_onboarding(self):
        def _on_closed(saved: bool):
            if saved:
                self._refresh_status()
                self._reset_chat("Profile preferences applied.")
                self._log_process("Profile saved.")
        self.push_screen(OnboardingModal(), _on_closed)

    def action_show_help(self):
        log = self.query_one("#log", RichLog)
        log.write(
            "[bold cyan]Ally IDE Keyboard & Slash Commands:[/]\n"
            "  [bold]F1[/]              Display command guide\n"
            "  [bold]F2[/]              Open Model Selection\n"
            "  [bold]F3[/]              Open Project Prep Wizard\n"
            "  [bold]F4[/]              Open Token Analytics & Key Usage\n"
            "  [bold]Ctrl+B[/]          Toggle Project Explorer Sidebar\n"
            "  [bold]Ctrl+P[/]          Toggle Process & Trace Box\n"
            "  [bold]Ctrl+K[/]          Configure Dual GEMINI_API_KEYs (Key 1 & Key 2)\n"
            "  [bold]Ctrl+O[/]          Edit Developer Profile\n"
            "  [bold]Ctrl+Q[/]          Quit Ally\n"
            "  /usage            View Token Analytics\n"
            "  /key              Set Gemini API keys\n"
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
            agent.reset_client()
            self.chat = agent.new_chat()
            if msg:
                log.write(f"[green]{msg}[/]")
        except Exception as e:
            log.write(format_clean_error(e, STATE.model))

    async def request_approval(self, name: str, args: dict) -> bool:
        log = self.query_one("#log", RichLog)
        path = args.get("path", "?")
        if name == "write_file":
            body = args.get("content", "")
            preview = body[:600] + ("\n... (truncated)" if len(body) > 600 else "")
            panel = Panel(preview, title=f"[bold yellow]WRITE:[/] {path}", border_style="yellow")
            log.write(panel)
        elif name == "patch_file":
            preview = f"--- OLD ---\n{args.get('old','')[:250]}\n--- NEW ---\n{args.get('new','')[:250]}"
            panel = Panel(preview, title=f"[bold yellow]PATCH:[/] {path}", border_style="yellow")
            log.write(panel)
        elif name == "delete_file":
            panel = Panel(f"Delete file: {path}", title="[bold red]DELETE[/]", border_style="red")
            log.write(panel)
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

        if text.startswith("/"):
            log = self.query_one("#log", RichLog)
            self._handle_command(text, log)
            return

        if self.chat is None:
            self.query_one("#log", RichLog).write("[red]Ally not initialized. Press Ctrl+K to enter your API Keys.[/]")
            return

        if self._busy:
            self.query_one("#log", RichLog).write("[yellow]Ally is busy. Wait for current turn to complete.[/]")
            return

        self._execute_turn_worker(text)

    @work(exclusive=True)
    async def _execute_turn_worker(self, text: str):
        log = self.query_one("#log", RichLog)
        log.write(f"\n[bold cyan]{STATE.username}:[/] {text}")
        self._log_process(f"Prompt: '{text[:20]}...'")

        self._busy = True
        self._set_activity("thinking")

        buffer = []

        def _on_token(chunk: str):
            buffer.append(chunk)

        def _on_step(step_name: str):
            self._log_process(step_name)

        try:
            await agent.run_turn(
                self.chat,
                text,
                _on_token,
                self.request_approval,
                on_step=_on_step,
            )
            full_reply = "".join(buffer)
            if full_reply:
                md_rendered = Markdown(full_reply)
                panel = Panel(
                    md_rendered,
                    title=f"[bold green]Ally ({STATE.model})[/]",
                    border_style="cyan",
                    padding=(1, 2),
                )
                log.write(panel)
            tree = self.query_one("#file-tree", WorkspaceTree)
            tree.reload()
            self._refresh_status()
        except Exception as e:
            error_card = format_clean_error(e, STATE.model)
            log.write(error_card)
            self._log_process("[red]Execution notice[/]")

            try:
                agent.reset_client()
                self.chat = agent.new_chat()
            except Exception:
                pass
        finally:
            self._busy = False
            self._set_activity("ready")

    def _handle_command(self, text: str, log: RichLog):
        parts = text.split(maxsplit=1)
        cmd = parts[0]
        arg = parts[1] if len(parts) > 1 else ""

        if cmd == "/help":
            self.action_show_help()
        elif cmd == "/usage":
            self.action_open_usage()
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
            log.write(f"User: {STATE.username} | Mode: {STATE.mode} | Model: {STATE.model} | Active Key: #{STATE.active_key_index} | Root: {STATE.root}")
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
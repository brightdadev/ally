"""
Cleaned-Up Pitch-Black Terminal IDE for Ally with Friendly Human Phrasing.
Author: Bright da dev
Version: 1.1.0
"""
import asyncio
import os
import subprocess
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
from app.ignore import is_ignored, create_default_allyignore
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
            limit_note = " (20 requests/day limit)"
        elif "limit:" in err_str:
            try:
                val = err_str.split("limit:")[1].split(",")[0].strip()
                limit_note = f" (limit: {val})"
            except Exception:
                pass

        body = (
            f"[bold #ff4444]Daily Quota Limit Reached for {current_model}[/]{limit_note}\n\n"
            f"[#666666]What to do:[/] Press [bold #ffffff]F2[/] to switch model, or press [bold #ffffff]Ctrl+K[/] to configure Backup Key (Key 2)."
        )
        return Panel(body, title="[#ff4444]Quota Limit (429)[/]", border_style="#331111", padding=(1, 2))

    if "503" in err_str or "unavailable" in err_lower:
        body = (
            f"[bold #ff4444]Google Servers Are Currently Busy (503)[/]\n\n"
            f"The server is experiencing high demand. Ally retried automatically, but the servers are still saturated.\n"
            f"[#666666]What to do:[/] Press [bold #ffffff]F2[/] to select a faster model, or ask your question again in a moment."
        )
        return Panel(body, title="[#ff4444]Server Busy (503)[/]", border_style="#331111", padding=(1, 2))

    if "10053" in err_str:
        body = (
            "[bold #ffaa00]Connection Reset[/]\n\n"
            "The network connection dropped briefly. Your session is reconnected and ready."
        )
        return Panel(body, title="[#ffaa00]Network Reset[/]", border_style="#332200", padding=(1, 2))

    clean_msg = err_str
    if "'message':" in err_str:
        try:
            clean_msg = err_str.split("'message':")[1].split("',")[0].strip(" '\"")
        except Exception:
            clean_msg = err_str[:160]
    else:
        clean_msg = err_str[:160]

    body = f"[bold #ff4444]Notice:[/] {clean_msg}"
    return Panel(body, title="[#ff4444]Execution Notice[/]", border_style="#331111", padding=(1, 2))


class WorkspaceTree(DirectoryTree):
    def filter_paths(self, paths):
        root = STATE.root.resolve()
        return [p for p in paths if not is_ignored(p, root)]


class AllyApp(App):
    TITLE = "Ally"
    SUB_TITLE = "Engineering Partner"

    CSS = """
    Screen {
        layout: vertical;
        background: #000000;
    }
    Header {
        background: #000000;
        color: #555555;
        dock: top;
        height: 1;
        border-bottom: solid #1a1a1a;
    }
    Footer {
        background: #000000;
        color: #555555;
        dock: bottom;
        height: 1;
        border-top: solid #1a1a1a;
    }
    .footer--key {
        background: #111111;
        color: #888888;
    }
    .footer--description {
        color: #555555;
    }
    #ide-layout {
        height: 1fr;
        layout: horizontal;
        background: #000000;
    }
    #sidebar {
        width: 26;
        background: #000000;
        border-right: solid #1a1a1a;
    }
    #sidebar.hidden {
        display: none;
    }
    #process-panel {
        width: 38;
        background: #000000;
        border-left: solid #1a1a1a;
    }
    #process-panel.hidden {
        display: none;
    }
    .panel-header {
        height: 1;
        background: #000000;
        color: #555555;
        text-style: bold;
        padding: 0 1;
        border-bottom: solid #1a1a1a;
    }
    #file-tree {
        height: 1fr;
        background: #000000;
        padding: 0 1;
        color: #777777;
    }
    #process-log {
        height: 1fr;
        background: #000000;
        padding: 0 1;
        color: #555555;
    }
    #main-panel {
        width: 1fr;
        height: 1fr;
        layout: vertical;
        background: #000000;
    }
    #top-breadcrumbs {
        height: 1;
        background: #000000;
        padding: 0 1;
        border-bottom: solid #1a1a1a;
    }
    .badge-pill {
        margin-right: 2;
        color: #555555;
    }
    #log {
        height: 1fr;
        background: #000000;
        border: none;
        padding: 1 2;
    }
    #thinking-indicator {
        height: 1;
        background: #000000;
        color: #00ccff;
        padding: 0 2;
        display: none;
    }
    #thinking-indicator.active {
        display: block;
    }
    #composer-container {
        height: 3;
        background: #000000;
        border-top: solid #1a1a1a;
        padding: 0 1;
    }
    #prompt {
        background: #000000;
        border: none;
        color: #ffffff;
    }
    #prompt:focus {
        border: none;
    }
    """

    BINDINGS = [
        Binding("f1", "show_help", "Help", priority=True),
        Binding("f2", "switch_model", "Model", priority=True),
        Binding("f3", "open_prep", "Prep", priority=True),
        Binding("f4", "open_usage", "Usage", priority=True),
        Binding("ctrl+b", "toggle_sidebar", "Explorer", priority=True),
        Binding("ctrl+p", "toggle_process", "Process", priority=True),
        Binding("ctrl+k", "open_api_key", "Keys"),
        Binding("ctrl+o", "open_onboarding", "Profile"),
        Binding("ctrl+q", "quit", "Quit", priority=True),
    ]

    def __init__(self):
        super().__init__()
        self.chat = None
        self._approval_future = None
        self._busy = False
        self._anim_timer = None
        self._anim_frame = 0

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Horizontal(
            # Left: Explorer
            Vertical(
                Label("EXPLORER", classes="panel-header"),
                WorkspaceTree(str(STATE.root), id="file-tree"),
                id="sidebar",
            ),
            # Center: Main Workspace
            Vertical(
                Horizontal(
                    Static("[bold #00ffaa]Ally is ready[/]", id="badge-status", classes="badge-pill"),
                    Static(f"model: [bold #ffffff]{STATE.model}[/]", id="badge-model", classes="badge-pill"),
                    Static(f"mode: [bold #00ffaa]partner[/]", id="badge-mode", classes="badge-pill"),
                    Static(f"key: [bold #aaaaaa]{STATE.active_key_index}/2[/]", id="badge-key", classes="badge-pill"),
                    Static(f"root: [dim #888888]{STATE.root.name}[/]", id="badge-root", classes="badge-pill"),
                    id="top-breadcrumbs",
                ),
                RichLog(id="log", wrap=True, highlight=False, markup=True),
                Static("", id="thinking-indicator"),
                Vertical(
                    Input(placeholder="Talk with Ally as your engineering partner (or /help)...", id="prompt"),
                    id="composer-container",
                ),
                id="main-panel",
            ),
            # Right: Process Monitor
            Vertical(
                Label("PROCESS MONITOR", classes="panel-header"),
                RichLog(id="process-log", wrap=True, highlight=False, markup=True),
                id="process-panel",
            ),
            id="ide-layout",
        )
        yield Footer()

    def on_mount(self):
        self.query_one("#prompt").focus()

        # Initialize .allyignore defense in project root if missing
        create_default_allyignore(STATE.root)

        if profile_exists():
            prof = load_profile()
            STATE.username = prof.username
            if prof.default_model in ROUTER.list_models():
                STATE.model = prof.default_model
            else:
                STATE.model = ROUTER.get_default_model()
            STATE.mode = prof.default_mode or "auto"
            if prof.api_key_1 and not os.environ.get("GEMINI_API_KEY"):
                os.environ["GEMINI_API_KEY"] = prof.api_key_1
            self._refresh_status()

        self._log_process("Ally is ready")

        if not os.environ.get("GEMINI_API_KEY") and not agent.get_active_key():
            self.action_open_api_key()
        else:
            self._boot()

    def _get_git_branch() -> str:
        try:
            r = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=str(STATE.root),
                capture_output=True,
                text=True,
                timeout=2,
            )
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip()
        except Exception:
            pass
        return ""

    def _boot(self):
        log = self.query_one("#log", RichLog)
        if not os.environ.get("GEMINI_API_KEY") and not agent.get_active_key():
            return

        try:
            agent.reset_client()
            self.chat = agent.new_chat()

            branch = self._get_git_branch()
            branch_str = f" [dim #555555]({branch})[/]" if branch else ""
            mode_badge = "[bold #00ffaa]Autonomous Partner[/]" if STATE.mode == "auto" else f"[bold #aaaaaa]{STATE.mode}[/]"
            key_info = f"Dual-Key (Active: #{STATE.active_key_index})"

            welcome_body = (
                f"[bold #ffffff]ALLY[/]  [dim #666666]v1.1.0 — Engineering Partner[/]\n\n"
                f"  [dim #777777]Workspace:[/]   [bold #ffffff]{STATE.root.name}[/]{branch_str}\n"
                f"  [dim #777777]Mode:[/]        {mode_badge} [dim #555555](collaborative first, zero unsolicited edits)[/]\n"
                f"  [dim #777777]Security:[/]    [bold #00ffaa].allyignore active[/] [dim #555555](secrets & .env protected)[/]\n"
                f"  [dim #777777]Model:[/]       [bold #ffffff]{STATE.model}[/] [dim #555555]•[/] [dim #888888]{key_info}[/]\n\n"
                f"[dim #888888]Ready when you are. Tell me what we're building, or explore shortcuts:[/]\n"
                f"[dim #555555]  F1[/] Guide   [dim #555555]F2[/] Models   [dim #555555]F4[/] Usage   [dim #555555]Ctrl+B[/] Files   [dim #555555]Ctrl+P[/] Processes"
            )

            welcome_card = Panel(
                welcome_body,
                title="[bold #ffffff] Welcome Home [/]",
                border_style="#222222",
                padding=(1, 3),
            )
            log.write(welcome_card)
            log.write("\n")
            self._log_process(f"Active model: {STATE.model}")
        except Exception as e:
            log.write(format_clean_error(e, STATE.model))
            self._log_process("Startup notice: model unavailable")

    def _refresh_status(self):
        mode_label = "[bold #00ffaa]partner[/]" if STATE.mode == "auto" else f"[bold #cccccc]{STATE.mode}[/]"
        self.query_one("#badge-model", Static).update(f"model: [bold #ffffff]{STATE.model}[/]")
        self.query_one("#badge-mode", Static).update(f"mode: {mode_label}")
        self.query_one("#badge-key", Static).update(f"key: [bold #aaaaaa]{STATE.active_key_index}/2[/]")
        self.query_one("#badge-root", Static).update(f"root: [dim #888888]{STATE.root.name}[/]")

    def _start_thinking_animation(self, label: str = "Ally is thinking of a response"):
        indicator = self.query_one("#thinking-indicator", Static)
        indicator.add_class("active")
        self._anim_frame = 0

        frames = [
            "[bold #00ffaa]●[/] [dim #444444]○ ○[/]",
            "[dim #444444]○[/] [bold #00ccff]●[/] [dim #444444]○[/]",
            "[dim #444444]○ ○[/] [bold #ffff00]●[/]",
            "[dim #444444]○[/] [bold #00ccff]●[/] [dim #444444]○[/]",
        ]

        def _tick():
            if not self._busy:
                return
            idx = self._anim_frame % len(frames)
            indicator.update(f"{frames[idx]} [dim #aaaaaa]{label}...[/]")
            self._anim_frame += 1

        _tick()
        if self._anim_timer:
            self._anim_timer.stop()
        self._anim_timer = self.set_interval(0.35, _tick)

    def _stop_thinking_animation(self):
        if self._anim_timer:
            self._anim_timer.stop()
            self._anim_timer = None
        indicator = self.query_one("#thinking-indicator", Static)
        indicator.remove_class("active")
        indicator.update("")

    def _set_activity(self, state: str):
        badge = self.query_one("#badge-status", Static)
        if state == "thinking":
            badge.update("[bold #ffff00]Ally is thinking...[/]")
        elif state == "streaming":
            badge.update("[bold #00d2ff]Ally is writing...[/]")
        elif state == "executing":
            badge.update("[bold #ffaa00]Ally is working...[/]")
        else:
            badge.update("[bold #00ffaa]Ally is ready[/]")

    def _log_process(self, message: str):
        plog = self.query_one("#process-log", RichLog)
        timestamp = datetime.now().strftime("%H:%M:%S")
        clean_msg = message[:34] + ("..." if len(message) > 34 else "")
        plog.write(f"[dim #555555]{timestamp}[/]  {clean_msg}")

    def action_toggle_sidebar(self):
        self.query_one("#sidebar").toggle_class("hidden")

    def action_toggle_process(self):
        self.query_one("#process-panel").toggle_class("hidden")

    def action_open_api_key(self):
        def _on_key_set(saved: bool):
            if saved:
                log = self.query_one("#log", RichLog)
                log.write("[bold #00ffaa]API Keys configured successfully.[/]\n")
                self._log_process("API keys updated")
                self._boot()
        self.push_screen(ApiKeyModal(), _on_key_set)

    def action_open_usage(self):
        self.push_screen(TokenUsageModal())

    def action_switch_model(self):
        def _on_switched(new_model: str):
            if new_model:
                STATE.model = new_model
                self._refresh_status()
                self._reset_chat(f"Switched model to {new_model}.")
                self._log_process(f"Switched model: {new_model}")
        self.push_screen(ModelSelectModal(STATE.model, is_quota_alert=False), _on_switched)

    def action_open_prep(self):
        def _on_closed(prepped: bool):
            if prepped:
                self._refresh_status()
                self._reset_chat("Project brief and memory initialized.")
                tree = self.query_one("#file-tree", WorkspaceTree)
                tree.reload()
                self._log_process("Project brief initialized")
        self.push_screen(ProjectPrepModal(), _on_closed)

    def action_open_onboarding(self):
        def _on_closed(saved: bool):
            if saved:
                self._refresh_status()
                self._reset_chat("Profile preferences applied.")
                self._log_process("Profile updated")
        self.push_screen(OnboardingModal(), _on_closed)

    def action_show_help(self):
        log = self.query_one("#log", RichLog)
        help_panel = Panel(
            "[bold #ffffff]Command Palette & Shortcuts:[/]\n\n"
            "  [bold #ffffff]F1[/]              Help guide\n"
            "  [bold #ffffff]F2[/]              Switch active model\n"
            "  [bold #ffffff]F3[/]              Project preparation wizard\n"
            "  [bold #ffffff]F4[/]              Token usage & key analytics\n"
            "  [bold #ffffff]Ctrl+B[/]          Toggle project explorer\n"
            "  [bold #ffffff]Ctrl+P[/]          Toggle process monitor\n"
            "  [bold #ffffff]Ctrl+K[/]          Configure dual API keys\n"
            "  [bold #ffffff]Ctrl+O[/]          Developer profile settings\n"
            "  [bold #ffffff]Ctrl+Q[/]          Exit Ally\n\n"
            "  /auto             Autonomous Partner mode (seamless execution)\n"
            "  /plan             Read-only planning mode\n"
            "  /accept           Prompt approval mode\n"
            "  /usage            View token analytics\n"
            "  /model <name>     Switch active model\n"
            "  /reset            Reset chat conversation\n"
            "  /quit             Exit Ally",
            title="[#555555]commands[/]",
            border_style="#1a1a1a",
            padding=(1, 2),
        )
        log.write(help_panel)

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
                log.write(f"[dim #555555]{msg}[/]\n")
        except Exception as e:
            log.write(format_clean_error(e, STATE.model))

    async def request_approval(self, name: str, args: dict) -> bool:
        log = self.query_one("#log", RichLog)
        path = args.get("path", args.get("command", "?"))
        panel = Panel(f"Action: {name}\nTarget: {path}", title="[#ffaa00]Approval Request[/]", border_style="#ffaa00")
        log.write(panel)
        log.write("[bold #ffaa00]Approve action? (y/n)[/]")
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
            self.query_one("#log", RichLog).write("[#ff4444]Ally is not initialized. Press Ctrl+K to enter your API key.[/]\n")
            return

        if self._busy:
            self.query_one("#log", RichLog).write("[#ffaa00]Ally is currently working on your request. Please wait a moment...[/]\n")
            return

        self._execute_turn_worker(text)

    @work(exclusive=True)
    async def _execute_turn_worker(self, text: str):
        log = self.query_one("#log", RichLog)

        log.write(f"\n[bold #00ccff]you[/] [dim #555555]›[/] [bold #ffffff]{text}[/]\n")
        self._log_process(f"Prompt: '{text[:22]}...'")

        self._busy = True
        self._set_activity("thinking")
        self._start_thinking_animation("Ally is thinking of a response")

        buffer = []

        def _on_token(chunk: str):
            buffer.append(chunk)

        def _on_step(step_name: str):
            if "running" in step_name.lower() or "writing" in step_name.lower() or "updating" in step_name.lower():
                self._set_activity("executing")
                self._start_thinking_animation(step_name)
            elif "thinking" in step_name.lower():
                self._set_activity("thinking")
                self._start_thinking_animation(step_name)
            self._log_process(step_name)

        try:
            await agent.run_turn(
                self.chat,
                text,
                _on_token,
                self.request_approval,
                on_step=_on_step,
            )
            self._stop_thinking_animation()
            full_reply = "".join(buffer)
            if full_reply:
                md_rendered = Markdown(full_reply)
                panel = Panel(
                    md_rendered,
                    title=f"[bold #ffffff]ally[/] [dim #555555]({STATE.model})[/]",
                    border_style="#1a1a1a",
                    padding=(1, 2),
                )
                log.write(panel)
            tree = self.query_one("#file-tree", WorkspaceTree)
            tree.reload()
            self._refresh_status()
        except Exception as e:
            self._stop_thinking_animation()
            error_card = format_clean_error(e, STATE.model)
            log.write(error_card)
            self._log_process("Turn failed: server busy")
            # CRITICAL: Do NOT reset self.chat so conversation memory is completely preserved
        finally:
            self._stop_thinking_animation()
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
            log.write(f"[#555555]Available Models:[/] {', '.join(ROUTER.list_models())}\n")
        elif cmd == "/model":
            if not arg:
                log.write(f"Active model: {STATE.model}\n")
                return
            if arg in ROUTER.list_models():
                STATE.model = arg
                self._refresh_status()
                self._reset_chat(f"Switched model to {arg}.")
            else:
                log.write(f"[#ff4444]Unknown model '{arg}'. Available: {ROUTER.list_models()}[/]\n")
        elif cmd in ("/plan", "/accept", "/auto"):
            STATE.mode = cmd[1:]
            self._refresh_status()
            log.write(f"[#00ffaa]Mode updated to {STATE.mode}[/]\n")
        elif cmd == "/status":
            branch = self._get_git_branch()
            log.write(f"User: {STATE.username} | Mode: {STATE.mode} | Model: {STATE.model} | Branch: {branch or 'none'} | Key: #{STATE.active_key_index}\n")
        elif cmd == "/reset":
            self._reset_chat("Conversation context reset.")
        elif cmd == "/quit":
            self.exit()
        else:
            log.write(f"[#ff4444]Unknown command '{cmd}'. Type /help or press F1.[/]\n")


def run():
    AllyApp().run()


if __name__ == "__main__":
    run()
"""
Cleaned-Up Pitch-Black Terminal IDE for Ally.
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
            limit_note = " (20 requests/day limit)"
        elif "limit:" in err_str:
            try:
                val = err_str.split("limit:")[1].split(",")[0].strip()
                limit_note = f" (limit: {val})"
            except Exception:
                pass

        body = (
            f"[bold #ff4444]Quota Limit Reached for {current_model}[/]{limit_note}\n\n"
            f"[#666666]Action:[/] Press [bold #ffffff]F2[/] to switch model, or [bold #ffffff]Ctrl+K[/] to configure Backup Key (Key 2)."
        )
        return Panel(body, title="[#ff4444]API Quota (429)[/]", border_style="#331111", padding=(1, 2))

    if "503" in err_str or "unavailable" in err_lower:
        body = (
            f"[bold #ff4444]Service Unavailable (503)[/]\n\n"
            f"Model [bold]{current_model}[/] is currently experiencing high server demand.\n"
            f"[#666666]Action:[/] Retry in a few seconds or press [bold #ffffff]F2[/] to select another model."
        )
        return Panel(body, title="[#ff4444]Service Unavailable (503)[/]", border_style="#331111", padding=(1, 2))

    if "10053" in err_str:
        body = (
            "[bold #ffaa00]Connection Reset by Host[/]\n\n"
            "The network socket connection dropped. Session has been automatically reconnected."
        )
        return Panel(body, title="[#ffaa00]Network Reset[/]", border_style="#332200", padding=(1, 2))

    clean_msg = err_str
    if "'message':" in err_str:
        try:
            clean_msg = err_str.split("'message':")[1].split("',")[0].strip(" '\"")
        except Exception:
            clean_msg = err_str[:140]
    else:
        clean_msg = err_str[:140]

    body = f"[bold #ff4444]Error:[/] {clean_msg}"
    return Panel(body, title="[#ff4444]Execution Error[/]", border_style="#331111", padding=(1, 2))


class WorkspaceTree(DirectoryTree):
    def filter_paths(self, paths):
        ignored = {".git", "__pycache__", ".venv", "venv", ".egg-info", "dist", "build"}
        return [p for p in paths if p.name not in ignored]


class AllyApp(App):
    TITLE = "Ally"
    SUB_TITLE = "Terminal IDE"

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
        width: 36;
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
                    Static("[bold #00ff66][ready][/]", id="badge-status", classes="badge-pill"),
                    Static(f"model: [bold #ffffff]{STATE.model}[/]", id="badge-model", classes="badge-pill"),
                    Static(f"mode: [bold #cccccc]{STATE.mode}[/]", id="badge-mode", classes="badge-pill"),
                    Static(f"key: [bold #aaaaaa]{STATE.active_key_index}/2[/]", id="badge-key", classes="badge-pill"),
                    Static(f"root: [dim #555555]{STATE.root.name}[/]", id="badge-root", classes="badge-pill"),
                    id="top-breadcrumbs",
                ),
                RichLog(id="log", wrap=True, markup=True),
                Vertical(
                    Input(placeholder="Ask Ally... (/help, F2 model, F4 stats, ^B explorer, ^P process)", id="prompt"),
                    id="composer-container",
                ),
                id="main-panel",
            ),
            # Right: Process Log
            Vertical(
                Label("PROCESS", classes="panel-header"),
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

        self._log_process("[init] system ready")

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
            log.write(f"[bold #ffffff]Ally Terminal[/] [dim #555555]v1.0.4[/] · [dim #555555]model:[/] [bold #ffffff]{STATE.model}[/] · [dim #555555]root:[/] [bold #aaaaaa]{STATE.root.name}[/]")
            log.write("[dim #444444]shortcuts: F2 model · F3 prep · F4 usage · Ctrl+K keys · Ctrl+B explorer · Ctrl+P process[/]\n")
            self._log_process(f"[active] {STATE.model}")
        except Exception as e:
            log.write(format_clean_error(e, STATE.model))
            self._log_process("[error] init failed")

    def _refresh_status(self):
        self.query_one("#badge-model", Static).update(f"model: [bold #ffffff]{STATE.model}[/]")
        self.query_one("#badge-mode", Static).update(f"mode: [bold #cccccc]{STATE.mode}[/]")
        self.query_one("#badge-key", Static).update(f"key: [bold #aaaaaa]{STATE.active_key_index}/2[/]")
        self.query_one("#badge-root", Static).update(f"root: [dim #555555]{STATE.root.name}[/]")

    def _set_activity(self, state: str):
        badge = self.query_one("#badge-status", Static)
        if state == "thinking":
            badge.update("[bold #ffff00][thinking][/]")
        elif state == "streaming":
            badge.update("[bold #00d2ff][streaming][/]")
        elif state == "executing":
            badge.update("[bold #ffaa00][executing][/]")
        else:
            badge.update("[bold #00ff66][ready][/]")

    def _log_process(self, message: str):
        plog = self.query_one("#process-log", RichLog)
        timestamp = datetime.now().strftime("%H:%M:%S")
        clean_msg = message[:30] + ("..." if len(message) > 30 else "")
        plog.write(f"[dim #555555]{timestamp}[/]  {clean_msg}")

    def action_toggle_sidebar(self):
        self.query_one("#sidebar").toggle_class("hidden")

    def action_toggle_process(self):
        self.query_one("#process-panel").toggle_class("hidden")

    def action_open_api_key(self):
        def _on_key_set(saved: bool):
            if saved:
                log = self.query_one("#log", RichLog)
                log.write("[bold #00ff66]API Keys configured successfully.[/]\n")
                self._log_process("[config] keys updated")
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
                self._log_process(f"[switch] {new_model}")
        self.push_screen(ModelSelectModal(STATE.model, is_quota_alert=False), _on_switched)

    def action_open_prep(self):
        def _on_closed(prepped: bool):
            if prepped:
                self._refresh_status()
                self._reset_chat("Project brief and memory initialized.")
                tree = self.query_one("#file-tree", WorkspaceTree)
                tree.reload()
                self._log_process("[prep] complete")
        self.push_screen(ProjectPrepModal(), _on_closed)

    def action_open_onboarding(self):
        def _on_closed(saved: bool):
            if saved:
                self._refresh_status()
                self._reset_chat("Profile preferences applied.")
                self._log_process("[profile] updated")
        self.push_screen(OnboardingModal(), _on_closed)

    def action_show_help(self):
        log = self.query_one("#log", RichLog)
        help_panel = Panel(
            "[bold #ffffff]Command Palette & Keybindings:[/]\n\n"
            "  [bold #ffffff]F1[/]              Help guide\n"
            "  [bold #ffffff]F2[/]              Switch active model\n"
            "  [bold #ffffff]F3[/]              Project preparation wizard\n"
            "  [bold #ffffff]F4[/]              Token usage & key statistics\n"
            "  [bold #ffffff]Ctrl+B[/]          Toggle project explorer\n"
            "  [bold #ffffff]Ctrl+P[/]          Toggle process monitor\n"
            "  [bold #ffffff]Ctrl+K[/]          Configure dual API keys\n"
            "  [bold #ffffff]Ctrl+O[/]          Developer profile settings\n"
            "  [bold #ffffff]Ctrl+Q[/]          Exit Ally\n\n"
            "  /usage            View token analytics\n"
            "  /key              Set Gemini API keys\n"
            "  /model <name>     Switch model\n"
            "  /plan             Set plan mode (read-only)\n"
            "  /accept           Set accept mode (approval)\n"
            "  /auto             Set auto mode (autonomous)\n"
            "  /reset            Reset chat conversation",
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
        path = args.get("path", "?")
        if name == "write_file":
            body = args.get("content", "")
            preview = body[:600] + ("\n... (truncated)" if len(body) > 600 else "")
            panel = Panel(preview, title=f"[#ffaa00]write:[/] {path}", border_style="#ffaa00")
            log.write(panel)
        elif name == "patch_file":
            preview = f"--- OLD ---\n{args.get('old','')[:250]}\n--- NEW ---\n{args.get('new','')[:250]}"
            panel = Panel(preview, title=f"[#ffaa00]patch:[/] {path}", border_style="#ffaa00")
            log.write(panel)
        elif name == "delete_file":
            panel = Panel(f"Delete file: {path}", title="[#ff4444]delete[/]", border_style="#ff4444")
            log.write(panel)
        else:
            log.write(f"[#ffaa00]{name}:[/] {args}")

        log.write("[bold #ffaa00]Approve change? (y/n)[/]")
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
            self.query_one("#log", RichLog).write("[#ff4444]Ally not initialized. Press Ctrl+K to enter API keys.[/]\n")
            return

        if self._busy:
            self.query_one("#log", RichLog).write("[#ffaa00]Ally is busy. Wait for current turn to complete.[/]\n")
            return

        self._execute_turn_worker(text)

    @work(exclusive=True)
    async def _execute_turn_worker(self, text: str):
        log = self.query_one("#log", RichLog)
        
        # Clean terminal prompt line (no oversized box)
        log.write(f"\n[dim #555555]you>[/] [bold #ffffff]{text}[/]")
        self._log_process(f"[prompt] '{text[:18]}...'")

        self._busy = True
        self._set_activity("thinking")

        buffer = []

        def _on_token(chunk: str):
            buffer.append(chunk)

        def _on_step(step_name: str):
            self._log_process(f"[step] {step_name}")

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
                    title=f"[dim #555555]ally ({STATE.model})[/]",
                    border_style="#1a1a1a",
                    padding=(1, 2),
                )
                log.write(panel)
            tree = self.query_one("#file-tree", WorkspaceTree)
            tree.reload()
            self._refresh_status()
        except Exception as e:
            error_card = format_clean_error(e, STATE.model)
            log.write(error_card)
            self._log_process("[error] turn failed")

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
            log.write(f"[#555555]Catalog:[/] {', '.join(ROUTER.list_models())}\n")
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
            log.write(f"[#00ff66]Mode updated to {STATE.mode}[/]\n")
        elif cmd == "/status":
            log.write(f"user: {STATE.username} | mode: {STATE.mode} | model: {STATE.model} | key: {STATE.active_key_index}/2 | root: {STATE.root.name}\n")
        elif cmd == "/reset":
            self._reset_chat("Session context reset.")
        elif cmd == "/quit":
            self.exit()
        else:
            log.write(f"[#ff4444]Unknown command '{cmd}'. Type /help or press F1.[/]\n")


def run():
    AllyApp().run()


if __name__ == "__main__":
    run()
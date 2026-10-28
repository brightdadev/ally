"""
Pitch-Black Terminal IDE with Zero Mouse Tracking Spam.
Author: Bright da dev
"""
import asyncio
import os
import re
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
from textual.theme import Theme
from textual.widgets import (
    Input, RichLog, Static, Header, Footer, DirectoryTree, Label, Select
)
from textual.containers import Vertical, Horizontal
from textual.binding import Binding
from textual import work

from app import agent
from app.state import STATE
from app.model.router import ROUTER
from user.onboarding import profile_exists, load_profile, save_profile
from tui.theme import get_theme, THEMES
from tui.screens import (
    OnboardingModal,
    ProjectPrepModal,
    ModelSelectModal,
    ApiKeyModal,
    TokenUsageModal,
    ThemePaletteModal,
)

NATIVE_THEMES = {
    "purple": Theme(
        name="ally-purple",
        primary="#6d3bcc",
        accent="#a78bfa",
        background="#000000",
        surface="#000000",
        panel="#000000",
        foreground="#ffffff",
    ),
    "amber": Theme(
        name="ally-amber",
        primary="#b87004",
        accent="#f59e0b",
        background="#000000",
        surface="#000000",
        panel="#000000",
        foreground="#ffffff",
    ),
    "monochrome": Theme(
        name="ally-monochrome",
        primary="#444444",
        accent="#888888",
        background="#000000",
        surface="#000000",
        panel="#000000",
        foreground="#ffffff",
    ),
    "cobalt": Theme(
        name="ally-cobalt",
        primary="#005a9e",
        accent="#007acc",
        background="#000000",
        surface="#000000",
        panel="#000000",
        foreground="#ffffff",
    ),
    "emerald": Theme(
        name="ally-emerald",
        primary="#0e7a53",
        accent="#10b981",
        background="#000000",
        surface="#000000",
        panel="#000000",
        foreground="#ffffff",
    ),
    "cyan": Theme(
        name="ally-cyan",
        primary="#0088a8",
        accent="#00e5ff",
        background="#000000",
        surface="#000000",
        panel="#000000",
        foreground="#ffffff",
    ),
}

PREVIEW_URL_REGEX = re.compile(r"PREVIEW URL:\s*(https?://[^\s]+)", re.IGNORECASE)

# Filter any raw SGR mouse escape sequences from text input
SGR_FILTER_REGEX = re.compile(r"(\[?<\d+;\d+;\d+[Mm]|\b\d+;\d+;\d+[Mm]|\b\d+[Mm]\b|\^\[\[?<\d+;\d+;\d+[Mm]?|[\x1b\x00-\x1f])")

WINDOWS_JUNCTIONS_AND_NOISE = {
    ".git", "__pycache__", ".venv", "venv", ".egg-info", "dist", "build",
    "node_modules", "AppData", "Application Data", "Local Settings",
    "Cookies", "NetHood", "PrintHood", "Recent", "SendTo", "Start Menu",
    "Templates", "My Documents", "Searches", "Saved Games"
}


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


class CleanInput(Input):
    """Input widget with strict SGR mouse escape code filtering."""
    def insert_text_at_cursor(self, text: str) -> None:
        clean = SGR_FILTER_REGEX.sub("", text)
        if clean:
            super().insert_text_at_cursor(clean)


class WorkspaceTree(DirectoryTree):
    def filter_paths(self, paths):
        return [p for p in paths if p.name not in WINDOWS_JUNCTIONS_AND_NOISE]


class AllyApp(App):
    TITLE = "Ally"
    SUB_TITLE = "Terminal IDE v1.0.6"

    CSS = """
    Screen {
        layout: vertical;
        background: $background;
        overflow: hidden;
    }
    ModalScreen {
        background: rgba(0, 0, 0, 0.9);
    }
    Header {
        background: $background;
        color: #444444;
        height: 1;
    }
    Footer {
        background: $background;
        color: #444444;
        height: 1;
    }
    .footer--key {
        background: #0d0d0d;
        color: #777777;
    }
    .footer--description {
        color: #444444;
    }

    Button.-primary {
        background: $primary;
        color: #ffffff;
        border: solid $accent;
    }
    Button.-primary:hover {
        background: $accent;
    }
    Button.-default {
        background: #141414;
        color: #777777;
        border: solid #222222;
    }
    Button.-default:hover {
        background: #222222;
        color: #cccccc;
    }

    Select {
        background: $background;
        border: none;
        padding: 0;
    }
    SelectCurrent {
        background: $background;
        border: solid $primary;
        color: #ffffff;
    }
    Select:focus > SelectCurrent {
        border: solid $accent;
    }
    SelectOverlay {
        background: $background;
        border: solid $primary;
    }
    OptionList {
        background: $background;
    }
    OptionList > .option-list--option-highlighted {
        background: $primary;
        color: #ffffff;
        text-style: bold;
    }

    #ide-layout {
        height: 1fr;
        layout: horizontal;
        background: $background;
        overflow: hidden;
    }
    #sidebar {
        width: 26;
        background: $background;
        border-right: solid #141414;
        overflow: hidden;
    }
    #sidebar.hidden {
        display: none;
    }
    #process-panel {
        width: 36;
        background: $background;
        border-left: solid #141414;
        overflow: hidden;
    }
    #process-panel.hidden {
        display: none;
    }
    .panel-header {
        height: 1;
        background: $background;
        color: #444444;
        text-style: bold;
        padding: 0 1;
    }
    #file-tree {
        height: 1fr;
        background: $background;
        border: none;
        padding: 0 1;
        color: #666666;
    }
    #process-log {
        height: 1fr;
        background: $background;
        border: none;
        padding: 0 1;
        color: #555555;
    }
    #main-panel {
        width: 1fr;
        height: 1fr;
        layout: vertical;
        background: $background;
        overflow: hidden;
    }
    #top-breadcrumbs {
        height: 1;
        background: $background;
        padding: 0 1;
    }
    .badge-pill {
        margin-right: 2;
        color: #555555;
    }
    #log {
        height: 1fr;
        background: $background;
        border: none;
        padding: 1 2;
        overflow-x: hidden;
    }

    #composer-container {
        height: 3;
        background: $background;
        border-top: solid $primary;
        padding: 0 1;
    }
    #prompt {
        background: $background;
        border: none;
        color: #ffffff;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("f1", "show_help", "Help", priority=True),
        Binding("f2", "switch_model", "Model", priority=True),
        Binding("f3", "open_prep", "Prep", priority=True),
        Binding("f4", "open_usage", "Usage", priority=True),
        Binding("ctrl+b", "toggle_sidebar", "Explorer", priority=True),
        Binding("ctrl+p", "toggle_process", "Process", priority=True),
        Binding("ctrl+t", "open_palette", "Palette", priority=True),
        Binding("ctrl+k", "open_api_key", "Keys"),
        Binding("ctrl+o", "open_onboarding", "Profile"),
        Binding("ctrl+q", "quit", "Quit", priority=True),
    ]

    def __init__(self):
        super().__init__()
        self.chat = None
        self._approval_future = None
        self._busy = False
        self.accent_theme = "purple"

    def _start_mouse_tracking(self) -> None:
        """PERMANENTLY DISABLE SGR MOUSE TRACKING IN WINDOWS TERMINAL."""
        pass

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="ide-layout"):
            with Vertical(id="sidebar"):
                yield Label("EXPLORER", classes="panel-header")
                yield WorkspaceTree(str(STATE.root), id="file-tree")
            with Vertical(id="main-panel"):
                with Horizontal(id="top-breadcrumbs"):
                    yield Static("[bold #00ff66][ready][/]", id="badge-status", classes="badge-pill")
                    yield Static(f"model: [bold #ffffff]{STATE.model}[/]", id="badge-model", classes="badge-pill")
                    yield Static(f"mode: [bold #00ff66]{STATE.mode}[/]", id="badge-mode", classes="badge-pill")
                    yield Static(f"key: [bold #aaaaaa]{STATE.active_key_index}/2[/]", id="badge-key", classes="badge-pill"),
                    yield Static(f"theme: [bold]{self.accent_theme}[/]", id="badge-theme", classes="badge-pill"),
                    yield Static(f"root: [dim #555555]{STATE.root.name}[/]", id="badge-root", classes="badge-pill"),
                yield RichLog(id="log", wrap=True, markup=True)
                with Horizontal(id="composer-container"):
                    yield CleanInput(placeholder="Ask Ally... (/help, F2 model, F4 stats, ^T palette, ^B explorer)", id="prompt")
            with Vertical(id="process-panel"):
                yield Label("PROCESS", classes="panel-header")
                yield RichLog(id="process-log", wrap=True, markup=True)
        yield Footer()

    def on_mount(self):
        self.query_one("#prompt").focus()
        self.query_one("#log", RichLog).can_focus = False
        self.query_one("#process-log", RichLog).can_focus = False

        # Kill mouse tracking on driver
        if hasattr(self, "_driver") and hasattr(self._driver, "disable_mouse_support"):
            try:
                self._driver.disable_mouse_support()
            except Exception:
                pass

        for t_obj in NATIVE_THEMES.values():
            self.register_theme(t_obj)

        prof = load_profile()
        STATE.username = prof.username
        if prof.default_model in ROUTER.list_models():
            STATE.model = prof.default_model
        else:
            STATE.model = ROUTER.get_default_model()
        STATE.mode = prof.default_mode
        self.accent_theme = prof.accent_theme or "purple"
        if prof.api_key_1 and not os.environ.get("GEMINI_API_KEY"):
            os.environ["GEMINI_API_KEY"] = prof.api_key_1

        self._apply_native_theme(self.accent_theme)
        self._refresh_status()

        self._log_process("[init] system ready")

        if not os.environ.get("GEMINI_API_KEY") and not agent.get_active_key():
            self.action_open_api_key()
        else:
            self._boot()

    def _apply_native_theme(self, theme_name: str):
        clean = theme_name if theme_name in NATIVE_THEMES else "purple"
        self.theme = f"ally-{clean}"
        self.accent_theme = clean

    def _boot(self):
        log = self.query_one("#log", RichLog)
        if not os.environ.get("GEMINI_API_KEY") and not agent.get_active_key():
            return

        try:
            agent.reset_client()
            self.chat = agent.new_chat()
            log.write(f"[bold #ffffff]Ally Terminal[/] [dim #555555]v1.0.6[/] · [dim #555555]model:[/] [bold #ffffff]{STATE.model}[/] · [dim #555555]root:[/] [bold #aaaaaa]{STATE.root.name}[/]")
            self._log_process(f"[active] {STATE.model}")
        except Exception as e:
            log.write(format_clean_error(e, STATE.model))
            self._log_process("[error] init failed")

    def _refresh_status(self):
        self.query_one("#badge-model", Static).update(f"model: [bold #ffffff]{STATE.model}[/]")
        self.query_one("#badge-mode", Static).update(f"mode: [bold #00ff66]{STATE.mode}[/]")
        self.query_one("#badge-key", Static).update(f"key: [bold #aaaaaa]{STATE.active_key_index}/2[/]")
        self.query_one("#badge-theme", Static).update(f"theme: [bold]{self.accent_theme}[/]")
        self.query_one("#badge-root", Static).update(f"root: [dim #555555]{STATE.root.name}[/]")

    def _set_activity(self, state: str):
        badge = self.query_one("#badge-status", Static)
        if state == "thinking":
            badge.update("[bold #ffff00][thinking][/]")
        elif state == "streaming":
            badge.update("[bold #ffffff][streaming][/]")
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

    def action_open_palette(self):
        def _on_theme_selected(theme_name: str):
            if theme_name:
                self._apply_native_theme(theme_name)
                prof = load_profile()
                prof.accent_theme = theme_name
                save_profile(prof)
                self._refresh_status()
                log = self.query_one("#log", RichLog)
                log.write(f"[dim #888888]Framework theme switched to [bold]{theme_name}[/].[/]\n")
                self._log_process(f"[theme] {theme_name}")
        self.push_screen(ThemePaletteModal(), _on_theme_selected)

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
            "  [bold #ffffff]Ctrl+T[/]          Accent theme palette\n"
            "  [bold #ffffff]Ctrl+K[/]          Configure dual API keys\n"
            "  [bold #ffffff]Ctrl+O[/]          Developer profile settings\n"
            "  [bold #ffffff]Ctrl+Q[/]          Exit Ally\n\n"
            "  /servers          List running background dev servers\n"
            "  /stopserver [pid] Stop a running background server\n"
            "  /theme <name>     Change theme (purple, amber, monochrome, emerald, cobalt, cyan)\n"
            "  /palette          Open theme palette switcher\n"
            "  /usage            View token analytics\n"
            "  /key              Set Gemini API keys\n"
            "  /model <name>     Switch model\n"
            "  /plan             Set plan mode (read-only)\n"
            "  /accept           Set accept mode (approval)\n"
            "  /auto             Set auto mode (autonomous)\n"
            "  /reset            Reset chat conversation",
            title="[#444444]commands[/]",
            border_style="#141414",
            padding=(1, 2),
        )
        log.write(help_panel)

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected):
        prompt = self.query_one("#prompt", CleanInput)
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

        if name == "run_command":
            cmd = args.get("command", "")
            panel = Panel(
                f"[bold #ffffff]{cmd}[/]\n\n[dim #666666]Directory:[/] {STATE.root}",
                title="[#ffaa00]execute command[/]",
                border_style="#ffaa00",
                padding=(1, 2),
            )
            log.write(panel)
        elif name == "stop_server":
            pid = args.get("pid", "Active Server")
            panel = Panel(
                f"[bold #ff4444]Stop background server (PID: {pid})?[/]",
                title="[#ff4444]stop server[/]",
                border_style="#ff4444",
                padding=(1, 2),
            )
            log.write(panel)
        elif name == "write_file":
            body = args.get("content", "")
            preview = body[:600] + ("\n... (truncated)" if len(body) > 600 else "")
            panel = Panel(preview, title=f"write: {path}", border_style="#444444")
            log.write(panel)
        elif name == "patch_file":
            preview = f"--- OLD ---\n{args.get('old','')[:250]}\n--- NEW ---\n{args.get('new','')[:250]}"
            panel = Panel(preview, title=f"patch: {path}", border_style="#444444")
            log.write(panel)
        elif name == "delete_file":
            panel = Panel(f"Delete file: {path}", title="delete", border_style="#ff4444")
            log.write(panel)
        else:
            log.write(f"[#888888]{name}:[/] {args}")

        log.write("[bold #ffffff]Approve change? (y/n)[/]")
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
        log.write(f"\n[dim #555555]you>[/] [bold #ffffff]{text}[/]")
        self._log_process(f"[prompt] '{text[:18]}...'")

        self._busy = True
        self._set_activity("thinking")

        buffer = []
        modified_files = False

        def _on_token(chunk: str):
            buffer.append(chunk)

        def _on_step(step_name: str):
            self._log_process(f"[step] {step_name}")

        async def _approval_interceptor(name, args):
            nonlocal modified_files
            if name in ("write_file", "patch_file", "delete_file"):
                modified_files = True
            return await self.request_approval(name, args)

        try:
            await agent.run_turn(
                self.chat,
                text,
                _on_token,
                _approval_interceptor,
                on_step=_on_step,
            )
            full_reply = "".join(buffer)
            if full_reply:
                url_match = PREVIEW_URL_REGEX.search(full_reply)
                if url_match:
                    preview_url = url_match.group(1)
                    server_card = Panel(
                        f"[bold #ffffff]Local Development Server is Running in Background[/]\n\n"
                        f"[bold #00ff66]Preview URL:[/] [bold #00d2ff underline]{preview_url}[/]\n\n"
                        f"[dim #888888]Ally is monitoring live logs. Type /servers or /stopserver anytime.[/dim]",
                        title="[bold #00ff66]● SERVER ONLINE[/]",
                        border_style="#00ff66",
                        padding=(1, 2),
                    )
                    log.write(server_card)

                md_rendered = Markdown(full_reply, inline_code_lexer="text", code_theme="monokai")
                panel = Panel(
                    md_rendered,
                    title=f"[dim #555555]ally ({STATE.model})[/]",
                    border_style="#1a1a1a",
                    padding=(1, 2),
                )
                log.write(panel)

            if modified_files:
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
        elif cmd == "/servers":
            log.write(f"[#58a6ff]Active Servers:\n[/]{agent.tools.list_servers()}\n")
        elif cmd == "/stopserver":
            target_pid = int(arg) if arg.isdigit() else None
            log.write(f"[#ffaa00]{agent.tools.stop_server(target_pid)}[/]\n")
        elif cmd == "/palette":
            self.action_open_palette()
        elif cmd == "/theme":
            if not arg:
                log.write(f"[#555555]Current theme:[/] {self.accent_theme} · Available: {', '.join(NATIVE_THEMES.keys())}\n")
                return
            if arg in NATIVE_THEMES:
                self._apply_native_theme(arg)
                prof = load_profile()
                prof.accent_theme = arg
                save_profile(prof)
                self._refresh_status()
                log.write(f"[dim #888888]Framework theme switched to [bold]{arg}[/].[/]\n")
                self._log_process(f"[theme] {arg}")
            else:
                log.write(f"[#ff4444]Unknown theme '{arg}'. Choose from: {', '.join(NATIVE_THEMES.keys())}[/]\n")
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
            log.write(f"user: {STATE.username} | mode: {STATE.mode} | model: {STATE.model} | theme: {self.accent_theme} | key: {STATE.active_key_index}/2 | root: {STATE.root.name}\n")
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
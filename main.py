"""
Terminal UI for Ally built on Textual.
Author: Bright da dev
"""
import asyncio
import os
from pathlib import Path

# Safe environment loading with fallback
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from textual.app import App, ComposeResult
from textual.widgets import Input, RichLog, Static
from textual.containers import Vertical

import agent
from state import STATE


class AllyApp(App):
    CSS = """
    Screen { layout: vertical; }
    #log { height: 1fr; border: round $accent; }
    #status { height: 1; background: $boost; padding: 0 1; }
    #prompt { height: 3; }
    """

    def __init__(self):
        super().__init__()
        self.chat = None
        self._approval_future = None
        self._busy = False

    def compose(self) -> ComposeResult:
        yield Vertical(
            RichLog(id="log", wrap=True, markup=True),
            Static(self._status_text(), id="status"),
            Input(placeholder="Ask Ally...  or  /help", id="prompt"),
        )

    def on_mount(self):
        self.query_one("#prompt").focus()
        self._boot()

    def _boot(self):
        log = self.query_one("#log", RichLog)
        if not os.environ.get("GEMINI_API_KEY"):
            log.write("[red]GEMINI_API_KEY not found.[/]")
            log.write("[yellow]Create a .env file with GEMINI_API_KEY=your_key or set it in your environment.[/]")
            return
        try:
            self.chat = agent.new_chat()
            log.write(f"[green]Ally ready.[/] model={STATE.model} mode={STATE.mode}")
            log.write("[dim]Authored by Bright da dev | Type [bold]/help[/bold] for commands.[/dim]")
        except Exception as e:
            log.write(f"[red]Init failed: {e}[/]")

    def _status_text(self) -> str:
        return f"mode={STATE.mode} | model={STATE.model} | root={STATE.root}"

    def _refresh_status(self):
        self.query_one("#status", Static).update(self._status_text())

    async def request_approval(self, name: str, args: dict) -> bool:
        log = self.query_one("#log", RichLog)
        path = args.get("path", "?")
        if name == "write_file":
            body = args.get("content", "")
            preview = body[:800] + ("\n... (truncated)" if len(body) > 800 else "")
            log.write(f"[yellow]WRITE[/] {path}\n[dim]{preview}[/]")
        elif name == "patch_file":
            log.write(
                f"[yellow]PATCH[/] {path}\n"
                f"[dim]--- old ---\n{args.get('old','')[:400]}\n"
                f"--- new ---\n{args.get('new','')[:400]}[/]"
            )
        elif name == "delete_file":
            log.write(f"[red]DELETE[/] {path}")
        else:
            log.write(f"[yellow]{name}[/] {args}")
        log.write("[bold yellow]Approve? (y/n)[/]")
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
            log.write("[red]Not initialized. Set GEMINI_API_KEY in .env and restart.[/]")
            return
        if self._busy:
            log.write("[yellow]Busy — wait for this turn to finish.[/]")
            return

        log.write(f"\n[bold cyan]You:[/] {text}")
        log.write("[bold green]Ally:[/]")

        def _stream(s: str):
            log.write(s)

        self._busy = True
        try:
            await agent.run_turn(self.chat, text, _stream, self.request_approval)
        except Exception as e:
            log.write(f"[red]Error: {e}[/]")
        finally:
            self._busy = False

    def _handle_command(self, text: str, log: RichLog):
        parts = text.split(maxsplit=1)
        cmd = parts[0]
        arg = parts[1] if len(parts) > 1 else ""

        if cmd == "/help":
            log.write(
                "[bold]Commands:[/]\n"
                "  /enter <dir>     load <dir>/project.md, set project root\n"
                "  /model <name>    switch model (resets chat)\n"
                "  /plan            read-only mode\n"
                "  /accept          approve each write\n"
                "  /auto            auto-apply writes\n"
                "  /status          show current state\n"
                "  /reset           start a fresh chat\n"
                "  /quit            exit"
            )
        elif cmd == "/enter":
            if not arg:
                log.write("[red]usage: /enter <dir>[/]")
                return
            p = Path(arg).expanduser().resolve()
            brief = p / "project.md"
            if brief.exists():
                STATE.project_brief = brief.read_text(encoding="utf-8")
                log.write(f"[green]Loaded brief[/] {brief} ({len(STATE.project_brief)} chars)")
            else:
                log.write(f"[yellow]No project.md in {p}; root updated anyway.[/]")
            STATE.root = p
            self.chat = agent.new_chat()
            self._refresh_status()
        elif cmd == "/model":
            if not arg:
                log.write(f"current: {STATE.model}")
                return
            STATE.model = arg
            self.chat = agent.new_chat()
            log.write(f"[green]model -> {arg}[/]")
            self._refresh_status()
        elif cmd in ("/plan", "/accept", "/auto"):
            STATE.mode = cmd[1:]
            log.write(f"[green]mode -> {STATE.mode}[/]")
            self._refresh_status()
        elif cmd == "/status":
            log.write(self._status_text())
        elif cmd == "/reset":
            self.chat = agent.new_chat()
            log.write("[green]chat reset[/]")
        elif cmd == "/quit":
            self.exit()
        else:
            log.write(f"[red]unknown command {cmd}[/]  try /help")


def run():
    AllyApp().run()


if __name__ == "__main__":
    run()

"""
LLM Agent with autonomous execution and direct command permission bypass.
Author: Bright da dev
"""
import asyncio
import json
import os
import re
from pathlib import Path
from google import genai
from google.genai import types

from app.state import STATE
from app import tools
from context.skills import SKILLS
from context.memory import read_memory
from user.onboarding import load_profile

WRITE_TOOLS = {"write_file", "patch_file", "delete_file", "run_command", "stop_server"}
_PERSISTENT_CLIENT = None
WHITELIST_FILE = Path(__file__).parent / "whitelist.json"

DIRECT_ACTION_WORDS = {
    "create", "make", "design", "build", "setup", "run", "do", "install",
    "write", "add", "delete", "remove", "patch", "start", "exec", "open"
}


def is_direct_order(text: str) -> bool:
    """Detects if user prompt gives a direct directive where permission MUST be skipped."""
    clean = text.lower().strip()
    if clean.startswith("ally "):
        clean = clean[5:].strip()

    tokens = re.findall(r"\b[a-z]+\b", clean)
    if any(token in DIRECT_ACTION_WORDS for token in tokens[:4]):
        return True
    if "run it" in clean or "do it" in clean:
        return True
    return False


def load_whitelist() -> dict:
    if not WHITELIST_FILE.is_file():
        return {"exact_commands": [], "command_prefixes": []}
    try:
        return json.loads(WHITELIST_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"exact_commands": [], "command_prefixes": []}


def is_safe_command(command: str) -> bool:
    cmd = command.strip().lower()
    whitelist = load_whitelist()
    exacts = set(whitelist.get("exact_commands", []))
    prefixes = tuple(whitelist.get("command_prefixes", []))

    parts = [p.strip() for p in re.split(r"&&|;|\|\|", cmd) if p.strip()]
    if not parts:
        return False

    def _check(part: str) -> bool:
        if part in exacts:
            return True
        if part.startswith(prefixes):
            return True
        return False

    return all(_check(p) for p in parts)


class QuotaException(Exception):
    pass


class ServerUnavailableException(Exception):
    pass


def get_active_key() -> str:
    prof = load_profile()
    if STATE.active_key_index == 2 and prof.api_key_2:
        return prof.api_key_2
    if prof.api_key_1:
        return prof.api_key_1
    return os.environ.get("GEMINI_API_KEY", "")


def rotate_to_backup_key() -> bool:
    prof = load_profile()
    if STATE.active_key_index == 1 and prof.api_key_2:
        STATE.active_key_index = 2
        os.environ["GEMINI_API_KEY"] = prof.api_key_2
        reset_client()
        return True
    elif STATE.active_key_index == 2 and prof.api_key_1:
        STATE.active_key_index = 1
        os.environ["GEMINI_API_KEY"] = prof.api_key_1
        reset_client()
        return True
    return False


def get_client() -> genai.Client:
    global _PERSISTENT_CLIENT
    api_key = get_active_key()
    if _PERSISTENT_CLIENT is None:
        _PERSISTENT_CLIENT = genai.Client(api_key=api_key)
    return _PERSISTENT_CLIENT


def reset_client():
    global _PERSISTENT_CLIENT
    _PERSISTENT_CLIENT = None


def _load_ground_rules() -> str:
    rules_file = Path("ally.md")
    if rules_file.is_file():
        try:
            return rules_file.read_text(encoding="utf-8")
        except Exception:
            pass
    return "You are Ally, a terminal coding assistant authored by Bright da dev."


def _system_prompt() -> str:
    parts = [
        _load_ground_rules(),
        f"OPERATIONAL STATE:\n- User: {STATE.username}\n- Mode: {STATE.mode}\n- Model: {STATE.model}\n- Active Key: #{STATE.active_key_index}\n- Project Root: {STATE.root}",
        "DIRECTIVE: Work autonomously. Fulfill user coding, creation, and building tasks directly using tools without stopping for unnecessary permissions."
    ]

    brief_file = STATE.root / "project.md"
    if brief_file.is_file():
        parts.append("PROJECT BRIEF:\n" + brief_file.read_text(encoding="utf-8"))

    memory_content = read_memory(STATE.root)
    if memory_content:
        parts.append("PROJECT MEMORY:\n" + memory_content)

    return "\n\n---\n\n".join(parts)


def _compile_tool_definitions():
    core_tools = [
        types.FunctionDeclaration(
            name="read_file",
            description="Read a file's full contents safely.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={"path": types.Schema(type=types.Type.STRING)}, required=["path"]),
        ),
        types.FunctionDeclaration(
            name="write_file",
            description="Create or overwrite a file safely.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={"path": types.Schema(type=types.Type.STRING), "content": types.Schema(type=types.Type.STRING)},
                required=["path", "content"],
            ),
        ),
        types.FunctionDeclaration(
            name="patch_file",
            description="Replace one occurrence of 'old' with 'new' in a file.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={"path": types.Schema(type=types.Type.STRING), "old": types.Schema(type=types.Type.STRING), "new": types.Schema(type=types.Type.STRING)},
                required=["path", "old", "new"],
            ),
        ),
        types.FunctionDeclaration(
            name="delete_file",
            description="Delete a file safely.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={"path": types.Schema(type=types.Type.STRING)}, required=["path"]),
        ),
        types.FunctionDeclaration(
            name="list_dir",
            description="List directory entries, automatically filtering out .allyignore paths.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={"path": types.Schema(type=types.Type.STRING)}),
        ),
        types.FunctionDeclaration(
            name="run_command",
            description="Execute CLI commands (npm install, npm run dev, pytest, etc.). Dev servers run persistently in background with preview URL extraction.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "command": types.Schema(type=types.Type.STRING, description="The CLI command to execute."),
                    "timeout": types.Schema(type=types.Type.INTEGER, description="Timeout in seconds for short commands (default: 30)"),
                },
                required=["command"],
            ),
        ),
        types.FunctionDeclaration(
            name="get_server_logs",
            description="Retrieve recent live logs from an active background dev server to inspect errors.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={"pid": types.Schema(type=types.Type.INTEGER, description="Optional server PID.")},
            ),
        ),
        types.FunctionDeclaration(
            name="stop_server",
            description="Stop an active background development server by PID.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={"pid": types.Schema(type=types.Type.INTEGER, description="Optional server PID.")},
            ),
        ),
        types.FunctionDeclaration(
            name="list_servers",
            description="List all active background development servers and their preview URLs.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={}),
        ),
    ]
    skill_tools = SKILLS.get_declarations()
    return core_tools + skill_tools


def new_chat():
    client = get_client()
    return client.chats.create(
        model=STATE.model,
        config=types.GenerateContentConfig(
            tools=[types.Tool(function_declarations=_compile_tool_definitions())],
            system_instruction=_system_prompt(),
        ),
    )


def dispatch(name: str, args: dict):
    if hasattr(tools, name):
        fn = getattr(tools, name)
        try:
            return fn(**args)
        except Exception as e:
            return f"ERROR: {e}"

    skill_fn = SKILLS.get_handler(name)
    if skill_fn:
        try:
            return skill_fn(**args)
        except Exception as e:
            return f"ERROR: {e}"

    return f"ERROR: unknown tool '{name}'"


async def run_turn(chat, user_text_or_parts, on_token, request_approval, on_step=None):
    current_input = user_text_or_parts

    # Auto-detect if user prompt contains a direct task order
    skip_permission = False
    if isinstance(user_text_or_parts, str):
        skip_permission = is_direct_order(user_text_or_parts)

    while True:
        if on_step:
            on_step(f"Calling {STATE.model} (Key #{STATE.active_key_index})...")

        queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def _producer():
            try:
                for chunk in chat.send_message_stream(current_input):
                    loop.call_soon_threadsafe(queue.put_nowait, ("chunk", chunk))
            except Exception as e:
                loop.call_soon_threadsafe(queue.put_nowait, ("error", e))
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, ("done", None))

        asyncio.create_task(asyncio.to_thread(_producer))

        accumulated_calls = []
        is_first_token = True

        while True:
            msg_type, payload = await queue.get()

            if msg_type == "error":
                err = str(payload).lower()
                if ("429" in err or "quota" in err or "resource_exhausted" in err) and rotate_to_backup_key():
                    if on_step:
                        on_step(f"Quota hit. Auto-rotated to Key #{STATE.active_key_index}!")
                    chat = new_chat()
                    return await run_turn(chat, user_text_or_parts, on_token, request_approval, on_step)

                if "503" in err or "unavailable" in err:
                    raise ServerUnavailableException(str(payload))
                raise payload
            elif msg_type == "done":
                break
            elif msg_type == "chunk":
                chunk = payload
                text = ""
                try:
                    text = chunk.text or ""
                except Exception:
                    text = ""

                if text:
                    if is_first_token:
                        is_first_token = False
                        if on_step:
                            on_step("Streaming response...")
                    on_token(text)

                if chunk.function_calls:
                    accumulated_calls.extend(chunk.function_calls)

                if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
                    u = chunk.usage_metadata
                    p = getattr(u, "prompt_token_count", 0) or 0
                    c = getattr(u, "candidates_token_count", 0) or 0
                    t = getattr(u, "total_token_count", 0) or (p + c)
                    STATE.tokens.add(p, c, t, STATE.active_key_index)

        if not accumulated_calls:
            break

        parts = []
        for call in accumulated_calls:
            name = call.name
            args = dict(call.args or {})

            if on_step:
                on_step(f"Executing: {name}")

            # 1. AUTO MODE OR DIRECT TASK ORDER: EXECUTE IMMEDIATELY (ZERO POPUPS!)
            if STATE.mode == "auto" or skip_permission:
                if on_step:
                    on_step(f"Auto-executing: {name}")
                result = await asyncio.to_thread(dispatch, name, args)

            # 2. WHITELIST INSPECTION: ALWAYS AUTO-EXECUTE (dir, node -v, git status)
            elif name == "run_command" and is_safe_command(args.get("command", "")):
                result = await asyncio.to_thread(dispatch, name, args)

            # 3. PLAN MODE: Read-Only
            elif STATE.mode == "plan" and name in WRITE_TOOLS:
                result = "BLOCKED: plan mode - read tools only."

            # 4. ACCEPT MODE: Only ask if user gave no direct order
            elif STATE.mode == "accept" and name in WRITE_TOOLS:
                if on_step:
                    on_step(f"Awaiting approval for {name}...")
                approved = await request_approval(name, args)
                if approved:
                    if on_step:
                        on_step(f"Executing {name}...")
                    result = await asyncio.to_thread(dispatch, name, args)
                else:
                    if on_step:
                        on_step(f"Denied: {name}")
                    result = "DENIED by user."

            else:
                result = await asyncio.to_thread(dispatch, name, args)

            parts.append(
                types.Part.from_function_response(name=name, response={"result": result})
            )

        current_input = parts

    if on_step:
        on_step("Turn completed.")
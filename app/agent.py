"""
LLM Agent with parallel tool execution, persistent server defense, and zero-waste speed.
Author: Bright da dev
Version: 1.1.0
"""
import asyncio
import os
import subprocess
from pathlib import Path
from google import genai
from google.genai import types

from app.state import STATE
from app import tools
from app.ignore import is_ignored
from context.skills import SKILLS
from context.memory import read_memory
from user.onboarding import load_profile


WRITE_TOOLS = {"write_file", "patch_file", "delete_file", "run_command"}
_PERSISTENT_CLIENT = None


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
    return "You are Ally, a terminal engineering partner authored by Bright da dev."


def _get_workspace_snapshot() -> str:
    root = STATE.root.resolve()
    try:
        entries = sorted(root.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
        filtered = [f"{'d' if e.is_dir() else 'f'} {e.name}" for e in entries if not is_ignored(e, root)]
        return "\n".join(filtered[:45])
    except Exception:
        return "(empty or inaccessible)"


def _get_git_branch() -> str:
    try:
        r = subprocess.run(["git", "branch", "--show-current"], cwd=str(STATE.root), capture_output=True, text=True, timeout=2)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass
    return "not a git repo"


def _system_prompt() -> str:
    prof = load_profile()
    username = prof.username or STATE.username or "bright"
    role = getattr(prof, "role", "Lead Developer")
    is_home_dir = STATE.root.resolve() == Path.home().resolve()

    parts = [
        _load_ground_rules(),
        f"PARTNER RELATIONSHIP:\n- Lead Developer: {username} ({role})\n- Workspace: {STATE.root.name} (Path: {STATE.root})\n- Git Branch: {_get_git_branch()}\n- Running in User Home: {is_home_dir}",
        f"WORKSPACE OVERVIEW:\n{_get_workspace_snapshot()}",
    ]

    brief_file = STATE.root / "project.md"
    if brief_file.is_file():
        try:
            parts.append("PROJECT BRIEF:\n" + brief_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    memory_content = read_memory(STATE.root)
    if memory_content:
        parts.append("PROJECT MEMORY:\n" + memory_content)

    parts.append(
        "CRITICAL BEHAVIORAL DIRECTIVES:\n"
        f"1. ZERO ASSUMPTIONS: You must NEVER invent a project, tech stack, or feature on your own.\n"
        f"2. REQUIREMENT ALIGNMENT FIRST: When {username} asks to build, create, or design something new, you MUST engage in dialogue: ask what the vision is, what stack they prefer, and what requirements they have. Present a concise plan and ask for approval.\n"
        f"3. NO PERSISTENT SERVERS: NEVER run 'npm run dev', 'next dev', or 'vite' with run_command. To check if a project is running, inspect the port with 'netstat -ano | findstr :3000' in under 1 second. Never freeze the app waiting for a web server.\n"
        f"4. BATCH ACTIONS: Perform multiple file writes or commands in batches to minimize roundtrips."
    )

    return "\n\n---\n\n".join(parts)


def _compile_tool_definitions():
    core_tools = [
        types.FunctionDeclaration(
            name="read_file",
            description="Read a file's full contents safely. Protected by .allyignore.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={"path": types.Schema(type=types.Type.STRING)}, required=["path"]),
        ),
        types.FunctionDeclaration(
            name="write_file",
            description="Create or overwrite a file safely. Protected by .allyignore.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={"path": types.Schema(type=types.Type.STRING), "content": types.Schema(type=types.Type.STRING)},
                required=["path", "content"],
            ),
        ),
        types.FunctionDeclaration(
            name="patch_file",
            description="Replace one occurrence of 'old' with 'new' in a file. Protected by .allyignore.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={"path": types.Schema(type=types.Type.STRING), "old": types.Schema(type=types.Type.STRING), "new": types.Schema(type=types.Type.STRING)},
                required=["path", "old", "new"],
            ),
        ),
        types.FunctionDeclaration(
            name="delete_file",
            description="Delete a file safely. Protected by .allyignore.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={"path": types.Schema(type=types.Type.STRING)}, required=["path"]),
        ),
        types.FunctionDeclaration(
            name="list_dir",
            description="List directory entries. Automatically filters files protected by .allyignore.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={"path": types.Schema(type=types.Type.STRING)}),
        ),
        types.FunctionDeclaration(
            name="run_command",
            description="Execute a non-interactive shell command in the project root and inspect exit code, stdout, and stderr. Do NOT run persistent dev servers.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "command": types.Schema(type=types.Type.STRING, description="Command to execute (e.g. pytest, npm test, netstat -ano | findstr :3000)"),
                    "timeout": types.Schema(type=types.Type.INTEGER, description="Timeout in seconds (default: 30)"),
                },
                required=["command"],
            ),
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


def _format_friendly_step(name: str, args: dict) -> str:
    if name == "read_file":
        return f"Ally is reading {args.get('path', 'file')}"
    if name == "write_file":
        return f"Ally is writing {args.get('path', 'file')}"
    if name == "patch_file":
        return f"Ally is updating {args.get('path', 'file')}"
    if name == "run_command":
        cmd = args.get('command', '')
        return f"Ally is running: {cmd[:28]}..." if len(cmd) > 28 else f"Ally is running: {cmd}"
    if name == "list_dir":
        return "Ally is checking workspace files"
    if name == "record_decision":
        return "Ally is updating project memory"
    return f"Ally is working ({name})"


async def run_turn(chat, user_text_or_parts, on_token, request_approval, on_step=None):
    current_input = user_text_or_parts

    while True:
        if on_step:
            on_step("Ally is thinking of a response...")

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
                        on_step(f"Quota reached. Auto-rotated to Key #{STATE.active_key_index}!")
                    chat = new_chat()
                    return await run_turn(chat, user_text_or_parts, on_token, request_approval, on_step)

                if "503" in err or "unavailable" in err:
                    if on_step:
                        on_step("Google servers busy. Retrying in 2s...")
                    await asyncio.sleep(2)
                    return await run_turn(chat, user_text_or_parts, on_token, request_approval, on_step)
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
                            on_step("Ally is writing response...")
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

        # Parallelize execution of multiple tool calls within the same turn
        async def _exec_one(call):
            name = call.name
            args = dict(call.args or {})

            if on_step:
                on_step(_format_friendly_step(name, args))

            if STATE.mode == "plan" and name in WRITE_TOOLS:
                result = "BLOCKED: plan mode - read tools only."
            elif STATE.mode == "accept" and name in WRITE_TOOLS:
                approved = await request_approval(name, args)
                if approved:
                    result = await asyncio.to_thread(dispatch, name, args)
                else:
                    result = "DENIED by user."
            else:
                result = await asyncio.to_thread(dispatch, name, args)

            return types.Part.from_function_response(name=name, response={"result": result})

        parts = await asyncio.gather(*[_exec_one(call) for call in accumulated_calls])
        current_input = list(parts)

    if on_step:
        on_step("Ally is finished.")
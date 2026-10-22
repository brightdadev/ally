"""
LLM Agent with dual-key rotation and token usage collection.
Author: Bright da dev
"""
import asyncio
import os
from pathlib import Path
from google import genai
from google.genai import types

from app.state import STATE
from app import tools
from context.skills import SKILLS
from context.memory import read_memory
from user.onboarding import load_profile, save_profile


WRITE_TOOLS = {"write_file", "patch_file", "delete_file"}
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
    """Rotates to secondary key if primary hits quota."""
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
            description="List directory entries.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={"path": types.Schema(type=types.Type.STRING)}),
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
                # Check for quota error and attempt failover to Key 2
                if ("429" in err or "quota" in err or "resource_exhausted" in err) and rotate_to_backup_key():
                    if on_step:
                        on_step(f"Quota hit. Auto-rotated to Key #{STATE.active_key_index}!")
                    # Retry stream with backup key
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

                # Collect usage metadata if reported by Gemini
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
                on_step(f"Tool request: {name}")

            if STATE.mode == "plan" and name in WRITE_TOOLS:
                result = "BLOCKED: plan mode - read tools only."
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
                if on_step:
                    on_step(f"Executing: {name}...")
                result = await asyncio.to_thread(dispatch, name, args)

            parts.append(
                types.Part.from_function_response(name=name, response={"result": result})
            )

        current_input = parts

    if on_step:
        on_step("Turn completed.")
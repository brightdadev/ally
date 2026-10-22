"""
LLM Agent integration powered by Google GenAI.
Author: Bright da dev
"""
import asyncio
from pathlib import Path
from google import genai
from google.genai import types
from google.genai.errors import APIError

from app.state import STATE
from app import tools
from context.skills import SKILLS
from context.memory import read_memory


WRITE_TOOLS = {"write_file", "patch_file", "delete_file"}


class QuotaException(Exception):
    """Raised when Gemini returns a 429 quota exhaustion or rate limit."""
    pass


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
        f"OPERATIONAL STATE:\n- User: {STATE.username}\n- Mode: {STATE.mode}\n- Model: {STATE.model}\n- Project Root: {STATE.root}",
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
    client = genai.Client()
    return client.chats.create(
        model=STATE.model,
        config=types.GenerateContentConfig(
            tools=[types.Tool(function_declarations=_compile_tool_definitions())],
            system_instruction=_system_prompt(),
        ),
    )


def _get_text(response) -> str:
    try:
        t = response.text
        return t or ""
    except Exception:
        out = []
        for c in response.candidates or []:
            for p in c.content.parts or []:
                if getattr(p, "text", None):
                    out.append(p.text)
        return "".join(out)


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


async def run_turn(chat, user_text: str, log, request_approval):
    try:
        response = await asyncio.to_thread(chat.send_message, user_text)
    except Exception as e:
        err_str = str(e).lower()
        if "429" in err_str or "quota" in err_str or "rate limit" in err_str:
            raise QuotaException(str(e))
        raise e

    while True:
        text = _get_text(response)
        if text:
            log(text)

        calls = response.function_calls or []
        if not calls:
            break

        parts = []
        for call in calls:
            name = call.name
            args = dict(call.args or {})

            if STATE.mode == "plan" and name in WRITE_TOOLS:
                result = "BLOCKED: plan mode - read tools only. Explain your architectural plan instead."
            elif STATE.mode == "accept" and name in WRITE_TOOLS:
                approved = await request_approval(name, args)
                if approved:
                    result = await asyncio.to_thread(dispatch, name, args)
                else:
                    result = "DENIED by user."
            else:
                result = await asyncio.to_thread(dispatch, name, args)

            parts.append(
                types.Part.from_function_response(name=name, response={"result": result})
            )

        try:
            response = await asyncio.to_thread(chat.send_message, parts)
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "quota" in err_str or "rate limit" in err_str:
                raise QuotaException(str(e))
            raise e

    return response
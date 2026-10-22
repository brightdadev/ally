"""
LLM Agent integration powered by Google GenAI.
Author: Bright da dev
"""
import asyncio
from google import genai
from google.genai import types

from state import STATE
import tools


TOOL_DEFS = [
    types.FunctionDeclaration(
        name="read_file",
        description="Read a file's full contents.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={"path": types.Schema(type=types.Type.STRING)},
            required=["path"],
        ),
    ),
    types.FunctionDeclaration(
        name="write_file",
        description="Create or overwrite a file with the given content.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "path": types.Schema(type=types.Type.STRING),
                "content": types.Schema(type=types.Type.STRING),
            },
            required=["path", "content"],
        ),
    ),
    types.FunctionDeclaration(
        name="patch_file",
        description="Replace one occurrence of 'old' with 'new' in a file.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "path": types.Schema(type=types.Type.STRING),
                "old": types.Schema(type=types.Type.STRING),
                "new": types.Schema(type=types.Type.STRING),
            },
            required=["path", "old", "new"],
        ),
    ),
    types.FunctionDeclaration(
        name="delete_file",
        description="Delete a file.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={"path": types.Schema(type=types.Type.STRING)},
            required=["path"],
        ),
    ),
    types.FunctionDeclaration(
        name="list_dir",
        description="List entries in a directory.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={"path": types.Schema(type=types.Type.STRING)},
        ),
    ),
]

WRITE_TOOLS = {"write_file", "patch_file", "delete_file"}

SYSTEM = (
    "You are Ally, a terminal coding assistant authored by Bright da dev. Work in stages. "
    "In plan mode, only read files and describe a plan; do not call write tools. "
    "When the user asks you to code, use tools one step at a time: create or modify "
    "ONE file per turn, then stop and report. Prefer patch_file over write_file for edits. "
    "Be concise."
)


def _system_prompt() -> str:
    parts = [SYSTEM, f"Current mode: {STATE.mode}.", f"Project root: {STATE.root}."]
    if STATE.project_brief:
        parts.append("PROJECT BRIEF:\n" + STATE.project_brief)
    return "\n\n".join(parts)


def new_chat():
    client = genai.Client()
    return client.chats.create(
        model=STATE.model,
        config=types.GenerateContentConfig(
            tools=[types.Tool(function_declarations=TOOL_DEFS)],
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
    fn = getattr(tools, name, None)
    if not fn:
        return f"ERROR: unknown tool {name}"
    try:
        return fn(**args)
    except Exception as e:
        return f"ERROR: {e}"


async def run_turn(chat, user_text: str, log, request_approval):
    response = await asyncio.to_thread(chat.send_message, user_text)

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
                result = "BLOCKED: plan mode — read tools only. Describe your plan instead."
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

        response = await asyncio.to_thread(chat.send_message, parts)

    return response

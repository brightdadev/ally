"""
Skill Registry orchestrator for Ally.
Author: Bright da dev
"""
from typing import Callable, Dict, Any, List
from context.skills.git_skill import get_git_status
from context.skills.info_skill import get_project_tree
from context.memory import record_decision


class SkillRegistry:
    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
        self._specs: List[Dict[str, Any]] = []
        self._register_default_skills()

    def _register_default_skills(self):
        self.register(
            name="get_git_status",
            description="Inspect the current git branch, staged files, and modified working tree.",
            handler=get_git_status,
            properties={},
            required=[],
        )
        self.register(
            name="get_project_tree",
            description="Inspect directory layout and file hierarchy of the project workspace.",
            handler=get_project_tree,
            properties={"max_depth": {"type": "integer", "description": "Depth level (default: 2)"}},
            required=[],
        )
        self.register(
            name="record_decision",
            description="Record a significant architectural decision or milestone into .ally/memory.md.",
            handler=record_decision,
            properties={
                "decision": {"type": "string", "description": "The architectural decision or fact to retain."},
                "category": {"type": "string", "description": "Category (Architecture, Convention, Security)"},
            },
            required=["decision"],
        )

    def register(self, name: str, description: str, handler: Callable, properties: dict, required: list = None):
        self._handlers[name] = handler
        self._specs.append({
            "name": name,
            "description": description,
            "properties": properties,
            "required": required or [],
        })

    def get_specs(self) -> List[Dict[str, Any]]:
        return list(self._specs)

    def get_declarations(self):
        try:
            from google.genai import types
        except ImportError:
            return []

        declarations = []
        for s in self._specs:
            schema_props = {}
            for k, v in s["properties"].items():
                p_type = types.Type.INTEGER if v.get("type") == "integer" else types.Type.STRING
                schema_props[k] = types.Schema(type=p_type, description=v.get("description", ""))

            declarations.append(
                types.FunctionDeclaration(
                    name=s["name"],
                    description=s["description"],
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties=schema_props,
                        required=s["required"],
                    ),
                )
            )
        return declarations

    def get_handler(self, name: str):
        return self._handlers.get(name)


SKILLS = SkillRegistry()
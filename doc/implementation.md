# Ally Implementation Architecture

Author: Bright da dev
Version: 0.1.2

This document details the architectural design, internal data flows, and security mechanics of the Ally terminal coding agent.

---

## 1. High-Level Architecture

Ally is built on a decoupled, four-pillar modular design:

- state.py: Thread-safe, reactive state container holding runtime configuration.
- tools.py: Sandboxed filesystem engine enforcing boundary confinement.
- agent.py: Google GenAI tool-calling orchestrator with dynamic mode gating.
- main.py: Textual-based terminal user interface (TUI) with an asynchronous event loop.

---

## 2. Security Subsystem (Path Jail)

To prevent prompt injection or malicious LLM tool calls from reading or modifying sensitive host files, tools.py implements path containment:

- Every file path passed to _resolve() is resolved against STATE.root.
- target.relative_to(root) is evaluated before every filesystem interaction.
- If an operation resolves outside the designated root directory, a PermissionError is raised immediately and reported back to the LLM.

---

## 3. Agent Execution & Approval Pipeline

The core execution loop in agent.py implements a finite state machine with three modes:

1. Plan Mode (mode = "plan"):
   - Write tools (write_file, patch_file, delete_file) are blocked at dispatch.
   - The LLM can only query structure and inspect code.

2. Accept Mode (mode = "accept"):
   - Write tools pause the execution loop.
   - An asynchronous Future is sent to the Textual UI.
   - The user inspects the preview/diff and approves (y) or denies (n).

3. Auto Mode (mode = "auto"):
   - Tool calls execute directly and stream output back into the conversation context.

---

## 4. UI Layer (Textual)

The TUI in main.py runs an async event-driven interface:
- RichLog widget: Renders colorized output and formatted previews.
- Static widget: Displays active mode, model name, and project root.
- Input widget: Captures user prompts and slash-commands (/help, /model, /enter, /plan, /accept, /auto, /reset, /quit).
- python-dotenv integration automatically injects credentials on boot.
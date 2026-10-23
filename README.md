# Ally - Terminal Coding Agent

Author: Bright da dev
Version: 1.0.5
License: MIT

Ally is an autonomous Terminal-Native IDE coding assistant powered by Google Gemini. Designed with clean architecture, a pitch-black minimalist terminal aesthetic, sandboxed filesystem execution, dual-key auto-failover, and real-time execution tracing.

---

## Highlights in v1.0.5

- Pitch-Black Canvas (#000000): Zero blue/slate tinting. Pure black developer interface with subtle #1a1a1a graphite dividers.
- 3-Column Terminal IDE:
  - Left: Interactive Project Explorer (`Ctrl+B` to toggle).
  - Center: Conversation Workspace with Rich Markdown cards.
  - Right: Real-time Process & Execution Monitor (`Ctrl+P` to toggle).
- Dual API Key Management & Auto-Failover: Configure Primary Key (Key 1) and Backup Key (Key 2). If Key 1 hits Google rate limits (429), Ally automatically hot-swaps to Key 2.
- Token Analytics Screen (`F4` or `/usage`): Tracks live prompt tokens, completion tokens, combined consumption, and per-key request distributions.
- Sub-Second Token Streaming: Asynchronous threadsafe queue bridge delivering real-time streaming with zero UI freeze.
- Sandboxed Filesystem Defense: All read, write, patch, and delete operations are strictly verified within project boundaries.

---

## Keybindings & Shortcuts

| Shortcut | Description |
| :--- | :--- |
| F1 | Open Command Guide |
| F2 | Model Switcher |
| F3 | Project Prep Wizard (generates project.md) |
| F4 | Token Usage & Key Statistics |
| Ctrl+B | Toggle Project Explorer Sidebar |
| Ctrl+P | Toggle Process Monitor Drawer |
| Ctrl+K | Configure Dual API Keys (Key 1 & Key 2) |
| Ctrl+O | Developer Profile Settings |
| Ctrl+Q | Exit Application |

---

## Slash Commands

- `/help` - View available commands
- `/usage` - Open Token Analytics modal
- `/key` - Configure Gemini API keys
- `/model <name>` - Switch active model
- `/models` - List catalog models
- `/prep` - Launch Project Prep Wizard
- `/plan` - Read-only planning mode
- `/accept` - Human-in-the-loop approval mode
- `/auto` - Autonomous file modification mode
- `/status` - Display active runtime state
- `/reset` - Clear chat context
- `/quit` - Exit Ally

---

## Architecture
ally/
├── app/ # Core engine
│ ├── agent.py # Real-time queue streaming & tool loop
│ ├── state.py # Reactive state & token tracking
│ ├── tools.py # Sandboxed filesystem CRUD
│ └── model/ # Dynamic model router (models.json)
├── user/ # Profile & dual key storage
│ ├── onboarding.py # Global ~/.ally/user_profile.json
│ └── project_prep.py # Project brief & memory initialization
├── context/ # Memory & capabilities
│ ├── memory.py # Autonomous .ally/memory.md
│ └── skills/ # Git status, workspace tree, decision tools
├── tui/ # Pitch-black presentation layer
│ ├── app.py # 3-column Textual IDE
│ └── screens/ # Keys, Usage, Models, Prep, Onboarding
├── ally.md # Operating constitution
├── pyproject.toml # PEP 621 packaging
├── CHANGELOG.md # Release history
└── README.md # Documentation
---

## Installation & Setup

1. Install package in editable mode:
   pip install -e .

2. Launch Ally:
   ally

3. Set API Keys:
   Press Ctrl+K inside the app to paste your Gemini API keys (Key 1 and optional Key 2). Keys are safely saved to local .env and globally in ~/.ally/.

---

## Author

Bright da dev
Backend Developer & System Architect
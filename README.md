# Ally - Terminal Coding Agent

**Author:** Bright da dev  
**Version:** 1.1.0  
**License:** MIT

Ally is a terminal-native coding assistant powered by Google Gemini. It runs as a three-column IDE in your terminal with sandboxed filesystem access, dual API key failover, token analytics, and real-time execution monitoring. Version 1.1.0 adds a collaborative planning workflow, a terminal command runner, context filtering, and more resilient session memory.

---

## Features

### Core (v1.0.5)
- **3-Column Terminal IDE**  
  Left: Project Explorer (`Ctrl+B`)  
  Center: Conversation workspace with Markdown support  
  Right: Process and execution monitor (`Ctrl+P`)
- **Dual API Key Management**  
  Configure a primary and backup Gemini key. If the primary hits a rate limit (429), Ally switches to the backup automatically.
- **Token Analytics**  
  Press `F4` or run `/usage` to see prompt tokens, completion tokens, total consumption, and per-key request distribution.
- **Real-Time Token Streaming**  
  Asynchronous queue bridge for sub-second streaming without freezing the UI.
- **Sandboxed Filesystem**  
  All read, write, patch, and delete operations are verified within the project root.
- **Pitch-Black Interface**  
  Pure black (`#000000`) canvas with `#1a1a1a` graphite dividers.

### New in v1.1.0
- **Collaborative Planning**  
  Ally asks clarifying questions and proposes a plan before creating files or assuming project scope. After you approve, it executes multi-step changes without stopping for routine approvals.
- **Terminal Command Runner (`run_command`)**  
  Run tests (`pytest`, `npm test`), build scripts (`next build`), and port checks directly. Commands have a 30-second timeout and run isolated (`CREATE_NO_WINDOW`, `DEVNULL` stdin) to avoid console corruption.
- **Security and Context Filtering (`.allyignore`)**  
  Blocks sensitive files (`.env`, `.ssh/`, `id_rsa`, `*.pem`, `*.key`) from reaching the Gemini API. Filters large directories (`node_modules/`, `.git/`, `.venv/`, `dist/`, `build/`, etc.) from context snapshots.
- **Status Indicator**  
  A pulsing 3-dot animation (`● ○ ○` → `○ ● ○` → `○ ○ ●`) and plain status text: “Ally is thinking...”, “Ally is working on your code...”, “Ally is ready”.
- **Resilient Session Memory**  
  Network errors no longer clear chat history. 503 responses retry with exponential backoff. On first entry, Ally detects the workspace tech stack and stores project memory in `.ally/memory.md`.

---

## Installation

```bash
git clone https://github.com/<your-username>/ally.git
cd ally
pip install -e .
ally
```

### API Key Setup
Press `Ctrl+K` inside the app, or run `/key`, to paste your Gemini API keys (Key 1 and optional Key 2). Keys are saved to the local `.env` and globally in `~/.ally/`.

---

## Usage

### Keybindings

| Shortcut | Action |
|----------|--------|
| F1 | Command guide |
| F2 | Model switcher |
| F3 | Project prep wizard (generates `project.md`) |
| F4 | Token usage and key statistics |
| Ctrl+B | Toggle project explorer |
| Ctrl+P | Toggle process monitor |
| Ctrl+K | Configure API keys |
| Ctrl+O | Developer profile settings |
| Ctrl+Q | Exit |

### Slash Commands

| Command | Description |
|---------|-------------|
| `/help` | List available commands |
| `/usage` | Open token analytics |
| `/key` | Configure Gemini API keys |
| `/model <name>` | Switch active model |
| `/models` | List catalog models |
| `/prep` | Launch project prep wizard |
| `/plan` | Read-only planning mode |
| `/accept` | Human-in-the-loop approval mode |
| `/auto` | Autonomous file modification mode |
| `/status` | Show active runtime state |
| `/reset` | Clear chat context |
| `/quit` | Exit Ally |

---

## Architecture

```
ally/
├── app/                  # Core engine
│   ├── agent.py          # Queue streaming and tool loop
│   ├── state.py          # Reactive state and token tracking
│   ├── tools.py          # Sandboxed filesystem CRUD and run_command
│   └── model/            # Dynamic model router (models.json)
├── user/                 # Profile and key storage
│   ├── onboarding.py     # Global ~/.ally/user_profile.json
│   └── project_prep.py   # Project brief and memory initialization
├── context/              # Memory and capabilities
│   ├── memory.py         # Autonomous .ally/memory.md
│   └── skills/           # Git status, workspace tree, decision tools
├── tui/                  # Terminal presentation layer
│   ├── app.py            # 3-column Textual IDE
│   └── screens/          # Keys, Usage, Models, Prep, Onboarding
├── ally.md               # Operating constitution
├── pyproject.toml        # PEP 621 packaging
├── CHANGELOG.md          # Release history
└── README.md
```

---

## Configuration

- **`.allyignore`**  
  Place this file in your project root to extend the default filter list. Ally already blocks common secrets and large directories by default.

- **Project memory**  
  Stored in `.ally/memory.md`. Ally updates it automatically as it learns about your project.

- **API keys**  
  Saved locally in `.env` and globally in `~/.ally/`. The backup key is used only when the primary fails with a 429.

---

## License

MIT

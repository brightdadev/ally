# Changelog

All notable changes to Ally are documented in this file.
Author: Bright da dev

---

## [1.0.2-nightly] - 2026-10-22

### Added
- True real-time streaming via asynchronous thread-safe queue bridge (`asyncio.Queue`).
- Immediate inline chatting indicator (`Ally: ⠋ Thinking...`) directly in the conversation log.
- Textual `@work` background worker ensuring complete TUI fluidity during token generation.
- 503 Server Overload handling with automatic graceful recovery alerts.
- Dedicated in-app API Key modal (`ApiKeyModal`) and context-aware Model Selector (`F2`).

### Changed
- Purged all legacy models; strictly standardized on next-gen catalog:
  - gemini-4-argon
  - gemini-3.8-flash
  - gemini-3.7-flash (Default)
  - gemini-3.1-pro-preview
- Fixed generator blocking bug by eliminating synchronous `list()` consumption.

---

## [1.0.1] - 2026-10-22

### Added
- Complete Clean Architecture overhaul (`app/`, `user/`, `context/`, `tui/`).
- Terminal-native IDE layout with collapsible File Explorer sidebar (`Ctrl+B`).
- Native in-app GEMINI_API_KEY onboarding and configuration (`Ctrl+K`).
- Dynamic model catalog (`app/model/models.json`) and instant Model Switcher (`F2`).
- Project Prep Wizard (`F3`) and persistent markdown memory (`.ally/memory.md`).
- Behavioral operating constitution (`ally.md`).
- Sandboxed filesystem tools with path traversal defense (`tools.py`).
- Extensible context skills registry (`context/skills/`).
- Persistent transport connection pooling for Google GenAI client.
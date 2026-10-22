# Changelog

All notable changes to Ally are documented in this file.
Author: Bright da dev

---

## [1.0.3] - 2026-10-22

### Added
- **3-Column Terminal IDE**: Integrated right-hand **Process & Execution Monitor** pane tracking real-time thoughts, tool calls, and milestones with timestamps.
- **Formal Markdown Response Cards**: Responses render inside stylized, bordered panels (`Panel(Markdown)`), eliminating raw `###`, `---`, and symbol clutter.
- **Clean Actionable Error Cards**: Parsed Google API error cards (429, 503, socket disconnects) replacing raw internal JSON RPC dictionary dumps.
- **Header Branding**: App header officially branded as `Ally` (replacing default `AllyApp`).
- **Keyboard Controls**: Added `Ctrl+P` to toggle the Process Monitor drawer on/off.

### Fixed
- **Safe Tool Chunk Extraction**: Prevented socket aborts (`WinError 10053`) caused by accessing `.text` when Gemini emits function call candidates.
- **Session Auto-Heal**: Automatically resets chat state on connection drops to prevent consecutive user turn desyncs.

---

## [1.0.2-nightly] - 2026-10-22
- Real-time token streaming via asynchronous thread-safe queue bridge (`asyncio.Queue`).
- Inline chatting thinking indicator (`⠋ Thinking...`) in the conversation stream.
- Textual `@work` non-blocking worker thread.
- Enforced next-gen model catalog.

---

## [1.0.1] - 2026-10-22
- Complete Clean Architecture overhaul (`app/`, `user/`, `context/`, `tui/`).
- Initial Terminal IDE layout.
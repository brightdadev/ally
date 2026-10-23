# Changelog

All notable changes to Ally are documented in this file.
Author: Bright da dev

---

## [1.0.4] - 2026-10-22

### Added
- **Dual API Key Management (Total: 2 Keys)**: Primary Key (`Key 1`) and Backup Key (`Key 2`).
- **Automatic Quota Failover**: Hot-rotates from Key 1 to Key 2 seamlessly when Google's daily rate-limit (429) is encountered.
- **Token Usage Analytics Screen (`F4` or `/usage`)**: Live metrics tracking total requests, prompt tokens, completion tokens, combined consumption, and per-key distribution.
- Clean human-readable error formatting cards, eliminating raw internal JSON dumps.

### Changed
- Replaced `gemini-3.7-flash` with **`gemini-3.6-flash`** as primary default model.
- Fixed indentation in `tui/app.py` for `TokenUsageModal`.

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
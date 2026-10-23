# Changelog

All notable changes to Ally are documented in this file.
Author: Bright da dev

---

## [1.0.5] - 2026-10-22

### Added
- **Pitch-Black Terminal Interface**: Unified absolute black `#000000` canvas across canvas, explorer, conversation log, process monitor, and composer.
- **De-Cluttered Minimalist Workflow**: Streamlined startup into a subtle 2-line terminal statusline; user prompts render as clean `you > <text>` CLI lines.
- **Subdued Graphite Dividers**: Razor-sharp `#1a1a1a` 1px borders between panels and response cards.
- **Pure-Black Header & Footer**: Seamless `#000000` status bars with muted `#555555` shortcuts.

### Fixed
- Fixed Rich markup parser exception on composite closing tags.

---

## [1.0.4] - 2026-10-22
- Dual API Key management (Primary Key 1 + Backup Key 2) with automatic quota failover.
- Replaced 3.7 with `gemini-3.6-flash` as primary standard model.
- Added Token Usage Screen (`F4` or `/usage`).
- Clean human-readable error cards.

---

## [1.0.3] - 2026-10-22
- 3-column layout with real-time Process Monitor (`Ctrl+P`).
- Markdown response rendering.
- Header branded as `Ally`.

---

## [1.0.2-nightly] - 2026-10-22
- Real-time token streaming via `asyncio.Queue`.
- Inline thinking indicator.

---

## [1.0.1] - 2026-10-22
- Complete Clean Architecture overhaul (`app/`, `user/`, `context/`, `tui/`).
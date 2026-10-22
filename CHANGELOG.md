# Changelog

All notable changes to Ally are documented in this file.
Author: Bright da dev

---

## [1.0.4] - 2026-10-22

### Added
- **Dual API Key Management**: Support for Primary Key (`Key 1`) and Secondary Key (`Key 2`).
- **Automatic Quota Failover**: When Key 1 hits Google's free-tier rate limit (429), Ally automatically hot-rotates to Key 2 seamlessly and retries the turn.
- **Token Usage Analytics Screen (`F4` or `/usage`)**: Tracks total turns, prompt tokens, candidate tokens, total token consumption, and per-key request distributions.
- Clean human-readable error formatting cards, eliminating raw Google RPC stack dumps.

### Changed
- Replaced `gemini-3.7-flash` with **`gemini-3.6-flash`** as the default primary standard model.
- Updated `ApiKeyModal` with dual key configuration inputs.
- Safe chunk extraction avoiding socket aborts on tool calls.

---

## [1.0.3-nightly] - 2026-10-22
- Dedicated 3-column IDE layout with real-time Process Monitor.
- Formal Markdown Response Cards (`Panel(Markdown)`).
- Header branded as `Ally`.

---

## [1.0.2-nightly] - 2026-10-22
- Real-time token streaming via `asyncio.Queue`.
- Inline thinking indicator.

---

## [1.0.1] - 2026-10-22
- Complete Clean Architecture overhaul (`app/`, `user/`, `context/`, `tui/`).
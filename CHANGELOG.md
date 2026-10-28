# Changelog

All notable changes to Ally are documented in this file.
Author: Bright da dev

---

## [1.0.6] - 2026-10-22

### Added
- **Permanent SGR Mouse Tracking Disabling**: Completely disabled terminal mouse coordinate reporting, permanently killing all raw `35;...M` escape code spam in the input bar.
- **.allyignore Shield Engine**: Project-level security shield blocking Ally from accessing, reading, or traversing `.env`, `node_modules/`, `dist/`, `build/`, and `.git/`.
- **run_command Execution Tool**: Sandboxed command execution with stdout/stderr capture, allowing Ally to run `npm install`, `build`, `test`, and framework CLI tools.
- **Deadlock-Proof Process Termination**: Integrated `_kill_process_tree` with Windows `taskkill /F /T /PID` to forcibly kill hanging processes on timeout.
- **Dev Server Probing Engine**: Persistent background server lifecycle for `npm run dev`, `vite`, etc., with live preview URL extraction.
- **Smart Direct Execution**: Skips permission prompts when user issues explicit imperative orders (`create`, `run`, `make`, `install`, `do it`).
- **Dynamic Whitelist (`app/whitelist.json`)**: Expandable JSON registry of safe inspection commands that execute with zero permission stops.

---

## [1.0.5] - 2026-10-22
- Pure pitch-black (`#000000`) terminal interface with `#1a1a1a` graphite dividers.
- Dual API keys with auto-failover (Key 1 -> Key 2).
- Token analytics screen (`F4` or `/usage`).
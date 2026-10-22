# Ally - Terminal Coding Agent

Author: Bright da dev
Version: 0.1.2
License: MIT

Ally is an interactive Terminal User Interface (TUI) coding assistant powered by Google Gemini. It operates directly inside your workspace with sandboxed filesystem execution, structured approval modes, and real-time streaming feedback.

## Features
- Terminal User Interface (TUI) via Textual and Rich
- Path-traversal containment defense
- Modes: plan (read-only), accept (approval prompt), auto (autonomous)
- Built-in file tools: read_file, write_file, patch_file, delete_file, list_dir

## Quickstart
1. Install dependencies:
   pip install -e .

2. Setup API key:
   Copy .env.example to .env and insert your GEMINI_API_KEY.

3. Launch:
   ally
   (or: python main.py)

## Author
Bright da dev
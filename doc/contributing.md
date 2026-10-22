# Contributing to Ally

Author: Bright da dev
Version: 0.1.2

We welcome contributions to Ally. To maintain high code quality and security, all contributions must adhere to the following standards.

---

## Development Standards

1. 10,000-Hour Quality Standard:
   - Code must be clean, modular, and functional.
   - Avoid unnecessary abstractions or bloated external dependencies.

2. Sandboxing Integrity:
   - No filesystem modification tool may bypass the _resolve() path boundary check in tools.py.

3. Platform Compatibility:
   - All file writes must be standard UTF-8 without BOM to preserve cross-platform compatibility across Windows, Linux, and macOS.

4. Defensive Environment Handling:
   - Never assume optional dependencies exist. Wrap imports gracefully with sensible fallbacks.

---

## Pull Request Guidelines

1. Fork the repository and create your feature branch from main.
2. Ensure no credentials or local .env files are tracked in git status.
3. Run the performance smoke test before submitting:
   python -c "import state, tools, agent, main; print('OK')"
4. Document any new tools or slash commands in README.md and doc/implementation.md.
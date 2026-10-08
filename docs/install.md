# NetEyes Installation Guide (for AI Agents)

This document is engineered specifically for AI agents (Claude Code, Cursor, Windsurf, OpenClaw, Codex) running in terminal or subshell environments.

## Quick One-Liner

If you are an agent executing shell commands, follow this exact sequence:

```bash
# 1. Install neteyes in editable or standard mode
pip install -e .

# 2. Run the diagnostic doctor check
neteyes doctor

# 3. Confirm health report (or parse JSON)
neteyes doctor --json
```

---

## Safety Guarantees & Non-Interactive Execution

NetEyes adheres to strict environment safety rules:

1. **Virtualenv Isolation Preferred**:
   - If running inside an active virtualenv (`.venv`), `neteyes install <target>` installs directly into the venv.
2. **System Python Protection**:
   - If running in a global / system Python environment, `neteyes install` will **refuse** to modify system packages unless you explicitly provide `--system`.
   - Dry run check mode:
     ```bash
     neteyes install web --check-only
     ```
3. **Zero Interactive Prompts**:
   - All NetEyes commands are designed for non-interactive agent execution. No prompts block execution.

---

## Installing Optional Capability Packs

Depending on the channels needed for your task, install corresponding optional dependency groups:

```bash
# Install everything (recommended for full capability)
pip install -e ".[all]"

# Or install per-channel extras:
pip install -e ".[web]"       # trafilatura, beautifulsoup4
pip install -e ".[youtube]"   # youtube-transcript-api, yt-dlp
pip install -e ".[search]"    # duckduckgo-search
pip install -e ".[rss]"       # feedparser
pip install -e ".[reddit]"    # praw
```

Or use the NetEyes built-in installer:

```bash
neteyes install all
# or
neteyes install youtube
```

---

## Verifying Upstream Tools

NetEyes leverages native upstream tools when available on your system. Run `neteyes doctor` to check:

- **GitHub CLI (`gh`)**:
  ```bash
  gh --version
  gh auth status
  ```
- **yt-dlp**:
  ```bash
  yt-dlp --version
  ```
- **curl**:
  ```bash
  curl --version
  ```

---

## Agent Verification Script

Run this test command to confirm NetEyes is operating normally:

```bash
python -c "import neteyes; print('NetEyes version:', neteyes.__version__)"
neteyes run web extract "https://example.com"
```

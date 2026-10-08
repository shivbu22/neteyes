<div align="center">

<img src="assets/netty.png" alt="Netty - NetEyes Mascot" width="220" style="border-radius: 24px; box-shadow: 0 10px 30px rgba(0, 150, 255, 0.25);" />

# NetEyes 👁️✨
### Meet **Netty** — Giving Any AI Agent Real Eyes on the Internet

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)
[![Built with Hatchling](https://img.shields.io/badge/Build-Hatchling-purple.svg)](https://hatch.pypa.io/)
[![Zero Config](https://img.shields.io/badge/Zero--Config-Supported-success.svg)](#zero-config-channels)
[![Mascot: Netty](https://img.shields.io/badge/Mascot-Netty%20%F0%9F%91%81%EF%B8%8F%E2%9C%A8-cyan.svg)](#-meet-netty--the-official-neteyes-mascot)

</div>

---

## 👁️ Meet Netty — The Official NetEyes Mascot

> *"Hi! I'm Netty, your internet perception buddy! Never blind an AI agent when the internet is wide open!"*

**Netty** is the curious, high-bandwidth cyber-scout living inside NetEyes. Netty is a round, friendly optic explorer equipped with a cosmic deep-space iris, a multi-spectrum wireless antenna, and little cyber-sneakers for running across platforms.

Whenever your AI agent needs information from the web, YouTube, Reddit, or GitHub, Netty springs into action:
- 🔭 **Optical Zoom:** Extracts clean Markdown while filtering out ads, popups, and tracker noise.
- 🥷 **Stealth Walk:** Seamlessly bypasses rate limits with managed proxy rotation.
- 🔑 **Passkey Bag:** Safely carries local browser cookies to access walled content without sharing credentials.
- ⚡ **Fast Delivery:** Feeds structured knowledge directly to Claude, Cursor, and Windsurf via MCP stdio.

```bash
# Meet Netty in your terminal anytime!
neteyes mascot
```

---

NetEyes is a **capability layer** and multi-backend router for AI agents (Claude Code, Cursor, Windsurf, OpenClaw, Codex).

Instead of creating another fragile, monolithic web scraper wrapper, NetEyes:
- **Selects the best current backend** for each internet platform
- **Health-checks and installs** those backends with non-destructive diagnostics
- **Routes the agent directly to the optimal upstream CLI / tool** (`neteyes route`) so agents can execute commands natively without wrapper bloat
- **Provides unified execution with automatic fallback chains** (`neteyes run`) when primary tools fail or are blocked
- **Manages local browser session cookies** for walled platforms (Twitter/X, Bilibili, Xiaohongshu, LinkedIn)


---

## ⚡ Quickstart

### 1. Installation

```bash
# Clone and install in editable mode
git clone https://github.com/shivbu22/neteyes.git
cd neteyes
pip install -e .

# Or install with all optional dependencies
pip install -e ".[all]"
```

### 2. Run the Health Doctor

```bash
neteyes doctor
```
```
NetEyes — Give any AI agent real eyes on the internet

System Diagnostic Report
OS: Windows-11 | Python: 3.14 (Virtualenv: False)

Category       Component                Status      Details
environment    Python Version           healthy     Python 3.14.7 (meets requirement >= 3.10)
cli_binary     gh                       healthy     Found on system PATH (GitHub official CLI)
cli_binary     curl                     healthy     Found on system PATH (Standard HTTP utility)
package        trafilatura              healthy     Installed (v2.3.1)
package        duckduckgo_search        healthy     Installed (v8.1.1)
channel        web                      healthy     Web Pages — Ready for routing
channel        search                   healthy     Web Search (Free) — Ready for routing
channel        youtube                  healthy     YouTube — Ready for routing
channel        reddit                   healthy     Reddit — Ready for routing
```

Or for machine-readable JSON:
```bash
neteyes doctor --json
```

---

## 🧭 Core Workflow: Routing vs Execution

NetEyes gives AI agents two seamless execution modes:

### Mode 1: Direct Capability Routing (`neteyes route`)
Get the exact upstream CLI command to run directly in your shell:

```bash
neteyes route web extract "https://news.ycombinator.com"
```
```
Capability Route: web -> extract
Selected Backend: Trafilatura (Local Readability) (`trafilatura`)
Routing Reason:   Selected 'Trafilatura' - Health: healthy
Fallback Chain:   trafilatura -> jina_reader -> direct_http

Direct Upstream Command (Run in Shell):
trafilatura -u "https://news.ycombinator.com" --output-format markdown
```

### Mode 2: Unified Execution with Auto-Fallback (`neteyes run`)
Execute directly through NetEyes. If the primary backend is unavailable or blocked, NetEyes automatically attempts the fallback chain:

```bash
# Extract clean Markdown from any web page
neteyes run web extract "https://en.wikipedia.org/wiki/Artificial_intelligence"

# Free web search (no API keys required)
neteyes run search query "latest AI reasoning models"

# Extract timestamped YouTube transcript
neteyes run youtube transcript "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Read Reddit discussion thread & top comments
neteyes run reddit sub "LocalLLaMA" limit=5

# Inspect GitHub repository
neteyes run github repo "astral-sh/uv"

# Zero-login Twitter/X tweet extraction
neteyes run twitter tweet "https://x.com/OpenAI/status/1780287739502756019"
```

---

## 🌐 Supported Platforms & Priority

| Platform | Channel | Primary Backend | Secondary Fallback | Zero-Config? |
|---|---|---|---|:---:|
| **Web Pages** | `web` | `trafilatura` (local parsing) | `jina_reader` (cloud JS reader) | ✅ Yes |
| **Web Search** | `search` | `ddg_search` (DuckDuckGo search) | `searxng` (open meta-search) | ✅ Yes |
| **YouTube** | `youtube` | `youtube_transcript` (direct API) | `yt_dlp` (metadata & search) | ✅ Yes |
| **Twitter / X** | `twitter`| `twitter_syndication` (zero-login) | `twitter_session` (cookie session) | ✅ (Tweets) |
| **Reddit** | `reddit` | `reddit_json` (public JSON API) | `praw` (API wrapper) | ✅ Yes |
| **GitHub** | `github` | `gh_cli` (upstream CLI) | `github_api` (REST API) | ✅ Yes |
| **Bilibili** | `bilibili` | `bilibili_web` (public Web API) | `ytdlp_bilibili` (yt-dlp adapter) | ✅ Yes |
| **RSS / Atom** | `rss` | `feedparser` (universal parser) | `xml_rss` (native ElementTree) | ✅ Yes |
| **XiaoHongShu** | `xhs` | `xhs_web` (session state parser) | `xhs_shortlink` (link resolver) | 🔐 Cookies |
| **V2EX** | `v2ex` | `v2ex` (community public API) | - | ✅ Yes |
| **Xueqiu (雪球)**| `xueqiu` | `xueqiu` (stock quotes & search) | - | ✅ Yes |
| **Podcasts** | `podcast` | `podcast_rss` (audio enclosures) | - | ✅ Yes |
| **LinkedIn** | `linkedin` | `linkedin_session` (profile client) | - | 🔐 Cookies |
| **Instagram** | `instagram`| `instagram_session` (web profile) | - | 🔐 Cookies |
| **Boss直聘** | `boss` | `boss_web` (job extractor) | - | 🔐 Cookies |

---

## 🔐 Cookie & Session Management (Walled Gardens)

For platforms that enforce login walls (Xiaohongshu, LinkedIn, Instagram, Boss直聘, Twitter user search):

1. Export cookies from your browser using the **Cookie-Editor** extension (Format: JSON) or Netscape `cookies.txt`.
2. Import the cookies into NetEyes:
   ```bash
   neteyes auth twitter --import twitter_cookies.json
   neteyes auth xhs --import xhs_cookies.json
   ```
3. Check authentication status across all platforms:
   ```bash
   neteyes auth status
   ```
4. Delete cookies when no longer needed:
   ```bash
   neteyes auth delete twitter
   ```

> **Privacy Guarantee**: Cookies are saved strictly on your local machine (`~/.neteyes/cookies/<platform>.json`). They are **never** uploaded to any external server or telemetry service.

---

## 🛡️ Safe-by-Default Installer

NetEyes prevents unintended modifications to system Python environments:

```bash
# Check what is missing without installing (dry-run)
neteyes install web --check-only

# Install dependencies for a specific channel
neteyes install youtube

# Install into system Python requires explicit permission flag
neteyes install all --system
```

---

## ⚙️ Configuration & Backend Preferences

Override default backend priority or set custom proxies in `~/.neteyes/config.json`:

```bash
# View current configuration
neteyes config show

# Set preferred backend for a channel
neteyes config prefer web trafilatura
```

---

## 🖥️ Live Terminal Dashboard (`neteyes dashboard`)

Launch a real-time terminal visual operations monitor showing channel health, active backends, cookie statuses, and proxy pools:

```bash
# Snapshot overview
neteyes dashboard

# Live auto-refreshing monitor
neteyes dashboard --watch
```

---

## 🔌 Model Context Protocol (MCP) Server

Connect Claude Desktop, Cursor, Zed, or Windsurf directly to NetEyes via standard JSON-RPC stdio:

```bash
# Run server over stdio
neteyes mcp
```

Add to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "neteyes": {
      "command": "neteyes",
      "args": ["mcp"]
    }
  }
}
```

---

## 🛡️ Anti-Blocking & Proxy Pool Manager (`neteyes proxy`)

Prevent IP blocks and rate limits with managed proxy rotation:

```bash
# Add proxies
neteyes proxy add http://127.0.0.1:7890
neteyes proxy add socks5://127.0.0.1:1080

# Select rotation strategy
neteyes proxy strategy round_robin    # or 'failover', 'random'

# Probe latency and connectivity
neteyes proxy test

# View pool status
neteyes proxy list
```

---

## 🤖 AI Agent Integration (`SKILL.md`)

NetEyes is designed from the ground up for agent pairing. Copy `SKILL.md` to your agent's skills directory:

- **Claude Code**: Put in `.claude/skills/neteyes/SKILL.md` or global skills root.
- **Cursor**: Reference in `.cursorrules` or Agent Prompts.
- **Windsurf**: Place in `.windsurfrules`.
- **OpenClaw / Codex**: Reference `neteyes` command line and `neteyes doctor --json`.

---

## 📖 Documentation

- [Architecture & Philosophy](docs/architecture.md) — Why NetEyes is a capability layer.
- [Agent Installation Guide](docs/install.md) — Non-interactive setup for AI agents.

---

## 🧪 Verification & Testing

NetEyes includes built-in verification suites for continuous integration, local testing, and agent environment probing:

```bash
# Full automated unit, integration & resilience test suite (36/36 passing)
python -m pytest -v

# Universal cross-platform functional verifier (Any OS)
python test_neteyes.py

# Full bash verification suite (Linux, macOS, WSL, Git Bash)
./test_neteyes_full.sh

# Windows native PowerShell verification
powershell -ExecutionPolicy Bypass -File test_neteyes.ps1
```

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.

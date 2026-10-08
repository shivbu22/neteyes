---
name: neteyes
description: Capability layer and multi-backend router giving any AI agent real eyes on the internet. Use for web pages, YouTube transcripts/search, Twitter/X, Reddit, GitHub, Bilibili, Xiaohongshu, RSS, and free web search.
---

# NetEyes Skill Guide for AI Agents

NetEyes gives AI agents (Claude Code, Cursor, Windsurf, OpenClaw, Codex) clean, reliable, multi-backend access to the internet without heavy wrappers or fragile single-point scrapers.

## Core Philosophy

NetEyes is a **capability layer**, not a monolithic wrapper:
1. Every platform has an ordered list of backends (primary + fallbacks).
2. You can query the optimal direct upstream command to execute directly in your shell (`neteyes route`).
3. Or you can execute through NetEyes with automatic multi-backend failover (`neteyes run`).
4. Zero-config channels work immediately with zero API keys.
5. Login-walled platforms use secure local browser session cookies (Cookie-Editor format).

---

## Quick Reference Commands

| Intent | Command |
|---|---|
| Health check system & backends | `neteyes doctor` (or `neteyes doctor --json`) |
| Interactive visual dashboard | `neteyes dashboard` (or `neteyes dashboard -w`) |
| List all channels & backends | `neteyes list` |
| Get direct upstream CLI command | `neteyes route <channel> <action> [args...]` |
| Execute with automatic fallback | `neteyes run <channel> <action> [args...]` |
| Sync session cookies from browser | `neteyes auth sync` (`--browser chrome/edge/brave`) |
| Check / import platform cookies | `neteyes auth status` or `neteyes auth import <channel> <file>` |
| Manage proxy pool & anti-blocking | `neteyes proxy add/list/strategy/test` |
| Model Context Protocol (MCP) Server | `neteyes mcp` |
| Safe dependency installation | `neteyes install [channel] [--check-only]` |

---

## High-Priority Channels and Actions

### 1. Web Pages (`web`)
Extracts clean, noise-free Markdown with boilerplate stripped.
- **Backends:** `trafilatura` (local parser) -> `jina_reader` (cloud JS renderer) -> `direct_http`
- **Route / Direct Command:**
  ```bash
  neteyes route web extract "https://example.com/article"
  ```
- **Execute via NetEyes:**
  ```bash
  neteyes run web extract "https://example.com/article"
  ```

### 2. Web Search (`search`)
100% free web search with snippet extraction. No API keys required.
- **Backends:** `ddg_search` (DuckDuckGo Search) -> `searxng` (open meta-search)
- **Route:**
  ```bash
  neteyes route search query "latest AI agents 2026"
  ```
- **Execute:**
  ```bash
  neteyes run search query "latest AI agents 2026" --format=markdown
  ```

### 3. YouTube (`youtube`)
Extracts timestamped video subtitles, search results, and metadata.
- **Backends:** `youtube_transcript` -> `yt_dlp` -> `youtube_direct` (oEmbed)
- **Get Transcript:**
  ```bash
  neteyes run youtube transcript "https://www.youtube.com/watch?v=VIDEO_ID"
  ```
- **Search Videos:**
  ```bash
  neteyes run youtube search "quantum computing explained"
  ```
- **Video Info:**
  ```bash
  neteyes run youtube info "https://www.youtube.com/watch?v=VIDEO_ID"
  ```

### 4. Twitter / X (`twitter`)
Extracts tweets, threads, and engagement without requiring login via syndication CDN.
- **Backends:** `twitter_syndication` (zero-login) -> `twitter_session` (cookie session)
- **Read Tweet (No login needed):**
  ```bash
  neteyes run twitter tweet "https://x.com/username/status/123456789"
  ```
- **Inspect User Profile (Requires cookies):**
  ```bash
  neteyes run twitter user "sama"
  ```

### 5. Reddit (`reddit`)
Zero-config access to subreddits, posts, threads, comments, and search.
- **Backends:** `reddit_json` (public JSON API) -> `praw` (official API wrapper)
- **View Subreddit:**
  ```bash
  neteyes run reddit sub "LocalLLaMA" limit=10
  ```
- **Read Post & Top Comments:**
  ```bash
  neteyes run reddit post "https://www.reddit.com/r/LocalLLaMA/comments/..."
  ```
- **Search Reddit:**
  ```bash
  neteyes run reddit search "fine-tuning reasoning models"
  ```

### 6. GitHub (`github`)
Repositories, README files, open issues, and pull requests.
- **Backends:** `gh_cli` (upstream official `gh` CLI) -> `github_api` (REST API)
- **View Repo:**
  ```bash
  neteyes run github repo "astral-sh/uv"
  ```
- **Fetch Raw README:**
  ```bash
  neteyes run github readme "astral-sh/uv"
  ```
- **List Issues:**
  ```bash
  neteyes run github issues "astral-sh/uv" limit=10
  ```

### 7. Bilibili (`bilibili`)
Video details, view/danmaku stats, and CC subtitles.
- **Backends:** `bilibili_web` -> `ytdlp_bilibili`
- **Video Details:**
  ```bash
  neteyes run bilibili view "BV1xx411c7mD"
  ```
- **Get Subtitles:**
  ```bash
  neteyes run bilibili subtitles "BV1xx411c7mD"
  ```

### 8. XiaoHongShu (`xhs`)
Lifestyle notes, text content, image assets, and engagement stats.
- **Backends:** `xhs_web` -> `xhs_shortlink`
- **Extract Note:**
  ```bash
  neteyes run xhs note "https://www.xiaohongshu.com/explore/NOTE_ID"
  ```
  *(Note: Requires session cookie `a1` or `web_session`)*

### 9. RSS & Atom Feeds (`rss`)
Blog posts, newsletters, and syndication feeds.
- **Backends:** `feedparser` -> `xml_rss`
- **Read Feed:**
  ```bash
  neteyes run rss read "https://news.ycombinator.com/rss" limit=10
  ```

---

## Authentication & Browser Sessions

### Zero-Touch Auto-Sync from Local Browsers
Sync logged-in sessions directly from Chrome, Edge, or Brave profiles with DPAPI decryption:
```bash
neteyes auth sync --browser all
```

### Manual Cookie Import (Cookie-Editor format)
1. Open the target site in your browser and ensure you are logged in.
2. Export cookies using the **Cookie-Editor** browser extension (Format: JSON) or Netscape `cookies.txt`.
3. Save to a file (e.g. `twitter_cookies.json`).
4. Import into NetEyes:
   ```bash
   neteyes auth import twitter twitter_cookies.json
   ```
5. Check authentication health anytime:
   ```bash
   neteyes auth status
   ```
*Cookies remain strictly local inside `~/.neteyes/cookies/` and are never shared or sent to third-party telemetry.*

---

## Model Context Protocol (MCP) Server

Connect Claude Desktop, Cursor, Zed, or Windsurf to NetEyes via standard JSON-RPC stdio.

Add to your `claude_desktop_config.json` or Cursor MCP settings:
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
Exposes:
- `neteyes_doctor` (System health and backend probe)
- `neteyes_web_extract` (Boilerplate-free clean markdown web scraper)
- `neteyes_youtube_transcript` (Timestamped transcripts and subtitles)
- `neteyes_search_query` (Free web search)
- `neteyes_reddit_post`, `neteyes_reddit_sub`, `neteyes_reddit_search`
- `neteyes_github_repo`, `neteyes_github_readme`, `neteyes_github_issues`
- `neteyes_bilibili_view`, `neteyes_bilibili_subtitles`
- `neteyes_xhs_note`

---

## Proxy & Anti-Blocking Rotation Manager

Configure proxy pools with automatic round-robin, random, or failover rotation:
```bash
# Add proxies
neteyes proxy add http://127.0.0.1:7890
neteyes proxy add socks5://127.0.0.1:1080

# Select strategy
neteyes proxy strategy round_robin    # or 'failover', 'random'

# Test latency & reachability
neteyes proxy test

# View active pool
neteyes proxy list
```
When configured, all HTTP requests through NetEyes automatically rotate through the healthy proxy pool.


---

## Agent Troubleshooting Protocol

1. If any command returns degraded output, first run:
   ```bash
   neteyes doctor --json
   ```
2. Review the `fix_prescriptions` list in the output.
3. If dependencies are missing, run safe install:
   ```bash
   neteyes install <channel>
   ```
4. If a specific backend is preferred, configure it:
   ```bash
   neteyes config prefer web trafilatura
   ```

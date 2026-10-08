# NetEyes Architecture & Design Philosophy

> **"NetEyes is a capability layer, not another tool wrapper."**

Traditional agent scraping and internet tools suffer from three fundamental flaws:
1. **Single-point fragility:** One platform layout or anti-bot change breaks the entire tool.
2. **Wrapper bloat:** They wrap CLI tools in heavy layers that introduce latency, obscure upstream errors, and break flag compatibility.
3. **Black-box failures:** When an endpoint fails, the agent receives a generic error with no alternative.

NetEyes solves this through a decoupled **Capability Layer**.

---

## Architecture Diagram

```
                 AI AGENT (Claude Code, Cursor, Windsurf, OpenClaw, Codex)
                                    │
               ┌────────────────────┴────────────────────┐
               │                                         │
        [neteyes route]                           [neteyes run]
               │                                         │
               ▼                                         ▼
   Route Selector & Health Check             Fallback Execution Engine
               │                                         │
               ├─────────────────────────────────────────┤
               │               CHANNELS                  │
               │  web, youtube, twitter, reddit, github, │
               │  bilibili, xhs, rss, search, ...        │
               ├─────────────────────────────────────────┤
               │               BACKENDS                  │
               │  Primary Backend (P10)                  │
               │       │ (if unhealthy / fails)          │
               │       ▼                                 │
               │  Secondary Fallback (P20)               │
               │       │ (if fails)                      │
               │       ▼                                 │
               │  Zero-Dep Fallback (P30)                │
               └────────────────────┬────────────────────┘
                                    │
                                    ▼
         UPSTREAM TOOLS / DIRECT APIS / LOCAL BROWSER COOKIES
      (trafilatura, r.jina.ai, gh, yt-dlp, Reddit JSON, DuckDuckGo)
```

---

## 1. Direct Upstream Execution vs Unified Failover

NetEyes offers two modes depending on what the agent needs:

### Mode A: Direct Capability Routing (`neteyes route`)
When an agent calls `neteyes route <platform> <action> [args...]`, NetEyes evaluates the health of the backends and outputs the **exact upstream CLI command** (e.g. `trafilatura -u "..."` or `gh repo view ...` or `curl -sL "https://r.jina.ai/..."`).

The agent can then copy and execute that command directly in its shell. This eliminates all wrapper overhead and allows the agent full native control over flags and streaming.

### Mode B: Unified Resilient Execution (`neteyes run`)
When an agent wants NetEyes to handle execution and resilience automatically, `neteyes run <platform> <action> [args...]` executes the primary backend. If the primary backend is degraded, blocked, or throws an error, NetEyes immediately catches it and fails over to the secondary backend in the priority chain.

---

## 2. Channels vs Backends Separation

- **`channels/` (Platform Declarations)**:
  Each file in `neteyes/channels/` represents an internet platform or resource type (e.g. `youtube.py`, `reddit.py`, `web.py`). A channel defines supported actions, parameter schemas, whether login is needed, and declares an **ordered priority list of backends**.
  
- **`backends/` (Implementations)**:
  Each backend implements `BaseBackend`. It defines:
  - `check_health()`: Non-destructive health check (verifying binary on PATH, Python import, or endpoint reachability).
  - `get_direct_command()`: Command line string for direct upstream execution.
  - `execute()`: Resilient fetch logic returning unified `ExecutionResult`.

---

## 3. Ordered Fallback Chains

When one backend fails, we reorder or fallback:

| Channel | Primary Backend (P10) | Secondary Fallback (P20) | Tertiary Fallback (P30) |
|---|---|---|---|
| **Web** | `trafilatura` (local parsing) | `jina_reader` (cloud JS renderer) | `direct_http` (native cleaner) |
| **YouTube** | `youtube_transcript` (direct API) | `yt_dlp` (rich metadata & search) | `youtube_direct` (oEmbed) |
| **Twitter** | `twitter_syndication` (zero-login) | `twitter_session` (cookie session) | - |
| **Reddit** | `reddit_json` (zero-config) | `praw` (official API wrapper) | - |
| **GitHub** | `gh_cli` (upstream CLI) | `github_api` (REST API) | - |
| **Bilibili** | `bilibili_web` (public Web API) | `ytdlp_bilibili` (yt-dlp extractor)| - |
| **Search** | `ddg_search` (DuckDuckGo engine)| `searxng` (open meta-search) | `ddg_html` (lite fallback) |
| **RSS** | `feedparser` (universal feed) | `xml_rss` (native ElementTree) | - |

---

## 4. Privacy & Session Cookie Model

For platforms that require login sessions (Xiaohongshu, LinkedIn, Instagram, Boss直聘):
- Users export cookies from browser extensions like **Cookie-Editor** or Netscape format.
- NetEyes parses and saves them exclusively to `~/.neteyes/cookies/<platform>.json`.
- **Zero Cloud Leakage**: Cookies are strictly stored on the user's local filesystem and sent solely to the respective platform domain.

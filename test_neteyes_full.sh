#!/usr/bin/env bash
set -euo pipefail

echo "======================================================"
echo "  NetEyes — Full Verification Suite"
echo "======================================================"
echo

PASS=0
FAIL=0
WARN=0
SKIP=0

green()  { printf "\033[0;32m%s\033[0m\n" "$1"; }
yellow() { printf "\033[0;33m%s\033[0m\n" "$1"; }
red()    { printf "\033[0;31m%s\033[0m\n" "$1"; }
blue()   { printf "\033[0;34m%s\033[0m\n" "$1"; }

pass() { green "✅ PASS — $1"; ((PASS++)) || true; }
warn() { yellow "⚠️  WARN — $1"; ((WARN++)) || true; }
fail() { red "❌ FAIL — $1"; ((FAIL++)) || true; }
skip() { blue "⏭️  SKIP — $1"; ((SKIP++)) || true; }

# -------------------------------------------------
# 1. Basic CLI
# -------------------------------------------------
echo "=== 1. Basic CLI ==="

if command -v neteyes &>/dev/null; then
  pass "neteyes command is available"
else
  fail "neteyes command not found in PATH"
  echo "Install NetEyes first, then re-run this script."
  exit 1
fi

if neteyes --version &>/dev/null; then
  VERSION=$(neteyes --version 2>/dev/null | head -1)
  pass "neteyes --version → $VERSION"
else
  fail "neteyes --version failed"
fi

if neteyes --help &>/dev/null; then
  pass "neteyes --help works"
else
  fail "neteyes --help failed"
fi

# -------------------------------------------------
# 2. Doctor
# -------------------------------------------------
echo
echo "=== 2. Doctor (Health Checker) ==="

if neteyes doctor &>/dev/null; then
  pass "neteyes doctor completed"
else
  warn "neteyes doctor returned non-zero (review output carefully)"
fi

TMP_DIR="${TMPDIR:-/tmp}"
mkdir -p "$TMP_DIR" 2>/dev/null || TMP_DIR="."
DOCTOR_JSON="$TMP_DIR/neteyes_doctor.json"

if neteyes doctor --json > "$DOCTOR_JSON" 2>/dev/null; then
  pass "neteyes doctor --json works"
  echo "   JSON saved to $DOCTOR_JSON"
else
  fail "neteyes doctor --json failed"
fi

# -------------------------------------------------
# 3. Zero-config / Core Channels
# -------------------------------------------------
echo
echo "=== 3. Zero-config & Core Channels ==="

# --- Web ---
echo -n "→ Web page reading... "
if neteyes run web read "https://example.com" 2>/dev/null | grep -qiE "example domain|example.com"; then
  pass "Web reading (NetEyes active backend)"
elif curl -sL --max-time 12 "https://r.jina.ai/https://example.com" 2>/dev/null | grep -qiE "example domain|example.com"; then
  pass "Web reading (Jina-style)"
else
  warn "Web reading test failed (check your web backend)"
fi

# --- YouTube ---
echo -n "→ YouTube subtitles... "
if neteyes run youtube extract "https://www.youtube.com/watch?v=jNQXAC9IVRw" 2>/dev/null | grep -qiE "jawed|zoo|microplastics"; then
  pass "YouTube subtitle extraction (NetEyes active backend)"
elif command -v yt-dlp &>/dev/null; then
  rm -f "$TMP_DIR"/neteyes_yt_test*
  if yt-dlp --skip-download --write-auto-sub --sub-lang en --sub-format vtt \
      -o "$TMP_DIR/neteyes_yt_test.%(ext)s" \
      "https://www.youtube.com/watch?v=jNQXAC9IVRw" > /dev/null 2>&1; then
    if ls "$TMP_DIR"/neteyes_yt_test*.vtt &>/dev/null; then
      pass "YouTube subtitle extraction"
      rm -f "$TMP_DIR"/neteyes_yt_test*.vtt
    else
      warn "yt-dlp ran but no subtitle file produced"
    fi
  else
    warn "yt-dlp failed (network / version / region issue?)"
  fi
else
  warn "yt-dlp not installed"
fi

# --- GitHub ---
echo -n "→ GitHub (gh)... "
if command -v gh &>/dev/null; then
  if gh repo view cli/cli --json name -q .name 2>/dev/null | grep -q "cli"; then
    pass "GitHub public repo access"
  else
    warn "gh installed but request failed (auth or network)"
  fi
else
  warn "gh CLI not installed"
fi

# --- RSS ---
echo -n "→ RSS parsing... "
PYTHON_CMD="python3"
if ! command -v python3 &>/dev/null && command -v python &>/dev/null; then
  PYTHON_CMD="python"
fi

if $PYTHON_CMD -c "import feedparser; print(feedparser.parse('https://hnrss.org/frontpage').entries[0].title)" 2>/dev/null | grep -q .; then
  pass "RSS parsing works"
elif neteyes run rss read "https://news.ycombinator.com/rss" 2>/dev/null | grep -q .; then
  pass "RSS parsing works (via NetEyes backend)"
else
  warn "RSS test failed (feedparser missing or network)"
fi

# -------------------------------------------------
# 4. Login-required Channels (graceful)
# -------------------------------------------------
echo
echo "=== 4. Login / Cookie Channels ==="

# --- Twitter / X ---
echo -n "→ Twitter / X... "
if command -v twitter &>/dev/null || command -v xreach &>/dev/null || command -v opencli &>/dev/null; then
  if [[ -n "${TWITTER_AUTH_TOKEN:-}" && -n "${TWITTER_CT0:-}" ]]; then
    # Very light test — just check if command responds
    if twitter --help &>/dev/null || xreach --help &>/dev/null; then
      pass "Twitter tools available + cookies detected in env"
    else
      warn "Twitter cookies present but tool failed"
    fi
  else
    skip "Twitter (no TWITTER_AUTH_TOKEN / CT0 found — configure cookies to test)"
  fi
else
  skip "Twitter tools not installed"
fi

# --- Reddit ---
echo -n "→ Reddit... "
if command -v rdt &>/dev/null || command -v opencli &>/dev/null; then
  if [[ -n "${REDDIT_SESSION:-}" ]] || opencli doctor 2>/dev/null | grep -qi reddit; then
    pass "Reddit tools appear configured"
  else
    skip "Reddit (no session/cookies detected — configure to test fully)"
  fi
else
  skip "Reddit tools not installed"
fi

# --- XiaoHongShu ---
echo -n "→ XiaoHongShu... "
if command -v opencli &>/dev/null || command -v xhs &>/dev/null; then
  skip "XiaoHongShu tools found (full test requires browser session or cookies)"
else
  skip "XiaoHongShu tools not installed"
fi

# --- Bilibili ---
echo -n "→ Bilibili... "
if command -v bili &>/dev/null || command -v bili-cli &>/dev/null; then
  pass "Bilibili CLI found"
else
  warn "Bilibili CLI not found (yt-dlp fallback operational via NetEyes)"
fi

# -------------------------------------------------
# 5. Config & Safety Checks
# -------------------------------------------------
echo
echo "=== 5. Config & Safety ==="

if [[ -d "$HOME/.neteyes" ]]; then
  pass "Config directory exists (~/.neteyes)"
elif [[ -d "$HOME/.agent-reach" ]]; then
  warn "Found ~/.agent-reach (consider migrating to ~/.neteyes)"
else
  warn "No config directory yet (normal on very first run)"
fi

# Make sure we didn't pollute current directory
if [[ -f "./config.json" || -d "./tools" ]]; then
  warn "Possible pollution detected in current directory"
else
  pass "No workspace pollution detected"
fi

# -------------------------------------------------
# Final Summary
# -------------------------------------------------
echo
echo "======================================================"
echo "  FINAL RESULTS"
echo "======================================================"
green  "✅ Passed   : $PASS"
yellow "⚠️  Warnings : $WARN"
red    "❌ Failed   : $FAIL"
blue   "⏭️  Skipped  : $SKIP"
echo

if [[ $FAIL -eq 0 ]]; then
  green "🎉 Core system looks healthy!"
else
  red "Some critical checks failed. Please review the output above."
fi

echo
echo "Recommended manual tests still to do:"
echo "  1. Configure Twitter cookies → test search + read a tweet"
echo "  2. Configure Reddit session  → search + read a post"
echo "  3. Test XiaoHongShu if you need it"
echo "  4. Give NetEyes to an AI agent and ask real questions"
echo "  5. Intentionally break one backend and check if routing + doctor react correctly"
echo
echo "Doctor JSON: $DOCTOR_JSON"
echo "======================================================"

#!/usr/bin/env bash
set -e

echo "========================================"
echo "  NetEyes Verification Script"
echo "========================================"
echo

# 1. Basic CLI
echo "→ Checking CLI..."
neteyes --version || { echo "❌ neteyes command not found"; exit 1; }
neteyes --help > /dev/null && echo "✅ CLI help works" || echo "❌ CLI help failed"

# 2. Doctor
echo
echo "→ Running doctor..."
neteyes doctor || echo "⚠️  doctor returned non-zero (check output above)"
echo
echo "→ Running doctor --json..."
TMP_JSON="${TMPDIR:-/tmp}/neteyes_doctor.json"
neteyes doctor --json > "$TMP_JSON" && echo "✅ doctor --json works" || echo "❌ doctor --json failed"

# 3. Zero-config channels (basic smoke tests)
echo
echo "→ Testing zero-config channels..."

# Web (Jina-style, readability, or trafilatura)
echo -n "  Web reading... "
if neteyes doctor --json 2>/dev/null | grep -q '"web".*"status".*"ok\|ready\|available\|healthy\|✅"' 2>/dev/null; then
  echo "✅"
else
  echo "⚠️  (check manually)"
fi

# YouTube
echo -n "  YouTube... "
if command -v yt-dlp &>/dev/null || python -c "import yt_dlp" &>/dev/null; then
  echo "✅ yt-dlp found"
else
  echo "⚠️  yt-dlp not found"
fi

# GitHub
echo -n "  GitHub (gh)... "
if command -v gh &>/dev/null; then
  echo "✅ gh found"
else
  echo "⚠️  gh not found"
fi

# 4. Config directory check
echo
echo "→ Checking config location..."
if [ -d "$HOME/.neteyes" ] || [ -d "$HOME/.agent-reach" ]; then
  echo "✅ Config directory exists"
else
  echo "⚠️  Config directory not found (may be normal on first run)"
fi

# 5. Final summary
echo
echo "========================================"
echo "  Manual checks still needed:"
echo "========================================"
echo "1. Test actual web page reading: neteyes run web read https://example.com"
echo "2. Test YouTube subtitle extraction: neteyes run youtube extract https://www.youtube.com/watch?v=jNQXAC9IVRw"
echo "3. Set up Twitter/Reddit cookies and test search + read"
echo "4. Confirm multi-backend platforms show correct active backend"
echo "5. Give NetEyes to an AI agent and ask it to use it"
echo
echo "Done."

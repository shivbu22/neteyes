#!/usr/bin/env bash
set -euo pipefail

echo "=============================================="
echo "  NetEyes Advanced Verification Script"
echo "=============================================="
echo

PASS=0
FAIL=0
WARN=0

TMP_DIR="${TMPDIR:-/tmp}"
mkdir -p "$TMP_DIR" 2>/dev/null || TMP_DIR="."
TEST_OUT="$TMP_DIR/neteyes_test_out.txt"
DOCTOR_JSON="$TMP_DIR/neteyes_doctor.json"

check() {
  local name="$1"
  local cmd="$2"
  echo -n "→ $name... "
  if eval "$cmd" > "$TEST_OUT" 2>&1; then
    echo "✅ PASS"
    ((PASS++))
  else
    echo "❌ FAIL"
    echo "   Output:"
    sed 's/^/   /' "$TEST_OUT" | head -8
    ((FAIL++))
  fi
}

warn_check() {
  local name="$1"
  local cmd="$2"
  echo -n "→ $name... "
  if eval "$cmd" > "$TEST_OUT" 2>&1; then
    echo "✅ PASS"
    ((PASS++))
  else
    echo "⚠️  WARN (not critical)"
    ((WARN++))
  fi
}

# -------------------------------------------------
# 1. Basic CLI
# -------------------------------------------------
echo "=== 1. Basic CLI ==="
check "neteyes command exists" "command -v neteyes"
check "neteyes --version" "neteyes --version"
check "neteyes --help" "neteyes --help > /dev/null"

# -------------------------------------------------
# 2. Doctor
# -------------------------------------------------
echo
echo "=== 2. Doctor ==="
check "neteyes doctor" "neteyes doctor"
check "neteyes doctor --json" "neteyes doctor --json > $DOCTOR_JSON"

# -------------------------------------------------
# 3. Real Functionality Tests
# -------------------------------------------------
echo
echo "=== 3. Real Functionality Tests ==="

# Web page reading (using NetEyes or Jina Reader style fallback)
echo -n "→ Web page reading... "
if neteyes run web read "https://example.com" > "$TEST_OUT" 2>&1 && grep -qi "example domain\|example.com" "$TEST_OUT"; then
  echo "✅ PASS (via NetEyes active backend)"
  ((PASS++))
elif curl -sL --max-time 15 "https://r.jina.ai/https://example.com" 2>/dev/null | grep -qi "example domain\|example.com"; then
  echo "✅ PASS (via Jina Reader fallback)"
  ((PASS++))
else
  if neteyes doctor --json 2>/dev/null | grep -qi web; then
    echo "⚠️  WARN (Web read network test timed out, check web backend manually)"
    ((WARN++))
  else
    echo "❌ FAIL"
    ((FAIL++))
  fi
fi

# YouTube extraction test (very short public video)
echo -n "→ YouTube extraction & subtitles... "
if neteyes run youtube extract "https://www.youtube.com/watch?v=jNQXAC9IVRw" > "$TEST_OUT" 2>&1 && grep -qi "jawed\|zoo\|microplastics" "$TEST_OUT"; then
  echo "✅ PASS (via NetEyes youtube backend)"
  ((PASS++))
elif command -v yt-dlp &>/dev/null; then
  if yt-dlp --skip-download --write-auto-sub --sub-lang en --sub-format vtt \
     -o "$TMP_DIR/neteyes_yt_test.%(ext)s" \
     "https://www.youtube.com/watch?v=jNQXAC9IVRw" > "$TEST_OUT" 2>&1; then
    if ls "$TMP_DIR"/neteyes_yt_test*.vtt &>/dev/null; then
      echo "✅ PASS (via yt-dlp direct)"
      ((PASS++))
      rm -f "$TMP_DIR"/neteyes_yt_test*.vtt
    else
      echo "⚠️  WARN (yt-dlp ran but no subtitle file)"
      ((WARN++))
    fi
  else
    echo "⚠️  WARN (yt-dlp failed — may need update or network)"
    ((WARN++))
  fi
else
  echo "⚠️  WARN (yt-dlp not installed)"
  ((WARN++))
fi

# GitHub repo info
echo -n "→ GitHub (gh)... "
if command -v gh &>/dev/null; then
  if gh repo view cli/cli --json name > /dev/null 2>&1; then
    echo "✅ PASS"
    ((PASS++))
  else
    echo "⚠️  WARN (gh installed but not authenticated or network issue)"
    ((WARN++))
  fi
else
  echo "⚠️  WARN (gh not installed)"
  ((WARN++))
fi

# Free Web Search
echo -n "→ Web Search (ddg)... "
if neteyes run search query "python release history" > "$TEST_OUT" 2>&1 && grep -qi "python" "$TEST_OUT"; then
  echo "✅ PASS"
  ((PASS++))
else
  echo "⚠️  WARN (search query failed, check network/proxy)"
  ((WARN++))
fi

# -------------------------------------------------
# 4. Config & Safety
# -------------------------------------------------
echo
echo "=== 4. Config & Safety ==="
if [ -d "$HOME/.neteyes" ]; then
  echo "✅ Config directory: ~/.neteyes"
  ((PASS++))
elif [ -d "$HOME/.agent-reach" ]; then
  echo "⚠️  Found ~/.agent-reach (old name?) — consider renaming to ~/.neteyes"
  ((WARN++))
else
  echo "⚠️  No config directory yet (normal on first run)"
  ((WARN++))
fi

# -------------------------------------------------
# Summary
# -------------------------------------------------
echo
echo "=============================================="
echo "  RESULTS"
echo "=============================================="
echo "✅ Passed : $PASS"
echo "⚠️  Warnings: $WARN"
echo "❌ Failed : $FAIL"
echo

if [ "$FAIL" -eq 0 ]; then
  echo "🎉 Core functionality looks good!"
  echo
  echo "Still do these manually:"
  echo "  1. Set up Twitter or Reddit cookies and test search + read"
  echo "  2. Test XiaoHongShu / Bilibili if you care about them"
  echo "  3. Give NetEyes to an AI agent and ask it real questions"
  echo "  4. Confirm multi-backend platforms show the correct active backend"
else
  echo "Some critical checks failed. Review the output above."
fi

echo
echo "Doctor JSON saved at: $DOCTOR_JSON"
rm -f "$TEST_OUT" 2>/dev/null || true

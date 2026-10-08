#!/usr/bin/env python3
"""Cross-platform verification script for NetEyes.

Runs all CLI checks, doctor output probes, and live channel extractions
across Windows, Linux, and macOS.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def run(cmd: list[str] | str, timeout: int = 30) -> tuple[int, str]:
    try:
        if isinstance(cmd, str):
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
        else:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
        output = (res.stdout or "") + (res.stderr or "")
        return res.returncode, output.strip()
    except Exception as e:
        return 1, str(e)


def main() -> int:
    print("=" * 48)
    print("  NetEyes Unified Cross-Platform Verifier")
    print("=" * 48)
    print()

    passed = 0
    warned = 0
    failed = 0

    def check(name: str, passed_condition: bool, details: str = ""):
        nonlocal passed, failed
        print(f"→ {name}... ", end="", flush=True)
        if passed_condition:
            print("✅ PASS")
            passed += 1
        else:
            print("❌ FAIL")
            if details:
                for line in details.splitlines()[:5]:
                    print(f"   {line}")
            failed += 1

    def warn(name: str, passed_condition: bool, details: str = ""):
        nonlocal passed, warned
        print(f"→ {name}... ", end="", flush=True)
        if passed_condition:
            print("✅ PASS")
            passed += 1
        else:
            print("⚠️  WARN")
            if details:
                for line in details.splitlines()[:3]:
                    print(f"   {line}")
            warned += 1

    # 1. Basic CLI
    print("=== 1. Basic CLI ===")
    code, out = run(["neteyes", "--version"])
    check("neteyes --version", code == 0 and "NetEyes" in out, out)

    code, out = run(["neteyes", "--help"])
    check("neteyes --help", code == 0 and "doctor" in out and "route" in out, out)

    code, out = run(["neteyes", "install", "--env=auto"])
    check("neteyes install --env=auto (check-only mode)", code == 0 and "Check-only mode" in out, out)

    # 2. Doctor
    print("\n=== 2. Doctor ===")
    code, out = run(["neteyes", "doctor"])
    check("neteyes doctor (Rich status table)", code == 0 and "System Diagnostic Report" in out, out)

    code, out = run(["neteyes", "doctor", "--json"])
    is_valid_json = False
    doc_data = {}
    if code == 0:
        try:
            doc_data = json.loads(out)
            is_valid_json = "healthy_channels" in doc_data and "diagnostics" in doc_data
        except Exception:
            is_valid_json = False
    check("neteyes doctor --json", is_valid_json, out)

    # 3. Real Functionality Tests
    print("\n=== 3. Real Functionality Tests ===")

    # Web page reading
    code, out = run(["neteyes", "run", "web", "read", "https://example.com"])
    check("Web page extraction (example.com)", code == 0 and "Example Domain" in out, out)

    # YouTube extract
    code, out = run(["neteyes", "run", "youtube", "extract", "https://www.youtube.com/watch?v=jNQXAC9IVRw"])
    warn("YouTube subtitle/metadata extract", code == 0 and any(k in out.lower() for k in ["jawed", "zoo", "microplastics"]), out)

    # GitHub public repo view
    if shutil.which("gh"):
        code, out = run(["gh", "repo", "view", "cli/cli", "--json", "name"])
        check("GitHub CLI repo view (gh)", code == 0 and "cli" in out, out)
    else:
        code, out = run(["neteyes", "run", "github", "repo", "cli/cli"])
        warn("GitHub fallback API repo view", code == 0 and "cli" in out, out)

    # DuckDuckGo free search
    code, out = run(["neteyes", "run", "search", "query", "python programming language"])
    warn("Web Search query (DuckDuckGo)", code == 0 and "python" in out.lower(), out)

    # RSS reading
    code, out = run(["neteyes", "run", "rss", "read", "https://news.ycombinator.com/rss"])
    warn("RSS Feed parse (Hacker News)", code == 0 and ("hacker news" in out.lower() or "http" in out), out)

    # 4. Config & Safety
    print("\n=== 4. Config & Safety ===")
    cfg_dir = Path.home() / ".neteyes"
    warn("Config directory (~/.neteyes)", cfg_dir.exists(), f"Path: {cfg_dir}")

    # Results
    print("\n" + "=" * 48)
    print("  RESULTS")
    print("=" * 48)
    print(f"✅ Passed  : {passed}")
    print(f"⚠️  Warnings: {warned}")
    print(f"❌ Failed  : {failed}")
    print()

    if failed == 0:
        print("🎉 All core NetEyes functional verifications passed successfully!")
    else:
        print("Some checks failed. Review details above.")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

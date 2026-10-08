# NetEyes PowerShell Verification Script
$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  NetEyes PowerShell Verification Script" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

$Pass = 0
$Warn = 0
$Fail = 0

function Run-Check {
    param([string]$Name, [scriptblock]$Action)
    Write-Host -NoNewline "→ $Name... "
    try {
        $result = & $Action
        if ($LASTEXITCODE -eq 0 -or $null -eq $LASTEXITCODE) {
            Write-Host "✅ PASS" -ForegroundColor Green
            $global:Pass++
        } else {
            Write-Host "❌ FAIL" -ForegroundColor Red
            $global:Fail++
        }
    } catch {
        Write-Host "❌ FAIL ($($_.Exception.Message))" -ForegroundColor Red
        $global:Fail++
    }
}

function Run-WarnCheck {
    param([string]$Name, [scriptblock]$Action)
    Write-Host -NoNewline "→ $Name... "
    try {
        $result = & $Action
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ PASS" -ForegroundColor Green
            $global:Pass++
        } else {
            Write-Host "⚠️  WARN (not critical)" -ForegroundColor Yellow
            $global:Warn++
        }
    } catch {
        Write-Host "⚠️  WARN (not critical)" -ForegroundColor Yellow
        $global:Warn++
    }
}

# 1. Basic CLI
Write-Host "=== 1. Basic CLI ===" -ForegroundColor DarkCyan
Run-Check "neteyes command exists" { Get-Command neteyes -ErrorAction Stop }
Run-Check "neteyes --version" { neteyes --version }
Run-Check "neteyes --help" { neteyes --help | Out-Null }

# 2. Doctor
Write-Host "`n=== 2. Doctor ===" -ForegroundColor DarkCyan
Run-Check "neteyes doctor" { neteyes doctor }
$DoctorFile = "$env:TEMP\neteyes_doctor.json"
Run-Check "neteyes doctor --json" { neteyes doctor --json | Out-File -Encoding utf8 $DoctorFile }

# 3. Real Functionality Tests
Write-Host "`n=== 3. Real Functionality Tests ===" -ForegroundColor DarkCyan

Write-Host -NoNewline "→ Web page reading... "
try {
    $webOut = neteyes run web read "https://example.com"
    if ($webOut -match "Example Domain|example\.com") {
        Write-Host "✅ PASS (via NetEyes active backend)" -ForegroundColor Green
        $Pass++
    } else {
        Write-Host "⚠️  WARN" -ForegroundColor Yellow
        $Warn++
    }
} catch {
    Write-Host "❌ FAIL" -ForegroundColor Red
    $Fail++
}

Write-Host -NoNewline "→ YouTube subtitle extraction... "
try {
    $ytOut = neteyes run youtube extract "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    if ($ytOut -match "jawed|zoo|microplastics") {
        Write-Host "✅ PASS (via NetEyes youtube backend)" -ForegroundColor Green
        $Pass++
    } else {
        Write-Host "⚠️  WARN" -ForegroundColor Yellow
        $Warn++
    }
} catch {
    Write-Host "⚠️  WARN" -ForegroundColor Yellow
    $Warn++
}

Write-Host -NoNewline "→ GitHub (gh)... "
if (Get-Command gh -ErrorAction SilentlyContinue) {
    try {
        $ghOut = gh repo view cli/cli --json name
        if ($ghOut -match "cli") {
            Write-Host "✅ PASS" -ForegroundColor Green
            $Pass++
        } else {
            Write-Host "⚠️  WARN" -ForegroundColor Yellow
            $Warn++
        }
    } catch {
        Write-Host "⚠️  WARN" -ForegroundColor Yellow
        $Warn++
    }
} else {
    Write-Host "⚠️  WARN (gh not installed)" -ForegroundColor Yellow
    $Warn++
}

Write-Host -NoNewline "→ Web Search (ddg)... "
try {
    $searchOut = neteyes run search query "python release history"
    if ($searchOut -match "python") {
        Write-Host "✅ PASS" -ForegroundColor Green
        $Pass++
    } else {
        Write-Host "⚠️  WARN" -ForegroundColor Yellow
        $Warn++
    }
} catch {
    Write-Host "⚠️  WARN" -ForegroundColor Yellow
    $Warn++
}

# 4. Config & Safety
Write-Host "`n=== 4. Config & Safety ===" -ForegroundColor DarkCyan
$cfgDir = Join-Path $HOME ".neteyes"
if (Test-Path $cfgDir) {
    Write-Host "✅ Config directory: ~/.neteyes" -ForegroundColor Green
    $Pass++
} else {
    Write-Host "⚠️  No ~/.neteyes yet (created on first save)" -ForegroundColor Yellow
    $Warn++
}

# Summary
Write-Host "`n==============================================" -ForegroundColor Cyan
Write-Host "  RESULTS" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "✅ Passed   : $Pass" -ForegroundColor Green
Write-Host "⚠️  Warnings : $Warn" -ForegroundColor Yellow
Write-Host "❌ Failed   : $Fail" -ForegroundColor Red
Write-Host ""

if ($Fail -eq 0) {
    Write-Host "🎉 Core functionality looks good!" -ForegroundColor Green
} else {
    Write-Host "Some critical checks failed. Review the output above." -ForegroundColor Red
}

Write-Host "Doctor JSON saved at: $DoctorFile`n"

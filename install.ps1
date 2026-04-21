# fux-voice — Bootstrap-Installer
#
# Laedt die neueste fux-voice.exe aus GitHub Releases herunter,
# installiert nach %LOCALAPPDATA%\fux-voice und registriert Autostart.
#
# Verwendung (PowerShell, normaler User — kein Admin noetig):
#   irm https://raw.githubusercontent.com/fuxbert79/fux-voice/main/install.ps1 | iex
#
# Parameter (bei lokalem Aufruf):
#   .\install.ps1                    # Install / Upgrade
#   .\install.ps1 -OpenAIKey "sk-..."
#   .\install.ps1 -Uninstall
#   .\install.ps1 -Version "v0.1.0"  # Spezifische Version

param(
    [string]$OpenAIKey = "",
    [string]$Version = "latest",
    [switch]$Uninstall = $false
)

$ErrorActionPreference = "Stop"
$ProgressPreference    = "SilentlyContinue"

$AppName    = "fux-voice"
$Repo       = "fuxbert79/fux-voice"
$InstallDir = Join-Path $env:LOCALAPPDATA $AppName
$ExeDst     = Join-Path $InstallDir   "$AppName.exe"
$RunKey     = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$StartMenu  = Join-Path $env:APPDATA  "Microsoft\Windows\Start Menu\Programs\$AppName.lnk"

function Write-Header {
    param([string]$Text)
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor Cyan
    Write-Host "  $Text" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor Cyan
}

function Stop-RunningApp {
    try {
        Get-Process -Name $AppName -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 300
    } catch {}
}

function Remove-Installation {
    Write-Header "Entferne $AppName"
    Stop-RunningApp
    if (Test-Path $InstallDir) {
        Remove-Item $InstallDir -Recurse -Force
        Write-Host "  Ordner entfernt:    $InstallDir"
    }
    if (Test-Path $StartMenu) {
        Remove-Item $StartMenu -Force
        Write-Host "  Startmenue entfernt"
    }
    Remove-ItemProperty -Path $RunKey -Name $AppName -ErrorAction SilentlyContinue
    Write-Host "  Autostart entfernt"
    Write-Host ""
    Write-Host "OK — deinstalliert." -ForegroundColor Green
}

function Get-ReleaseInfo {
    param([string]$Tag)

    $apiUrl = if ($Tag -eq "latest") {
        "https://api.github.com/repos/$Repo/releases/latest"
    } else {
        "https://api.github.com/repos/$Repo/releases/tags/$Tag"
    }

    try {
        return Invoke-RestMethod -Uri $apiUrl -Headers @{ "User-Agent" = "fux-voice-installer" }
    } catch {
        throw "Konnte Release-Info nicht laden von $apiUrl — $($_.Exception.Message)"
    }
}

function Install-FuxVoice {
    Write-Header "Installiere $AppName"

    Write-Host "  Lade Release-Info ($Version) …"
    $release = Get-ReleaseInfo -Tag $Version

    $exeAsset = $release.assets | Where-Object { $_.name -eq "$AppName.exe" } | Select-Object -First 1
    $shaAsset = $release.assets | Where-Object { $_.name -eq "$AppName.exe.sha256" } | Select-Object -First 1

    if (-not $exeAsset) {
        throw "Release $($release.tag_name) enthaelt kein $AppName.exe"
    }

    Write-Host "  Version:            $($release.tag_name)"
    Write-Host "  Zielpfad:           $InstallDir"

    Stop-RunningApp
    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

    $tmpExe = Join-Path $env:TEMP "$AppName-$([Guid]::NewGuid()).exe"
    Write-Host "  Lade $AppName.exe ($([math]::Round($exeAsset.size / 1MB, 2)) MB) …"
    Invoke-WebRequest -Uri $exeAsset.browser_download_url -OutFile $tmpExe

    if ($shaAsset) {
        Write-Host "  Verifiziere SHA-256 …"
        $tmpSha = Join-Path $env:TEMP "$AppName-$([Guid]::NewGuid()).sha256"
        Invoke-WebRequest -Uri $shaAsset.browser_download_url -OutFile $tmpSha -UseBasicParsing
        $shaText = [System.IO.File]::ReadAllText($tmpSha, [System.Text.Encoding]::UTF8)
        Remove-Item $tmpSha -Force -ErrorAction SilentlyContinue
        $expected = ($shaText.Trim() -split '\s+')[0].ToLower()
        $actual   = (Get-FileHash $tmpExe -Algorithm SHA256).Hash.ToLower()
        if ($expected -ne $actual) {
            Remove-Item $tmpExe -Force
            throw "Checksum-Fehler! Erwartet $expected, tatsaechlich $actual"
        }
        Write-Host "  Checksum OK" -ForegroundColor Green
    }

    Move-Item -Path $tmpExe -Destination $ExeDst -Force

    # .env anlegen falls nicht vorhanden
    $EnvDst = Join-Path $InstallDir ".env"
    if (!(Test-Path $EnvDst)) {
        $envContent = if ($OpenAIKey) {
            "OPENAI_API_KEY=$OpenAIKey"
        } else {
            "# OpenAI API-Key fuer Whisper-Transkription`nOPENAI_API_KEY="
        }
        $envContent | Out-File -FilePath $EnvDst -Encoding UTF8 -NoNewline
        if ($OpenAIKey) {
            Write-Host "  .env erstellt mit API-Key"
        } else {
            Write-Host "  .env erstellt (Key kann via Tray-Icon > Konfiguration gesetzt werden)"
        }
    }

    # Autostart
    Set-ItemProperty -Path $RunKey -Name $AppName -Value "`"$ExeDst`""
    Write-Host "  Autostart registriert (HKCU Run)"

    # Startmenue
    $Shell = New-Object -ComObject WScript.Shell
    $Shortcut = $Shell.CreateShortcut($StartMenu)
    $Shortcut.TargetPath = $ExeDst
    $Shortcut.WorkingDirectory = $InstallDir
    $Shortcut.IconLocation = $ExeDst
    $Shortcut.Description  = "fux-voice — Speech-to-Text"
    $Shortcut.Save()
    Write-Host "  Startmenue-Eintrag erstellt"

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "  $AppName $($release.tag_name) installiert" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Starten:        via Startmenue oder $ExeDst"
    Write-Host "  Konfiguration:  Rechtsklick aufs Tray-Icon > Konfiguration"
    Write-Host "  Hotkey:         Strg+Alt+Leertaste (Aufnahme)"
    Write-Host "  Deinstall:      irm https://raw.githubusercontent.com/$Repo/main/install.ps1 | iex -Args '-Uninstall'"
    Write-Host ""

    # Direkt starten
    Write-Host "Starte $AppName …" -ForegroundColor Cyan
    Start-Process -FilePath $ExeDst -WorkingDirectory $InstallDir
}

# Windows-Check
if ($PSVersionTable.Platform -and $PSVersionTable.Platform -ne "Win32NT") {
    Write-Error "fux-voice laeuft nur auf Windows."
    exit 1
}

if ($Uninstall) {
    Remove-Installation
    exit 0
}

try {
    Install-FuxVoice
} catch {
    Write-Host ""
    Write-Error "Installation fehlgeschlagen: $($_.Exception.Message)"
    exit 1
}

# fux-voice — Windows-Installer
# Kopiert .exe nach %LOCALAPPDATA%\fux-voice, erstellt Konfig, registriert Autostart.
#
# Aufruf (PowerShell als aktueller Benutzer, KEIN Admin noetig):
#   .\installer\install.ps1
# Optional: .\installer\install.ps1 -OpenAIKey "sk-proj-..."

param(
    [string]$OpenAIKey = "",
    [switch]$Uninstall = $false
)

$ErrorActionPreference = "Stop"

$AppName    = "fux-voice"
$InstallDir = Join-Path $env:LOCALAPPDATA $AppName
$ExeSrc     = Join-Path $PSScriptRoot "..\dist\$AppName.exe"
$ExeDst     = Join-Path $InstallDir   "$AppName.exe"
$RunKey     = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$StartMenu  = Join-Path $env:APPDATA  "Microsoft\Windows\Start Menu\Programs\$AppName.lnk"

function Remove-Installation {
    Write-Host "Entferne $AppName ..." -ForegroundColor Yellow
    try { Stop-Process -Name $AppName -Force -ErrorAction SilentlyContinue } catch {}
    if (Test-Path $InstallDir) { Remove-Item $InstallDir -Recurse -Force }
    if (Test-Path $StartMenu)  { Remove-Item $StartMenu -Force }
    Remove-ItemProperty -Path $RunKey -Name $AppName -ErrorAction SilentlyContinue
    Write-Host "OK — deinstalliert." -ForegroundColor Green
}

if ($Uninstall) { Remove-Installation; exit 0 }

if (!(Test-Path $ExeSrc)) {
    Write-Error "Nicht gefunden: $ExeSrc — bitte zuerst 'installer\build.bat' ausfuehren."
    exit 1
}

Write-Host "Installiere $AppName nach $InstallDir" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Copy-Item $ExeSrc $ExeDst -Force

# config.json anlegen falls nicht vorhanden
$ConfigSrc = Join-Path $PSScriptRoot "..\config.json.example"
$ConfigDst = Join-Path $InstallDir "config.json"
if (!(Test-Path $ConfigDst) -and (Test-Path $ConfigSrc)) {
    Copy-Item $ConfigSrc $ConfigDst
    Write-Host "  config.json erstellt"
}

# .env anlegen
$EnvDst = Join-Path $InstallDir ".env"
if (!(Test-Path $EnvDst)) {
    if ($OpenAIKey) {
        "OPENAI_API_KEY=$OpenAIKey" | Out-File -FilePath $EnvDst -Encoding UTF8
        Write-Host "  .env mit API-Key erstellt"
    } else {
        "OPENAI_API_KEY=sk-proj-..." | Out-File -FilePath $EnvDst -Encoding UTF8
        Write-Host "  .env erstellt — bitte API-Key eintragen: $EnvDst" -ForegroundColor Yellow
    }
}

# Autostart-Registry
Set-ItemProperty -Path $RunKey -Name $AppName -Value "`"$ExeDst`""
Write-Host "  Autostart registriert (HKCU Run)"

# Startmenue-Verknuepfung
$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($StartMenu)
$Shortcut.TargetPath = $ExeDst
$Shortcut.WorkingDirectory = $InstallDir
$Shortcut.IconLocation = $ExeDst
$Shortcut.Save()
Write-Host "  Startmenue-Eintrag erstellt"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  $AppName installiert in $InstallDir" -ForegroundColor Green
Write-Host "  Starte via Startmenue oder direkt: $ExeDst" -ForegroundColor Green
Write-Host "  Deinstallieren: .\installer\install.ps1 -Uninstall" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green

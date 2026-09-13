# Enable WSL2 / Virtual Machine Platform so Docker Desktop can start.
# Cooperledge already has a hypervisor (VBS). WSL is what was missing.
#
# From a normal PowerShell (this script will prompt for Administrator):
#   Set-ExecutionPolicy -Scope Process Bypass
#   .\scripts\enable-wsl.ps1
# Then reboot, open Docker Desktop, and run .\scripts\compose-local.ps1

$ErrorActionPreference = "Stop"

$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)
if (-not $isAdmin) {
    Write-Host "Re-launching elevated. Accept the UAC prompt..."
    $script = $MyInvocation.MyCommand.Path
    Start-Process -FilePath "powershell.exe" -Verb RunAs -Wait -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $script
    )
    exit $LASTEXITCODE
}

Write-Host "Enabling Windows features for Docker Desktop (WSL2)..."
$features = @(
    "VirtualMachinePlatform",
    "Microsoft-Windows-Subsystem-Linux",
    "HypervisorPlatform"
)
foreach ($name in $features) {
    Write-Host "  -> $name"
    dism.exe /online /enable-feature /featurename:$name /all /norestart | Out-Host
}

Write-Host "Installing WSL (no Linux distro required for Docker)..."
wsl --install --no-distribution

Write-Host @"

Reboot Windows, then:
  1. Open Docker Desktop and wait until it is Running
  2. .\scripts\compose-local.ps1

If Docker still says virtualization is missing after reboot:
  BIOS (ASUS ROG, Del/F2) -> Advanced -> CPU Configuration
  Intel Virtualization Technology = Enabled
  Intel VT-d = Enabled

Until Docker works, the Watcher pipeline can run without it:
  .\scripts\start-backend-local.ps1
"@
Read-Host "Press Enter to close"

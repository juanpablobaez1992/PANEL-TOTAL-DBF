param(
    [string]$HostAlias = "panel-vps",
    [string]$RemotePath = "/docker/panel-total-dbf",
    [string]$Branch = "main",
    [switch]$Push,
    [switch]$Logs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

function Invoke-Step {
    param(
        [string]$Label,
        [scriptblock]$Action
    )

    Write-Host ""
    Write-Host "==> $Label" -ForegroundColor Cyan
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed: $Label"
    }
}

if ($Push) {
    Invoke-Step "Pushing $Branch to origin" {
        git -C $repoRoot push origin $Branch
    }
}

$remoteCommands = @(
    "set -e"
    "cd '$RemotePath'"
    "git pull origin $Branch"
    "docker compose up -d --build"
    "docker compose ps"
)

if ($Logs) {
    $remoteCommands += "docker compose logs --tail=50 backend frontend"
}

$remoteScript = $remoteCommands -join "; "

Invoke-Step "Deploying to $HostAlias:$RemotePath" {
    ssh $HostAlias $remoteScript
}

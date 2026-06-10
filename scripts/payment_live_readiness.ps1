param(
    [string]$WebsiteDir = (Split-Path -Parent $PSScriptRoot),
    [switch]$SkipNetwork,
    [switch]$SkipSupervisor,
    [switch]$SkipPm2,
    [switch]$SkipLocalService,
    [switch]$StartLocalService,
    [string]$LocalServiceHost = "127.0.0.1",
    [int]$LocalServicePort = 5051,
    [int]$LocalServiceStartupSeconds = 20,
    [switch]$SkipLegalSurface,
    [switch]$RequireReady
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "== $Message =="
}

Set-Location -LiteralPath $WebsiteDir

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw "python is not available on PATH"
}
if ($StartLocalService -and $SkipLocalService) {
    throw "-StartLocalService cannot be combined with -SkipLocalService"
}

$localProcess = $null
try {
    if ($StartLocalService) {
        Write-Step "Starting local payment service"
        $serveArgs = @(
            "payment_server.py",
            "serve",
            "--host",
            $LocalServiceHost,
            "--port",
            [string]$LocalServicePort
        )
        $localProcess = Start-Process -FilePath $python.Source -ArgumentList $serveArgs -WorkingDirectory $WebsiteDir -PassThru -WindowStyle Hidden
        $healthUrl = "http://$LocalServiceHost`:$LocalServicePort/health"
        $ready = $false
        $deadline = (Get-Date).AddSeconds($LocalServiceStartupSeconds)
        while ((Get-Date) -lt $deadline) {
            Start-Sleep -Milliseconds 500
            try {
                $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 2
                if ($health.service -eq "DueSight Payment Server") {
                    $ready = $true
                    break
                }
            } catch {
                if ($localProcess.HasExited) {
                    break
                }
            }
        }
        if (-not $ready) {
            throw "local payment service did not become ready at $healthUrl"
        }
        Write-Host "local_payment_service_ready"
    }

    Write-Step "DueSight payment readiness"
    $readinessArgs = @("payment_server.py", "readiness-check")
    if ($SkipNetwork) {
        $readinessArgs += "--skip-network"
    }
    if ($SkipSupervisor -or $SkipPm2) {
        $readinessArgs += "--skip-supervisor"
    }
    if ($SkipLocalService) {
        $readinessArgs += "--skip-local-service"
    }
    if ($RequireReady) {
        $readinessArgs += "--fail-on-blocked"
    }
    & $python.Source @readinessArgs
    if ($RequireReady -and $LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    if (-not $SkipLegalSurface) {
        Write-Step "Legal launch surface"
        $legalOutput = & $python.Source tools\legal_launch_surface_check.py
        $legalExitCode = $LASTEXITCODE
        $legalOutput
        if ($legalExitCode -ne 0) {
            exit $legalExitCode
        }
        if ($RequireReady) {
            $legalPayload = $legalOutput -join "`n" | ConvertFrom-Json
            if (-not $legalPayload.ready_for_live_payments) {
                exit 4
            }
        }
    }

    Write-Step "Redacted smoke config"
    & $python.Source payment_server.py smoke-config

    if (-not $SkipNetwork) {
        Write-Step "Public TLS and route probes"
        $targets = @(
            "https://duesight.nl",
            "https://www.duesight.nl",
            "https://duesight.nl/health",
            "https://duesight.nl/api/payment/products"
        )
        foreach ($target in $targets) {
            Write-Host ""
            Write-Host $target
            curl.exe -I $target --max-time 20
        }
    }

    if (-not ($SkipSupervisor -or $SkipPm2)) {
        Write-Step "Payment supervisor service state"
        Get-Service -Name DueSight-Payment, DueSight-DeliveryWorker -ErrorAction SilentlyContinue |
            Select-Object Name, Status, StartType
    }
} finally {
    if ($localProcess -and -not $localProcess.HasExited) {
        Stop-Process -Id $localProcess.Id -Force
        $localProcess.WaitForExit(5000) | Out-Null
    }
}

param([ValidateSet("dashboard","pipeline","search","leads","menu")][string]$Command = "dashboard")

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

function Start-Dashboard {
    Clear-Host
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host "   LeadOS — Cold Email Command Center" -ForegroundColor Cyan
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host " Dashboard: http://localhost:8000" -ForegroundColor Green
    Write-Host ""

    $job = Start-Job -ScriptBlock { param($d) Set-Location $d; python -m app serve } -ArgumentList $root
    Start-Sleep -Seconds 3
    Start-Process "http://localhost:8000"
    Read-Host "`nPress Enter to stop server"
    Stop-Job $job -ErrorAction SilentlyContinue
    Remove-Job $job -ErrorAction SilentlyContinue
}

switch ($Command) {
    "dashboard" { Start-Dashboard }
    "pipeline" {
        Write-Host "Running full pipeline..." -ForegroundColor Yellow
        python -m app match
        Read-Host "`nPress Enter to exit"
    }
    "search" {
        $query = Read-Host "Enter search query"
        python -m app search $query
        Read-Host "`nPress Enter to exit"
    }
    "leads" {
        python -m app leads
        Read-Host "`nPress Enter to exit"
    }
    "menu" {
        do {
            Clear-Host
            Write-Host "=== LeadOS ===" -ForegroundColor Cyan
            Write-Host "1) Start Dashboard" -ForegroundColor Green
            Write-Host "2) Run Full Pipeline" -ForegroundColor Yellow
            Write-Host "3) View Hot Leads" -ForegroundColor Magenta
            Write-Host "4) Search Web" -ForegroundColor Blue
            Write-Host "5) Exit"
            $choice = Read-Host "`nSelect option"
            switch ($choice) {
                "1" { Start-Dashboard }
                "2" { python -m app match; Read-Host "`nPress Enter to return to menu" }
                "3" { python -m app leads; Read-Host "`nPress Enter to return to menu" }
                "4" { $q = Read-Host "Enter search query"; python -m app search $q; Read-Host "`nPress Enter to return to menu" }
            }
        } while ($choice -ne "5")
    }
}

param([ValidateSet("dashboard","pipeline","search","leads","menu")][string]$Command = "dashboard")

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

switch ($Command) {
    "dashboard" {
        Clear-Host
        Write-Host "============================================" -ForegroundColor Cyan
        Write-Host "   LeadOS — Cold Email Command Center" -ForegroundColor Cyan
        Write-Host "============================================" -ForegroundColor Cyan
        Write-Host ""
        Write-Host " Dashboard: http://localhost:8000" -ForegroundColor Green
        Write-Host ""
        Start-Process "http://localhost:8000"
        python -m app serve
        Read-Host "`nPress Enter to exit"
    }
    "pipeline" {
        Write-Host "Running full pipeline..." -ForegroundColor Yellow
        python -m app run-all
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
                "1" { & $MyInvocation.MyCommand.Path -Command dashboard }
                "2" { & $MyInvocation.MyCommand.Path -Command pipeline }
                "3" { & $MyInvocation.MyCommand.Path -Command leads }
                "4" { & $MyInvocation.MyCommand.Path -Command search }
            }
        } while ($choice -ne "5")
    }
}

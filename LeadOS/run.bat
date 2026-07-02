@echo off
title LeadOS — Cold Email Pipeline
cls
echo ============================================
echo    LeadOS — Cold Email Command Center
echo ============================================
echo.
echo  Dashboard: http://localhost:8000
echo  CLI:       python -m app [command]
echo.
echo  Commands:
echo    python -m app match      Full pipeline
echo    python -m app leads      View hot leads
echo    python -m app export     Export to CSV
echo    python -m app list all   List everything
echo.
echo  Press Ctrl+C to stop server
echo ============================================
echo.
start /B "" python -m app serve
timeout /t 3 /nobreak >nul
start http://localhost:8000

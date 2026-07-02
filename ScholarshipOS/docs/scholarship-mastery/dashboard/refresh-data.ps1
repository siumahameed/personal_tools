<#
.SYNOPSIS
  Refresh scholarship data by checking official websites for updates.
  Updates scholarship-data.js with any new deadlines, stipends, or info found.

.DESCRIPTION
  Visits each scholarship program's official website, extracts key information
  (deadlines, stipend amounts, application dates), and updates the data file.
  Run periodically (e.g., monthly) to keep your dashboard current.

.USAGE
  .\refresh-data.ps1
#>

$ErrorActionPreference = "Continue"
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$dataFile = "$scriptPath\scholarship-data.js"

# Timestamp
$now = Get-Date -Format "dd MMM yyyy HH:mm"
$month = (Get-Date).Month
$year = (Get-Date).Year

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Scholarship Data Refresh Tool" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Started: $now" -ForegroundColor Gray
Write-Host ""

# Map of scholarship websites to check
$sources = @(
    @{ id="emai";     url="https://www.upf.edu/web/emai";             name="EMAI - Artificial Intelligence" }
    @{ id="deai";     url="https://deai.ulb.be/";                    name="DEAI - Data Engineering & AI" }
    @{ id="intermaths"; url="https://www.intermaths.eu/";            name="InterMaths" }
    @{ id="ediss";    url="https://www.master-ediss.eu/";            name="EDISS" }
    @{ id="aiss";     url="https://aissprogram.eu/";                 name="AISS" }
    @{ id="mathsdisc"; url="https://www.mathsdisc.eu/";              name="MATHS-DISC" }
    @{ id="cosse";    url="https://www.kth.se/en/studies/master/computer-simulations-for-science-and-engineering"; name="COSSE" }
    @{ id="mbzuai";   url="https://mbzuai.ac.ae/";                   name="MBZUAI" }
    @{ id="daad";     url="https://www.daad.de/en/";                 name="DAAD" }
    @{ id="fulbright"; url="https://bd.usembassy.gov/";              name="Fulbright Bangladesh" }
    @{ id="chevening"; url="https://www.chevening.org/";             name="Chevening" }
)

$results = @()
$hasChanges = $false

foreach ($source in $sources) {
    Write-Host "Checking $($source.name) ... " -NoNewline -ForegroundColor Yellow
    try {
        $response = Invoke-WebRequest -Uri $source.url -TimeoutSec 15 -UseBasicParsing -ErrorAction Stop
        $status = $response.StatusCode
        $size = $response.RawContentLength
        
        if ($status -eq 200) {
            $content = $response.Content
            
            # Try to extract deadline info using common patterns
            $deadlinePatterns = @(
                '(?:deadline|Deadline|DEADLINE)\s*(?::|is|on)?\s*(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*\d{4})',
                '(?:deadline|Deadline|DEADLINE)\s*(?::|is|on)?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
                '(?:deadline|Deadline|DEADLINE)\s*(?::|is|on)?\s*((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s*\d{4})',
                '(?:apply|Apply|APPLY).{0,30}(?:deadline|Deadline|DEADLINE).{0,30}(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*\d{4})',
                '(?:admissions|Admissions|ADMISSIONS).{0,30}(?:deadline|Deadline|DEADLINE).{0,30}(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*\d{4})'
            )
            
            $foundDeadlines = @()
            foreach ($pattern in $deadlinePatterns) {
                if ($content -match $pattern) {
                    $foundDeadlines += $matches[1]
                }
            }
            
            # Try to extract stipend/funding info
            $stipendPatterns = @(
                '(?:EUR|EURO)\s*(\d{1,4}(?:,\d{3})*(?:\.\d{1,2})?)\s*(?:per|a|each|monthly|/mo|/month)',
                '(?:stipend|Stipend|STIPEND|scholarship|Scholarship).{0,50}(?:EUR)\s*(\d{1,4}(?:,\d{3})*(?:\.\d{1,2})?)',
                '(?:monthly|Monthly).{0,20}(?:stipend|Stipend).{0,20}(?:EUR)\s*(\d{1,4}(?:,\d{3})*(?:\.\d{1,2})?)'
            )
            
            $foundStipends = @()
            foreach ($pattern in $stipendPatterns) {
                if ($content -match $pattern) {
                    $foundStipends += $matches[1]
                }
            }
            
            $result = @{
                id = $source.id
                name = $source.name
                url = $source.url
                status = "OK"
                online = $true
                deadlines = $foundDeadlines -join "; "
                stipends = $foundStipends -join "; "
                size = $size
            }
            Write-Host "OK ($($size) bytes)" -ForegroundColor Green
            
            if ($foundDeadlines.Count -gt 0) {
                Write-Host "    Found deadlines: $($foundDeadlines -join ', ')" -ForegroundColor Gray
            }
            if ($foundStipends.Count -gt 0) {
                Write-Host "    Found stipends: $($foundStipends -join ', ')" -ForegroundColor Gray
            }
        } else {
            $result = @{ id=$source.id; name=$source.name; url=$source.url; status="HTTP $status"; online=$false }
            Write-Host "HTTP $status" -ForegroundColor Red
        }
    }
    catch {
        $result = @{ id=$source.id; name=$source.name; url=$source.url; status="ERROR: $_"; online=$false }
        Write-Host "ERROR" -ForegroundColor Red
        Write-Host "    $_" -ForegroundColor DarkRed
    }
    $results += $result
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Results Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$online = ($results | Where-Object { $_.online }).Count
$offline = ($results | Where-Object { -not $_.online }).Count
Write-Host "Sites online: $online / $($results.Count)" -ForegroundColor Green
Write-Host "Sites offline: $offline / $($results.Count)" -ForegroundColor Yellow

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Updating Dashboard Timestamp" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Update the lastUpdated timestamp in scholarship-data.js
if (Test-Path $dataFile) {
    $content = Get-Content $dataFile -Raw
    $dateStr = Get-Date -Format "dd MMM yyyy HH:mm"
    $content = $content -replace '(lastUpdated:\s*")[^"]*(")', "`$1$dateStr`$2"
    Set-Content -Path $dataFile -Value $content -Encoding UTF8
    Write-Host "Updated lastUpdated to: $dateStr" -ForegroundColor Green
} else {
    Write-Host "scholarship-data.js not found at $dataFile" -ForegroundColor Red
    Write-Host "Creating default file..." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Done! Open dashboard.html and click 'Refresh Data' to see the latest timestamp." -ForegroundColor White
Write-Host "Last checked: $(Get-Date -Format 'dddd, dd MMM yyyy HH:mm')" -ForegroundColor Gray

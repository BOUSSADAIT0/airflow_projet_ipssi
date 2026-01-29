# verify_services.ps1 - Vérifie que Backend, Frontend et Airflow répondent
# Usage: .\verify_services.ps1
# Prérequis: docker-compose -f docker-compose.yml -f docker-compose.airflow.yml up -d

$ErrorActionPreference = "SilentlyContinue"

function Test-Service {
    param([string]$Name, [string]$Url, [string]$Expected = "200")
    Write-Host -NoNewline "  $Name (${Url}) ... "
    try {
        $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10
        if ($r.StatusCode -eq $Expected -or $r.StatusCode -eq 200) {
            Write-Host "OK" -ForegroundColor Green
            return $true
        }
        Write-Host "KO (HTTP $($r.StatusCode))" -ForegroundColor Red
        return $false
    } catch {
        Write-Host "KO ($($_.Exception.Message))" -ForegroundColor Red
        return $false
    }
}

Write-Host "`n=== Vérification Backend / Frontend / Airflow ===`n" -ForegroundColor Cyan

$backend = Test-Service -Name "Backend " -Url "http://localhost:8000/health"
$frontend = Test-Service -Name "Frontend" -Url "http://localhost/"
$airflow  = Test-Service -Name "Airflow " -Url "http://localhost:8080/health"

Write-Host ""
if ($backend -and $frontend -and $airflow) {
    Write-Host "Tous les services sont OK." -ForegroundColor Green
    Write-Host "  - Backend :  http://localhost:8000" -ForegroundColor Gray
    Write-Host "  - Frontend:  http://localhost" -ForegroundColor Gray
    Write-Host "  - Airflow :  http://localhost:8080 (admin / admin)" -ForegroundColor Gray
    exit 0
} else {
    Write-Host "Un ou plusieurs services ne répondent pas." -ForegroundColor Yellow
    Write-Host "Lancer les conteneurs : docker-compose -f docker-compose.yml -f docker-compose.airflow.yml up -d" -ForegroundColor Gray
    Write-Host "Voir les logs : docker logs ocr-backend | ocr-frontend | ocr-airflow" -ForegroundColor Gray
    exit 1
}

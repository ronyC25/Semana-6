Write-Host "Iniciando CYBER-SORT (interface_brazo.py)..." -ForegroundColor Cyan
if (Test-Path ".venv\Scripts\python.exe") {
    & .venv\Scripts\python.exe interface_brazo.py
} else {
    Write-Host "[ERROR] Entorno virtual no encontrado. Ejecuta primero install_project_windows.ps1" -ForegroundColor Red
}

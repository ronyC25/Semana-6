@echo off
echo Iniciando CYBER-SORT (interface_brazo.py)...
if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe interface_brazo.py
) else (
    echo [ERROR] Entorno virtual no encontrado. Ejecuta primero install_project_windows.ps1
    pause
)

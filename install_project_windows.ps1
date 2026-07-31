# PowerShell Installation Script for CYBER-SORT
# Este script instala todos los requisitos para ejecutar la aplicacion

$ProjectName = "CYBER-SORT Robotic Sorting Cell"
$VenvDir = ".venv"
$RequirementsFile = "requirements.txt"
$MainScript = "interface_brazo.py"
$ModelFile = "best01.pt"
$CalibrationFile = "calibracion_cinta.json"
$DatasetDir = "dataset"

function Write-Success {
    param([string]$Message)
    Write-Host -ForegroundColor Green "[OK] $Message"
}

function Write-Warning {
    param([string]$Message)
    Write-Host -ForegroundColor Yellow "[WARN] $Message"
}

function Write-Error {
    param([string]$Message)
    Write-Host -ForegroundColor Red "[FAIL] $Message"
}

function Command-Exists {
    param([string]$CommandName)
    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    $result = (Get-Command $CommandName -ErrorAction SilentlyContinue)
    $ErrorActionPreference = $oldPreference
    return $result
}

Write-Host "==============================================="
Write-Host "Instalacion de $ProjectName (Windows)"
Write-Host "==============================================="

$PythonCmd = $null
foreach ($cmd in @("python", "py", "python3")) {
    if (Command-Exists $cmd) {
        $ver = & $cmd --version 2>&1
        if ($LASTEXITCODE -eq 0 -and $ver -like "*Python*") {
            $PythonCmd = $cmd
            break
        }
    }
}

if (-not $PythonCmd) {
    Write-Error "No se encontro un ejecutable de Python valido. Instala Python o agregalo al PATH."
    exit 1
}

Write-Success "Usando Python: $PythonCmd"

if (Test-Path ".git") {
    Write-Success "Directorio git detectado."
}

if (-not (Test-Path $VenvDir)) {
    Write-Success "Creando entorno virtual: $VenvDir"
    & $PythonCmd -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Error al crear el entorno virtual"
        exit 1
    }
}
else {
    Write-Warning "El entorno virtual $VenvDir ya existe. Se reutilizara."
}

$VenvPip = "$VenvDir\Scripts\pip.exe"
if (Test-Path $VenvPip) {
    $PipCmd = $VenvPip
}
else {
    Write-Error "No se pudo encontrar pip en el entorno virtual."
    exit 1
}

Write-Success "Usando pip: $PipCmd"

Write-Success "Actualizando pip..."
& $PipCmd install --upgrade pip

if (Test-Path $RequirementsFile) {
    Write-Success "Instalando dependencias desde $RequirementsFile..."
    & $PipCmd install -r $RequirementsFile
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Error al instalar dependencias desde $RequirementsFile"
        exit 1
    }
}
else {
    Write-Error "Archivo requirements.txt no encontrado en $RequirementsFile"
    exit 1
}

if (Test-Path $MainScript) {
    Write-Success "Script principal $MainScript listo para ejecutar"
}

Write-Host ""
Write-Host "==============================================="
Write-Host "Instalacion completada con exito."
Write-Host "Ejecutar aplicacion: $VenvDir\Scripts\python.exe $MainScript"
Write-Host "==============================================="

Write-Success "Verificando compatibilidad de la aplicacion..."
try {
    & "$VenvDir\Scripts\python.exe" -c "import customtkinter, serial, cv2, ultralytics, torch, psutil, matplotlib; print('Todas las dependencias importadas correctamente')"
}
catch {
    Write-Error "Error al verificar las dependencias"
}

Write-Success "Instalacion finalizada correctamente."

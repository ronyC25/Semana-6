# PowerShell Installation Script for CYBER-SORT
# Este script instala todos los requisitos para ejecutar la aplicación
# interface_brazo.py en una computadora nueva con Windows.

# Configuración
$ProjectName = "CYBER-SORT Robotic Sorting Cell"
$VenvDir = ".venv"
$RequirementsFile = "requirements.txt"
$MainScript = "interface_brazo.py"
$ModelFile = "best01.pt"
$CalibrationFile = "calibracion_cinta.json"
$DatasetDir = "dataset"

# Colores para PowerShell (Windows 10/11)
$Green = "\033[0;32m"
$Yellow = "\033[1;33m"
$Red = "\033[0;31m"
$NC = "\033[0m" # Sin color

# Función para imprimir mensajes de éxito
function Write-Success {
    param([string]$Message)
    Write-Host -ForegroundColor Green "[✓] $Message"
}

# Función para imprimir mensajes de advertencia
function Write-Warning {
    param([string]$Message)
    Write-Host -ForegroundColor Yellow "[⚠] $Message"
}

# Función para imprimir mensajes de error
function Write-Error {
    param([string]$Message)
    Write-Host -ForegroundColor Red "[✗] $Message"
}

# Función para verificar si un comando existe
function Command-Exists {
    param([string]$CommandName)
    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = "Silencioso"
    $result = (Get-Command $CommandName -ErrorAction SilentlyContinue)
    $ErrorActionPreference = $oldPreference
    return $result
}

# Imprimir encabezado
Write-Host "==============================================="
Write-Host "Instalación de $ProjectName (Windows)"
Write-Host "==============================================="

# Detectar el intérprete de Python adecuado
if (Command-Exists "python3") {
    $PythonCmd = "python3"
}
elseif (Command-Exists "python") {
    $PythonCmd = "python"
}
else {
    Write-Error "No se encontró Python. Por favor instala Python 3.7 o superior desde https://www.python.org/"
    exit 1
}

Write-Success "Usando Python: $PythonCmd"

# Verificar si estamos en un directorio git (opcional)
if (Test-Path ".git") {
    Write-Success "Directorio git detectado."
}
else {
    Write-Warning "No se detectó un directorio git. ¿Este script debe ejecutarse desde la raíz del repositorio?"
}

# Crear y activar entorno virtual
if (-not (Test-Path $VenvDir)) {
    Write-Success "Creando entorno virtual: $VenvDir"
    & $PythonCmd -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Error al crear el entorno virtual"
        exit 1
    }
}
else {
    Write-Warning "El entorno virtual $VenvDir ya existe. Se reutilizará."
}

# Detectar el comando pip adecuado
$VenvPip = "$VenvDir\Scripts\pip.exe"
if (Test-Path $VenvPip) {
    $PipCmd = $VenvPip
}
else {
    Write-Error "No se pudo encontrar pip en el entorno virtual."
    exit 1
}

Write-Success "Usando pip: $PipCmd"

# Actualizar pip a la última versión
Write-Success "Actualizando pip..."
& $PipCmd install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    Write-Error "Error al actualizar pip"
    exit 1
}

# Instalar dependencias desde requirements.txt
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

# Verificar archivos esenciales
$RequiredFiles = @($MainScript, $ModelFile)
foreach ($file in $RequiredFiles) {
    if (Test-Path $file) {
        Write-Success "✓ $file encontrado"
    }
    else {
        if ($file -eq $ModelFile) {
            Write-Warning "⚠️ $file no encontrado. La detección de IA no funcionará sin el modelo.
                 Puedes descargar un modelo YOLOv8 compatible desde https://github.com/ultralytics/ultralytics/releases"
        }
        else {
            Write-Error "❌ $file no encontrado. La aplicación no funcionará sin este archivo."
        }
    }
}

# Verificar si el directorio dataset existe
if (Test-Path $DatasetDir) {
    Write-Success "✓ Directorio de dataset '$DatasetDir' encontrado"
}
else {
    Write-Warning "⚠️ Directorio de dataset '$DatasetDir' no encontrado. Se creará al ejecutar la aplicación."
}

# Verificar si el archivo de calibración existe
if (Test-Path $CalibrationFile) {
    Write-Success "✓ Archivo de calibración '$CalibrationFile' encontrado"
}
else {
    Write-Warning "⚠️ Archivo de calibración '$CalibrationFile' no encontrado. Se usarán valores por defecto al ejecutar la aplicación."
}

# Hacer el script principal ejecutable (Windows)
if (Test-Path $MainScript) {
    # En Windows, no necesitamos chmod, pero podemos verificar las propiedades del archivo
    Write-Success "Script principal $MainScript listo para ejecutar"
}
else {
    Write-Error "Script principal $MainScript no encontrado"
}

# Mostrar comandos útiles
Write-Success "\n==============================================="
Write-Host "Instalación completada con éxito."
Write-Host ""
Write-Host "Comandos útiles:"
Write-Host "  Activar entorno virtual: $VenvDir\Scripts\activate.bat"
Write-Host "  Desactivar entorno virtual: deactivate"
Write-Host "  Ejecutar aplicación: $VenvDir\Scripts\python.exe $MainScript"
Write-Host ""
Write-Host "Archivos importantes:"
Write-Host "  Main application: $MainScript"
Write-Host "  Environment: $VenvDir\" (con todos los scripts en Scripts\)
Write-Host "  Requirements: $RequirementsFile"
Write-Host ""
Write-Host "Para más información, consulta la documentación en GUIA_INSTALACION.md"
Write-Host "==============================================="

# Verificar si se puede importar la aplicación
Write-Success "\nVerificando compatibilidad de la aplicación..."
try {
    & "$VenvDir\Scripts\python.exe" -c "import customtkinter, serial, cv2, ultralytics, torch, psutil, matplotlib; print('✓ Todas las dependencias importadas correctamente')"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Algunos módulos fallaron al importarse. Por favor verifica la instalación."
        exit 1
    }
}
catch {
    Write-Error "Error al verificar las dependencias: $($_.Exception.Message)"
    exit 1
}

Write-Success "¡Instalación completada! Ya puedes ejecutar la aplicación con: $VenvDir\Scripts\python.exe $MainScript"

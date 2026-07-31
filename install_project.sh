#!/bin/bash

# =============================================================================
# Script de Instalación del Proyecto CYBER-SORT
# =============================================================================
# Este script instala todos los requisitos para ejecutar la aplicación
# interface_brazo.py en una computadora nueva.
# =============================================================================

set -e  # Detener ejecución en caso de error

# Configuración
PROJECT_NAME="CYBER-SORT Robotic Sorting Cell"
VENV_DIR=".venv"
REQUIREMENTS_FILE="requirements.txt"
MAIN_SCRIPT="interface_brazo.py"
MODEL_FILE="best01.pt"
CALIBRATION_FILE="calibracion_cinta.json"
DATASET_DIR="dataset"

# Colores para la salida (opcional, para mejorar la experiencia)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # Sin color

# Función para imprimir mensajes de éxito
imprimir_exito() {
    echo -e "${GREEN}[✓]${NC} $1"
}

# Función para imprimir mensajes de advertencia
imprimir_advertencia() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

# Función para imprimir mensajes de error
imprimir_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Imprimir encabezado

echo "==============================================="
echo "Instalación de $PROJECT_NAME"
echo "==============================================="

# Detectar el intérprete de Python adecuado
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    imprimir_error "No se encontró Python. Por favor instala Python 3.7 o superior."
    exit 1
fi

imprimir_exito "Usando Python: $PYTHON_CMD"

# Verificar si estamos en un directorio git (opcional)
if [ -d ".git" ]; then
    imprimir_exito "Directorio git detectado."
else
    imprimir_advertencia "No se detectó un directorio git. ¿Este script debe ejecutarse desde la raíz del repositorio?"
fi

# Crear y activar entorno virtual
if [ ! -d "$VENV_DIR" ]; then
    imprimir_exito "Creando entorno virtual: $VENV_DIR"
    $PYTHON_CMD -m venv $VENV_DIR
else
    imprimir_advertencia "El entorno virtual $VENV_DIR ya existe. Se reutilizará."
fi

# Detectar el comando pip adecuado
if [ -f "$VENV_DIR/bin/pip" ]; then
    PIP_CMD="$VENV_DIR/bin/pip"
elif [ -f "$VENV_DIR/Scripts/pip.exe" ]; then
    PIP_CMD="$VENV_DIR/Scripts/pip.exe"
else
    imprimir_error "No se pudo encontrar pip en el entorno virtual."
    exit 1
fi

imprimir_exito "Usando pip: $PIP_CMD"

# Actualizar pip a la última versión
imprimir_exito "Actualizando pip..."
$PIP_CMD install --upgrade pip

# Instalar dependencias desde requirements.txt
if [ -f "$REQUIREMENTS_FILE" ]; then
    imprimir_exito "Instalando dependencias desde $REQUIREMENTS_FILE..."
    $PIP_CMD install -r $REQUIREMENTS_FILE
else
    imprimir_error "Archivo requirements.txt no encontrado en $REQUIREMENTS_FILE"
    exit 1
fi

# Verificar archivos esenciales
archivos_requeridos=("$MAIN_SCRIPT" "$MODEL_FILE")
for archivo in "${archivos_requeridos[@]}"; do
    if [ -f "$archivo" ]; then
        imprimir_exito "✓ $archivo encontrado"
    else
        if [ "$archivo" = "$MODEL_FILE" ]; then
            imprimir_advertencia "⚠️ $archivo no encontrado. La detección de IA no funcionará sin el modelo.
                 Puedes descargar un modelo YOLOv8 compatible desde https://github.com/ultralytics/ultralytics/releases"
        else
            imprimir_error "❌ $archivo no encontrado. La aplicación no funcionará sin este archivo."
        fi
    fi
done

# Verificar si el directorio dataset existe
if [ -d "$DATASET_DIR" ]; then
    imprimir_exito "✓ Directorio de dataset '$DATASET_DIR' encontrado"
else
    imprimir_advertencia "⚠️ Directorio de dataset '$DATASET_DIR' no encontrado. Se creará al ejecutar la aplicación."
fi

# Verificar si el archivo de calibración existe
if [ -f "$CALIBRATION_FILE" ]; then
    imprimir_exito "✓ Archivo de calibración '$CALIBRATION_FILE' encontrado"
else
    imprimir_advertencia "⚠️ Archivo de calibración '$CALIBRATION_FILE' no encontrado. Se usarán valores por defecto al ejecutar la aplicación."
fi

# Hacer el script principal ejecutable
chmod +x $MAIN_SCRIPT
imprimir_exito "Hecho $MAIN_SCRIPT ejecutable"

# Mostrar comandos útiles
imprimir_exito "\n==============================================="
echo "Instalación completada con éxito."
echo ""
echo "Comandos útiles:"
echo "  Activar entorno virtual: $VENV_DIR/bin/activate (Linux/Mac) o $VENV_DIR/Scripts/activate.bat (Windows)"
echo "  Desactivar entorno virtual: deactivate"
echo "  Ejecutar aplicación: $VENV_DIR/bin/python $MAIN_SCRIPT"
echo ""
echo "Archivos importantes:"
echo "  Main application: $MAIN_SCRIPT"
echo "  Environment: $VENV_DIR/"
echo "  Requirements: $REQUIREMENTS_FILE"
echo ""
echo "Para más información, consulta la documentación en GUIA_INSTALACION.md"
echo "==============================================="

# Verificar si se puede importar la aplicación
imprimir_exito "\nVerificando compatibilidad de la aplicación..."
$VENV_DIR/bin/python -c "import customtkinter, serial, cv2, ultralytics, torch, psutil, matplotlib; print('✓ Todas las dependencias importadas correctamente')" || {
    imprimir_error "Algunos módulos fallaron al importarse. Por favor verifica la instalación."
    exit 1
}

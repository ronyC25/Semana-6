#!/bin/bash

echo "Iniciando la instalación de dependencias para interface_brazo.py..."

# Actualizar pip a la última versión
python -m pip install --upgrade pip

# Instalación de librerías estándar y de visión/control
pip install pyserial opencv-python ultralytics

# Instalación de PyTorch
# Nota: Este comando instala la versión por defecto (usualmente CPU o la última versión compatible con CUDA estándar).
# Si necesitas una versión específica de CUDA, visita: https://pytorch.org/get-started/locally/
pip install torch torchvision torchaudio

echo "¡Instalación de dependencias completada!"

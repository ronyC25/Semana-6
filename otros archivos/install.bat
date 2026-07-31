@echo off
echo Iniciando la instalacion de dependencias para interface_brazo.py...

REM Actualizar pip a la ultima version
python -m pip install --upgrade pip

REM Instalacion de librerias estandar y de vision/control
pip install pyserial opencv-python ultralytics

REM Instalacion de PyTorch
REM Nota: Este comando instala la version por defecto. Si necesitas aceleracion por hardware CUDA,
REM por favor visita: https://pytorch.org/get-started/locally/ para ver el comando exacto de tu entorno.
pip install torch torchvision torchaudio

echo.
echo Instalacion de dependencias completada!
pause

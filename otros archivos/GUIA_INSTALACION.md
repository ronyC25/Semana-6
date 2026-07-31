# Guía de Instalación de Dependencias

Esta guía te explicará cómo ejecutar los scripts de instalación (`install.sh` y `install.bat`) que instalan las librerías necesarias para ejecutar tu programa `interface_brazo.py`.

El código requiere de las siguientes librerías principales:
- `pyserial`: Para la comunicación por puerto serie con el ESP32.
- `opencv-python` (`cv2`): Para el manejo de la cámara web.
- `ultralytics`: Para la detección de objetos usando YOLOv8.
- `torch`, `torchvision`, `torchaudio`: Redes neuronales (backend de YOLO).

---

## Opción 1: Usar el script de Windows (`install.bat`) - Recomendado ⭐
Dado que estás en el sistema operativo Windows, esta es la forma más rápida y nativa.

**Método A (Desde el Explorador de Archivos):**
1. Abre tu Explorador de Archivos de Windows.
2. Navega hasta la carpeta de tu proyecto: `e:\Estudios Rony\9no SEMESTRE\Robotica 2\Semana 6\`.
3. Haz doble clic sobre el archivo `install.bat`.
4. Se abrirá una ventana de consola (CMD) mostrando el progreso de la instalación. Espera a que termine y presiona cualquier tecla para cerrar.

**Método B (Desde PowerShell / VS Code Terminal):**
1. Abre tu terminal de PowerShell en VS Code (o externamente).
2. Asegúrate de estar en la ruta correcta (`cd "e:\Estudios Rony\9no SEMESTRE\Robotica 2\Semana 6"`).
3. Ejecuta el script escribiendo: 
   ```powershell
   .\install.bat
   ```

---

## Opción 2: Usar el script Bash (`install.sh`)
Si prefieres usar un entorno Bash (por ejemplo, si usas **Git Bash** en Windows), puedes utilizar el script `.sh`.

1. Abre tu terminal **Git Bash**.
2. Navega a la carpeta de tu proyecto:
   ```bash
   cd "/e/Estudios Rony/9no SEMESTRE/Robotica 2/Semana 6"
   ```
3. Otorga permisos de ejecución al script (opcional pero recomendado):
   ```bash
   chmod +x install.sh
   ```
4. Ejecuta el script:
   ```bash
   ./install.sh
   ```
   *(Alternativamente, puedes simplemente ejecutar `bash install.sh`)*

---

## Solución de Problemas Comunes

> [!WARNING]
> **Error: "python no se reconoce como un comando interno o externo"**
> Esto significa que Python no está agregado al "PATH" de tu sistema operativo. Deberás reinstalar Python o buscar la opción de "Add Python to PATH" en las variables de entorno de Windows.

> [!TIP]
> **Aceleración por hardware de IA (CUDA / GPU)**
> El script instala la versión básica de `torch`. Si tu computadora cuenta con una tarjeta gráfica NVIDIA y la detección de YOLO te va muy lenta, puedes instalar la versión optimizada para tu GPU.
> 1. Primero, desinstala la versión normal: `pip uninstall torch torchvision torchaudio`
> 2. Ve a la página [PyTorch - Get Started](https://pytorch.org/get-started/locally/) y selecciona "Windows", "Pip", "Python" y tu versión de CUDA (por ejemplo 11.8 o 12.1) para copiar el comando de instalación correcto.
> 3. Ejecuta ese comando en tu terminal.

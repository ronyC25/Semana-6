# Guía de Migración a una Nueva Laptop

Para mudar todo este proyecto a otra computadora y que el *Dashboard Avanzado*, el *YOLOv8* y la conexión con el *ESP32* funcionen de inmediato, debes seguir estos pasos para empaquetar y replicar el entorno.

## 1. Archivos que debes copiar (aislamiento del código)
Copia **toda la carpeta del proyecto** en una memoria USB (o comprímela en un `.zip`). Sin embargo, asegúrate de que los siguientes archivos clave estén ahí:

- `interface_brazo.py` (El código principal con el nuevo Dashboard)
- `best01.pt` o `best.pt` (El modelo de IA entrenado)
- `calibracion_cinta.json` (Para no perder tu configuración)
- `requirements.txt` (Contiene **todas** las librerías actualizadas que aislamos)
- Carpetas adicionales como `dataset/` si quieres conservar las fotos que has tomado.

> [!WARNING]  
> **NO COPIES** la carpeta `.venv` si la tienes. Los entornos virtuales no se pueden mover de computadora a computadora; hay que crear uno nuevo en la otra laptop.

## 2. Preparar la nueva laptop

Una vez que pases la carpeta a la nueva laptop y la abras en VS Code (o tu terminal), debes preparar Python:

1. **Asegúrate de tener Python 3.10 o 3.11 instalado** (marcando la opción *Add Python to PATH* durante su instalación).
2. Abre la terminal dentro de la carpeta y, de manera opcional, crea un entorno virtual (muy recomendado para no ensuciar la nueva laptop):
   ```bash
   python -m venv .venv
   ```
3. Actívalo:
   - En Windows (PowerShell): `.\.venv\Scripts\Activate.ps1`
   - En Windows (CMD): `.\.venv\Scripts\activate.bat`

## 3. Instalar las Librerías (Requirements)

Ya he actualizado y purgado el archivo `requirements.txt` con **absolutamente todas** las dependencias necesarias para este dashboard.

Ejecuta el siguiente comando en la terminal de la nueva laptop:
```bash
pip install -r requirements.txt
```

Esto instalará automáticamente:
- `customtkinter` y `Pillow` (para la interfaz)
- `matplotlib` (para la gráfica de rendimiento)
- `pyserial` y `psutil` (para el control y KPIs)
- `opencv-python` y `ultralytics` (para la cámara y la IA)
- `torch` (Motor Neuronal)

> [!TIP]
> Si la nueva laptop tiene una tarjeta de video **NVIDIA** y quieres usar CUDA para que el brazo no tenga retraso, deberás desinstalar el PyTorch básico y poner el de GPU con este comando:
> `pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118`

## 4. Ejecutar

Conecta tu ESP32, conecta tu cámara (si usas una web externa), revisa que el número de puerto (COM) sea el mismo en el código (si cambió en la nueva laptop, edita `PUERTO = 'COMX'` en la línea 18) y lanza el sistema:

```bash
python interface_brazo.py
```

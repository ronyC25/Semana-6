# 🚀 Guía Definitiva de Instalación y Migración del Proyecto (Windows)

Esta guía documenta paso a paso cómo instalar y ejecutar el proyecto **CYBER-SORT (Robotic Sorting Cell)** en una computadora nueva con Windows 10/11 sin experimentar errores de dependencias, permisos o rutas de archivos.

---

## 📋 Requisitos Previos

Antes de comenzar, asegúrate de tener instalado en la computadora nueva:

1. **Python 3.10 o superior**:
   - Descargar de [python.org](https://www.python.org/downloads/).
   - ⚠️ **CRÍTICO:** Durante la instalación, marca la casilla **"Add Python.exe to PATH"** en la primera pantalla del instalador.
2. **Git para Windows**:
   - Descargar de [git-scm.com](https://git-scm.com/).

---

## 🛠️ Paso 1: Configuración Inicial de Windows (Evitar errores conocidos)

### A. Habilitar Rutas Largas (`MAX_PATH`) en Windows
Para evitar el error `[WinError 206] El nombre del archivo es demasiado largo` al instalar PyTorch/YOLO:

1. Abre **PowerShell como Administrador** (clic derecho en el menú Inicio > *PowerShell como Administrador* o *Terminal como Administrador*).
2. Ejecuta el siguiente comando:
   ```powershell
   Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name 'LongPathsEnabled' -Value 1
   ```

### B. Habilitar la ejecución de Scripts en PowerShell
En la misma consola de PowerShell (o consola normal):
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
```

---

## 📥 Paso 2: Descargar el Proyecto

Abre la consola de **PowerShell**, navega a la carpeta donde deseas guardar el proyecto (por ejemplo `Documents`) y ejecuta:

```powershell
git clone https://github.com/ronyC25/Semana-6.git
cd Semana-6
```

---

## ⚡ Paso 3: Instalación Automática de Dependencias

Dentro de la carpeta `Semana-6`, ejecuta el script automatizado:

```powershell
.\install_project_windows.ps1
```

### ¿Qué hace este script?
- Detecta el ejecutable real de Python (omitiendo accesos directos falsos de la Tienda de Microsoft).
- Crea el entorno virtual aislado `.venv`.
- Actualiza `pip` e instala automáticamente todas las librerías necesarias:
  - `customtkinter` (Interfaz gráfica)
  - `pyserial` (Comunicación serie con el ESP32)
  - `opencv-python` (Cámara web)
  - `ultralytics` y `torch` / `torchvision` (Visión por Computadora YOLOv8)
  - `psutil` y `matplotlib` (Dashboard y métricas)
- Verifica la compatibilidad e integridad de todos los módulos importados.

---

## 🎮 Paso 4: Conexión de Hardware y Ejecución

1. **Cámara Web**:
   - Conecta la cámara USB a la computadora.

2. **Brazo Robótico / ESP32**:
   - Conecta el controlador por USB.
   - Abre el **Administrador de Dispositivos** de Windows y revisa la sección **Puertos (COM y LPT)** para identificar el puerto (ejemplo: `COM3`, `COM4` o `COM5`).
   - Si tu puerto es diferente a `COM5`, abre `interface_brazo.py` y modifica la línea 21:
     ```python
     PUERTO = 'COM3'  # Ajusta según corresponda
     ```

3. **Ejecutar la Aplicación**:
   Puedes iniciar el programa de dos formas sencillas:
   - **Opción A (Desde PowerShell):**
     ```powershell
     .\run.ps1
     ```
   - **Opción B (Desde el Explorador de Archivos):**
     Haz **doble clic** sobre el archivo **`run.bat`**.

---

## ❓ Solución de Problemas Frecuentes

| Problema / Error | Causa | Solución |
| :--- | :--- | :--- |
| **`WinError 206` / Ruta demasiado larga** | Límite por defecto de 260 caracteres en Windows al instalar PyTorch. | Ejecuta la instrucción del **Paso 1.A** como Administrador o mueve el proyecto a una carpeta con ruta corta (ej. `C:\Semana-6`). |
| **`ModuleNotFoundError: No module named 'customtkinter'`** | Se ejecutó Python global fuera del entorno virtual `.venv` o la instalación previa se canceló a la mitad. | Usa siempre `.\run.ps1` o `run.bat` para lanzar la app, y ejecuta `.\install_project_windows.ps1` para asegurar la instalación completa. |
| **`No se encontró Python / Redirección a Microsoft Store`** | Windows tiene activado el alias ejecutable de la Tienda de Windows para `python3`. | El script `install_project_windows.ps1` ya corrige esto automáticamente seleccionando `python`. Asegúrate de haber hecho `git pull`. |
| **No se conecta al brazo robótico** | El puerto COM no coincide o faltan drivers del chip USB-Serial (CH340/CP2102). | Verifica el puerto en el Administrador de Dispositivos e instala los drivers del ESP32 si aparece con un signo de advertencia amarillo. |


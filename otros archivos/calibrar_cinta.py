"""
CALIBRACION DE CINTA - SCRIPT EJECUTABLE
==========================================
Ejecutar con:

    python calibrar_cinta.py

Requiere que el ESP32 este conectado y la camara disponible, igual que
interface_brazo.py. NO mueve el brazo, solo la cinta.
"""

import time
import serial
import cv2
import numpy as np
from ultralytics import YOLO

# --- MISMA CONFIGURACION QUE interface_brazo.py ---
PUERTO = 'COM5'
BAUDRATE = 115200
MODELO_PATH = 'best01.pt'

# --- AJUSTA ESTO ANTES DE CORRER ---
# Cuantos pixeles equivalen a 1 cm real en tu imagen (mide con una regla
# frente a la camara, en el plano de la cinta).
PX_POR_CM = 20.0  # <-- CAMBIAR por tu valor medido real


class CalibradorCinta:
    def __init__(self, px_por_cm):
        self.px_por_cm = px_por_cm
        self.resultados_calibracion = []

        print(f"🔌 Conectando a {PUERTO}...")
        self.esp = serial.Serial(PUERTO, BAUDRATE, timeout=1)
        time.sleep(2)
        self.esp.reset_input_buffer()
        print("✅ ESP32 conectado.")

        print(f"🖥️ Cargando modelo {MODELO_PATH}...")
        self.model = YOLO(MODELO_PATH)
        print("✅ Modelo cargado.")

        print("🎥 Abriendo camara...")
        self.cap = cv2.VideoCapture(1)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        print("✅ Camara lista.")

    def enviar_comando_serial(self, comando_texto):
        self.esp.write(comando_texto.encode('utf-8'))

    def medir_velocidad_actual(self, duracion_segundos=1.5):
        posiciones = []
        t_inicio = time.time()

        while time.time() - t_inicio < duracion_segundos:
            ret, frame = self.cap.read()
            if not ret:
                continue

            resultados = self.model.track(frame, persist=True,
                                           tracker="bytetrack.yaml",
                                           conf=0.5, verbose=False)

            if resultados[0].boxes.id is not None and len(resultados[0].boxes) > 0:
                box = resultados[0].boxes[0]
                x1, y1, x2, y2 = box.xyxy[0]
                cx = float((x1 + x2) / 2)
                posiciones.append((time.time(), cx))

            cv2.imshow("Calibracion - presiona Q para abortar", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                raise KeyboardInterrupt("Abortado por el usuario")

        if len(posiciones) < 2:
            return None

        tiempos = np.array([p[0] for p in posiciones])
        posiciones_px = np.array([p[1] for p in posiciones])
        v_px_por_seg, _ = np.polyfit(tiempos - tiempos[0], posiciones_px, 1)
        return abs(v_px_por_seg / self.px_por_cm)

    def buscar_deadband_motor(self, pwm_max_prueba=255, paso=5,
                                umbral_cm_s=0.5):
        print("\n🔍 BUSCANDO DEADBAND DEL MOTOR NUEVO")
        print("   (coloca un objeto de referencia visible sobre la cinta)\n")
        for pwm in range(0, pwm_max_prueba + 1, paso):
            self.enviar_comando_serial(f"C:{pwm}\n")
            time.sleep(0.4)
            cms = self.medir_velocidad_actual(1.0)
            self.enviar_comando_serial("C:0\n")

            if cms is not None and cms >= umbral_cm_s:
                print(f"✅ Deadband detectado en PWM={pwm} ({cms:.2f} cm/s)\n")
                return pwm
            print(f"   PWM={pwm} → sin movimiento ({cms})")

        print("⚠️ No se detecto movimiento en todo el rango.")
        return None

    def calibrar_pwm(self, pwm, duracion_segundos=2.0):
        print(f"🔧 Calibrando PWM={pwm} ...")
        self.enviar_comando_serial(f"C:{pwm}\n")
        time.sleep(0.5)
        cms = self.medir_velocidad_actual(duracion_segundos)
        self.enviar_comando_serial("C:0\n")

        if cms is not None:
            print(f"   → {cms:.2f} cm/s")
            self.resultados_calibracion.append((pwm, cms))
        else:
            print("   → No se detecto movimiento, se descarta este punto")
        return cms

    def ajustar_modelo_pwm(self):
        if len(self.resultados_calibracion) < 2:
            print("⚠️ Se necesitan al menos 2 puntos validos.")
            return None
        pwms = np.array([r[0] for r in self.resultados_calibracion])
        cms = np.array([r[1] for r in self.resultados_calibracion])
        m, b = np.polyfit(cms, pwms, 1)
        print(f"\n✅ MODELO AJUSTADO: pwm = {m:.3f} * cms + {b:.3f}")
        return m, b

    def cerrar(self):
        self.enviar_comando_serial("C:0\n")
        self.esp.close()
        self.cap.release()
        cv2.destroyAllWindows()


def main():
    calibrador = CalibradorCinta(PX_POR_CM)

    try:
        # PASO 1: encontrar el nuevo minimo real del motor
        pwm_min = calibrador.buscar_deadband_motor()
        if pwm_min is None:
            print("No se pudo continuar sin detectar el deadband.")
            return

        # PASO 2: medir velocidad en varios puntos por encima del minimo
        pwms_a_probar = sorted(set([
            pwm_min, pwm_min + 20, pwm_min + 50, pwm_min + 90, 200, 255
        ]))
        pwms_a_probar = [p for p in pwms_a_probar if p <= 255]

        for pwm in pwms_a_probar:
            calibrador.calibrar_pwm(pwm)

        # PASO 3: ajustar modelo lineal
        resultado = calibrador.ajustar_modelo_pwm()

        if resultado:
            m, b = resultado
            print("\n" + "=" * 50)
            print("COPIA ESTOS VALORES EN interface_brazo.py:")
            print("=" * 50)
            print(f"  pwm_min_nuevo = {pwm_min}")
            print(f"  m = {m:.3f}")
            print(f"  b = {b:.3f}")
            print("\nEn convertir_cms_a_pwm() y en on_cinta_move(),")
            print(f"reemplaza 140 por {pwm_min} y usa pwm = int(m*cms + b)")
            print("=" * 50)

    except KeyboardInterrupt:
        print("\n⏹️ Calibracion abortada por el usuario.")
    finally:
        calibrador.cerrar()


if __name__ == "__main__":
    main()
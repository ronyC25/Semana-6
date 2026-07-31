import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from PIL import Image, ImageTk
import serial
import time
import threading
import json
import os
import cv2
import numpy as np
from ultralytics import YOLO
import torch
import psutil
import collections
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# --- CONFIGURACIÓN SERIAL ---
PUERTO = 'COM5'
BAUDRATE = 115200

# --- CONFIGURACIÓN DEL MODELO DE VISIÓN ---
MODELO_PATH = 'best01.pt'
CALIBRACION_FILE = 'calibracion_cinta.json'
DATASET_DIR = 'dataset'

if not os.path.exists(DATASET_DIR):
    os.makedirs(DATASET_DIR)

CONFIG_BRAZO = {
    'Base (MG996R)':           {'canal': 8,  'min': 0,   'max': 180, 'home': 15,  'dh_index': 0},
    'Hombro (MG996R)':         {'canal': 9,  'min': 10,  'max': 170, 'home': 150, 'dh_index': 1},
    'Codo (MG996R)':           {'canal': 10, 'min': 30,  'max': 160, 'home': 130, 'dh_index': 2},
    'Muñeca 1 - Cabeceo':      {'canal': 11, 'min': 0,   'max': 180, 'home': 90,  'dh_index': 3},
    'Muñeca 2 - Alabeo (SG90)':{'canal': 12, 'min': 0,   'max': 180, 'home': 80,  'dh_index': 4},
    'Pinza - Garra (MG90S)':   {'canal': 13, 'min': 10,  'max': 110, 'home': 50,  'dh_index': None}
}

DEFAULTS_CALIBRACION = {
    'modelo_m': 10.5,
    'modelo_b': 97.5,
    'modelo_pwm_min': 140,
    'px_por_cm': None
}

class AppBrazoRobotico:
    def __init__(self, root):
        self.root = root
        self.root.title("CYBER-SORT // Robotic Sorting Cell Dashboard")
        self.root.geometry("1400x850")
        
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.sliders_vars = {}
        self.labels_angulos = {}
        self.last_sent_values = {}
        self.dh_items = {}

        self.velocidad_cinta_cms = 10.0
        self.distancia_ciega_cm = 5.0
        self.retraso_fino_segundos = 2.00

        self.brazo_ocupado = False
        self.historial_confianza = {}
        self.minerales_confirmados = set()
        self.minerales_encolados = set()
        self.cola_recoleccion = []

        self.rocas_detectadas_total = 0
        self.rocas_recogidas_total = 0
        
        self.lock_deteccion = threading.Lock()
        self.deteccion_actual = None
        self.modo_calibracion = False
        self.resultados_calibracion = []
        
        # Para el módulo de Dataset
        self.ultimo_frame_limpio = None
        self.lock_frame = threading.Lock()

        self.cargar_calibracion_cinta()

        self.dispositivo = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"🖥️ IA asignada a: {self.dispositivo.upper()}")

        self.conectar_serial()
        self.crear_interfaz()
        self.cargar_modelo_ia()

        threading.Thread(target=self.procesar_vision_artificial, daemon=True).start()
        threading.Thread(target=self.gestor_cola_recoleccion, daemon=True).start()

        self.root.after(1000, lambda: threading.Thread(target=self.arranque_inicial, daemon=True).start())
        
        # Bucle seguro de renderizado de video en el hilo principal para evitar parpadeos
        self.current_frame_img = None
        
        # Nuevas variables de métricas avanzadas (Nivel 2)
        self.inicio_sistema = time.time()
        self.suma_ancho_rocas = 0
        self.historial_throughput = collections.deque([0]*60, maxlen=60)
        self.tiempo_grafico = collections.deque([0]*60, maxlen=60)
        self.throughput_counter = 0
        self.estado_cam = False
        self.estado_esp = False
        self.estado_ia = False
        
        # Iniciar bucles de interfaz
        self.actualizar_kpis()
        self.root.after(33, self._renderizar_video_loop)
        self.root.after(1000, self.actualizar_grafico)

    def cargar_calibracion_cinta(self):
        datos = dict(DEFAULTS_CALIBRACION)
        if os.path.exists(CALIBRACION_FILE):
            try:
                with open(CALIBRACION_FILE, 'r') as f:
                    datos.update(json.load(f))
                print(f"✅ Calibración de cinta cargada desde {CALIBRACION_FILE}")
            except Exception as e:
                print(f"⚠️ No se pudo leer {CALIBRACION_FILE}, usando valores por defecto ({e})")

        self.modelo_m = datos['modelo_m']
        self.modelo_b = datos['modelo_b']
        self.modelo_pwm_min = datos['modelo_pwm_min']
        self.px_por_cm = datos['px_por_cm']

    def guardar_calibracion_cinta(self):
        datos = {
            'modelo_m': self.modelo_m,
            'modelo_b': self.modelo_b,
            'modelo_pwm_min': self.modelo_pwm_min,
            'px_por_cm': self.px_por_cm,
        }
        with open(CALIBRACION_FILE, 'w') as f:
            json.dump(datos, f, indent=2)
        print(f"💾 Calibración guardada en {CALIBRACION_FILE}")

    def convertir_cms_a_pwm(self, cms):
        if cms <= 0: return 0
        pwm = int(self.modelo_m * cms + self.modelo_b)
        if pwm < self.modelo_pwm_min: pwm = self.modelo_pwm_min
        if pwm > 255: pwm = 255
        return pwm

    def calcular_angulo_pinza(self, ancho_pixeles):
        px_min = 50
        px_max = 180
        angulo_mas_cerrado = 15
        angulo_mas_abierto = 60

        if ancho_pixeles <= px_min: return angulo_mas_cerrado
        if ancho_pixeles >= px_max: return angulo_mas_abierto

        angulo = angulo_mas_cerrado + ((ancho_pixeles - px_min) * (angulo_mas_abierto - angulo_mas_cerrado) / (px_max - px_min))
        margen_apriete = 12
        angulo_final = int(angulo) - margen_apriete

        if angulo_final < angulo_mas_cerrado:
            angulo_final = angulo_mas_cerrado

        return int(angulo_final)

    def cargar_modelo_ia(self):
        if not os.path.exists(MODELO_PATH):
            messagebox.showerror("Error de IA", f"No se encontró el modelo: {MODELO_PATH}")
            self.model = None
            self.estado_ia = False
        else:
            self.model = YOLO(MODELO_PATH)
            self.estado_ia = True
            print("✅ Modelo YOLOv8 cargado con éxito.")

    def conectar_serial(self):
        try:
            self.esp = serial.Serial(PUERTO, BAUDRATE, timeout=1)
            time.sleep(2)
            self.esp.reset_input_buffer()
            self.estado_esp = True
            print(f"✅ Conectado al ESP32 ({PUERTO})")
        except serial.SerialException:
            self.estado_esp = False
            print("⚠️ ESP32 no detectado en el puerto especificado.")

    def enviar_comando_serial(self, comando_texto):
        if hasattr(self, 'esp') and self.esp.is_open:
            self.esp.write(comando_texto.encode('utf-8'))

    def _sincronizar_ui_servo(self, nombre, angulo):
        self.sliders_vars[nombre].set(angulo)
        self.labels_angulos[nombre].configure(text=f"{angulo}°")
        if nombre in self.dh_items:
            item_id = self.dh_items[nombre]
            valores = self.tree_dh.item(item_id, "values")
            self.tree_dh.item(item_id, values=(valores[0], valores[1], f"{angulo}°", valores[3], valores[4], valores[5]))

    def actualizar_posicion_local(self, canal, angulo):
        self.last_sent_values[canal] = angulo
        for nombre, conf in CONFIG_BRAZO.items():
            if conf['canal'] == canal:
                self.root.after(0, self._sincronizar_ui_servo, nombre, angulo)
                break

    def gestor_cola_recoleccion(self):
        while True:
            if not self.brazo_ocupado and len(self.cola_recoleccion) > 0:
                id_roca, tiempo_llegada, angulo_agarre, ancho_pixeles = self.cola_recoleccion[0]

                if time.time() >= tiempo_llegada:
                    print(f"🎯 ¡Tiempo cumplido para Mineral ID: {id_roca}! Interceptando...")
                    self.brazo_ocupado = True
                    self.cola_recoleccion.pop(0)
                    threading.Thread(target=self.rutina_pick_and_place, args=(id_roca, angulo_agarre, ancho_pixeles), daemon=True).start()

            time.sleep(0.01)

    def procesar_vision_artificial(self):
        cap = cv2.VideoCapture(1)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)

        LIMITE_SALIDA_X = 1150

        while cap.isOpened() and self.model is not None:
            ret, frame = cap.read()
            if not ret: 
                self.estado_cam = False
                continue
            self.estado_cam = True
            
            with self.lock_frame:
                self.ultimo_frame_limpio = frame.copy()

            if self.brazo_ocupado:
                overlay = frame.copy()
                cv2.rectangle(overlay, (0, 0), (1280, 50), (15, 15, 15), -1)
                cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
                cv2.line(frame, (0, 50), (1280, 50), (0, 0, 255), 2)
                cv2.putText(frame, "WARNING: BRAZO EN MOVIMIENTO - INTERCEPTANDO", (30, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                
                self.actualizar_feed_ui(frame)
                time.sleep(0.03) # Limitar un poco para no saturar UI
                continue

            resultados = self.model.track(frame, persist=True, tracker="bytetrack.yaml", conf=0.5, verbose=False)
            frame_anotado = frame.copy()

            if resultados[0].boxes.id is not None:
                for box in resultados[0].boxes:
                    id_roca = int(box.id[0])
                    confianza = float(box.conf[0])
                    clase_id = int(box.cls[0])
                    nombre_clase = resultados[0].names[clase_id].lower()

                    x1, y1, x2, y2 = box.xyxy[0]
                    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                    cx = int((x1 + x2) / 2)
                    ancho_pixeles = int(x2 - x1)

                    color_neon = (255, 255, 0) # Cyan
                    if id_roca in self.minerales_encolados:
                        color_neon = (0, 0, 255) # Rojo
                    elif id_roca in self.minerales_confirmados:
                        color_neon = (0, 255, 0) # Verde

                    l_corner = 20
                    t_line = 2
                    cv2.line(frame_anotado, (x1, y1), (x1+l_corner, y1), color_neon, t_line)
                    cv2.line(frame_anotado, (x1, y1), (x1, y1+l_corner), color_neon, t_line)
                    cv2.line(frame_anotado, (x2, y1), (x2-l_corner, y1), color_neon, t_line)
                    cv2.line(frame_anotado, (x2, y1), (x2, y1+l_corner), color_neon, t_line)
                    cv2.line(frame_anotado, (x1, y2), (x1+l_corner, y2), color_neon, t_line)
                    cv2.line(frame_anotado, (x1, y2), (x1, y2-l_corner), color_neon, t_line)
                    cv2.line(frame_anotado, (x2, y2), (x2-l_corner, y2), color_neon, t_line)
                    cv2.line(frame_anotado, (x2, y2), (x2, y2-l_corner), color_neon, t_line)
                    cv2.drawMarker(frame_anotado, (cx, int((y1+y2)/2)), color_neon, cv2.MARKER_CROSS, 10, 1)

                    texto_obj = f"[{id_roca}] {nombre_clase.upper()} {confianza:.2f}"
                    cv2.rectangle(frame_anotado, (x1, y1-22), (x1 + len(texto_obj)*8, y1), color_neon, -1)
                    cv2.putText(frame_anotado, texto_obj, (x1+4, y1-6), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1, cv2.LINE_AA)

                    if "mineral" in nombre_clase:
                        with self.lock_deteccion:
                            self.deteccion_actual = (time.time(), cx, ancho_pixeles)

                        if self.modo_calibracion: continue

                        if id_roca not in self.historial_confianza:
                            self.historial_confianza[id_roca] = []

                        self.historial_confianza[id_roca].append(confianza)

                        if len(self.historial_confianza[id_roca]) > 15:
                            self.historial_confianza[id_roca].pop(0)

                        promedio = sum(self.historial_confianza[id_roca]) / len(self.historial_confianza[id_roca])

                        if promedio > 0.80 and len(self.historial_confianza[id_roca]) >= 5:
                            if id_roca not in self.minerales_confirmados:
                                self.minerales_confirmados.add(id_roca)
                                self.rocas_detectadas_total += 1
                                self.throughput_counter += 1

                    if (not self.modo_calibracion and id_roca in self.minerales_confirmados
                            and id_roca not in self.minerales_encolados):
                        if cx > LIMITE_SALIDA_X:
                            self.minerales_encolados.add(id_roca)

                            tiempo_viaje_segundos = (self.distancia_ciega_cm / self.velocidad_cinta_cms) + self.retraso_fino_segundos
                            tiempo_exacto_llegada = time.time() + tiempo_viaje_segundos

                            es_fantasma = False
                            if len(self.cola_recoleccion) > 0:
                                _, ultimo_tiempo, _, _ = self.cola_recoleccion[-1]
                                if tiempo_exacto_llegada - ultimo_tiempo < 1.5:
                                    es_fantasma = True
                                    print(f"👻 Reflejo fantasma evitado! Mineral ID {id_roca} ignorado por estar muy cerca.")

                            if not es_fantasma:
                                angulo_agarre = self.calcular_angulo_pinza(ancho_pixeles)
                                self.cola_recoleccion.append((id_roca, tiempo_exacto_llegada, angulo_agarre, ancho_pixeles))

            if not hasattr(self, '_last_hud_update'): self._last_hud_update = 0
            if not hasattr(self, '_hud_cpu'): self._hud_cpu = 0
            if not hasattr(self, '_hud_gpu'): self._hud_gpu = 0
            if time.time() - self._last_hud_update > 1.0:
                self._hud_cpu = psutil.cpu_percent()
                if torch.cuda.is_available():
                    self._hud_gpu = torch.cuda.memory_allocated() / (1024**2)
                self._last_hud_update = time.time()

            overlay = frame_anotado.copy()
            cv2.rectangle(overlay, (0, 0), (1280, 50), (15, 15, 15), -1)
            cv2.addWeighted(overlay, 0.7, frame_anotado, 0.3, 0, frame_anotado)
            cv2.line(frame_anotado, (0, 50), (1280, 50), (255, 0, 255), 2)

            cv2.putText(frame_anotado, "NEURAL_NET: YOLOv8_ON_BYTETRACK", (15, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            stats = f"SYS_CPU: {self._hud_cpu}%  //  GPU_VRAM: {self._hud_gpu:.1f}MB  //  DEVICE: {str(self.dispositivo).upper()}"
            cv2.putText(frame_anotado, stats, (400, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(frame_anotado, "TARGETING_SYS: ONLINE", (1030, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            cv2.line(frame_anotado, (640, 50), (640, 720), (255, 255, 255), 1)
            for i in range(100, 720, 100):
                cv2.line(frame_anotado, (635, i), (645, i), (255, 255, 255), 1)

            if self.modo_calibracion:
                cv2.putText(frame_anotado, ">> MODO CALIBRACION ACTIVO <<", (30, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
            else:
                cv2.line(frame_anotado, (LIMITE_SALIDA_X, 50), (LIMITE_SALIDA_X, 720), (0, 0, 255), 2)
                cv2.putText(frame_anotado, "ZONA_INTERCEPCION", (LIMITE_SALIDA_X - 190, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

            self.actualizar_feed_ui(frame_anotado)

        cap.release()
        
    def actualizar_feed_ui(self, frame):
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_resized = cv2.resize(frame_rgb, (960, 540))
        # Guardamos la imagen procesada; el hilo principal (GUI) se encarga de pintarla sin parpadeos.
        self.current_frame_img = Image.fromarray(frame_resized)

    def _renderizar_video_loop(self):
        if hasattr(self, 'current_frame_img') and self.current_frame_img is not None:
            imgtk = ImageTk.PhotoImage(image=self.current_frame_img)
            self.lbl_video.imgtk = imgtk
            self.lbl_video.configure(image=imgtk)
        self.root.after(33, self._renderizar_video_loop)

    def capturar_dataset(self):
        with self.lock_frame:
            if self.ultimo_frame_limpio is not None:
                ts = int(time.time() * 1000)
                ruta = os.path.join(DATASET_DIR, f"captura_{ts}.jpg")
                cv2.imwrite(ruta, self.ultimo_frame_limpio)
                print(f"📸 Imagen guardada en {ruta}")
                
                orig_color = self.btn_capturar.cget("fg_color")
                self.btn_capturar.configure(fg_color="#f59e0b", text="¡CAPTURA EXITOSA!")
                self.root.after(1500, lambda: self.btn_capturar.configure(fg_color=orig_color, text="📸 Capturar Frame"))

    def actualizar_kpis(self):
        if hasattr(self, 'lbl_kpi_detectadas'):
            self.lbl_kpi_detectadas.configure(text=f"{self.rocas_detectadas_total}")
        if hasattr(self, 'lbl_kpi_recogidas'):
            self.lbl_kpi_recogidas.configure(text=f"{self.rocas_recogidas_total}")
        
        eficiencia = 0
        if self.rocas_detectadas_total > 0:
            eficiencia = int((self.rocas_recogidas_total / self.rocas_detectadas_total) * 100)
        
        if hasattr(self, 'lbl_kpi_eficiencia'):
            self.lbl_kpi_eficiencia.configure(text=f"{eficiencia}%")

        self.root.after(1000, self.actualizar_kpis)

    def accion_calibrar_completo(self):
        if self.px_por_cm is None:
            messagebox.showwarning("Falta calibrar escala", "Primero ingresa 'Píxeles por cm' y presiona Guardar escala.")
            return
        if self.brazo_ocupado:
            messagebox.showwarning("Brazo ocupado", "Espera a que el brazo termine su ciclo actual.")
            return
        threading.Thread(target=self._rutina_calibracion_completa, daemon=True).start()

    def medir_velocidad_actual(self, duracion_segundos=1.5):
        muestras = []
        t_inicio = time.time()
        ultimo_timestamp_visto = None
        while time.time() - t_inicio < duracion_segundos:
            with self.lock_deteccion:
                dato = self.deteccion_actual
            if dato is not None:
                ts, cx, _ancho = dato
                if ts != ultimo_timestamp_visto:
                    muestras.append((ts, cx))
                    ultimo_timestamp_visto = ts
            time.sleep(0.02)
        if len(muestras) < 2 or self.px_por_cm is None:
            return None
        tiempos = np.array([m[0] for m in muestras])
        posiciones_px = np.array([m[1] for m in muestras])
        v_px_por_seg, _ = np.polyfit(tiempos - tiempos[0], posiciones_px, 1)
        return abs(v_px_por_seg / self.px_por_cm)

    def log_calibracion(self, texto):
        print(texto)
        self.root.after(0, self._append_log_calibracion, texto)

    def _append_log_calibracion(self, texto):
        self.txt_log_calibracion.insert(tk.END, texto + "\n")
        self.txt_log_calibracion.see(tk.END)

    def _rutina_calibracion_completa(self):
        self.modo_calibracion = True
        self.resultados_calibracion = []
        self.root.after(0, lambda: self.txt_log_calibracion.delete(1.0, tk.END))
        self.log_calibracion("=== INICIANDO CALIBRACIÓN DE CINTA ===")
        self.log_calibracion("Coloca un mineral de referencia sobre la cinta.")

        try:
            self.log_calibracion("\n🔍 Buscando deadband del motor...")
            pwm_min = None
            for pwm in range(0, 256, 5):
                self.enviar_comando_serial(f"C:{pwm}\n")
                time.sleep(0.4)
                cms = self.medir_velocidad_actual(1.0)
                self.enviar_comando_serial("C:0\n")

                if cms is not None and cms >= 0.5:
                    pwm_min = pwm
                    self.log_calibracion(f"✅ Deadband detectado: PWM={pwm} ({cms:.2f} cm/s)")
                    break
                self.log_calibracion(f"   PWM={pwm} → sin movimiento detectable")

            if pwm_min is None:
                self.log_calibracion("⚠️ No se detectó movimiento en ningún PWM. Aborta y revisa el motor/driver.")
                return

            self.log_calibracion("\n📏 Midiendo velocidad real en varios PWM...")
            pwms_a_probar = sorted(set([pwm_min, pwm_min + 20, pwm_min + 50, pwm_min + 90, 200, 255]))
            pwms_a_probar = [p for p in pwms_a_probar if p <= 255]

            for pwm in pwms_a_probar:
                self.enviar_comando_serial(f"C:{pwm}\n")
                time.sleep(0.5)
                cms = self.medir_velocidad_actual(2.0)
                self.enviar_comando_serial("C:0\n")

                if cms is not None:
                    self.resultados_calibracion.append((pwm, cms))
                    self.log_calibracion(f"   PWM={pwm} → {cms:.2f} cm/s")
                else:
                    self.log_calibracion(f"   PWM={pwm} → sin datos, se descarta")

            if len(self.resultados_calibracion) < 2:
                self.log_calibracion("⚠️ No hay suficientes puntos válidos para ajustar el modelo.")
                return

            pwms = np.array([r[0] for r in self.resultados_calibracion])
            cms_arr = np.array([r[1] for r in self.resultados_calibracion])
            m, b = np.polyfit(cms_arr, pwms, 1)

            self.modelo_m = float(m)
            self.modelo_b = float(b)
            self.modelo_pwm_min = int(pwm_min)
            self.guardar_calibracion_cinta()

            self.log_calibracion(f"\n✅ MODELO ACTUALIZADO Y GUARDADO:")
            self.log_calibracion(f"   pwm_min = {self.modelo_pwm_min}")
            self.log_calibracion(f"   m = {self.modelo_m:.3f}, b = {self.modelo_b:.3f}")
            
            self.root.after(0, self._refrescar_labels_calibracion)
        finally:
            self.enviar_comando_serial("C:0\n")
            self.modo_calibracion = False

    def accion_guardar_escala(self):
        try:
            valor = float(self.entry_px_por_cm.get())
            if valor <= 0: raise ValueError
        except ValueError:
            messagebox.showerror("Valor inválido", "Ingresa un número mayor a 0 para píxeles por cm.")
            return
        self.px_por_cm = valor
        self.guardar_calibracion_cinta()
        self.log_calibracion(f"✅ Escala guardada: {valor} px/cm")

    def _refrescar_labels_calibracion(self):
        self.lbl_modelo_actual.configure(
            text=f"Modelo actual → pwm_min={self.modelo_pwm_min}, m={self.modelo_m:.3f}, b={self.modelo_b:.3f}, px/cm={self.px_por_cm}"
        )

    def rutina_pick_and_place(self, id_roca, angulo_agarre_dinamico, ancho_pixeles):
        self.enviar_comando_serial("C:0\n")
        self.root.after(0, lambda: self.lbl_estado_sistema.configure(text="ESTADO: FRENADO (Recogiendo)", text_color="#ef4444"))
        time.sleep(0.5)

        self.enviar_comando_serial("M:8:18\n"); self.actualizar_posicion_local(8, 75); time.sleep(1.0)
        self.enviar_comando_serial("M:10:132\n"); self.actualizar_posicion_local(10, 105); time.sleep(1.0)
        self.enviar_comando_serial("M:13:90\n"); self.actualizar_posicion_local(13, 90); time.sleep(0.5)
        self.enviar_comando_serial("M:11:90\n"); self.actualizar_posicion_local(11, 90); time.sleep(0.5)
        self.enviar_comando_serial("M:12:44\n"); self.actualizar_posicion_local(12, 25); time.sleep(0.5)

        self.enviar_comando_serial("M:9:116\n"); self.actualizar_posicion_local(9, 99); time.sleep(1.5)

        self.enviar_comando_serial(f"M:13:{angulo_agarre_dinamico}\n"); self.actualizar_posicion_local(13, angulo_agarre_dinamico); time.sleep(0.8)
        
        self.rocas_recogidas_total += 1
        self.suma_ancho_rocas += ancho_pixeles
        self.root.after(0, self.registrar_recoleccion_en_tabla, id_roca, ancho_pixeles, angulo_agarre_dinamico)

        self.enviar_comando_serial("M:9:120\n"); self.actualizar_posicion_local(9, 130); time.sleep(1.2)
        self.enviar_comando_serial("M:8:80\n"); self.actualizar_posicion_local(8, 20); time.sleep(1.5)
        self.enviar_comando_serial("M:10:135\n"); self.actualizar_posicion_local(10, 135); time.sleep(1.0)
        self.enviar_comando_serial("M:11:90\n"); self.actualizar_posicion_local(11, 105); time.sleep(0.5)
        self.enviar_comando_serial("M:12:29\n"); self.actualizar_posicion_local(12, 29); time.sleep(0.5)

        self.enviar_comando_serial("M:13:85\n"); self.actualizar_posicion_local(13, 85); time.sleep(0.5)

        self.arranque_inicial()
        self.brazo_ocupado = False

    def registrar_recoleccion_en_tabla(self, id_roca, ancho, angulo):
        hora_actual = time.strftime("%H:%M:%S")
        mensaje = f"SYS: Objeto fijado. Mineral ID {id_roca}. Tamaño: {ancho}px. Interceptando a {angulo}°."
        texto_formateado = f"[{hora_actual}] {mensaje}\n"
        self.terminal_logs.configure(state="normal")
        self.terminal_logs.insert(tk.END, texto_formateado)
        self.terminal_logs.see(tk.END)
        self.terminal_logs.configure(state="disabled")

    def arrancar_cinta_directo(self):
        self.enviar_comando_serial("C:255\n")
        self.lbl_estado_sistema.configure(text="ESTADO: OPERANDO LÍNEA (100%)", text_color="#10b981")
        if hasattr(self, 'slider_cinta'):
            self.slider_cinta.set(100)

    def detener_cinta_directo(self):
        self.enviar_comando_serial("C:0\n")
        self.lbl_estado_sistema.configure(text="ESTADO: LÍNEA DETENIDA", text_color="#ef4444")
        if hasattr(self, 'slider_cinta'):
            self.slider_cinta.set(0)

    def on_cinta_move(self, valor):
        porcentaje = int(float(valor))
        pwm_minimo = self.modelo_pwm_min
        pwm_maximo = 255
        if porcentaje == 0:
            pwm_salida = 0
            texto_estado = "Detenida (0%)"
        elif porcentaje > 0:
            pwm_salida = int(pwm_minimo + (porcentaje / 100.0) * (pwm_maximo - pwm_minimo))
            texto_estado = f"Avanzando ({porcentaje}%)"
        else:
            pwm_salida = -int(pwm_minimo + (abs(porcentaje) / 100.0) * (pwm_maximo - pwm_minimo))
            texto_estado = f"Reversa ({porcentaje}%)"
        
        self.lbl_vel_cinta_manual.configure(text=texto_estado)
        self.enviar_comando_serial(f"C:{pwm_salida}\n")

    def on_slider_move(self, valor, nombre, canal):
        if self.brazo_ocupado: return
        angulo = int(float(valor))
        if self.last_sent_values.get(canal) == angulo: return
        self.last_sent_values[canal] = angulo
        self.labels_angulos[nombre].configure(text=f"{angulo}°")
        if nombre in self.dh_items:
            item_id = self.dh_items[nombre]
            valores = self.tree_dh.item(item_id, "values")
            self.tree_dh.item(item_id, values=(valores[0], valores[1], f"{angulo}°", valores[3], valores[4], valores[5]))
        self.enviar_comando_serial(f"M:{canal}:{angulo}\n")

    def ir_a_home(self):
        self.detener_cinta_directo()
        orden_movimiento = ['Pinza - Garra (MG90S)', 'Muñeca 2 - Alabeo (SG90)', 'Muñeca 1 - Cabeceo', 'Codo (MG996R)', 'Hombro (MG996R)', 'Base (MG996R)']

        for nombre in orden_movimiento:
            config = CONFIG_BRAZO[nombre]
            home_val = config['home']
            self.enviar_comando_serial(f"M:{config['canal']}:{home_val}\n")
            self.actualizar_posicion_local(config['canal'], home_val)
            time.sleep(0.15)

        self.root.after(0, lambda: self.lbl_estado_sistema.configure(text="ESTADO: EN ESPERA (HOME)", text_color="#64748b"))

    def arranque_inicial(self):
        self.ir_a_home()
        time.sleep(0.5)
        self.enviar_comando_serial("C:255\n")
        self.root.after(0, lambda: self.lbl_estado_sistema.configure(text="ESTADO: OPERANDO LÍNEA (100%)", text_color="#10b981"))
        if hasattr(self, 'slider_cinta'):
            self.root.after(0, lambda: self.slider_cinta.set(100))

    def on_closing(self):
        self.enviar_comando_serial("C:0\n")
        time.sleep(0.1)
        if hasattr(self, 'esp') and self.esp.is_open: self.esp.close()
        self.root.destroy()

    # =========================================================
    # CONSTRUCCIÓN DE INTERFAZ GRÁFICA CON CUSTOMTKINTER
    # =========================================================
    def crear_interfaz(self):
        self.tabview = ctk.CTkTabview(self.root)
        self.tabview.pack(expand=True, fill="both", padx=10, pady=10)

        self.tab_dashboard = self.tabview.add("📊 Dashboard Operativo")
        self.tab_avanzado = self.tabview.add("⚙️ Configuración Avanzada")

        self.construir_tab_dashboard()
        self.construir_tab_avanzado()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def construir_tab_dashboard(self):
        # Frame izquierdo para KPIs y Controles
        frame_sidebar = ctk.CTkFrame(self.tab_dashboard, width=300)
        frame_sidebar.pack(side="left", fill="y", padx=10, pady=10)
        
        lbl_titulo = ctk.CTkLabel(frame_sidebar, text="PANEL DE CONTROL", font=("Courier", 18, "bold"))
        lbl_titulo.pack(pady=20)
        
        self.lbl_estado_sistema = ctk.CTkLabel(frame_sidebar, text="ESTADO: EN ESPERA", font=("Helvetica", 14, "bold"), text_color="#64748b")
        self.lbl_estado_sistema.pack(pady=10)
        
        # Botones de Operación
        btn_iniciar = ctk.CTkButton(frame_sidebar, text="▶ INICIAR CINTA (MÁX VEL.)", fg_color="#10b981", hover_color="#059669",
                                    font=("Helvetica", 12, "bold"), height=40, command=self.arrancar_cinta_directo)
        btn_iniciar.pack(fill="x", padx=20, pady=5)
        
        btn_stop = ctk.CTkButton(frame_sidebar, text="⏹ DETENER CINTA", fg_color="#ef4444", hover_color="#dc2626",
                                 font=("Helvetica", 12, "bold"), height=40, command=self.detener_cinta_directo)
        btn_stop.pack(fill="x", padx=20, pady=5)
        
        btn_home = ctk.CTkButton(frame_sidebar, text="🏠 RESTABLECER (HOME)", fg_color="#3b82f6", hover_color="#2563eb",
                                 font=("Helvetica", 12, "bold"), height=40, command=lambda: threading.Thread(target=self.ir_a_home).start())
        btn_home.pack(fill="x", padx=20, pady=5)

        # Módulo Dataset
        ctk.CTkLabel(frame_sidebar, text="MÓDULO DATASET", font=("Courier", 14, "bold"), text_color="#a855f7").pack(pady=(30,10))
        self.btn_capturar = ctk.CTkButton(frame_sidebar, text="📸 Capturar Frame", fg_color="#8b5cf6", hover_color="#7c3aed",
                                          font=("Helvetica", 12, "bold"), height=40, command=self.capturar_dataset)
        self.btn_capturar.pack(fill="x", padx=20)

        # Panel de KPIs
        ctk.CTkLabel(frame_sidebar, text="RENDIMIENTO (KPIs)", font=("Courier", 14, "bold")).pack(pady=(30,10))
        
        frame_kpis = ctk.CTkFrame(frame_sidebar, fg_color="transparent")
        frame_kpis.pack(fill="x", padx=20)
        
        ctk.CTkLabel(frame_kpis, text="Rocas Detectadas:", font=("Helvetica", 12)).grid(row=0, column=0, sticky="w", pady=2)
        self.lbl_kpi_detectadas = ctk.CTkLabel(frame_kpis, text="0", font=("Helvetica", 14, "bold"), text_color="#10b981")
        self.lbl_kpi_detectadas.grid(row=0, column=1, sticky="e", padx=10)
        
        ctk.CTkLabel(frame_kpis, text="Rocas Recogidas:", font=("Helvetica", 12)).grid(row=1, column=0, sticky="w", pady=2)
        self.lbl_kpi_recogidas = ctk.CTkLabel(frame_kpis, text="0", font=("Helvetica", 14, "bold"), text_color="#3b82f6")
        self.lbl_kpi_recogidas.grid(row=1, column=1, sticky="e", padx=10)
        
        ctk.CTkLabel(frame_kpis, text="Eficiencia Pick:", font=("Helvetica", 12)).grid(row=2, column=0, sticky="w", pady=2)
        self.lbl_kpi_eficiencia = ctk.CTkLabel(frame_kpis, text="0%", font=("Helvetica", 14, "bold"), text_color="#f59e0b")
        self.lbl_kpi_eficiencia.grid(row=2, column=1, sticky="e", padx=10)

        ctk.CTkLabel(frame_kpis, text="Uptime Sist.:", font=("Helvetica", 12)).grid(row=3, column=0, sticky="w", pady=2)
        self.lbl_kpi_uptime = ctk.CTkLabel(frame_kpis, text="00:00:00", font=("Helvetica", 14, "bold"), text_color="#a855f7")
        self.lbl_kpi_uptime.grid(row=3, column=1, sticky="e", padx=10)

        ctk.CTkLabel(frame_kpis, text="Tamaño Promedio:", font=("Helvetica", 12)).grid(row=4, column=0, sticky="w", pady=2)
        self.lbl_kpi_size = ctk.CTkLabel(frame_kpis, text="0 px", font=("Helvetica", 14, "bold"), text_color="#ec4899")
        self.lbl_kpi_size.grid(row=4, column=1, sticky="e", padx=10)

        # LEDs virtuales
        frame_leds = ctk.CTkFrame(frame_sidebar)
        frame_leds.pack(fill="x", padx=20, pady=20)
        ctk.CTkLabel(frame_leds, text="ESTADO DE ENLACE", font=("Courier", 12, "bold")).pack(pady=5)
        
        self.lbl_led_esp = ctk.CTkLabel(frame_leds, text="● ESP32 OFFLINE", text_color="#ef4444", font=("Helvetica", 12, "bold"))
        self.lbl_led_esp.pack(anchor="w", padx=10, pady=2)
        
        self.lbl_led_cam = ctk.CTkLabel(frame_leds, text="● CÁMARA LOST", text_color="#ef4444", font=("Helvetica", 12, "bold"))
        self.lbl_led_cam.pack(anchor="w", padx=10, pady=2)
        
        self.lbl_led_ia = ctk.CTkLabel(frame_leds, text="● NEURAL NET", text_color="#ef4444", font=("Helvetica", 12, "bold"))
        self.lbl_led_ia.pack(anchor="w", padx=10, pady=2)

        # Centro: Video y Logs
        frame_main = ctk.CTkFrame(self.tab_dashboard)
        frame_main.pack(side="right", expand=True, fill="both", padx=10, pady=10)
        
        # Frame superior para video y grafico
        frame_superior = ctk.CTkFrame(frame_main, fg_color="transparent")
        frame_superior.pack(fill="both", expand=True, pady=10)
        
        self.lbl_video = tk.Label(frame_superior, bg="black")
        self.lbl_video.pack(side="left", fill="both", expand=True, padx=5)
        
        # Matplotlib Canvas a la derecha del video
        frame_grafico = ctk.CTkFrame(frame_superior, width=250)
        frame_grafico.pack(side="right", fill="y", padx=5)
        ctk.CTkLabel(frame_grafico, text="THROUGHPUT (Rocas/min)", font=("Courier", 12, "bold")).pack(pady=5)
        
        self.fig, self.ax = plt.subplots(figsize=(3.5, 3), facecolor='#2b2b2b')
        self.fig.subplots_adjust(left=0.2, right=0.95, top=0.9, bottom=0.2)
        self.ax.set_facecolor('#1e1e1e')
        self.ax.tick_params(colors='white')
        for spine in self.ax.spines.values(): spine.set_color('#1e1e1e')
        self.line_plot, = self.ax.plot([], [], color='#06b6d4', linewidth=2)
        
        self.canvas_plot = FigureCanvasTkAgg(self.fig, master=frame_grafico)
        self.canvas_plot.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
        
        # Terminal Cyberpunk abajo
        frame_logs = ctk.CTkFrame(frame_main)
        frame_logs.pack(fill="x", pady=10, padx=5)
        ctk.CTkLabel(frame_logs, text="TERMINAL OPERATIVA [SYS_LOG]", font=("Courier", 12, "bold"), text_color="#10b981").pack(anchor="w", padx=10, pady=5)
        
        self.terminal_logs = tk.Text(frame_logs, height=8, bg="#0f172a", fg="#10b981", font=("Consolas", 10, "bold"), borderwidth=0, highlightthickness=0)
        self.terminal_logs.pack(fill="x", expand=True, padx=10, pady=(0, 10))
        self.terminal_logs.insert(tk.END, "[SYS] Terminal inicializada. Esperando eventos...\n")
        self.terminal_logs.configure(state="disabled")

    def construir_tab_avanzado(self):
        scrollable_frame = ctk.CTkScrollableFrame(self.tab_avanzado)
        scrollable_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Seccion 1: Actuadores del Brazo
        frame_actuadores = ctk.CTkFrame(scrollable_frame)
        frame_actuadores.pack(fill="x", pady=10)
        ctk.CTkLabel(frame_actuadores, text="Calibración Manual de Servos (PCA9685)", font=("Helvetica", 14, "bold")).pack(pady=10)
        
        for nombre, config in CONFIG_BRAZO.items():
            frame_fila = ctk.CTkFrame(frame_actuadores, fg_color="transparent")
            frame_fila.pack(fill="x", pady=5, padx=20)
            
            lbl = ctk.CTkLabel(frame_fila, text=f"{nombre}", width=150, anchor="w")
            lbl.pack(side="left")
            
            var = tk.IntVar(value=config['home'])
            self.sliders_vars[nombre] = var
            self.last_sent_values[config['canal']] = config['home']
            
            lbl_valor = ctk.CTkLabel(frame_fila, text=f"{config['home']}°", width=50, text_color="#3b82f6", font=("Helvetica", 12, "bold"))
            
            slider = ctk.CTkSlider(frame_fila, from_=config['min'], to=config['max'], variable=var,
                                   command=lambda val, nom=nombre, c=config['canal']: self.on_slider_move(val, nom, c))
            slider.pack(side="left", fill="x", expand=True, padx=20)
            lbl_valor.pack(side="right")
            self.labels_angulos[nombre] = lbl_valor

        # Seccion 2: Denavit-Hartenberg
        frame_dh = ctk.CTkFrame(scrollable_frame)
        frame_dh.pack(fill="x", pady=10)
        ctk.CTkLabel(frame_dh, text="Parámetros Denavit-Hartenberg", font=("Helvetica", 14, "bold")).pack(pady=10)
        
        columnas_dh = ("i", "Articulacion", "Theta", "d", "a", "Alpha")
        self.tree_dh = ttk.Treeview(frame_dh, columns=columnas_dh, show="headings", height=6)
        for col in columnas_dh: self.tree_dh.heading(col, text=col if col != "Theta" else "θi")
        self.tree_dh.pack(fill="x", padx=10, pady=10)
        
        for nombre, config in CONFIG_BRAZO.items():
            idx = config['dh_index']
            if idx is not None:
                i = idx + 1
                item_id = self.tree_dh.insert("", "end", values=(i, nombre.split(" (")[0], f"{config['home']}°", f"L{i}", f"L{i}_x", "0°"))
                self.dh_items[nombre] = item_id

        # Seccion 3: Cinta Transportadora
        frame_cinta = ctk.CTkFrame(scrollable_frame)
        frame_cinta.pack(fill="x", pady=10)
        ctk.CTkLabel(frame_cinta, text="Ajustes de Cinta Transportadora", font=("Helvetica", 14, "bold")).pack(pady=10)
        
        self.lbl_vel_cinta_manual = ctk.CTkLabel(frame_cinta, text="Detenida (0%)", font=("Helvetica", 12, "bold"))
        self.lbl_vel_cinta_manual.pack(pady=5)
        
        self.slider_cinta = ctk.CTkSlider(frame_cinta, from_=-100, to=100, command=self.on_cinta_move)
        self.slider_cinta.set(0)
        self.slider_cinta.pack(fill="x", expand=True, padx=40, pady=10)
        
        frame_escala = ctk.CTkFrame(frame_cinta, fg_color="transparent")
        frame_escala.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(frame_escala, text="Px por cm real:").pack(side="left")
        self.entry_px_por_cm = ctk.CTkEntry(frame_escala, width=80)
        if self.px_por_cm is not None:
            self.entry_px_por_cm.insert(0, str(self.px_por_cm))
        self.entry_px_por_cm.pack(side="left", padx=10)
        ctk.CTkButton(frame_escala, text="Guardar Escala", command=self.accion_guardar_escala).pack(side="left")

        ctk.CTkButton(frame_cinta, text="🎯 AUTO-CALIBRAR VELOCIDAD CINTA", fg_color="#f59e0b", hover_color="#d97706", 
                      command=self.accion_calibrar_completo).pack(pady=10)
        
        self.lbl_modelo_actual = ctk.CTkLabel(frame_cinta, text=f"Modelo → pwm_min={self.modelo_pwm_min}, m={self.modelo_m:.3f}, b={self.modelo_b:.3f}")
        self.lbl_modelo_actual.pack()
        
        self.txt_log_calibracion = tk.Text(frame_cinta, height=8, bg="#1e1e1e", fg="white", font=("Consolas", 9))
        self.txt_log_calibracion.pack(fill="x", padx=20, pady=10)

    def actualizar_kpis(self):
        # Stats Base
        if hasattr(self, 'lbl_kpi_detectadas'):
            self.lbl_kpi_detectadas.configure(text=str(self.rocas_detectadas_total))
            self.lbl_kpi_recogidas.configure(text=str(self.rocas_recogidas_total))
            
            if self.rocas_detectadas_total > 0:
                eficiencia = int((self.rocas_recogidas_total / self.rocas_detectadas_total) * 100)
                self.lbl_kpi_eficiencia.configure(text=f"{eficiencia}%")
                
            # Uptime
            uptime_segundos = int(time.time() - self.inicio_sistema)
            horas = uptime_segundos // 3600
            minutos = (uptime_segundos % 3600) // 60
            segundos = uptime_segundos % 60
            self.lbl_kpi_uptime.configure(text=f"{horas:02d}:{minutos:02d}:{segundos:02d}")
    
            # Avg Size
            if self.rocas_recogidas_total > 0:
                avg = int(self.suma_ancho_rocas / self.rocas_recogidas_total)
                self.lbl_kpi_size.configure(text=f"{avg} px")
                
            # Actualizar LEDs Virtuales
            if self.estado_esp:
                self.lbl_led_esp.configure(text="● ESP32 ONLINE", text_color="#10b981")
            else:
                self.lbl_led_esp.configure(text="● ESP32 OFFLINE", text_color="#ef4444")
                
            if self.estado_cam:
                self.lbl_led_cam.configure(text="● CÁMARA SYNC", text_color="#10b981")
            else:
                self.lbl_led_cam.configure(text="● CÁMARA LOST", text_color="#ef4444")
                
            if self.estado_ia:
                self.lbl_led_ia.configure(text="● NEURAL NET", text_color="#10b981")
            else:
                self.lbl_led_ia.configure(text="● IA OFFLINE", text_color="#ef4444")

        self.root.after(1000, self.actualizar_kpis)
        
    def actualizar_grafico(self):
        if hasattr(self, 'canvas_plot'):
            # Extrapolar a rocas por minuto (throughput_counter * 60)
            self.historial_throughput.append(self.throughput_counter * 60)
            self.tiempo_grafico.append(time.time() - self.inicio_sistema)
            self.throughput_counter = 0
    
            self.line_plot.set_xdata(list(self.tiempo_grafico))
            self.line_plot.set_ydata(list(self.historial_throughput))
            self.ax.relim()
            self.ax.autoscale_view()
            self.canvas_plot.draw()
            
        self.root.after(1000, self.actualizar_grafico)

if __name__ == "__main__":
    root = ctk.CTk()
    app = AppBrazoRobotico(root)
    root.mainloop()
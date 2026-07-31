import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import serial
import time
import threading

# --- CONFIGURACIÓN SERIAL ---
PUERTO = 'COM5'
BAUDRATE = 115200

# --- CONFIGURACIÓN DE ARTICULACIONES ---
CONFIG_BRAZO = {
    'Base (MG996R)':           {'canal': 8,  'min': 0,   'max': 180, 'home': 80,  'dh_index': 0},
    'Hombro (MG996R)':         {'canal': 9,  'min': 10,  'max': 170, 'home': 150, 'dh_index': 1},
    'Codo (MG996R)':           {'canal': 10, 'min': 30,  'max': 160, 'home': 130, 'dh_index': 2},
    'Muñeca 1 - Cabeceo':      {'canal': 11, 'min': 0,   'max': 180, 'home': 90,  'dh_index': 3},
    'Muñeca 2 - Alabeo (SG90)':{'canal': 12, 'min': 0,   'max': 180, 'home': 20,  'dh_index': 4},
    'Pinza - Garra (MG90S)':   {'canal': 13, 'min': 10,  'max': 90,  'home': 50,  'dh_index': None}
}

class AppBrazoRobotico:
    def __init__(self, root):
        self.root = root
        self.root.title("Panel de Control Automático - Pick & Place")
        self.root.geometry("600x920") 
        self.root.resizable(False, False)
        
        self.sliders_vars = {}
        self.labels_angulos = {} 
        self.last_sent_values = {}
        self.dh_items = {} 
        
        # Candado de software para evitar la "Condición de Carrera" del sensor
        self.brazo_ocupado = False 
        
        self.conectar_serial()
        self.crear_widgets()
        
        # Iniciar hilo de escucha global para el sensor IR
        threading.Thread(target=self.escuchar_serial_continuo, daemon=True).start()
        
        # Llevar todo a posición segura inicial
        self.root.after(1000, self.ir_a_home)

    def conectar_serial(self):
        try:
            self.esp = serial.Serial(PUERTO, BAUDRATE, timeout=1)
            time.sleep(2)
            self.esp.reset_input_buffer()
            print(f"✅ Conectado al ESP32 ({PUERTO})")
        except serial.SerialException as e:
            messagebox.showwarning("Modo Simulación", f"No se detectó el ESP32 en {PUERTO}.")

    def enviar_comando_serial(self, comando_texto):
        if hasattr(self, 'esp') and self.esp.is_open:
            self.esp.write(comando_texto.encode('utf-8'))

    def escuchar_serial_continuo(self):
        """Escucha permanente para detectar el evento del sensor IR y evitar rebotes"""
        while hasattr(self, 'esp') and self.esp.is_open:
            try:
                if self.esp.in_waiting > 0:
                    res = self.esp.readline().decode('utf-8', errors='ignore').strip()
                    
                    if res == "EVENTO:PIEZA_DETECTADA":
                        # SOLO inicia la rutina si el brazo no está haciendo nada
                        if not self.brazo_ocupado:
                            self.brazo_ocupado = True # Pone el candado
                            print("\n🎯 ¡Sensor Activado! Pieza detectada en la cinta.")
                            threading.Thread(target=self.rutina_pick_and_place, daemon=True).start()
                        else:
                            # Si el sensor detecta luz extra mientras el brazo se mueve, la ignora
                            pass 
                    elif res:
                        print(f"[Hardware] {res}")
            except Exception:
                pass
            time.sleep(0.01)

    def rutina_pick_and_place(self):
        """Secuencia ESTRICTA de movimientos automáticos para evitar colisiones"""
        print("▶️ Ejecutando secuencia Pick & Place...")
        
        # Detener la cinta visualmente
        self.slider_cinta.set(0)
        self.lbl_vel_cinta.config(text="Pieza Detectada")

        # ========================================================
        # FASE 1: ACERCAMIENTO Y AGARRE DEL OBJETO
        # ========================================================
        self.enviar_comando_serial("M:8:91\n") 
        time.sleep(1.0) 
        
        self.enviar_comando_serial("M:10:106\n") 
        time.sleep(1.0)
        
        self.enviar_comando_serial("M:13:90\n") 
        time.sleep(0.5)
        
        self.enviar_comando_serial("M:11:99\n") 
        time.sleep(0.5)
        
        self.enviar_comando_serial("M:12:29\n") 
        time.sleep(0.5)
        
        self.enviar_comando_serial("M:9:100\n") 
        time.sleep(1.0)
        
        self.enviar_comando_serial("M:13:65\n") 
        time.sleep(0.8)

        # ========================================================
        # FASE 2: TRASLADO Y DESCARGA
        # ========================================================
        self.enviar_comando_serial("M:9:130\n") 
        time.sleep(1.0)
        
        self.enviar_comando_serial("M:8:65\n") 
        time.sleep(1.0)
        
        self.enviar_comando_serial("M:10:135\n") 
        time.sleep(1.0)
        
        self.enviar_comando_serial("M:11:105\n") 
        time.sleep(0.5)
        
        self.enviar_comando_serial("M:12:29\n") 
        time.sleep(0.5)
        
        self.enviar_comando_serial("M:13:85\n") 
        time.sleep(0.8)
        
        # ========================================================
        # FASE 3: RETORNO A BASE
        # ========================================================
        print("✅ Operación completada. Retornando a la posición base segura.")
        self.ir_a_home()
        
        # Tiempo de seguridad para que termine de llegar al Home
        time.sleep(2.0) 
        
        # Quitar el candado para permitir que procese la siguiente pieza
        self.brazo_ocupado = False
        print("🔓 Brazo libre. Esperando siguiente pieza...")

    def crear_widgets(self):
        titulo = tk.Label(self.root, text="SISTEMA DE MANUFACTURA UNIFICADO", font=("Helvetica", 13, "bold"), fg="#1e293b")
        titulo.pack(pady=10)
        
        # --- SECCIÓN 1: CINTA TRANSPORTADORA ---
        frame_cinta = tk.LabelFrame(self.root, text=" Cinta Transportadora (Motor DC) ", padx=15, pady=10, fg="#d97706", font=("Helvetica", 10, "bold"))
        frame_cinta.pack(padx=20, pady=5, fill="x")

        self.lbl_vel_cinta = tk.Label(frame_cinta, text="Detenida (0%)", font=("Helvetica", 10, "bold"))
        self.lbl_vel_cinta.pack(pady=5)

        self.slider_cinta = ttk.Scale(
            frame_cinta, from_=-100, to=100, orient="horizontal", command=self.on_cinta_move
        )
        self.slider_cinta.set(0)
        self.slider_cinta.pack(fill="x", expand=True, padx=5)

        btn_stop_cinta = tk.Button(frame_cinta, text="FRENAR CINTA", bg="#ef4444", fg="white", font=("Helvetica", 9, "bold"), command=lambda: self.slider_cinta.set(0))
        btn_stop_cinta.pack(pady=5)

        # --- SECCIÓN 2: SLIDERS DEL BRAZO ROBÓTICO ---
        frame_controles = tk.LabelFrame(self.root, text=" Actuadores del Brazo (PCA9685) ", padx=15, pady=10)
        frame_controles.pack(padx=20, pady=5, fill="both")

        for nombre, config in CONFIG_BRAZO.items():
            frame_fila = tk.Frame(frame_controles)
            frame_fila.pack(fill="x", pady=4) 
            
            lbl = tk.Label(frame_fila, text=f"{nombre}", width=20, anchor="w", font=("Helvetica", 9, "bold"))
            lbl.pack(side="left")
            
            var = tk.IntVar(value=config['home'])
            self.sliders_vars[nombre] = var
            self.last_sent_values[config['canal']] = config['home']
            
            lbl_valor = tk.Label(frame_fila, text=f"{config['home']}°", width=5, font=("Helvetica", 10, "bold"), fg="#2563eb")
            self.labels_angulos[nombre] = lbl_valor
            
            slider = ttk.Scale(
                frame_fila, from_=config['min'], to=config['max'], orient="horizontal", variable=var,
                command=lambda val, nom=nombre, c=config['canal']: self.on_slider_move(val, nom, c)
            )
            slider.pack(side="left", fill="x", expand=True, padx=5)
            lbl_valor.pack(side="right")

        # --- SECCIÓN 3: MATRIZ DENAVIT-HARTENBERG ---
        frame_dh = tk.LabelFrame(self.root, text=" Parámetros Denavit-Hartenberg (D-H) ", padx=10, pady=10)
        frame_dh.pack(padx=20, pady=5, fill="both")
        
        columnas = ("i", "Articulacion", "Theta", "d", "a", "Alpha")
        self.tree_dh = ttk.Treeview(frame_dh, columns=columnas, show="headings", height=5)
        
        for col in columnas:
            self.tree_dh.heading(col, text=col if col != "Theta" else "θi")
            
        self.tree_dh.column("i", width=30, anchor="center")
        self.tree_dh.column("Articulacion", width=120, anchor="w")
        self.tree_dh.column("Theta", width=60, anchor="center")
        self.tree_dh.column("d", width=60, anchor="center")
        self.tree_dh.column("a", width=60, anchor="center")
        self.tree_dh.column("Alpha", width=60, anchor="center")
        
        self.tree_dh.pack(fill="x")

        for nombre, config in CONFIG_BRAZO.items():
            idx = config['dh_index']
            if idx is not None:
                i = idx + 1
                item_id = self.tree_dh.insert("", "end", values=(i, nombre.split(" (")[0], f"{config['home']}°", f"L{i}", f"L{i}_x", "0°"))
                self.dh_items[nombre] = item_id

        # --- SECCIÓN 4: BOTONERA GENERAL ---
        frame_botones = tk.Frame(self.root)
        frame_botones.pack(pady=10, fill="x", padx=20)
        
        btn_home = tk.Button(frame_botones, text="Detener Todo y Restablecer Postura (Home)", font=("Helvetica", 10, "bold"), bg="#10b981", fg="white", height=2, command=self.ir_a_home)
        btn_home.pack(fill="x")

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_cinta_move(self, valor):
        porcentaje = int(float(valor))
        pwm_minimo = 140 
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
            
        self.lbl_vel_cinta.config(text=texto_estado)
        self.enviar_comando_serial(f"C:{pwm_salida}\n")

    def on_slider_move(self, valor, nombre, canal):
        # Evita que el usuario interfiera manualmente mientras la rutina Pick & Place está activa
        if self.brazo_ocupado:
            return 
            
        angulo = int(float(valor))
        
        if self.last_sent_values.get(canal) == angulo: return
        self.last_sent_values[canal] = angulo
        
        self.labels_angulos[nombre].config(text=f"{angulo}°")
        
        if nombre in self.dh_items:
            item_id = self.dh_items[nombre]
            valores = self.tree_dh.item(item_id, "values")
            self.tree_dh.item(item_id, values=(valores[0], valores[1], f"{angulo}°", valores[3], valores[4], valores[5]))
            
        self.enviar_comando_serial(f"M:{canal}:{angulo}\n")

    def ir_a_home(self):
        print("\n🏠 Apagando motores secundarios y retornando a Home...")
        
        self.slider_cinta.set(0)
        
        orden_movimiento = [
            'Pinza - Garra (MG90S)', 'Muñeca 2 - Alabeo (SG90)', 'Muñeca 1 - Cabeceo', 
            'Codo (MG996R)', 'Hombro (MG996R)', 'Base (MG996R)'
        ]
        
        for nombre in orden_movimiento:
            config = CONFIG_BRAZO[nombre]
            home_val = config['home']
            
            self.sliders_vars[nombre].set(home_val)
            self.labels_angulos[nombre].config(text=f"{home_val}°")
            self.last_sent_values[config['canal']] = home_val
            
            if nombre in self.dh_items:
                item_id = self.dh_items[nombre]
                valores = self.tree_dh.item(item_id, "values")
                self.tree_dh.item(item_id, values=(valores[0], valores[1], f"{home_val}°", valores[3], valores[4], valores[5]))
            
            self.enviar_comando_serial(f"M:{config['canal']}:{home_val}\n")
            self.root.update()
            time.sleep(0.15) 

    def on_closing(self):
        self.enviar_comando_serial("C:0\n")
        time.sleep(0.1)
        if hasattr(self, 'esp') and self.esp.is_open:
            self.esp.close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = AppBrazoRobotico(root)
    root.mainloop()
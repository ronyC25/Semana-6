import tkinter as tk
from tkinter import ttk
import serial
import time

PUERTO = 'COM5'
BAUDRATE = 115200

CONFIG_BRAZO = {
    'Base':           {'canal': 8,  'home': 75},
    'Hombro':         {'canal': 9,  'home': 150},
    'Codo':           {'canal': 10, 'home': 130},
    'Muñeca Cabeceo': {'canal': 11, 'home': 90},
    'Muñeca Alabeo':  {'canal': 12, 'home': 80},
    'Pinza':          {'canal': 13, 'home': 50}
}

class TeachPendant:
    def __init__(self, root):
        self.root = root
        self.root.title("Teach Pendant - Calibración Fina")
        self.root.geometry("500x650")
        self.root.resizable(False, False)

        self.angulos_actuales = {}
        self.variables_cajas = {} # Nueva memoria para las cajas de texto

        self.conectar_serial()
        self.crear_interfaz()
        
        self.root.after(1000, self.ir_a_home)

    def conectar_serial(self):
        try:
            self.esp = serial.Serial(PUERTO, BAUDRATE, timeout=1)
            time.sleep(2)
            self.esp.reset_input_buffer()
            print(f"✅ Conectado al ESP32 ({PUERTO})")
        except serial.SerialException:
            print(f"⚠️ Error: ESP32 no detectado en {PUERTO}.")

    def enviar_comando(self, canal, angulo):
        if hasattr(self, 'esp') and self.esp.is_open:
            self.esp.write(f"M:{canal}:{angulo}\n".encode('utf-8'))

    # --- NUEVO: FUNCIÓN PARA EL TECLADO ---
    def aplicar_angulo_teclado(self, event, nombre, canal):
        """Se ejecuta al presionar ENTER dentro de una caja de texto"""
        try:
            # Intentar convertir lo que el usuario escribió a un número entero
            nuevo_angulo = int(self.variables_cajas[nombre].get())
            
            # Barrera de seguridad física
            if 0 <= nuevo_angulo <= 180:
                self.angulos_actuales[nombre] = nuevo_angulo
                self.enviar_comando(canal, nuevo_angulo)
                print(f"⌨️ {nombre} ajustado a {nuevo_angulo}° por teclado.")
            else:
                # Si escribió 900°, se ignora y se restaura el último ángulo válido
                print("⚠️ Ángulo inválido. Debe estar entre 0 y 180.")
                self.variables_cajas[nombre].set(str(self.angulos_actuales[nombre]))
                
        except ValueError:
            # Si el usuario escribió letras (ej: "hola"), restaurar el número
            self.variables_cajas[nombre].set(str(self.angulos_actuales[nombre]))
            
        # Quitar el cursor de la caja de texto tras presionar Enter
        self.root.focus()

    def modificar_angulo(self, nombre, canal, incremento):
        """Suma o resta 1 grado y actualiza la caja de texto"""
        nuevo_angulo = self.angulos_actuales[nombre] + incremento
        
        if 0 <= nuevo_angulo <= 180:
            self.angulos_actuales[nombre] = nuevo_angulo
            # Actualizar lo que se ve en la caja de texto
            self.variables_cajas[nombre].set(str(nuevo_angulo))
            self.enviar_comando(canal, nuevo_angulo)

    def crear_interfaz(self):
        tk.Label(self.root, text="🕹️ CONSOLA DE MICRO-PASOS", font=("Helvetica", 14, "bold")).pack(pady=15)
        tk.Label(self.root, text="Usa los botones o ESCRIBE un número y presiona ENTER", fg="#64748b").pack()

        frame_controles = tk.Frame(self.root)
        frame_controles.pack(padx=20, pady=20, fill="both")

        for nombre, config in CONFIG_BRAZO.items():
            canal = config['canal']
            self.angulos_actuales[nombre] = config['home']

            fila = tk.Frame(frame_controles, pady=10)
            fila.pack(fill="x")

            # Nombre
            tk.Label(fila, text=nombre, width=15, font=("Helvetica", 10, "bold"), anchor="w").pack(side="left")

            # Botón -1°
            tk.Button(fila, text="◀ -1°", bg="#ef4444", fg="white", font=("Helvetica", 10, "bold"), width=6,
                      command=lambda n=nombre, c=canal: self.modificar_angulo(n, c, -1)).pack(side="left", padx=5)

            # --- NUEVO: CAJA DE ENTRADA (ENTRY) ---
            var_texto = tk.StringVar(value=str(config['home']))
            self.variables_cajas[nombre] = var_texto
            
            caja_entrada = tk.Entry(fila, textvariable=var_texto, font=("Consolas", 12, "bold"), width=5, justify="center", fg="#2563eb", bg="#f8fafc")
            caja_entrada.pack(side="left", padx=10)
            
            # Enlazar la tecla ENTER a esta caja específica
            caja_entrada.bind("<Return>", lambda event, n=nombre, c=canal: self.aplicar_angulo_teclado(event, n, c))

            # Botón +1°
            tk.Button(fila, text="+1° ▶", bg="#10b981", fg="white", font=("Helvetica", 10, "bold"), width=6,
                      command=lambda n=nombre, c=canal: self.modificar_angulo(n, c, 1)).pack(side="left", padx=5)

        # Botón Mágico
        btn_grabar = tk.Button(self.root, text="💾 GRABAR WAYPOINT (Generar Código)", 
                               bg="#f59e0b", fg="white", font=("Helvetica", 12, "bold"), height=2,
                               command=self.generar_codigo_python)
        btn_grabar.pack(fill="x", padx=20, pady=15)

        self.txt_codigo = tk.Text(self.root, height=8, font=("Consolas", 9), bg="#1e293b", fg="#10b981")
        self.txt_codigo.pack(padx=20, fill="x")

    def generar_codigo_python(self):
        self.txt_codigo.delete(1.0, tk.END)
        
        codigo = "# --- NUEVO WAYPOINT GENERADO ---\n"
        codigo += f"self.mover_servo_suave(8, {self.angulos_actuales['Base']}, tiempo_total_segundos=1.0) # Base\n"
        codigo += f"self.mover_servo_suave(10, {self.angulos_actuales['Codo']}, tiempo_total_segundos=1.0) # Codo\n"
        codigo += f"self.mover_servo_suave(11, {self.angulos_actuales['Muñeca Cabeceo']}, tiempo_total_segundos=0.5)\n"
        codigo += f"self.mover_servo_suave(12, {self.angulos_actuales['Muñeca Alabeo']}, tiempo_total_segundos=0.5)\n"
        codigo += f"self.mover_servo_suave(9, {self.angulos_actuales['Hombro']}, tiempo_total_segundos=1.5) # Hombro (Descenso)\n"
        codigo += f"self.mover_servo_suave(13, {self.angulos_actuales['Pinza']}, tiempo_total_segundos=0.8) # Pinza\n"

        self.txt_codigo.insert(tk.END, codigo)
        print("\n" + codigo) 

    def ir_a_home(self):
        for nombre, config in CONFIG_BRAZO.items():
            self.enviar_comando(config['canal'], config['home'])
            # Sincronizar las cajas de texto al ir a Home
            self.variables_cajas[nombre].set(str(config['home']))
            self.angulos_actuales[nombre] = config['home']
            time.sleep(0.1)

if __name__ == "__main__":
    root = tk.Tk()
    app = TeachPendant(root)
    root.mainloop()
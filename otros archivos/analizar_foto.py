import cv2
import os
import time
from ultralytics import YOLO
import torch

MODELO_PATH = 'best.pt'

def probar_modelo_optimizado():
    if not os.path.exists(MODELO_PATH):
        print(f"❌ ERROR: No se encuentra el modelo '{MODELO_PATH}'")
        return

    # --- CONFIGURACIÓN DE DISPOSITIVO (CPU vs GPU) ---
    if torch.cuda.is_available():
        dispositivo = 'cuda'
        nombre_gpu = torch.cuda.get_device_name(0)
        print(f"🚀 ¡Tarjeta Gráfica Detectada! Usando GPU: {nombre_gpu}")
    else:
        dispositivo = 'cpu'
        print("⚠️ No se detectó soporte CUDA. El modelo correrá en la CPU (será más lento).")

    print(f"🧠 Cargando modelo: {MODELO_PATH}...")
    model = YOLO(MODELO_PATH)

    cap = cv2.VideoCapture(1) # 1 para externa, 0 para integrada
    
    # Optimización de la cámara: Solicitar un tamaño estándar fluido al hardware
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    print("▶️ Iniciando video optimizado en tiempo real.")
    print("ℹ️ Presiona 'q' para salir.")
    print("-" * 50)

    # Variables para calcular los FPS reales en pantalla
    prev_time = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        # --- INFERENCIA OPTIMIZADA ---
        # device=dispositivo: Activa la GPU si está disponible
        # imgsz=640: Reajusta el tamaño interno para acelerar la red neuronal
        # stream=True: Procesa el video como un flujo continuo en memoria eficiente
        resultados = model.predict(frame, conf=0.5, device=dispositivo, imgsz=640, verbose=False, stream=True)

        for res in resultados:
            frame_anotado = res.plot()
            
            # Imprimir detecciones en la terminal
            for box in res.boxes:
                clase_id = int(box.cls[0])
                nombre_clase = res.names[clase_id]
                print(f"Viendo: '{nombre_clase}' con {float(box.conf[0])*100:.1f}%")

        # Calcular FPS reales
        curr_time = time.time()
        fps = 1 / (curr_time - prev_time)
        prev_time = curr_time

        # Dibujar los FPS en la esquina superior izquierda de la ventana de video
        cv2.putText(frame_anotado, f"FPS: {int(fps)}", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # Mostrar el video con los cuadros de YOLO y el medidor de FPS
        cv2.imshow("Prueba Optimizada YOLOv8", frame_anotado)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("🛑 Prueba finalizada.")

if __name__ == "__main__":
    probar_modelo_optimizado()
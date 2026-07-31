import cv2

def calibrar_camara():
    # 1. Iniciar la cámara (Cambia el 1 por 0 si no da imagen)
    cap = cv2.VideoCapture(1)
    
    if not cap.isOpened():
        print("❌ ERROR: No se pudo abrir la cámara.")
        return

    # Forzar resolución para ver los detalles de las rocas
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    # Crear la ventana donde pondremos los controles
    cv2.namedWindow('Calibracion Teros')

    # Función vacía requerida por OpenCV para los trackbars
    def nada(x):
        pass

    # Crear deslizador para el Autoenfoque (0 = Apagado, 1 = Encendido)
    # Por defecto lo apagamos (0) para poder usar el manual
    cv2.createTrackbar('AutoEnfoque', 'Calibracion Teros', 0, 1, nada)
    
    # Crear deslizador para el Enfoque Manual (Rango común de 0 a 255)
    cv2.createTrackbar('Nivel Enfoque', 'Calibracion Teros', 30, 255, nada)

    print("▶️ Herramienta de Calibración Iniciada.")
    print("1️⃣ Asegúrate de que 'AutoEnfoque' esté en 0.")
    print("2️⃣ Mueve el 'Nivel Enfoque' de izquierda a derecha.")
    print("ℹ️ Presiona la tecla 'q' para salir.")

    # Variables para no saturar la cámara enviando comandos repetidos
    ultimo_af = -1
    ultimo_enfoque = -1

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        # Leer la posición actual de los deslizadores en la ventana
        af_actual = cv2.getTrackbarPos('AutoEnfoque', 'Calibracion Teros')
        enfoque_actual = cv2.getTrackbarPos('Nivel Enfoque', 'Calibracion Teros')

        # Si el usuario movió el Autoenfoque, actualizar la cámara
        if af_actual != ultimo_af:
            cap.set(cv2.CAP_PROP_AUTOFOCUS, af_actual)
            ultimo_af = af_actual

        # Si el usuario movió el Enfoque Manual (y el autoenfoque está apagado), actualizar
        if enfoque_actual != ultimo_enfoque and af_actual == 0:
            cap.set(cv2.CAP_PROP_FOCUS, enfoque_actual)
            ultimo_enfoque = enfoque_actual

        # Mostrar texto de ayuda en el video
        cv2.putText(frame, "Ajusta las barras en la ventana", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        cv2.imshow('Calibracion Teros', frame)

        # Salir con la tecla 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("🛑 Calibración finalizada.")

if __name__ == "__main__":
    calibrar_camara()
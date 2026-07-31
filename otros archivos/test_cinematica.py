import math

# --- TUS MEDIDAS FÍSICAS EXACTAS ---
L1 = 120.0 # Hombro (mm)
L2 = 245.0 # Codo a Pinza (mm)

def calcular_cinematica_inversa(x, y, z):
    """
    Calcula los ángulos (Base, Hombro, Codo) para alcanzar la coordenada (X,Y,Z).
    El origen (0,0,0) está en el eje del Hombro.
    """
    print(f"\n📍 Calculando destino: X={x}, Y={y}, Z={z}")

    # 1. Ángulo de la Base (Plano XY)
    theta1_rad = math.atan2(y, x)
    theta1_deg = math.degrees(theta1_rad)

    # 2. Distancia Radial en el suelo (R)
    r = math.sqrt(x**2 + y**2)

    # 3. Distancia de la hipotenusa (D) desde el hombro hasta el objetivo
    d = math.sqrt(r**2 + z**2)

    # Comprobación de seguridad: ¿Alcanza el brazo?
    if d > (L1 + L2):
        print("❌ ERROR: El punto está demasiado lejos. Espacio de trabajo excedido.")
        return None

    # 4. Teorema del Coseno para el Hombro y el Codo
    # Ángulo beta (interno del triángulo)
    cos_beta = (L1**2 + d**2 - L2**2) / (2 * L1 * d)
    beta = math.acos(cos_beta)
    
    # Ángulo alpha (elevación del objetivo)
    alpha = math.atan2(z, r)
    
    # Theta 2 (Hombro) -> Configuración "Codo Arriba" (Elbow Up)
    theta2_rad = alpha + beta
    theta2_deg = math.degrees(theta2_rad)

    # Theta 3 (Codo) -> Ángulo relativo entre L1 y L2
    cos_gamma = (L1**2 + L2**2 - d**2) / (2 * L1 * L2)
    gamma = math.acos(cos_gamma)
    theta3_deg = 180 - math.degrees(gamma) # Conversión a ángulo de articulación

    return (theta1_deg, theta2_deg, theta3_deg)

# ==========================================
# ZONA DE PRUEBAS
# ==========================================
if __name__ == "__main__":
    # Prueba 1: Estirar el brazo hacia adelante sobre la cinta
    # X = 200mm hacia adelante, Y = 0 (centro), Z = 50mm de altura
    resultado = calcular_cinematica_inversa(200, 0, 50)
    
    if resultado:
        base, hombro, codo = resultado
        print("✅ Ángulos Matemáticos Calculados:")
        print(f"   -> Base (Theta 1):   {base:.1f}°")
        print(f"   -> Hombro (Theta 2): {hombro:.1f}°")
        print(f"   -> Codo (Theta 3):   {codo:.1f}°")
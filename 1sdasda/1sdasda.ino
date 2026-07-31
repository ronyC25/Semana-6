#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

// --- PINES DE LA CINTA TRANSPORTADORA (L298N) ---
const int pinENA = 13;
const int pinIN1 = 12;
const int pinIN2 = 14;

// Configuración PWM del ESP32 (Nueva API v3.x)
const int frecuencia_Cinta = 5000;
const int resolucion_Cinta = 8; // Velocidad de 0 a 255

void setup() {
  Serial.begin(115200);
  
  // 1. Configurar I2C y Brazo
  Wire.begin(27, 26); 
  pwm.begin();
  pwm.setPWMFreq(50);
  
  // 2. Configurar Cinta Transportadora
  pinMode(pinIN1, OUTPUT);
  pinMode(pinIN2, OUTPUT);
  
  // --- NUEVA FORMA DE INICIAR PWM EN ESP32 v3.x ---
  ledcAttach(pinENA, frecuencia_Cinta, resolucion_Cinta);
  
  // Detener cinta por seguridad al arrancar
  digitalWrite(pinIN1, LOW);
  digitalWrite(pinIN2, LOW);
  ledcWrite(pinENA, 0); // Ahora se usa el pin directamente

  Serial.println("========================================");
  Serial.println("Sistema Unificado: Brazo + Cinta Listo.");
  Serial.println("Compilado para ESP32 Core v3.x");
  Serial.println("========================================");
}

int anguloAPulsos(int angulo) {
  return map(angulo, 0, 180, 150, 600);
}

void loop() {
  if (Serial.available() > 0) {
    String comando = Serial.readStringUntil('\n');
    comando.trim();

    // COMANDOS DEL BRAZO (Ej. M:8:90)
    if (comando.startsWith("M:")) {
      int primerSeparador = comando.indexOf(':', 2);
      if (primerSeparador != -1) {
        int numServo = comando.substring(2, primerSeparador).toInt();
        int angulo = comando.substring(primerSeparador + 1).toInt();
        
        if (angulo < 0) angulo = 0;
        if (angulo > 180) angulo = 180;
        
        pwm.setPWM(numServo, 0, anguloAPulsos(angulo));
      }
    }
    // COMANDOS DE LA CINTA (Ej. C:200 o C:-150 o C:0)
    else if (comando.startsWith("C:")) {
      int velocidad = comando.substring(2).toInt();
      
      if (velocidad == 0) {
        digitalWrite(pinIN1, LOW);
        digitalWrite(pinIN2, LOW);
        ledcWrite(pinENA, 0); // Actualizado a pinENA
      } 
      else if (velocidad > 0) { // Avanzar
        int v_limitada = min(velocidad, 255);
        digitalWrite(pinIN1, HIGH);
        digitalWrite(pinIN2, LOW);
        ledcWrite(pinENA, v_limitada); // Actualizado a pinENA
      } 
      else { // Reversa
        int v_abs = min(abs(velocidad), 255);
        digitalWrite(pinIN1, LOW);
        digitalWrite(pinIN2, HIGH);
        ledcWrite(pinENA, v_abs); // Actualizado a pinENA
      }
    }
  }
}
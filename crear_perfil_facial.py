#!/usr/bin/env python3
"""
ATH1 - Generador de Perfil Biométrico Facial
Instrucciones: Ejecuta este script, mírate fijamente a la cámara y presiona la tecla 'S' para guardar tu rostro.
Requisitos: pip install opencv-python face_recognition
"""

import cv2
import numpy as np

def entrenar_modelo():
    print("📷 Iniciando sistema biométrico ligero...")
    # Cargar el detector de rostros por defecto de OpenCV
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    cap = cv2.VideoCapture(0)
    
    rostros_capturados = []
    etiquetas = []
    contador = 0
    
    print("😊 Mírate a la cámara. Analizando tu rostro en 3, 2, 1...")
    
    while True:
        ret, frame = cap.read()
        if not ret: continue
        
        # OpenCV procesa mejor en blanco y negro
        gris = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rostros = face_cascade.detectMultiScale(gris, 1.3, 5)
        
        for (x, y, w, h) in rostros:
            # Dibujar un cuadro verde
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            # Guardar el recorte del rostro
            rostro_recortado = gris[y:y+h, x:x+w]
            rostros_capturados.append(rostro_recortado)
            etiquetas.append(1) # ID 1 = MAOAZAking
            contador += 1
            
            # Mostrar progreso
            cv2.putText(frame, f"Captura: {contador}/50", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
            
        cv2.imshow('Entrenando ATH1', frame)
        cv2.waitKey(100) # Esperar 100ms entre fotos
        
        if contador >= 50:
            break

    cap.release()
    cv2.destroyAllWindows()
    
    if contador >= 50:
        print("🧠 Procesando datos y compilando modelo (LBPH)...")
        # Crear el reconocedor ligero
        reconocedor = cv2.face.LBPHFaceRecognizer_create()
        # Entrenar con las fotos tomadas
        reconocedor.train(rostros_capturados, np.array(etiquetas))
        # Guardar en un archivo .yml (mucho más estable en Windows)
        reconocedor.write("modelo_facial.yml")
        print("✅ ¡Modelo entrenado y guardado como 'modelo_facial.yml'!")
        print("Sube este archivo a tu repositorio de GitHub.")

if __name__ == "__main__":
    entrenar_modelo()
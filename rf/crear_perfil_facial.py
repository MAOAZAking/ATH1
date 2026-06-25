#!/usr/bin/env python3
"""
ATH1 - Generador de Perfil Biométrico Facial
Instrucciones: Ejecuta este script, mírate fijamente a la cámara y presiona la tecla 'S' para guardar tu rostro.
Requisitos: pip install opencv-python face_recognition
"""

import cv2
import face_recognition
import pickle
import os

def generar_perfil():
    print("📷 Inicializando cámara de captura biométrica...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Error: No se pudo acceder a la cámara web.")
        return

    print("\n😊 Mírate fijamente a la cámara en un lugar iluminado.")
    print("⌨️ Presiona la tecla [ S ] para capturar y guardar tu perfil.")
    print("⌨️ Presiona la tecla [ Q ] para cancelar.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("⚠️ Error al recibir el flujo de video.")
            break

        # Mostrar guía en pantalla
        cv2.putText(frame, "ATH1: Presiona 'S' para capturar", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imshow("Registro Biometrico ATH1", frame)

        tecla = cv2.waitKey(1) & 0xFF
        if tecla == ord('s') or tecla == ord('S'):
            # Cambiar de color a RGB (face_recognition usa RGB, OpenCV usa BGR)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            print("⏳ Analizando estructura facial...")
            ubicaciones = face_recognition.face_locations(rgb_frame)
            encodings = face_recognition.face_encodings(rgb_frame, ubicaciones)
            
            if len(encodings) > 0:
                mi_huella_facial = encodings[0]
                
                # Guardar el vector matemático en un archivo binario compacto
                with open("perfil_maoaza.pkl", "wb") as f:
                    pickle.dump(mi_huella_facial, f)
                
                print("\n✅ ¡Perfil Facial creado con éxito! Guardado como 'perfil_maoaza.pkl'.")
                print("Sube este archivo (.pkl) a tu repositorio de GitHub.")
                break
            else:
                print("❌ No se detectó ningún rostro en la toma. Inténtalo de nuevo, asegúrate de tener buena luz.")
                
        elif tecla == ord('q') or tecla == ord('Q'):
            print("❌ Registro cancelado por el usuario.")
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    generar_perfil()
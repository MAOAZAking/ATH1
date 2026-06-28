#!/usr/bin/env python3
"""
Double-clap AI Assistant for ATH1.

Detects 2 claps → Activates microphone → Transcribes user request (Online/Offline) →
Sends text to Gemini AI Brain (with SQLite local RAG/memory) → Speaks response.

Dependencias:
python -m pip install opencv-contrib-python
python -m pip install --upgrade pip
        pip install numpy sounddevice pyttsx3 pyautogui SpeechRecognition vosk google-genai opencv-contrib-python pyinstaller keyboard python-dotenv selenium webdriver-manager
"""

#!/usr/bin/env python3
import io
import os
import sys
import time
import json
import wave
import cv2
import keyboard
import platform
import getpass
import threading
import subprocess
import webbrowser
import pyautogui
import numpy as np
import sounddevice as sd
import pyttsx3
import speech_recognition as sr
import vosk
from dotenv import load_dotenv

# Módulos propios
import ath1_brain
from entrenar_nombre import extraer_espectrograma, calcular_distancia_dtw

# ─── CONFIGURACIÓN DE SEGURIDAD Y VARIABLES (.ENV) ───
# Esto asegura que PyInstaller encuentre las credenciales ocultas en cualquier PC
if hasattr(sys, '_MEIPASS'):
    load_dotenv(os.path.join(sys._MEIPASS, '.env'))
else:
    load_dotenv()

nivel_acceso = "invitado"

def solicitar_desbloqueo():
    """Se activa en cualquier momento al presionar Ctrl+Shift+F1"""
    global nivel_acceso
    if nivel_acceso == "admin":
        return
        
    import tkinter as tk
    from tkinter import simpledialog
    
    root = tk.Tk()
    root.attributes("-topmost", True) # Fuerza la ventana al frente
    root.withdraw() # Oculta la ventana principal, deja solo el cuadro de diálogo
    
    u = simpledialog.askstring("Seguridad ATH1", "Usuario:")
    p = simpledialog.askstring("Seguridad ATH1", "Contraseña:", show='*')
    
    root.destroy()
    
    if u == os.getenv("ATH1_USER") and p == os.getenv("ATH1_PASS"):
        print("[SISTEMA] ✅ Acceso de administrador concedido.")
        nivel_acceso = "admin"
    else:
        print("[SISTEMA] ❌ Credenciales incorrectas.")
        
# Dejar el atajo escuchando en segundo plano de forma permanente
try:
    keyboard.add_hotkey('ctrl+shift+f1', solicitar_desbloqueo)
except Exception:
    pass # Ignora silenciosamente si el ejecutable se abre sin permisos de administrador

def escaneo_facial_silencioso():
    """Revisa la cámara al inicio sin imprimir textos, manteniendo el secreto"""
    global nivel_acceso
    if os.path.exists("modelo_facial.yml"):
        try:
            reconocedor = cv2.face.LBPHFaceRecognizer_create()
            reconocedor.read("modelo_facial.yml")
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            
            cap = cv2.VideoCapture(0)
            ret, frame = cap.read()
            cap.release()
            
            if ret:
                gris = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                rostros = face_cascade.detectMultiScale(gris, 1.3, 5)
                for (x, y, w, h) in rostros:
                    rostro_recortado = gris[y:y+h, x:x+w]
                    id_usuario, confianza = reconocedor.predict(rostro_recortado)
                    if id_usuario == 1 and confianza < 70:
                        nivel_acceso = "admin"
        except Exception:
            pass

def main():
    global nivel_acceso
    
    # 1. Intentar el escaneo fantasma al iniciar
    escaneo_facial_silencioso()
    
    print("=" * 55)
    print("  🤖  ASISTENTE DE INTELIGENCIA ARTIFICIAL ATH1 ACTIVADO")
    print("  🎤  Escuchando tu huella geométrica para despertar... (Ctrl+C para salir)")
    print("=" * 55)
    
    if nivel_acceso == "admin":
        print("[SISTEMA] ✅ Sesión iniciada como Administrador (MAOAZAking).")
    else:
        print("[SISTEMA] ⚠️ MODO INVITADO. Funciones restringidas. (Presione Ctrl+Shift+F1 para desbloquear)")

    # ─── CARGA DE HUELLAS ACÚSTICAS ───
    huellas_templates = []
    if os.path.exists("ath1_voice_templates.json"):
        with open("ath1_voice_templates.json", "r") as f:
            try:
                huellas_templates = [np.array(t) for t in json.load(f)]
                print(f"📦 Se han cargado {len(huellas_templates)} patrones acústicos de activación.")
            except Exception as e:
                pass
                
# ... AQUÍ CONTINÚA EL RESTO DE TU CÓDIGO NORMAL (asistente_activo, try, get_vosk_model, etc.)
# ──────────────────────────────────────────────────────────────────────────────
#  Configuración
# ──────────────────────────────────────────────────────────────────────────────
SAMPLE_RATE    = 44100
BLOCK_SIZE     = int(SAMPLE_RATE * 0.05)   # 50 ms por bloque

# ──────────────────────────────────────────────────────────────────────────────
#  Modelo Offline Vosk (Carga diferida)
# ──────────────────────────────────────────────────────────────────────────────
vosk_model = None

def get_vosk_model():
    """Obtiene o inicializa el modelo de Vosk en español (descarga automática si es necesario)."""
    global vosk_model
    if vosk_model is None:
        print("⏳ Inicializando modelo offline de Vosk para español...")
        vosk_model = vosk.Model(lang="es")
    return vosk_model

def transcribir_audio_vosk(wav_data_bytes) -> str:
    """Realiza transcripción local usando el motor offline Vosk."""
    try:
        model = get_vosk_model()
        rec = vosk.KaldiRecognizer(model, 16000)
        
        wav_io = io.BytesIO(wav_data_bytes)
        with wave.open(wav_io, 'rb') as wf:
            data = wf.readframes(wf.getnframes())
            if rec.AcceptWaveform(data):
                res = json.loads(rec.Result())
            else:
                res = json.loads(rec.FinalResult())
            return res.get("text", "").strip()
    except Exception as e:
        print(f"⚠️ Error al transcribir offline con Vosk: {e}")
        return ""

# ──────────────────────────────────────────────────────────────────────────────
#  Grabador de Voz Inteligente (Micrófono via sounddevice)
# ──────────────────────────────────────────────────────────────────────────────
def grabar_audio(umbral=0.015, tiempo_silencio_limite=1.8, max_duracion=40.0) -> io.BytesIO:
    """
    Graba el audio de voz del usuario usando sounddevice.
    Detiene la grabación automáticamente cuando detecta silencio continuado.
    """
    print("\n🎤 [ATH1] Escuchando tu voz... Habla ahora.")
    
    sample_rate = 16000
    block_size = int(sample_rate * 0.1) # 100 ms por bloque
    
    audio_buffer = []
    hablando = False
    tiempo_silencio = 0.0
    tiempo_inicio = time.time()
    
    try:
        with sd.InputStream(samplerate=sample_rate, channels=1, blocksize=block_size, dtype='float32') as stream:
            while True:
                chunk, overflowed = stream.read(block_size)
                audio_buffer.append(chunk)
                
                rms = np.sqrt(np.mean(chunk**2))
                
                if rms > umbral:
                    if not hablando:
                        print("🎙️  [Voz detectada] Escuchando...", end="", flush=True)
                        hablando = True
                    else:
                        print("*", end="", flush=True)
                    tiempo_silencio = 0.0
                else:
                    if hablando:
                        print(".", end="", flush=True)
                        tiempo_silencio += 0.1
                    else:
                        print(".", end="", flush=True)
                        
                duracion_actual = time.time() - tiempo_inicio
                
                # Criterio 1: El usuario empezó a hablar y luego hizo silencio
                if hablando and tiempo_silencio >= tiempo_silencio_limite:
                    print("\n🤫 Silencio detectado, procesando audio...")
                    break
                # Criterio 2: Se superó la duración máxima tolerada
                if duracion_actual >= max_duracion:
                    print("\n⏰ Límite de tiempo alcanzado, procesando...")
                    break
                # Criterio 3: No habló en los primeros 40 segundos
                if not hablando and duracion_actual >= 40.0:
                    print("\n💤 No se detectó ninguna instrucción de voz.")
                    return None
    except Exception as e:
        print(f"⚠️ Error al acceder al micrófono: {e}")
        return None
        
    # Combinar los bloques en un array numpy
    audio_data = np.concatenate(audio_buffer, axis=0)
    # Convertir float32 [-1.0, 1.0] a int16 para formato WAV estándar
    audio_data_int16 = (audio_data * 32767).astype(np.int16)
    
    # Crear archivo WAV en memoria
    wav_io = io.BytesIO()
    with wave.open(wav_io, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data_int16.tobytes())
        
    wav_io.seek(0)
    return wav_io

# ──────────────────────────────────────────────────────────────────────────────
#  Transcripción (Speech-to-Text híbrido)
# ──────────────────────────────────────────────────────────────────────────────
def transcribir_audio(wav_io) -> str:
    """Convierte el archivo WAV de memoria en texto intentando online primero, y offline después."""
    if wav_io is None:
        return ""
        
    wav_bytes = wav_io.getvalue()
    
    # 1. Intentar Speech Recognition de Google si hay red
    if ath1_brain.check_internet():
        print("🔍 Transcribiendo con Google Speech API (Online)...")
        r = sr.Recognizer()
        wav_io.seek(0)
        try:
            with sr.AudioFile(wav_io) as source:
                audio = r.record(source)
            texto = r.recognize_google(audio, language="es-ES")
            if texto:
                print(f"🗣️  Usuario dijo (Online): «{texto}»")
                return texto
        except Exception as e:
            print(f"⚠️ Google API falló ({e}). Cambiando a reconocimiento local...")
            
    # 2. Si no hay conexión o falló, usar Vosk de forma local
    print("🔍 Transcribiendo con Vosk (Offline)...")
    texto_local = transcribir_audio_vosk(wav_bytes)
    if texto_local:
        print(f"🗣️  Usuario dijo (Offline): «{texto_local}»")
        return texto_local
        
    print("⚠️ No se detectó texto comprensible.")
    return ""

# ──────────────────────────────────────────────────────────────────────────────
#  Secuencia del Asistente Virtual
# ──────────────────────────────────────────────────────────────────────────────
def procesar_orden():
    try:
        wav_io = grabar_audio(max_duracion=30.0)
        if wav_io:
            texto = transcribir_audio(wav_io)
            if texto.strip():
                respuesta = ath1_brain.procesar_peticion(texto, nivel_acceso)
                respuesta_limpia = str(respuesta).strip().upper()
                
                # Capturar orden de apagado
                if "APAGANDO_SISTEMA" in respuesta_limpia:
                    if nivel_acceso == "admin":
                        hablar("Hasta luego MAOAZAking, que tengas un buen día.")
                    else:
                        hablar("Adiós.")  # Ahora sí está separado para no-administradores
                    
                    import os
                    os._exit(0)  # Cierra todo de forma fulminante tras hablar
                
                # Si no es apagado, dice la respuesta normal del cerebro
                hablar(respuesta)
            else:
                hablar("No logré comprender tu petición.")
        else:
            hablar("No he escuchado ninguna orden, estaré aquí esperando, solo llámame.")
    except Exception as e:
        print(f"⚠️ Error en secuencia: {e}")
        hablar("Lo siento, se ha producido un error interno.")


# ──────────────────────────────────────────────────────────────────────────────
#  Llamar a TTS (Text-to-Speech)
# ──────────────────────────────────────────────────────────────────────────────
def hablar(texto: str):
    """Pronuncia el texto de respuesta usando la voz del sistema operativo."""
    print(f"  🔊  ATH1 dice: «{texto}»")

    sistema = platform.system()

    # macOS say utility
    if sistema == "Darwin":
        try:
            subprocess.run(["say", "-v", "Monica", texto], check=True)
            return
        except Exception:
            pass

    # Windows / Linux pyttsx3
    engine = pyttsx3.init()
    voices = engine.getProperty("voices")

    for v in voices:
        if "spanish" in v.name.lower() or "es" in v.id.lower():
            engine.setProperty("voice", v.id)
            break

    engine.setProperty("rate", 155)
    engine.say(texto)
    engine.runAndWait()

# ──────────────────────────────────────────────────────────────────────────────
#  Main Loop
# ──────────────────────────────────────────────────────────────────────────────
def main():
    global nivel_acceso
    
    # 1. Intentar el escaneo fantasma al iniciar
    escaneo_facial_silencioso()
    
    print("=" * 55)
    print("  🤖  ASISTENTE DE INTELIGENCIA ARTIFICIAL ATH1 ACTIVADO")
    print("  🎤  Escuchando tu huella geométrica para despertar... (Ctrl+C para salir)")
    print("=" * 55)

    huellas_templates = []
    if os.path.exists("ath1_voice_templates.json"):
        with open("ath1_voice_templates.json", "r") as f:
            try:
                huellas_templates = [np.array(t) for t in json.load(f)]
                print(f"📦 Se han cargado {len(huellas_templates)} patrones acústicos de activación.")
            except Exception as e:
                pass

    asistente_activo = False
    tiempo_ultima_orden = 0
    TIEMPO_ESPERA_MAXIMO = 40.0

    try:
        model = get_vosk_model()
        rec = vosk.KaldiRecognizer(model, 16000)
        
        buffer_size = int(1.5 * 16000)
        audio_buffer = np.zeros(buffer_size, dtype=np.int16)
        
        with sd.RawInputStream(samplerate=16000, blocksize=4000, dtype='int16', channels=1) as stream:
            while True:
                data, overflowed = stream.read(4000)
                audio_np = np.frombuffer(data, dtype=np.int16)
                
                audio_buffer = np.roll(audio_buffer, -len(audio_np))
                audio_buffer[-len(audio_np):] = audio_np
                
                # Verificación del temporizador: Si pasaron 40 segundos de silencio, volver a reposo
                if asistente_activo and (time.time() - tiempo_ultima_orden > TIEMPO_ESPERA_MAXIMO):
                    print("\n💤 Pasaron 40 segundos. ATH1 vuelve a reposo. Esperando huella acústica...")
                    asistente_activo = False

                # ─── MODO REPOSO: BUSCAR HUELLA ACÚSTICA (UMBRAL < 1.7) ───
                if not asistente_activo:
                    if len(huellas_templates) > 0 and np.max(np.abs(audio_buffer)) > 1500:
                        huella_actual = extraer_espectrograma(audio_buffer)
                        if huella_actual is not None:
                            distancias = [calcular_distancia_dtw(huella_actual, t) for t in huellas_templates]
                            
                            if min(distancias) < 1.7: 
                                stream.stop() 
                                
                                # Saludo dinámico según permisos
                                if nivel_acceso == "admin":
                                    import random
                                    hablar(random.choice(["Sí señor.", "Aquí estoy señor.", "A sus órdenes."]))
                                else:
                                    hablar("Hola, dime qué necesitas.")
                                
                                # 🌟 ACTIVAMOS LA VENTANA DE ATENCIÓN DE 40 SEGUNDOS
                                asistente_activo = True
                                tiempo_ultima_orden = time.time()
                                
                                procesar_orden()
                                
                                # Al terminar de procesar la primera orden, reiniciamos el reloj
                                tiempo_ultima_orden = time.time()
                                audio_buffer.fill(0)
                                rec = vosk.KaldiRecognizer(model, 16000)
                                stream.start() 
                                continue

                # ─── MODO ATENCIÓN ACTIVA: ESCUCHA DIRECTA POR VOSK RE-INVERTIDA ───
                if rec.AcceptWaveform(bytes(data)):
                    res = json.loads(rec.Result())
                    texto = res.get("text", "").lower().strip()
                    
                    if texto:
                        # Si está en modo activo, cualquier frase refresca los 40 segundos
                        if asistente_activo:
                            tiempo_ultima_orden = time.time()
                        
                        # 1. Comandos de seguridad de apagado
                        if any(x in texto for x in ["apágate", "apagate", "finalizar ejecución", "apagar asistente"]):
                            stream.stop()
                            hablar("Entendido. Cerrando todos mis procesos en segundo plano. Hasta luego.")
                            print("\n🔌 software apagado por comando de voz de seguridad.")
                            sys.exit(0)
                            
                        # 2. Comandos directos si está despierto (Ej: "Pon pantalla completa")
                        elif asistente_activo:
                            print(f"\n⚡ Orden directa capturada (Sin requerir huella): «{texto}»")
                            stream.stop()
                            
                            # Si te despides, lo duermes antes de tiempo de forma manual
                            if any(x in texto for x in ["descansa", "adiós", "dormir", "silencio", "gracias"]):
                                hablar("Entendido, vuelvo a modo de espera.")
                                asistente_activo = False
                            else:
                                # Aquí puedes llamar directo a tu lógica de procesamiento o procesar_orden()
                                # NOTA: Asegúrate de que tu función procesar_orden() capture el 'texto' actual 
                                # o llama directo a 'ath1_brain.procesar_peticion(texto)'
                                respuesta = ath1_brain.procesar_peticion(texto, nivel_acceso)
                                hablar(respuesta)
                            
                            # Limpieza e inicio limpio para la siguiente orden en cola
                            tiempo_ultima_orden = time.time()
                            audio_buffer.fill(0)
                            rec = vosk.KaldiRecognizer(model, 16000)
                            stream.start()
                            continue
                            
    except KeyboardInterrupt:
        print("\n\nHasta luego! 👋")
        sys.exit(0)

if __name__ == "__main__":
    main()


############################################################
# Comando de PowerShell para ejecutar el asistente en cualquier dispositivo
# irm https://raw.githubusercontent.com/MAOAZAking/ATH1/main/lanzador.ps1 | iex
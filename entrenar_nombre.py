#!/usr/bin/env python3
import os
import json
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import sounddevice as sd

VOICE_TEMPLATES_FILE = "ath1_voice_templates.json"
SAMPLE_RATE = 16000
DURATION = 1.5  

# ──────────────────────────────────────────────────────────────────────────────
#  MOTOR DSP OPTIMIZADO (CON PUERTA DE RUIDO Y NORMALIZACIÓN)
# ──────────────────────────────────────────────────────────────────────────────
def extraer_espectrograma(audio, frame_size=1024, hop_size=512):
    """Convierte el audio crudo en una huella geométrica normalizada."""
    audio = np.ravel(audio)
    
    # 🌟 1. PUERTA DE RUIDO ABSOLUTA: Si el pico es menor a 1500, es ruido ambiental/silencio
    pico_max = np.max(np.abs(audio))
    if pico_max < 1500:
        return None
        
    if audio.dtype != np.float32:
        audio = audio.astype(np.float32) / 32768.0
        
    # Recorte de silencios relativo perimetral
    energia = np.abs(audio)
    umbral = np.max(energia) * 0.15
    zonas_activas = np.where(energia > umbral)[0]
    if len(zonas_activas) > 500:
        audio = audio[zonas_activas[0]:zonas_activas[-1]]
        
    frames = []
    for i in range(0, len(audio) - frame_size, hop_size):
        ventana = audio[i:i+frame_size] * np.hanning(frame_size)
        fft_res = np.abs(np.fft.rfft(ventana))
        frames.append(np.log1p(fft_res))
        
    if len(frames) < 5:
        return None
        
    # 🌟 2. RESOLUCIÓN AMPLIADA: 32 bandas de frecuencia para detectar fonemas claros
    spec = np.array(frames)
    num_frames, bins = spec.shape
    bandas = 32
    chunk = max(1, bins // bandas)
    spec_pooled = np.array([[np.mean(f[j*chunk:(j+1)*chunk]) for j in range(bandas)] for f in spec])
    
    # 🌟 3. NORMALIZACIÓN Z-SCORE: Elimina la influencia del siseo constante y volumen
    media = np.mean(spec_pooled)
    desviacion = np.std(spec_pooled) + 1e-6
    spec_normalized = (spec_pooled - media) / desviacion
    
    return spec_normalized

def calcular_distancia_dtw(spec1, spec2):
    """Algoritmo Dynamic Time Warping estándar."""
    N, M = len(spec1), len(spec2)
    coste = np.zeros((N, M))
    for i in range(N):
        for j in range(M):
            coste[i, j] = np.linalg.norm(spec1[i] - spec2[j])
            
    dtw = np.zeros((N, M))
    dtw[0, 0] = coste[0, 0]
    for i in range(1, N): dtw[i, 0] = dtw[i-1, 0] + coste[i, 0]
    for j in range(1, M): dtw[0, j] = dtw[0, j-1] + coste[0, j]
    
    for i in range(1, N):
        for j in range(1, M):
            dtw[i, j] = coste[i, j] + min(dtw[i-1, j], dtw[i, j-1], dtw[i-1, j-1])
            
    return dtw[-1, -1] / (N + M)

# ──────────────────────────────────────────────────────────────────────────────
#  INTERFAZ GRÁFICA NATIVA
# ──────────────────────────────────────────────────────────────────────────────
class EntrenadorAcusticoATH1:
    def __init__(self, root):
        self.root = root
        self.root.title("ATH1 - Calibrador de Huella Acústica Inteligente")
        self.root.geometry("620x500")
        self.root.configure(bg="#121212")
        self.root.resizable(False, False)
        
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("TButton", font=("Arial", 11, "bold"), background="#1f1f1f", foreground="#ffffff")
        
        self.corriendo_prueba = False
        self.historial_huellas = []
        self.cargar_huellas_existentes()
        
        self.lbl_titulo = tk.Label(root, text="🧠 RECONOCIMIENTO GEOMÉTRICO DE VOZ", font=("Arial", 12, "bold"), bg="#121212", fg="#00ffcc")
        self.lbl_titulo.pack(pady=15)
        
        btn_frame = tk.Frame(root, bg="#121212")
        btn_frame.pack(pady=5)
        
        self.btn_aprender = ttk.Button(btn_frame, text="🧠 Grabar Muestras (Ampliar)", command=self.iniciar_aprendizaje)
        self.btn_aprender.pack(side="left", padx=10)
        
        self.btn_probar = ttk.Button(btn_frame, text="🧪 Modo Prueba Real", command=self.alternar_prueba)
        self.btn_probar.pack(side="left", padx=10)
        
        self.txt_consola = tk.Text(root, height=11, width=68, bg="#1e1e1e", fg="#ffffff", font=("Courier New", 10), wrap="word")
        self.txt_consola.pack(pady=15)
        self.log(f"Sistema listo. Patrones limpios en memoria: {len(self.historial_huellas)}")
        if len(self.historial_huellas) == 0:
            self.log("⚠️ NOTA: El archivo de huellas está vacío o no existe. ¡Debes entrenarlo!")
        
        self.lbl_alerta = tk.Label(root, text="ESPERANDO ACCIÓN", font=("Arial", 14, "bold"), bg="#222222", fg="#888888", width=44, height=2)
        self.lbl_alerta.pack(pady=10)

    def log(self, texto):
        self.txt_consola.config(state="normal")
        self.txt_consola.insert("end", f"\n> {texto}")
        self.txt_consola.see("end")
        self.txt_consola.config(state="disabled")

    def cargar_huellas_existentes(self):
        if os.path.exists(VOICE_TEMPLATES_FILE):
            try:
                with open(VOICE_TEMPLATES_FILE, "r") as f:
                    self.historial_huellas = json.load(f)
            except Exception:
                self.historial_huellas = []

    def iniciar_aprendizaje(self):
        # Al empezar un entrenamiento limpio, es mejor purgar errores previos si lo deseas, 
        # pero respetando tu orden: vamos a AMPLIAR el conocimiento existente de forma limpia.
        self.btn_aprender.config(state="disabled")
        self.btn_probar.config(state="disabled")
        threading.Thread(target=self.bucle_aprendizaje, daemon=True).start()

    def bucle_aprendizaje(self):
        nuevas_huellas = []
        i = 1
        while i <= 3:
            self.root.after(0, lambda idx=i: self.lbl_alerta.config(text=f"🎙️ MUESTRA {idx}/3: ¡DI 'ATH1'!", bg="#0055ff", fg="#ffffff"))
            time.sleep(0.2)
            
            audio = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='int16')
            sd.wait()
            
            huella = extraer_espectrograma(audio)
            
            if huella is not None:
                nuevas_huellas.append(huella.tolist())
                self.root.after(0, lambda idx=i: self.log(f"Muestra {idx} capturada correctamente con geometría Z-Score."))
                i += 1
            else:
                self.root.after(0, lambda: self.log("⚠️ RECHAZADO: No hablaste o el ruido de fondo fue muy bajo. Repitiendo intento..."))
                self.root.after(0, lambda: self.lbl_alerta.config(text="❌ INTENTA DE NUEVO, MÁS FUERTE", bg="#ff3333", fg="#ffffff"))
                time.sleep(1.5)
                continue
                
            self.root.after(0, lambda: self.lbl_alerta.config(text="⏳ SILENCIO...", bg="#333333", fg="#ffcc00"))
            time.sleep(1.2)
            
        if nuevas_huellas:
            self.historial_huellas.extend(nuevas_huellas)
            with open(VOICE_TEMPLATES_FILE, "w") as f:
                json.dump(self.historial_huellas, f)
            self.root.after(0, lambda: messagebox.showinfo("Éxito", f"¡Conocimiento ampliado! Total de huellas válidas: {len(self.historial_huellas)}"))
        
        self.root.after(0, self.restablecer_interfaz)

    def restablecer_interfaz(self):
        self.btn_aprender.config(state="normal")
        self.btn_probar.config(state="normal")
        self.lbl_alerta.config(text="ESPERANDO ACCIÓN", bg="#222222", fg="#888888")

    def alternar_prueba(self):
        if self.corriendo_prueba:
            self.corriendo_prueba = False
            self.btn_probar.config(text="🧪 Modo Prueba Real")
            self.restablecer_interfaz()
        else:
            self.cargar_huellas_existentes()
            if not self.historial_huellas:
                messagebox.showwarning("Sin huellas", "El archivo de huellas está vacío. Registra muestras primero.")
                return
            self.corriendo_prueba = True
            self.btn_probar.config(text="🛑 Detener Prueba")
            self.btn_aprender.config(state="disabled")
            threading.Thread(target=self.bucle_prueba, daemon=True).start()

    def bucle_prueba(self):
        templates = [np.array(t) for t in self.historial_huellas]
        buffer_muestras = int(DURATION * SAMPLE_RATE)
        audio_buffer = np.zeros((buffer_muestras, 1), dtype='int16')
        
        self.root.after(0, lambda: self.lbl_alerta.config(text="🎤 HABLA LIBREMENTE...", bg="#00ffcc", fg="#121212"))
        block_size = int(SAMPLE_RATE * 0.25)
        
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='int16') as stream:
            while self.corriendo_prueba:
                data, _ = stream.read(block_size)
                audio_buffer = np.roll(audio_buffer, -block_size, axis=0)
                audio_buffer[-block_size:] = data
                
                # Modificado a > 1500 para acoplarse a la puerta de ruido absoluta
                if np.max(np.abs(audio_buffer)) > 1500:
                    huella_actual = extraer_espectrograma(audio_buffer)
                    if huella_actual is not None:
                        distancias = [calcular_distancia_dtw(huella_actual, t) for t in templates]
                        min_dist = min(distancias)
                        
                        # 🌟 CON NORMALIZACIÓN Z-SCORE: Un match real da valores menores a 1.7
                        if min_dist < 1.7:
                            self.root.after(0, lambda d=min_dist: self.lbl_alerta.config(text=f"🟢 ¡ME ESTÁS LLAMANDO! (Dist: {d:.2f})", bg="#00ff00", fg="#121212"))
                        else:
                            self.root.after(0, lambda d=min_dist: self.lbl_alerta.config(text=f"🔴 NO ES MI NOMBRE (Dist: {d:.2f})", bg="#ff3333", fg="#ffffff"))

if __name__ == "__main__":
    # Si notas que persisten capturas viejas erróneas, puedes borrar el archivo "ath1_voice_templates.json" 
    # manualmente antes de lanzar el script para empezar desde cero y limpio.
    root = tk.Tk()
    app = EntrenadorAcusticoATH1(root)
    root.mainloop()
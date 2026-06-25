#!/usr/bin/env python3
"""
ATH1 Brain Module.
Handles:
- SQLite Database for local memory, preferences, and knowledge base.
- Prepopulating the database with rich programming and system knowledge.
- RAG (Retrieval Augmented Generation) by querying local knowledge.
- Google Gemini API integration.
- Offline rule-based action execution and keyword matching.
- Online/Offline self-learning (extracting and saving facts to the DB).
- Actuator actions (minimizing windows, volume control, locking computer, time/date, VS Code, YouTube).
"""

import os
import re
import sys
import time
import sqlite3
import datetime
import urllib.parse
import urllib.request
import webbrowser
import pyautogui  # 🌟 Librería para controlar teclado/mouse físicamente
from google import genai  # 🌟 El nuevo SDK oficial de Google
import google.generativeai as genai

DB_NAME = "ath1_knowledge.db"

# ──────────────────────────────────────────────────────────────────────────────
#  Base de Datos (Inicialización y Carga de Conocimiento)
# ──────────────────────────────────────────────────────────────────────────────
def init_db():
    """Inicializa la base de datos y crea las tablas necesarias."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Tabla de conocimiento local (predefinido y aprendido)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            keyword TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabla para historial de chat (memoria conversacional)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_input TEXT,
            assistant_response TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabla para perfil y preferencias de usuario
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_profile (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    
    conn.commit()
    
    # Prepopular la base de datos si está vacía
    cursor.execute("SELECT COUNT(*) FROM knowledge")
    if cursor.fetchone()[0] == 0:
        print("🗄️ Inicializando base de datos local con conocimiento básico de programación...")
        seed_knowledge(conn)
        
    conn.close()

def seed_knowledge(conn):
    """Carga una cantidad masiva y detallada de conocimiento offline (no tacaño con el conocimiento)."""
    cursor = conn.cursor()
    
    knowledge_data = [
        # --- Python ---
        ("programming", "python decorador", "Un decorador en Python es una función que recibe otra función como argumento, añade cierta funcionalidad y retorna una nueva función sin modificar la original. Se definen con el símbolo @."),
        ("programming", "python generador", "Los generadores son funciones que usan 'yield' en lugar de 'return'. Devuelven un iterador que produce elementos uno a uno sobre la marcha, lo que optimiza mucho el consumo de memoria en colecciones grandes."),
        ("programming", "python list comprehension", "La compresión de listas es una forma concisa de crear listas en Python. Estructura básica: [expresion for item in iterable if condicion]. Ejemplo: [x**2 for x in range(10) if x%2==0]."),
        ("programming", "python context manager", "Los administradores de contexto controlan la asignación y liberación de recursos usando la palabra clave 'with'. El ejemplo clásico es abrir archivos: 'with open(file) as f:', asegurando su cierre automático."),
        ("programming", "python gil", "El Global Interpreter Lock (GIL) es un mutex en CPython que permite que solo un hilo nativo ejecute bytecode de Python a la vez. Esto limita el paralelismo multi-hilo en tareas intensivas de CPU, pero es seguro para hilos en operaciones I/O."),
        ("programming", "python virtualenv", "Un entorno virtual de Python es una carpeta aislada que contiene su propio ejecutable de Python y sus propias dependencias instaladas con pip, evitando conflictos de librerías globales."),
        ("programming", "python dict", "Un diccionario en Python es una estructura de datos de clave-valor mutable y optimizada. A partir de Python 3.7, preservan el orden de inserción de las llaves."),
        ("programming", "python lambda", "Las funciones lambda son funciones anónimas y rápidas definidas en una sola línea mediante 'lambda argumentos: expresion'."),
        
        # --- JavaScript ---
        ("programming", "javascript promise", "Una Promesa en JavaScript representa un valor que puede estar disponible ahora, en el futuro o nunca. Tiene tres estados: pendiente (pending), cumplida (fulfilled) o rechazada (rejected)."),
        ("programming", "javascript async await", "Async y Await son azúcares sintácticos construidos sobre Promesas para escribir código asíncrono que se lee como síncrono. La función debe llevar 'async' y las llamadas con promesa llevan 'await'."),
        ("programming", "javascript closure", "Un closure (clausura) es la combinación de una función y el entorno léxico en el que fue declarada, permitiendo que la función acceda a variables de un ámbito externo incluso después de haberse ejecutado."),
        
        # --- Git ---
        ("programming", "git commit", "Guarda los cambios locales confirmados en el historial del repositorio. Uso común: 'git commit -m \"Mensaje descriptivo\"'."),
        ("programming", "git branch", "Permite listar, crear o borrar ramas. Las ramas sirven para trabajar en funcionalidades aisladas del código principal. Uso: 'git branch <nombre>'."),
        ("programming", "git merge", "Une los historiales de dos ramas distintas, incorporando los cambios de una rama secundaria a la rama activa actual."),
        ("programming", "git rebase", "Reorganiza el historial de commits aplicando tus cambios locales encima de la última versión de otra rama. Mantiene un historial de Git limpio y lineal."),
        ("programming", "git stash", "Guarda temporalmente en una pila de trabajo los cambios pendientes que aún no están listos para un commit, permitiéndote cambiar de rama con el directorio limpio."),
        
        # --- SQL ---
        ("programming", "sql select", "Sentencia para consultar registros de una base de datos. Ejemplo: 'SELECT nombre, email FROM usuarios WHERE edad >= 18;'."),
        ("programming", "sql join", "Operación para combinar filas de dos o más tablas basándose en una columna común. Existen INNER JOIN, LEFT JOIN, RIGHT JOIN y FULL OUTER JOIN."),
        ("programming", "sql index", "Un índice es una estructura de datos física en el motor de base de datos que acelera notablemente las consultas de búsqueda a costa de mayor uso de disco y ralentizar las operaciones de inserción y actualización."),
        
        # --- Docker ---
        ("programming", "docker container", "Un contenedor es una instancia ejecutable de una imagen Docker. Aísla de manera ligera y portable la aplicación y su entorno completo (librerías, variables, sistema operativo base)."),
        ("programming", "dockerfile", "Un Dockerfile es un script de texto con instrucciones consecutivas que Docker utiliza para construir una imagen de contenedor de manera automática."),
        ("programming", "docker compose", "Herramienta que permite definir y correr aplicaciones multi-contenedor mediante un único archivo YAML de configuración."),
        
        # --- Conceptos de Software ---
        ("programming", "api", "Una Interfaz de Programación de Aplicaciones (API) es un conjunto de reglas y definiciones que permite a un software comunicarse y compartir servicios o datos con otro software."),
        ("programming", "mvc", "Modelo-Vista-Controlador es un patrón de arquitectura que separa los datos de negocio (Modelo), la interfaz de presentación (Vista) y la lógica de control o interacción (Controlador)."),
        ("programming", "oop poo", "La Programación Orientada a Objetos es un paradigma basado en clases y objetos que encapsulan datos (atributos) y comportamiento (métodos). Sus pilares son herencia, polimorfismo, abstracción y encapsulamiento."),
        ("programming", "algoritmo", "Un algoritmo es una secuencia precisa, ordenada y finita de instrucciones o pasos lógicos para resolver un problema o realizar una tarea determinada."),
        ("programming", "big o complejidad", "La notación Big O se usa para describir la complejidad temporal (velocidad) o espacial (memoria) de un algoritmo conforme el tamaño del conjunto de datos de entrada tiende a crecer."),
        
        # --- Información del Asistente ATH1 ---
        ("general", "quien eres", "Soy ATH1, tu asistente de inteligencia artificial inteligente y autónomo. Fui desarrollado por MAOAZA para asistirte en programación, control de sistema y aprendizaje continuo, tanto en línea como de manera local."),
        ("general", "creador maoaza", "MAOAZA es el creador de ATH1. Me configuró con lógica avanzada de Python, base de datos local auto-sostenible y conexión al motor de IA de Google Gemini."),
        ("general", "funcionamiento offline local", "Puedo funcionar offline buscando palabras clave en mi base de datos SQLite y analizando tu voz con el motor local Vosk. Si me enseñas cosas usando frases como 'aprende que X es Y', lo guardaré para responderte después."),
        ("general", "motivacion programacion", "La programación no tiene límites. Como programador puedes crear todo lo que pase por tu mente. El límite es tu imaginación; quita tus límites y construye el futuro."),
    ]
    
    cursor.executemany(
        "INSERT INTO knowledge (category, keyword, content) VALUES (?, ?, ?)",
        knowledge_data
    )
    conn.commit()
    print(f"✅ Se insertaron {len(knowledge_data)} registros de conocimiento inicial.")

# ──────────────────────────────────────────────────────────────────────────────
#  Búsqueda de Conocimiento Local (RAG y fallback)
# ──────────────────────────────────────────────────────────────────────────────
def buscar_conocimiento_local(query: str) -> str:
    """Busca en la base de datos local y devuelve resúmenes de coincidencias relevantes."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Limpiar y separar en palabras clave
    palabras = [p.lower() for p in re.findall(r'\w+', query) if len(p) > 2]
    if not palabras:
        conn.close()
        return ""
        
    resultados = []
    vistos = set()
    
    for palabra in palabras:
        # Evitar palabras comunes vacías
        if palabra in ["para", "como", "esta", "donde", "quien", "cual", "sobre", "python", "javascript"]:
            continue
            
        cursor.execute("""
            SELECT category, keyword, content FROM knowledge 
            WHERE keyword LIKE ? OR content LIKE ?
        """, (f"%{palabra}%", f"%{palabra}%"))
        
        for cat, key, content in cursor.fetchall():
            ref = (key, content)
            if ref not in vistos:
                vistos.add(ref)
                resultados.append(f"- [{cat.upper()}] ({key}): {content}")
                
    conn.close()
    
    if resultados:
        return "\n".join(resultados[:4]) # Limitar a los 4 más relevantes
    return ""

def guardar_conocimiento_local(category: str, keyword: str, content: str) -> bool:
    """Guarda dinámicamente un nuevo dato en la base de datos."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Comprobar si ya existe una llave idéntica
        cursor.execute("SELECT id FROM knowledge WHERE keyword = ? AND content = ?", (keyword.lower(), content))
        if cursor.fetchone():
            conn.close()
            return False
            
        cursor.execute(
            "INSERT INTO knowledge (category, keyword, content) VALUES (?, ?, ?)",
            (category.lower(), keyword.lower(), content)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"⚠️ Error al guardar conocimiento local: {e}")
        return False

# ──────────────────────────────────────────────────────────────────────────────
#  Memoria Conversacional
# ──────────────────────────────────────────────────────────────────────────────
def guardar_historial_chat(user_input: str, assistant_response: str):
    """Guarda la conversación actual en la base de datos."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_history (user_input, assistant_response) VALUES (?, ?)",
            (user_input, assistant_response)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️ Error al guardar historial: {e}")

def obtener_historial_chat(limite=3) -> str:
    """Devuelve los últimos intercambios del chat en texto estructurado."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_input, assistant_response FROM chat_history ORDER BY id DESC LIMIT ?",
            (limite,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        historial = []
        for user, assistant in reversed(rows):
            historial.append(f"Usuario: {user}\nATH1: {assistant}")
        return "\n".join(historial)
    except Exception as e:
        print(f"⚠️ Error al obtener historial: {e}")
        return ""

# ──────────────────────────────────────────────────────────────────────────────
#  Helpers de Aplicaciones y Perfil de Usuario
# ──────────────────────────────────────────────────────────────────────────────
def buscar_app_windows(executable_name: str) -> str:
    """Busca un ejecutable en las carpetas comunes de Windows y el PATH."""
    import shutil
    path = shutil.which(executable_name)
    if path:
        return path
        
    program_files = [
        os.environ.get("ProgramFiles", "C:\\Program Files"),
        os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"),
        os.environ.get("LocalAppData", "")
    ]
    
    common_subdirs = [
        "Microsoft Office\\root\\Office16",
        "Microsoft Office\\Office16",
        "Microsoft Office\\Office15",
        "Microsoft Office\\root\\Office15",
        "Google\\Chrome\\Application",
        "Programs\\Microsoft VS Code",
    ]
    
    for pf in program_files:
        if not pf:
            continue
        direct_path = os.path.join(pf, executable_name)
        if os.path.exists(direct_path):
            return direct_path
            
        for sd_path in common_subdirs:
            full_path = os.path.join(pf, sd_path, executable_name)
            if os.path.exists(full_path):
                return full_path
                
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        vscode_user = os.path.join(local_app_data, "Programs", "Microsoft VS Code", executable_name)
        if os.path.exists(vscode_user):
            return vscode_user
            
    return ""

def guardar_perfil_usuario(key: str, value: str) -> bool:
    """Guarda o actualiza una preferencia o rasgo del perfil del usuario en la base de datos."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO user_profile (key, value) VALUES (?, ?)",
            (key.lower().strip(), value.strip())
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"⚠️ Error al guardar perfil de usuario: {e}")
        return False

def obtener_perfil_usuario() -> str:
    """Devuelve todo el perfil guardado del usuario como texto estructurado."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM user_profile")
        rows = cursor.fetchall()
        conn.close()
        if rows:
            profile_lines = []
            for key, value in rows:
                profile_lines.append(f"- {key}: {value}")
            return "\n".join(profile_lines)
        return ""
    except Exception as e:
        print(f"⚠️ Error al obtener perfil de usuario: {e}")
        return ""

# ──────────────────────────────────────────────────────────────────────────────
#  Actuadores de Sistema (Acciones)
# ──────────────────────────────────────────────────────────────────────────────
def ejecutar_accion_sistema(query: str) -> str:
    """
    Analiza la petición del usuario para ejecutar acciones locales directas.
    Devuelve un mensaje si se ejecutó alguna acción, de lo contrario una cadena vacía.
    """
    q = query.lower()
    # 0. Comando de apagado del sistema
    if any(x in q for x in ["apágate", "apagate", "apagar", "finalizar", "apagar sistema"]):
        return "APAGANDO_SISTEMA"
        
    # 0.1. Ventana emergente para escritura manual (Portable con Tkinter)
    if any(x in q for x in ["quiero escribir", "escribirte algo", "escribir texto"]):
        import tkinter as tk
        from tkinter import simpledialog
        root = tk.Tk()
        root.attributes("-topmost", True) # Fuerza la ventana al frente
        root.withdraw()
        user_text = simpledialog.askstring("ATH1 - Interfaz Manual", "Escribe tu orden para ATH1:")
        root.destroy()
        if user_text:
            return procesar_peticion(user_text) # Procesa el texto recursivamente
        else:
            return "Se canceló la entrada de texto."
    
    # 1. YouTube
    if any(x in q for x in ["abre youtube", "pon en youtube", "reproduce en youtube"]):
        search_query = ""
        for term in ["reproduce en youtube", "pon en youtube", "abre youtube y busca", "busca en youtube"]:
            if term in q:
                search_query = q.split(term)[-1].strip()
                break
        
        if search_query:
            url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(search_query)}"
            webbrowser.open(url)
            return f"He abierto YouTube y he buscado {search_query}."
        else:
            webbrowser.open("https://www.youtube.com")
            return "He abierto la página principal de YouTube."
        
    """
    Analiza comandos directos del sistema de forma flexible y 
    controla aplicaciones abiertas mediante simulación de teclado.
    """
    q = peticion.lower().strip()
    
    # ─── 1. CONTROL TOTAL DE YOUTUBE Y REPRODUCTOR ───
    if "youtube" in q or "yutub" in q:
        # Caso A: Buscar y reproducir algo nuevo
        if any(x in q for x in ["busca", "reproduce", "pon"]):
            termino = q.replace("reproduce", "").replace("en youtube", "").replace("youtube", "").replace("yutub", "").replace("busca", "").replace("tú y", "").replace("entra el primer video", "").strip()
            url = f"https://www.youtube.com/results?search_query={termino}"
            webbrowser.open(url)
            
            # Automatización: Esperar carga y dar Enter al primer video
            print("⏳ Esperando que cargue YouTube para seleccionar el video...")
            time.sleep(4.5) 
            pyautogui.press('tab')  # Enfoca el contenedor principal
            pyautogui.press('enter') # Entra al primer resultado de la lista
            return f"He buscado '{termino}' en YouTube e intenté reproducir el primer video."
        
        # Caso B: Abrir la página limpia
        return "He abierto la página principal de YouTube." if webbrowser.open("https://www.youtube.com") else ""

    # ─── 2. COMANDOS DE REPRODUCCIÓN EN VIVO (Cuando ya estás viendo el video) ───
    if any(x in q for x in ["pantalla completa", "maximiza el video", "pantalla completa"]):
        pyautogui.press('f')  # Atajo nativo de YT para Fullscreen
        return "Activando pantalla completa."
        
    if any(x in q for x in ["subtítulos", "subtitulo", "activa subtitulos"]):
        pyautogui.press('c')  # Atajo nativo de YT para Captions/Subtítulos
        return "Alternando subtítulos del video."
        
    if any(x in q for x in ["pausa", "paúsalo", "reproduce el video", "continúa"]):
        pyautogui.press('space')  # Pausa/Play universal
        return "He pausado o reanudado el reproductor."

    # ─── 3. GOOGLE / NAVEGADOR COMPLETO ───
    if "google" in q or "navegador" in q:
        if webbrowser.open("https://www.google.com"):
            return "He abierto Google Chrome."

    return ""
            
    # 2. Bloc de Notas (Notepad)
    if any(x in q for x in ["abre bloc de notas", "abre notepad", "abrir bloc de notas", "abre el bloc de notas", "abre notas", "bloc de notas"]):
        import platform
        import subprocess
        sistema = platform.system()
        try:
            if sistema == "Windows":
                subprocess.Popen(["notepad.exe"])
            elif sistema == "Darwin":
                subprocess.Popen(["open", "-a", "TextEdit"])
            else:
                import shutil
                for editor in ["gedit", "mousepad", "kate", "nano"]:
                    if shutil.which(editor):
                        subprocess.Popen([editor])
                        break
                else:
                    return "No logré encontrar un editor de notas instalado en este sistema Linux."
            return "Entendido, estoy abriendo el Bloc de Notas."
        except Exception as e:
            return f"Intenté abrir el Bloc de Notas pero ocurrió un error: {e}"

    # 3. Google y Navegador Web
    if any(x in q for x in ["abre google", "abre el navegador", "abre chrome", "abre google chrome", "abras el navegador", "abrir google", "abras google"]):
        import platform
        import subprocess
        sistema = platform.system()
        try:
            if sistema == "Windows":
                chrome_path = buscar_app_windows("chrome.exe")
                if chrome_path:
                    subprocess.Popen([chrome_path])
                    return "He abierto Google Chrome."
            elif sistema == "Darwin":
                subprocess.Popen(["open", "-a", "Google Chrome"])
                return "He abierto Google Chrome."
            webbrowser.open("https://www.google.com")
            return "He abierto Google en tu navegador por defecto."
        except Exception as e:
            return f"Intenté abrir el navegador pero ocurrió un error: {e}"

    # 4. Visual Studio Code
    if any(x in q for x in ["abre vscode", "abre visual studio code", "abre vsc", "abre el editor"]):
        import platform
        import subprocess
        sistema = platform.system()
        try:
            if sistema == "Windows":
                vscode_path = buscar_app_windows("Code.exe")
                if vscode_path:
                    subprocess.Popen([vscode_path])
                    return "Entendido, estoy abriendo Visual Studio Code."
                else:
                    subprocess.Popen(["code"], shell=True)
                    return "Entendido, estoy abriendo Visual Studio Code."
            elif sistema == "Darwin":
                subprocess.Popen(["open", "-a", "Visual Studio Code"])
                return "Entendido, estoy abriendo Visual Studio Code."
            else:
                subprocess.Popen(["code"], shell=True)
                return "Entendido, estoy abriendo Visual Studio Code."
        except Exception as e:
            return f"Intenté abrir VS Code pero ocurrió un error: {e}"

    # 5. Documentos / Word (con fallback inteligente a Google Docs)
    if any(x in q for x in ["abre word", "abre microsoft word", "escribe una carta", "escribamos una carta", "crear un documento", "escribir una carta", "carta", "una carta"]):
        import platform
        import subprocess
        sistema = platform.system()
        try:
            if sistema == "Windows":
                word_path = buscar_app_windows("WINWORD.EXE")
                if word_path:
                    subprocess.Popen([word_path])
                    return "He abierto Microsoft Word localmente. Listo, ya tengo abierto donde escribiremos la carta. Dime qué quieres redactar."
            elif sistema == "Darwin":
                subprocess.Popen(["open", "-a", "Microsoft Word"])
                return "He abierto Microsoft Word para macOS. Listo, ya tengo abierto donde escribiremos la carta. Dime qué quieres redactar."
            
            # Fallback a Google Docs
            webbrowser.open("https://docs.new")
            return "Analicé tu dispositivo y no encontré Microsoft Word instalado localmente, así que abrí un documento nuevo de Google Docs en tu navegador. Listo, ya tengo abierto donde escribiremos la carta. Dime qué quieres redactar."
        except Exception as e:
            return f"Intenté abrir el procesador de textos pero ocurrió un error: {e}"

    # 6. Hojas de Cálculo / Excel (con fallback inteligente a Google Sheets)
    if any(x in q for x in ["abre excel", "abre microsoft excel", "crea una tabla", "abre una hoja de calculo", "abre planilla"]):
        import platform
        import subprocess
        sistema = platform.system()
        try:
            if sistema == "Windows":
                excel_path = buscar_app_windows("EXCEL.EXE")
                if excel_path:
                    subprocess.Popen([excel_path])
                    return "He abierto Microsoft Excel localmente."
            elif sistema == "Darwin":
                subprocess.Popen(["open", "-a", "Microsoft Excel"])
                return "He abierto Microsoft Excel para macOS."
            
            # Fallback a Google Sheets
            webbrowser.open("https://sheets.new")
            return "No encontré Microsoft Excel instalado en tu equipo, así que abrí una hoja de cálculo nueva en Google Sheets en tu navegador."
        except Exception as e:
            return f"Intenté abrir la hoja de cálculo pero ocurrió un error: {e}"

    # 7. Presentaciones / PowerPoint (con fallback inteligente a Google Slides)
    if any(x in q for x in ["abre powerpoint", "abre microsoft powerpoint", "crea una presentacion", "crea una diapositiva"]):
        import platform
        import subprocess
        sistema = platform.system()
        try:
            if sistema == "Windows":
                ppt_path = buscar_app_windows("POWERPNT.EXE")
                if ppt_path:
                    subprocess.Popen([ppt_path])
                    return "He abierto Microsoft PowerPoint localmente."
            elif sistema == "Darwin":
                subprocess.Popen(["open", "-a", "Microsoft PowerPoint"])
                return "He abierto Microsoft PowerPoint para macOS."
            
            # Fallback a Google Slides
            webbrowser.open("https://slides.new")
            return "No encontré Microsoft PowerPoint en tu equipo, por lo que abrí una presentación nueva en Google Slides en tu navegador."
        except Exception as e:
            return f"Intenté abrir PowerPoint pero ocurrió un error: {e}"

    # 8. Control de Volumen
    if "sube el volumen" in q or "subir volumen" in q:
        pyautogui.press('volumeup', presses=5)
        return "He subido el volumen."
    if "baja el volumen" in q or "bajar volumen" in q:
        pyautogui.press('volumedown', presses=5)
        return "He bajado el volumen."
    if "silencia" in q or "quitar sonido" in q or "silencio" in q:
        pyautogui.press('volumemute')
        return "He cambiado el estado de silencio de los altavoces."
        
    # 9. Control de Ventanas / Escritorio
    if "minimiza las ventanas" in q or "muestra el escritorio" in q or "minimizar todo" in q:
        pyautogui.hotkey('win', 'd')
        return "He minimizado todas las ventanas para mostrar el escritorio."
    if "abre el explorador" in q or "abre carpetas" in q:
        pyautogui.hotkey('win', 'e')
        return "He abierto el Explorador de Archivos de Windows."
    if "bloquea la computadora" in q or "bloquea el equipo" in q or "bloquear pc" in q:
        pyautogui.hotkey('win', 'l')
        return "He bloqueado el equipo de inmediato."
        
    # 10. Hora y Fecha
    if any(x in q for x in ["hora es", "dime la hora", "que hora es"]):
        ahora = datetime.datetime.now().strftime("%I:%M %p")
        return f"Son las {ahora}."
    if any(x in q for x in ["fecha es", "dime la fecha", "que dia es hoy", "fecha de hoy"]):
        dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        ahora = datetime.datetime.now()
        dia_sem = dias[ahora.weekday()]
        mes = meses[ahora.month - 1]
        return f"Hoy es {dia_sem}, {ahora.day} de {mes} de {ahora.year}."
        
    # 11. Crear carpeta de proyecto
    if "crea un proyecto" in q or "crea una carpeta de proyecto" in q:
        import subprocess
        base_dir = os.path.expanduser("~/Desktop/nuevo_proyecto")
        i = 1
        nuevo = base_dir
        while os.path.exists(nuevo):
            nuevo = f"{base_dir}_{i}"
            i += 1
        os.makedirs(nuevo, exist_ok=True)
        with open(os.path.join(nuevo, "inicio.txt"), "w", encoding="utf-8") as f:
            f.write("Proyecto iniciado por ATH1 a petición de voz.")
        try:
            subprocess.Popen(["code", nuevo], shell=True)
        except Exception:
            pass
        return f"He creado la carpeta de proyecto en tu escritorio y la he abierto en VS Code."

# ──────────────────────────────────────────────────────────────────────────────
#  Analizador de Aprendizaje Offline
# ──────────────────────────────────────────────────────────────────────────────
def analizar_aprendizaje_offline(query: str) -> str:
    """
    Analiza de forma offline si el usuario intenta enseñar un dato.
    Ejemplo: 'Aprende que el agua hierve a 100 grados'
    """
    match = re.search(r'(?i)(?:aprende|recuerda|guarda)\s+(?:que\s+)?(.+)', query)
    if match:
        hecho = match.group(1).strip()
        partes = re.split(r'\s+(?:es|significa|representa)\s+', hecho, maxsplit=1)
        if len(partes) == 2:
            keyword = partes[0].strip()
            content = partes[1].strip()
        else:
            keyword = hecho.split()[0] if hecho.split() else "general"
            content = hecho
            
        guardado = guardar_conocimiento_local("personal", keyword, hecho)
        if guardado:
            return f"Hecho aprendido sin conexión: Guardé que {hecho}."
        else:
            return "Ese dato ya lo tenía registrado en mi base de datos local."
    return ""

# ──────────────────────────────────────────────────────────────────────────────
#  Comprobación de Conexión
# ──────────────────────────────────────────────────────────────────────────────
def check_internet() -> bool:
    """Verifica de forma rápida si hay conexión activa a internet."""
    try:
        urllib.request.urlopen("https://8.8.8.8", timeout=2)
        return True
    except Exception:
        return False

# ──────────────────────────────────────────────────────────────────────────────
#  Procesamiento Principal (Gemini / Offline DB + RAG)
# ──────────────────────────────────────────────────────────────────────────────
def procesar_peticion(peticion: str) -> str:
    """
    Recibe la transcripción del usuario, ejecuta acciones o decide respuestas
    apoyándose en Gemini (online) o SQLite RAG (offline).
    """
    if not peticion.strip():
        return "No te he escuchado con claridad. ¿Podrías repetirlo?"
        
    print(f"\n🧠 Procesando petición: «{peticion}»")
    
    # 1. Comprobar si es un comando o acción de sistema directa
    accion_msg = ejecutar_accion_sistema(peticion)
    if accion_msg:
        guardar_historial_chat(peticion, accion_msg)
        return accion_msg
        
    # 2. Comprobar si es un intento de aprendizaje offline directo
    aprendizaje_msg = analizar_aprendizaje_offline(peticion)
    if aprendizaje_msg:
        guardar_historial_chat(peticion, aprendizaje_msg)
        return aprendizaje_msg
        
    # 3. Buscar conocimiento en DB Local para RAG u offline fallback
    contexto_local = buscar_conocimiento_local(peticion)
    historial = obtener_historial_chat(3)
    perfil_usuario = obtener_perfil_usuario()
    
    # 4. Decidir entre Online (Gemini) y Offline (SQLite)
    api_key = os.environ.get("GEMINI_API_KEY")
    hay_internet = check_internet()
    online = hay_internet and api_key is not None
    
    if online:
        print("🌐 Modo ONLINE activo (Conectando con Google Gemini...)")
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            prompt = f"""Eres ATH1, un asistente virtual inteligente y autónomo que controla la PC de MAOAZA.
Tus respuestas deben ser naturales, precisas y concisas porque serán leídas en voz alta.

PERFIL Y PREFERENCIAS DEL USUARIO (Su estilo de pensar, ambiciones, proyectos y metas):
{perfil_usuario if perfil_usuario else "(No hay datos registrados aún. Debes aprender de él.)"}

CONOCIMIENTO LOCAL (Extraído de tu base de datos SQLite por relevancia):
{contexto_local if contexto_local else "(No hay coincidencias en base de datos local)"}

HISTORIAL DE CHAT RECIENTE:
{historial if historial else "(Inicio de conversación)"}

PETICIÓN DEL USUARIO:
"{peticion}"

INSTRUCCIÓN ESPECIAL:
1. Si el usuario te enseña un concepto de programación o dato general, acéptalo de forma amable y añade al final de tu respuesta una línea con este formato exacto para guardarlo en tu conocimiento:
   [LEARN] categoria | palabra_clave | Hecho completo aprendido.
   Ejemplo: "[LEARN] programacion | python decorador | Un decorador es una función que modifica otra función."

2. Si el usuario te habla sobre sus metas, su forma de pensar, sus ambiciones (como crear un Jarvis o su visión de proyectos futuros), o te explica cómo quiere que actúes y pienses, acéptalo y añade al final de tu respuesta una línea con este formato exacto para guardarlo en su perfil:
   [PROFILE] clave_corta | Explicación detallada del rasgo de pensar o ambición del usuario.
   Ejemplo: "[PROFILE] ambicion_jarvis | El usuario desea construir un asistente virtual autónomo tipo Jarvis para colaborar en futuros proyectos."

No uses estas etiquetas a menos que el usuario realmente te esté dando información nueva que requiera ser aprendida o guardada en su perfil.

Respuesta:"""

            response = model.generate_content(prompt)
            texto_respuesta = response.text.strip()
            
            if "[LEARN]" in texto_respuesta or "[PROFILE]" in texto_respuesta:
                lineas = texto_respuesta.split("\n")
                respuesta_limpia = []
                for linea in lineas:
                    if "[LEARN]" in linea:
                        partes = linea.replace("[LEARN]", "").split("|")
                        if len(partes) == 3:
                            cat = partes[0].strip()
                            keyword = partes[1].strip()
                            content = partes[2].strip()
                            guardado = guardar_conocimiento_local(cat, keyword, content)
                            if guardado:
                                print(f"💾 Gemini me ha enseñado un nuevo dato: [{cat}] {keyword} -> {content}")
                    elif "[PROFILE]" in linea:
                        partes = linea.replace("[PROFILE]", "").split("|")
                        if len(partes) == 2:
                            key = partes[0].strip()
                            val = partes[1].strip()
                            guardado = guardar_perfil_usuario(key, val)
                            if guardado:
                                print(f"💾 Perfil actualizado: {key} -> {val}")
                    else:
                        respuesta_limpia.append(linea)
                texto_respuesta = "\n".join(respuesta_limpia).strip()
                
            guardar_historial_chat(peticion, texto_respuesta)
            return texto_respuesta
            
        except Exception as e:
            print(f"⚠️ Error al consultar Gemini: {e}. Activando fallback seguro...")
            
    # ──────────────────────────────────────────────────────────────────────────
    # 🛡️ MODO FALLBACK / OFFLINE SEGURO (Anti-Brechas de Seguridad)
    # ──────────────────────────────────────────────────────────────────────────
    q_min = peticion.lower()
    
    if hay_internet:
        # Caso: Tu PC sí tiene internet pero la API Key o la librería vieja de Gemini fallaron
        respuesta_offline = "Tengo conexión a internet, pero mi canal de comunicación con la Inteligencia Artificial principal falló o la API Key está inactiva. Por seguridad, no puedo procesar comandos web o consultas externas en este momento."
    else:
        # Caso: No hay internet real. Solo respondemos si es una consulta técnica explícita y NO un comando del sistema
        if contexto_local and not any(x in q_min for x in ["abre", "abras", "conéctes", "navegador", "desactívate", "apágate"]):
            respuesta_offline = f"Sin conexión a internet encontré esta información relevante en mi base de datos local:\n{contexto_local}"
        else:
            respuesta_offline = "Actualmente estoy operando en modo local/offline y no dispongo de una instrucción o conocimiento exacto en mi base de datos para ejecutar esa acción."
        
    guardar_historial_chat(peticion, respuesta_offline)
    return respuesta_offline

init_db()

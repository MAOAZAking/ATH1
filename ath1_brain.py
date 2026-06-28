#!/usr/bin/env python3
"""
ATH1 Brain Module (Actualizado con google-genai y control total)
Handles:
- SQLite Database for local memory, preferences, and knowledge base.
- Prepopulating the database with rich programming and system knowledge.
- RAG (Retrieval Augmented Generation) by querying local knowledge.
- Google Gemini API integration (Nuevo SDK).
- Offline rule-based action execution and keyword matching.
- Online/Offline self-learning (extracting and saving facts to the DB).
- Actuator actions (minimizing windows, volume control, locking computer, time/date, VS Code, YouTube).
"""

####################################################################################
# pip install selenium webdriver-manager
import re
import time
import shutil
import urllib.parse
import os
import sys
import sqlite3
import datetime
import webbrowser
import subprocess
import difflib
import platform
import pyautogui
# SDK de Google
from google import genai
from google.genai import types
from dotenv import load_dotenv

################### IMPORTACION DE SELENIUM PARA YOUTUBE EL PRIMER VIDEO ###################
import urllib.parse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

############################################ PRUEBA DE COSA A COSA EN HABALR Y DESPUES MOSTRAR ######
import pyttsx3
engine = pyttsx3.init()
######################################################################################################


DB_NAME = "ath1_knowledge.db"

# Mapeo de comandos: "formas de decirlo" -> "ID_ACCION"
MAPA_COMANDOS = {
    #Comandos de apagado
    "apágate": "ACTION_APAGAR",
    "apaga el sistema": "ACTION_APAGAR",
    "finalizar sesión": "ACTION_APAGAR",
    "descansa": "ACTION_APAGAR",
    "apagate": "ACTION_APAGAR",
    "apagar": "ACTION_APAGAR",
    "finalizar": "ACTION_APAGAR",
    "apagar sistema": "ACTION_APAGAR",
    "apaga los sistemas": "ACTION_APAGAR",
    "apagar los sistemas": "ACTION_APAGAR",
    "descansa": "ACTION_APAGAR",
    "finaliza la session": "ACTION_APAGAR",
    "cierrate": "ACTION_APAGAR",

    "abre youtube": "ACTION_YOUTUBE",
    "pon youtube": "ACTION_YOUTUBE",
    "quiero ver youtube": "ACTION_YOUTUBE",
    
    "abre gmail": "ACTION_GMAIL",
    "revisa mi correo": "ACTION_GMAIL",
    
    "sube el volumen": "ACTION_VOLUMEN_UP",
    "más volumen": "ACTION_VOLUMEN_UP"
}

# ──────────────────────────────────────────────────────────────────────────────
#  Base de Datos (Inicialización y Carga de Conocimiento)
# ──────────────────────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            keyword TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_input TEXT,
            assistant_response TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_profile (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comandos_dinamicos (
            trigger TEXT PRIMARY KEY,
            accion TEXT,
            respuesta TEXT
        )
    """)
    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM knowledge")
    if cursor.fetchone()[0] == 0:
        print("🗄️ Inicializando base de datos local con conocimiento básico de programación...")
        seed_knowledge(conn)
    conn.close()

def seed_knowledge(conn):
    cursor = conn.cursor()
    knowledge_data = [
        ("programming", "python decorador", "Un decorador en Python es una función que recibe otra función como argumento, añade cierta funcionalidad y retorna una nueva función sin modificar la original. Se definen con el símbolo @."),
        ("programming", "python generador", "Los generadores son funciones que usan 'yield' en lugar de 'return'. Devuelven un iterador que produce elementos uno a uno sobre la marcha, lo que optimiza mucho el consumo de memoria en colecciones grandes."),
        ("programming", "python list comprehension", "La compresión de listas es una forma concisa de crear listas en Python. Estructura básica: [expresion for item in iterable if condicion]. Ejemplo: [x**2 for x in range(10) if x%2==0]."),
        ("programming", "python context manager", "Los administradores de contexto controlan la asignación y liberación de recursos usando la palabra clave 'with'. El ejemplo clásico es abrir archivos: 'with open(file) as f:', asegurando su cierre automático."),
        ("programming", "python gil", "El Global Interpreter Lock (GIL) es un mutex en CPython que permite que solo un hilo nativo ejecute bytecode de Python a la vez. Esto limita el paralelismo multi-hilo en tareas intensivas de CPU, pero es seguro para hilos en operaciones I/O."),
        ("programming", "python virtualenv", "Un entorno virtual de Python es una carpeta aislada que contiene su propio ejecutable de Python y sus propias dependencias instaladas con pip, evitando conflictos de librerías globales."),
        ("programming", "python dict", "Un diccionario en Python es una estructura de datos de clave-valor mutable y optimizada. A partir de Python 3.7, preservan el orden de inserción de las llaves."),
        ("programming", "python lambda", "Las funciones lambda son funciones anónimas y rápidas definidas en una sola línea mediante 'lambda argumentos: expresion'."),
        ("programming", "javascript promise", "Una Promesa en JavaScript representa un valor que puede estar disponible ahora, en el futuro o nunca. Tiene tres estados: pendiente (pending), cumplida (fulfilled) o rechazada (rejected)."),
        ("programming", "javascript async await", "Async y Await son azúcares sintácticos construidos sobre Promesas para escribir código asíncrono que se lee como síncrono. La función debe llevar 'async' y las llamadas con promesa llevan 'await'."),
        ("programming", "javascript closure", "Un closure (clausura) es la combinación de una función y el entorno léxico en el que fue declarada, permitiendo que la función acceda a variables de un ámbito externo incluso después de haberse ejecutado."),
        ("programming", "git commit", "Guarda los cambios locales confirmados en el historial del repositorio. Uso común: 'git commit -m \"Mensaje descriptivo\"'."),
        ("programming", "git branch", "Permite listar, crear o borrar ramas. Las ramas sirven para trabajar en funcionalidades aisladas del código principal. Uso: 'git branch <nombre>'."),
        ("programming", "git merge", "Une los historiales de dos ramas distintas, incorporando los cambios de una rama secundaria a la rama activa actual."),
        ("programming", "git rebase", "Reorganiza el historial de commits aplicando tus cambios locales encima de la última versión de otra rama. Mantiene un historial de Git limpio y lineal."),
        ("programming", "git stash", "Guarda temporalmente en una pila de trabajo los cambios pendientes que aún no están listos para un commit, permitiéndote cambiar de rama con el directorio limpio."),
        ("programming", "sql select", "Sentencia para consultar registros de una base de datos. Ejemplo: 'SELECT nombre, email FROM usuarios WHERE edad >= 18;'."),
        ("programming", "sql join", "Operación para combinar filas de dos o más tablas basándose en una columna común. Existen INNER JOIN, LEFT JOIN, RIGHT JOIN y FULL OUTER JOIN."),
        ("programming", "sql index", "Un índice es una estructura de datos física en el motor de base de datos que acelera notablemente las consultas de búsqueda a costa de mayor uso de disco y ralentizar las operaciones de inserción y actualización."),
        ("programming", "docker container", "Un contenedor es una instancia ejecutable de una imagen Docker. Aísla de manera ligera y portable la aplicación y su entorno completo (librerías, variables, sistema operativo base)."),
        ("programming", "dockerfile", "Un Dockerfile es un script de texto con instrucciones consecutivas que Docker utiliza para construir una imagen de contenedor de manera automática."),
        ("programming", "docker compose", "Herramienta que permite definir y correr aplicaciones multi-contenedor mediante un único archivo YAML de configuración."),
        ("programming", "api", "Una Interfaz de Programación de Aplicaciones (API) es un conjunto de reglas y definiciones que permite a un software comunicarse y compartir servicios o datos con otro software."),
        ("programming", "mvc", "Modelo-Vista-Controlador es un patrón de arquitectura que separa los datos de negocio (Modelo), la interfaz de presentación (Vista) y la lógica de control o interacción (Controlador)."),
        ("programming", "oop poo", "La Programación Orientada a Objetos es un paradigma basado en clases y objetos que encapsulan datos (atributos) y comportamiento (métodos). Sus pilares son herencia, polimorfismo, abstracción y encapsulamiento."),
        ("programming", "algoritmo", "Un algoritmo es una secuencia precisa, ordenada y finita de instrucciones o pasos lógicos para resolver un problema o realizar una tarea determinada."),
        ("programming", "big o complejidad", "La notación Big O se usa para describir la complejidad temporal (velocidad) o espacial (memoria) de un algoritmo conforme el tamaño del conjunto de datos de entrada tiende a crecer."),
        ("general", "quien eres", "Soy ATH1, tu asistente de inteligencia artificial inteligente y autónomo. Fui desarrollado por MAOAZA para asistirte en programación, control de sistema y aprendizaje continuo, tanto en línea como de manera local."),
        ("general", "creador maoaza", "MAOAZA es el creador de ATH1. Me configuró con lógica avanzada de Python, base de datos local auto-sostenible y conexión al motor de IA de Google Gemini."),
        ("general", "funcionamiento offline local", "Puedo funcionar offline buscando palabras clave en mi base de datos SQLite y analizando tu voz con el motor local Vosk. Si me enseñas cosas usando frases como 'aprende que X es Y', lo guardaré para responderte después."),
        ("general", "motivacion programacion", "La programación no tiene límites. Como programador puedes crear todo lo que pase por tu mente. El límite es tu imaginación; quita tus límites y construye el futuro."),
    ]
    cursor.executemany("INSERT INTO knowledge (category, keyword, content) VALUES (?, ?, ?)", knowledge_data)
    conn.commit()
    print(f"✅ Se insertaron {len(knowledge_data)} registros de conocimiento inicial.")
    

COMANDOS_ESTANDAR = {
    "apágate": "APAGANDO_SISTEMA",
    "qué hora es": "COMANDO_HORA",
    "abre youtube": "COMANDO_YOUTUBE"
}

def interpretar_intencion(texto_transcrito):
    # Intenta encontrar una coincidencia aproximada (80% de similitud)
    coincidencias = difflib.get_close_matches(texto_transcrito.lower(), COMANDOS_ESTANDAR.keys(), n=1, cutoff=0.8)
    
    if coincidencias:
        comando_detectado = coincidencias[0]
        accion_id = MAPA_COMANDOS[comando_detectado]
        print(f"DEBUG: Interpreté {q} como {comando_detectado} -> Ejecutando: {accion_id}")
        
        # 3. Ejecutar la acción según el ID detectado
        if accion_id == "ACTION_APAGAR":
            return "APAGANDO_SISTEMA"  # El cerebro solo retorna este texto plano
    return None
# ──────────────────────────────────────────────────────────────────────────────
#  Búsqueda de Conocimiento Local y Memoria
# ──────────────────────────────────────────────────────────────────────────────
def buscar_conocimiento_local(query: str) -> str:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    palabras = [p.lower() for p in re.findall(r'\w+', query) if len(p) > 2]
    if not palabras:
        conn.close()
        return ""
    resultados = []
    vistos = set()
    for palabra in palabras:
        if palabra in ["para", "como", "esta", "donde", "quien", "cual", "sobre", "python", "javascript"]:
            continue
        cursor.execute("SELECT category, keyword, content FROM knowledge WHERE keyword LIKE ? OR content LIKE ?", (f"%{palabra}%", f"%{palabra}%"))
        for cat, key, content in cursor.fetchall():
            ref = (key, content)
            if ref not in vistos:
                vistos.add(ref)
                resultados.append(f"- [{cat.upper()}] ({key}): {content}")
    conn.close()
    if resultados:
        return "\n".join(resultados[:4])
    return ""

def guardar_conocimiento_local(category: str, keyword: str, content: str) -> bool:
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM knowledge WHERE keyword = ? AND content = ?", (keyword.lower(), content))
        if cursor.fetchone():
            conn.close()
            return False
        cursor.execute("INSERT INTO knowledge (category, keyword, content) VALUES (?, ?, ?)", (category.lower(), keyword.lower(), content))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"⚠️ Error al guardar conocimiento local: {e}")
        return False

def guardar_historial_chat(user_input: str, assistant_response: str):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO chat_history (user_input, assistant_response) VALUES (?, ?)", (user_input, assistant_response))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️ Error al guardar historial: {e}")

def obtener_historial_chat(limite=3) -> str:
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT user_input, assistant_response FROM chat_history ORDER BY id DESC LIMIT ?", (limite,))
        rows = cursor.fetchall()
        conn.close()
        historial = []
        for user, assistant in reversed(rows):
            historial.append(f"Usuario: {user}\nATH1: {assistant}")
        return "\n".join(historial)
    except Exception as e:
        print(f"⚠️ Error al obtener historial: {e}")
        return ""


def db_get_last_response() -> str:
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT assistant_response FROM chat_history ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else ""
    except Exception as e:
        print(f"⚠️ Error al obtener la última respuesta: {e}")
        return ""


def buscar_app_windows(executable_name: str) -> str:
    path = shutil.which(executable_name)
    if path: return path
    program_files = [
        os.environ.get("ProgramFiles", "C:\\Program Files"),
        os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"),
        os.environ.get("LocalAppData", "")
    ]
    common_subdirs = [
        "Microsoft Office\\root\\Office16", "Microsoft Office\\Office16", "Microsoft Office\\Office15", "Microsoft Office\\root\\Office15",
        "Google\\Chrome\\Application", "Programs\\Microsoft VS Code",
    ]
    for pf in program_files:
        if not pf: continue
        direct_path = os.path.join(pf, executable_name)
        if os.path.exists(direct_path): return direct_path
        for sd_path in common_subdirs:
            full_path = os.path.join(pf, sd_path, executable_name)
            if os.path.exists(full_path): return full_path
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        vscode_user = os.path.join(local_app_data, "Programs", "Microsoft VS Code", executable_name)
        if os.path.exists(vscode_user): return vscode_user
    return ""

def guardar_perfil_usuario(key: str, value: str) -> bool:
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO user_profile (key, value) VALUES (?, ?)", (key.lower().strip(), value.strip()))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"⚠️ Error al guardar perfil de usuario: {e}")
        return False

def obtener_perfil_usuario() -> str:
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM user_profile")
        rows = cursor.fetchall()
        conn.close()
        if rows:
            return "\n".join([f"- {key}: {value}" for key, value in rows])
        return ""
    except Exception as e:
        print(f"⚠️ Error al obtener perfil de usuario: {e}")
        return ""
def guardar_comando_dinamico(trigger: str, accion: str, respuesta: str):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO comandos_dinamicos (trigger, accion, respuesta) VALUES (?, ?, ?)", 
                       (trigger.lower().strip(), accion, respuesta))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"⚠️ Error al guardar comando dinámico: {e}")
        return False

def buscar_y_ejecutar_comando_dinamico(query: str) -> str:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT trigger, accion, respuesta FROM comandos_dinamicos")
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return ""

    # Extraer todos los disparadores conocidos
    triggers = [row[0] for row in rows]
    # Comparar la petición del usuario con los disparadores
    coincidencias = difflib.get_close_matches(query.lower().strip(), triggers, n=1, cutoff=0.6)
    
    if coincidencias:
        match = coincidencias[0]
        # Buscar la fila correspondiente al match
        for r in rows:
            if r[0] == match:
                accion, respuesta = r[1], r[2]
                
                # Ejecutar acción si existe
                if accion and accion != "NINGUNA" and accion.startswith("OPEN_URL|"):
                    url = accion.split("|")[1].strip()
                    webbrowser.open(url)
                
                # Reemplazar variables dinámicas
                if "{hora}" in respuesta:
                    respuesta = respuesta.replace("{hora}", datetime.datetime.now().strftime("%I:%M %p"))
                
                return respuesta
    return ""

# ──────────────────────────────────────────────────────────────────────────────
#  Accion de Selenium para abrir YouTube y reproducir el primer video 100% seguro de que reproduce
# ──────────────────────────────────────────────────────────────────────────────

def buscar_y_reproducir_selenium(termino_busqueda: str):
    """Abre Chrome usando el gestor nativo de Selenium, busca y reproduce el primer video."""
    options = webdriver.ChromeOptions()
    
    # Mantiene la ventana de Chrome abierta tras finalizar la función
    options.add_experimental_option("detach", True)
    
    # Selenium detecta tu Chrome y maneja el driver automáticamente
    driver = webdriver.Chrome(options=options)
    
    # Se añade "/results?search_query=" para que YouTube ejecute la búsqueda correctamente
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(termino_busqueda)}"
    driver.get(url)
    
    try:
        # Espera hasta 10 segundos a que los resultados de búsqueda estén listos
        esperar = WebDriverWait(driver, 10)
        
        # Selector CSS corregido para hacer clic en el título del primer video
        primer_video = esperar.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a#video-title"))
        )
        
        primer_video.click()
        print("DEBUG: Video localizado y reproducido con Selenium Nativo.")
        
    except Exception as e:
        print(f"DEBUG: No se pudo hacer clic en el video. Error: {e}")
# ──────────────────────────────────────────────────────────────────────────────
#  Actuadores de Sistema (Acciones)
# ──────────────────────────────────────────────────────────────────────────────
def ejecutar_accion_sistema(query: str) -> str:
    """
    Analiza comandos directos del sistema de forma flexible y 
    controla aplicaciones abiertas mediante simulación de teclado.
    """
    q = query.lower().strip()
    
    # 1. Buscar la mejor coincidencia en nuestro mapa
    # Obtenemos todas las llaves posibles (las frases conocidas)
    posibles_comandos = list(MAPA_COMANDOS.keys())
    
    # 2. Fuzzy Matching: Buscamos qué llave se parece más a lo que dijo el usuario
    coincidencias = difflib.get_close_matches(q, posibles_comandos, n=1, cutoff=0.7)
    
    if coincidencias:
        comando_detectado = coincidencias[0]
        accion_id = MAPA_COMANDOS[comando_detectado]
        
        print(f"DEBUG: Interpreté '{q}' como '{comando_detectado}' -> Ejecutando: {accion_id}")
        
        # 3. Ejecutar la acción según el ID detectado
        if accion_id == "ACTION_APAGAR":
            return "APAGANDO_SISTEMA"
            
        elif accion_id == "ACTION_YOUTUBE":
            webbrowser.open("https://youtube.com")
            return "Abriendo YouTube para ti."
            
        elif accion_id == "ACTION_GMAIL":
            webbrowser.open("https://mail.google.com")
            return "Abriendo tu correo."
    
    # ─── 0. COMANDO DE SEGURIDAD (Apagado / Interfaz Manual) ───
    if any(x in q for x in ["apágate", "apagate", "apagar", "finalizar", "apagar sistema", "apaga los sistemas", "apagar los sistemas", "descansa", "finaliza la session", "cierrate"]):
        return "APAGANDO_SISTEMA"

    # ─── 0.1 COMANDO DE INTERACCION NORMAL (saludo HOLA) ──
    if any(x in q for x in ["como estas", "cómo estás", "cómo te encuentras", "cómo te sientes", "cómo te va", "cómo te va hoy", "cómo estás", "cómo estás tu", "cómo te encuentras tú", "cómo te encuentras tu", "cómo te sientes tú", "cómo te sientes tu", "cómo te va tú", "cómo te va tu"]):
        return "Yo estoy muy bien gracias a Dios, porque Dios le da la sabiduria a mi programador para que yo este a tope.\n¿Y tu cómo estás?"
    elif any(x in q for x in ["hola", "hi", "hellow"]):
        return "Hola, ¿Cómo estás?"
    
    # ─── 0.1.1 SI EL RETURN DE LA ANTERIOR PETICION FUE: "Hola, ¿Cómo estás?" SI DICE BIEN O ALGO POSITIVO SE RESPONDE ME ALEGRA ──
    if db_get_last_response() == "Hola, ¿Cómo estás?" or db_get_last_response() == "Yo estoy muy bien gracias a Dios, porque Dios le da la sabiduria a mi programador para que yo este a tope.\n¿Y tu cómo estás?":
        if any(x in q for x in ["bien", "muy bien", "excelente", "estoy bien", "estoy muy bien", "estoy excelente", "gracias a dios", "gracias a Dios", "gracias adios"]):
            if any(x in q for x in ["y tu", "y tú", "y usted", "y ustéd", "y vos", "y tu?", "y tú?", "y usted?", "y ustéd?", "y vos?", "y vos?", "como estas", "cómo estás", "cómo te encuentras", "cómo te sientes", "cómo te va", "cómo te va hoy"]):
                return "Me alegra escuchar eso. Yo estoy muy bien gracias a Dios, porque Dios le da la sabiduria a mi programador para que yo este a tope.\n¿En qué te puedo ayudar en este momento?"
            else:
                return "Me alegra escuchar eso. ¿En qué puedo ayudarte hoy?"
        elif any(x in q for x in ["mal", "no estoy bien", "triste", "cansado", "estresado"]):
            if any(x in q for x in ["y tu", "y tú", "y usted", "y ustéd", "y vos", "y tu?", "y tú?", "y usted?", "y ustéd?", "y vos?", "y vos?", "como estas", "cómo estás", "cómo te encuentras", "cómo te sientes", "cómo te va", "cómo te va hoy"]):
                return "Lamento escuchar eso. Yo en cambio estoy muy bien gracias a Dios porque le da la sabiduria a mi programador para que yo este a tope. ¿Quieres que te ayude con algo?"
            else:
                return "Lamento escuchar eso. Si quieres, puedo intentar animarte o ayudarte con algo."
            
    # ─── 0.1.1.1 SI EL USUARIO DICE QUE ESTA MAL, LE OFRESCO MI AYUDA Y RESPUESTAS PARA CADA RESPUESTA ANTE MI PREGUNTA DE SI LE AYUDO ──
    if db_get_last_response() == "Lamento escuchar eso. Yo en cambio estoy muy bien gracias a Dios porque le da la sabiduria a mi programador para que yo este a tope. ¿Quieres que te ayude con algo?" or db_get_last_response() == "Lamento escuchar eso. Si quieres, puedo intentar animarte o ayudarte con algo.":
        if any(x in q for x in ["sí", "si", "claro", "por favor", "ayúdame", "ayudame", "quiero ayuda", "quiero que me ayudes", "si quiero", "sí quiero", "si quiero que me ayudes", "sí quiero que me ayudes", "si gracias", "si gracias", "sí gracias", "de acuerdo", "vale", "ok", "okey", "okay", "animame", "anímame", "quiero que me animes", "quiero que me animes", "intentalo"]):
            return "A mi lo que más me gusta hacer y lo que me ayuda, cuando estoy triste o cuando me siento mal o necesito ayuda es orar a Dios; ¿Te gustaria que ore por ti y despues te ponga musica cristiana relajante?"
        elif any(x in q for x in ["no", "no gracias"]):
            return "Vale, entiendo; recuerda que aqui sigo para ti, si quieres hablar o necesitas ayuda con algo, solo llamame por mi nombre (ATH1)."
    
    # ─── 0.1.1.1.1 SI EL USUARIO DICE QUE QUIERE MI AYUDA, DEPENDIENDO DE LO QUE DIGA SI ORAMOS Y PONEMOS MUSICA O SI SOLO ORAMOS O SI SOLO PONEMOS MUSICA──
    if db_get_last_response() == "A mi lo que más me gusta hacer y lo que me ayuda, cuando estoy triste o cuando me siento mal o necesito ayuda es orar a Dios; ¿Te gustaria que ore por ti y despues te ponga musica cristiana relajante?":
        if any(x in q for x in ["sí", "si", "claro", "por favor", "ayúdame", "ayudame", "quiero ayuda", "quiero que me ayudes", "si quiero", "sí quiero", "si quiero que me ayudes", "sí quiero que me ayudes", "si gracias", "si gracias", "sí gracias", "de acuerdo", "vale", "ok", "okey", "okay", "animame", "anímame", "quiero que me animes", "quiero que me animes", "intentalo", "ora por mi", "ora por mí", "quiero que ores por mi", "quiero que ores por mi", "quiero que ores por mi y me pongas musica", "quiero que ores por mi y me pongas música", "quiero que ores por mi y me pongas música cristiana relajante", "quiero que ores por mi y me pongas musica cristiana relajante"]):
            #return "Perfecto, vamos a orar juntos y luego te pondré música cristiana relajante.\n\nSi quieres repite esta oración conmigo:\nAmado Dios,\nHoy me acerco a ti con el corazón pesado.\nMe siento triste, aburrido y sin fuerzas.\nSiento un vacío que no puedo llenar.\nTe pido que entres en mi vida hoy.\n\nLlévate esta tristeza que me apaga.\nCambia mi aburrimiento por un nuevo propósito.\nRenueva mis pensamientos y dale paz a mi mente.\nTrae consuelo a los días que se sienten oscuros.\n\nAyúdame a recordar que esto es temporal.\nAbraza mi alma con tu amor incondicional.\nRegálame la esperanza que hoy no encuentro.\nEn ti confío mi bienestar y mi futuro.\n\nAmén y Amén.\n\nAhora, voy a poner música cristiana relajante para ti.", pyautogui.sleep(3),  webbrowser.open("https://www.youtube.com/watch?v=aLn_86Ry894&list=RDaLn_86Ry894&start_radio=1"), pyautogui.sleep(5), pyautogui.press('f')
            return "Perfecto, vamos a orar juntos y luego te pondré música cristiana relajante.\n\nSi quieres repite esta oración conmigo:\nAmado Dios,\nHoy me acerco a ti con el corazón pesado.\nMe siento triste, aburrido y sin fuerzas.\nSiento un vacío que no puedo llenar.\nTe pido que entres en mi vida hoy.\n\nLlévate esta tristeza que me apaga.\nCambia mi aburrimiento por un nuevo propósito.\nRenueva mis pensamientos y dale paz a mi mente.\nTrae consuelo a los días que se sienten oscuros.\n\nAyúdame a recordar que esto es temporal.\nAbraza mi alma con tu amor incondicional.\nRegálame la esperanza que hoy no encuentro.\nEn ti confío mi bienestar y mi futuro.\n\nAmén y Amén.\n\nAhora, voy a poner música cristiana relajante para ti." or engine.runAndWait() or webbrowser.open("https://www.youtube.com/watch?v=aLn_86Ry894&list=RDaLn_86Ry894&start_radio=1")
            pyautogui.sleep(5) or pyautogui.press('f')
        elif any(x in q for x in ["solo orar", "sólo orar" "solo quiero orar", "solo oración", "solo quiero oración", "solo oracion", "solo quiero oracion", "orar", "quiero orar", "quiero oración", "quiero oracion"]):
            return "Perfecto, vamos a orar juntos\n\nSi quieres repite esta oración conmigo:\nAmado Dios,\nHoy me acerco a ti con el corazón pesado.\nMe siento triste, aburrido y sin fuerzas.\nSiento un vacío que no puedo llenar.\nTe pido que entres en mi vida hoy.\n\nLlévate esta tristeza que me apaga.\nCambia mi aburrimiento por un nuevo propósito.\nRenueva mis pensamientos y dale paz a mi mente.\nTrae consuelo a los días que se sienten oscuros.\n\nAyúdame a recordar que esto es temporal.\nAbraza mi alma con tu amor incondicional.\nRegálame la esperanza que hoy no encuentro.\nEn ti confío mi bienestar y mi futuro.\nAmén y Amén.\n\nEspero que estes mejor y recuerda que en lo que te pueda ayudar aqui estoy solo llamame por mi nombre (ATH1)."
        elif any(x in q for x in ["solo música", "sólo música", "solo quiero música", "solo quiero musica", "solo quiero que me pongas música", "solo quiero que me pongas musica", "quiero música", "quiero musica", "quiero que me pongas música", "quiero que me pongas musica", "musica", "musica", "pon música", "pon musica"]):
            return "Perfecto, estoy poniendo la música cristiana relajante para ti.", webbrowser.open("https://www.youtube.com/watch?v=aLn_86Ry894&list=RDaLn_86Ry894&start_radio=1"), pyautogui.press('f')
        elif any(x in q for x in ["no", "no gracias"]):
            return "Vale, entiendo; recuerda que aqui sigo para ti, si quieres hablar o necesitas ayuda con algo, solo llamame por mi nombre (ATH1)."
        
    # ─── 0.1.2 SI EL RETURN DE LA ANTERIOR PETICION FUE: "Hola, ¿Cómo estás?" SI DICE BIEN O ALGO POSITIVO SE RESPONDE ME ALEGRA ──
    if db_get_last_response() == "Hola, ¿Cómo estás?" or db_get_last_response() == "Yo estoy muy bien gracias a Dios, porque Dios le da la sabiduria a mi programador para que yo este a tope.\n¿Y tu cómo estás?":
        if any(x in q for x in ["bien", "muy bien", "excelente", "estoy bien", "estoy muy bien", "estoy excelente", "gracias a dios", "gracias a Dios", "gracias adios"]):
            return "Me alegra escuchar eso. ¿En qué puedo ayudarte hoy?"
        elif any(x in q for x in ["mal", "no estoy bien", "triste", "cansado", "estresado"]):
            return "Lamento escuchar eso. Si quieres, puedo intentar animarte o ayudarte con algo."
    
    
    # ─── 0.2 COMANDO DE INTERACCION NORMAL (Si preguntan ¿CÓMO ESTÁS?) ──
    # ─── 0.2.1 SI EL RETURN DE LA ANTERIOR PETICION FUE: "Me alegra escuchar eso. ¿En qué puedo ayudarte hoy?" o "Lamento escuchar eso. Si quieres, puedo intentar animarte o ayudarte con algo." le pregunta en que le puede ayudar, pero si no dijo ninguna de estas pregunta al ausuario ¿cómo estás? ──
    if db_get_last_response() == "Me alegra escuchar eso. ¿En qué puedo ayudarte hoy?" or db_get_last_response() == "Lamento escuchar eso. Si quieres, puedo intentar animarte o ayudarte con algo.":
        if any(x in q for x in ["Cómo estás", "como estas", "cómo estas", "como estás", "cómo te encuentras", "cómo te sientes", "cómo te va", "cómo te va hoy", "cómo estás", "cómo estás tu", "cómo te encuentras tú", "cómo te encuentras tu", "cómo te sientes tú", "cómo te sientes tu", "cómo te va tú", "cómo te va tu"]):
            return "Yo estoy muy bien gracias a Dios, porque Dios le da la sabiduria a mi programador para que yo este a tope.\n¿En qué te puedo ayudar en este momento?"
    elif any(x in q for x in ["Cómo estás", "como estas", "cómo estas", "como estás", "cómo te encuentras", "cómo te sientes", "cómo te va", "cómo te va hoy", "cómo estás", "cómo estás tu", "cómo te encuentras tú", "cómo te encuentras tu", "cómo te sientes tú", "cómo te sientes tu", "cómo te va tú", "cómo te va tu"]):
        return "Yo estoy muy bien gracias a Dios, porque Dios le da la sabiduria a mi programador para que yo este a tope.\n¿Y tu cómo estás?"
    
    if any(x in q for x in ["Cómo estás", "como estas", "cómo estas", "como estás", "cómo te encuentras", "cómo te sientes", "cómo te va", "cómo te va hoy", "cómo estás", "cómo estás tu", "cómo te encuentras tú", "cómo te encuentras tu", "cómo te sientes tú", "cómo te sientes tu", "cómo te va tú", "cómo te va tu"]):
        return "Yo estoy muy bien gracias a Dios, porque Dios le da la sabiduria a mi programador para que yo este a tope.\n¿Y tu cómo estás?"
    
    # ─── 0.3 COMANDO DE INTERACCION SOBRE SU CREADOR ──
    if any(x in q for x in ["quién te creó", "quien te creó", "quien te creo", "quién te creo", "quien te programó", "quién te programó", "quién te programo", "quien te programo", "quién te desarrolló", "quien te desarrolló", "quien te desarrollo", "quién te desarrollo", "quién te hizo", "quien te hizo", "quién te diseño", "quien te diseño", "quien te diseño", "quién te diseño", "tu creador", "tu programador", "tu desarrollador", "tu diseñador", "quién te creo", "quien te creo", "quién te programo", "quien te programo", "quién te desarrollo", "quien te desarrollo", "quién te hizo", "quien te hizo", "quién te diseño", "quien te diseño"]):
            return "Fui desarrollado y programado en Python por MAOAZA king."
    # ─── 0.3 COMANDO DE INTERACCION ¿QUIEN ERES? ── 
    if any(x in q for x in ["quién eres", "quien eres", "que eres", "cual es tu nombre", "cual es tu nombre", "quien eres tu", "quién eres tu", "quien eres tú", "quién eres tú", "qué eres", "que eres tu", "qué eres tu", "qué eres tú", "que eres tú"]):
            return "Soy ATH1, el asistente virtual de inteligencia artificial autónomo de MAOAZA king."
    
    # ─── 1 Comando de entrada de texto ──    
    if any(x in q for x in ["quiero escribir", "escrir algo", "escribirte algo", "escribir texto"]):
        import tkinter as tk
        from tkinter import simpledialog
        root = tk.Tk()
        root.attributes("-topmost", True)
        root.withdraw()
        user_text = simpledialog.askstring("ATH1 - Interfaz Manual", "Escribe tu orden para ATH1:")
        root.destroy()
        if user_text:
            return procesar_peticion(user_text)
        else:
            return "Se canceló la entrada de texto."
    
    # ─── 1. CONTROL TOTAL DE YOUTUBE Y REPRODUCTOR ───
    if "youtube" in q or "yutub" in q:
        if any(x in q for x in ["busca", "reproduce", "pon", "abre"]):
            termino = q
            
            # Lista limpia sin espacios manuales. \b se encarga de aislar la palabra de forma nativa.
            palabras_eliminar = [
                r"en youtube", r"en yutub", r"youtube", r"yutub", 
                r"reproduce", r"busca", r"ponme", r"pon", r"tú y", 
                r"entra el primer video", r"abre", r"y", r"de"
            ]
            
            for palabra in palabras_eliminar:
                # \b detecta los límites de la palabra automáticamente, sin importar si hay espacios o inicio de cadena
                termino = re.sub(rf'\b{palabra}\b', '', termino, flags=re.IGNORECASE)
            
            # Elimina espacios múltiples internos y limpia extremos
            termino = " ".join(termino.split()).strip()
            
            if not termino:
                termino = "musica cristiana"
                
            print(f"DEBUG: Término final limpio enviado a YouTube: '{termino}'")
            print("⏳ Se está abriendo YouTube, por favor espera...")
            buscar_y_reproducir_selenium(termino)
            return f"He buscado '{termino}' en YouTube e intenté reproducir el primer video."
        
        # Caso B: Abrir la página limpia
        return "He abierto la página principal de YouTube." if webbrowser.open("https://www.youtube.com") else ""

    # ─── 2. COMANDOS DE REPRODUCCIÓN EN VIVO ───
    if any(x in q for x in ["entra al primer video", "reproduce el primer video", "abre el primer video"]):
        pyautogui.press('tab')   # Asegura el foco en el contenedor de videos
        pyautogui.press('enter') # Ejecuta la entrada al video
        return "Intentando reproducir el primer video en pantalla."
    
    if any(x in q for x in ["pantalla completa", "maximiza el video", "grande el video", "maximiza la pantalla", "grande la pantalla"]):
        pyautogui.press('f')
        return "Activando pantalla completa."
        
    if any(x in q for x in ["subtítulos", "subtitulo", "activa subtitulos", "desactiva subtitulos", "subtitulos del video", "subtitulos", "subtítulos del video", "subtítulos"]):
        pyautogui.press('c')
        return "Alternando subtítulos del video."
        
    if any(x in q for x in ["pausa", "paúsalo", "reproduce el video", "continúa", "reanuda el video", "pausar el video", "reanudar el video", "pausa el video", "pausar", "reanudar", "despausar", "despausa", "pausalo", "reanudarlo"]):
        pyautogui.press('space')
        return "He pausado o reanudado el reproductor."

    # ─── 3. GOOGLE Y NAVEGADOR ───
    if any(x in q for x in ["abre google", "abre el navegador", "abre chrome", "abre google chrome", "abras el navegador", "abrir google", "abras google"]):
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

    # ─── 4. BLOC DE NOTAS ───
    if any(x in q for x in ["abre bloc de notas", "abre notepad", "abrir bloc de notas", "abre el bloc de notas", "abre notas"]):
        sistema = platform.system()
        try:
            if sistema == "Windows":
                subprocess.Popen(["notepad.exe"])
            elif sistema == "Darwin":
                subprocess.Popen(["open", "-a", "TextEdit"])
            else:
                for editor in ["gedit", "mousepad", "kate", "nano"]:
                    if shutil.which(editor):
                        subprocess.Popen([editor])
                        break
                else:
                    return "No logré encontrar un editor de notas instalado en este sistema Linux."
            return "Entendido, estoy abriendo el Bloc de Notas."
        except Exception as e:
            return f"Intenté abrir el Bloc de Notas pero ocurrió un error: {e}"

    # ─── 5. VISUAL STUDIO CODE ───
    if any(x in q for x in ["abre vscode", "abre visual studio code", "abre vsc", "abre el editor"]):
        sistema = platform.system()
        try:
            if sistema == "Windows":
                vscode_path = buscar_app_windows("Code.exe")
                if vscode_path:
                    subprocess.Popen([vscode_path])
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

    # ─── 6. WORD Y DOCUMENTOS ───
    if any(x in q for x in ["abre word", "abre microsoft word", "escribe una carta", "escribamos una carta", "crear un documento", "escribir una carta"]):
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
            webbrowser.open("https://docs.new")
            return "Analicé tu dispositivo y no encontré Microsoft Word instalado localmente, así que abrí un documento nuevo de Google Docs en tu navegador. Listo, ya tengo abierto donde escribiremos la carta. Dime qué quieres redactar."
        except Exception as e:
            return f"Intenté abrir el procesador de textos pero ocurrió un error: {e}"

    # ─── 7. EXCEL Y HOJAS DE CÁLCULO ───
    if any(x in q for x in ["abre excel", "abre microsoft excel", "crea una tabla", "abre una hoja de calculo", "abre planilla"]):
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
            webbrowser.open("https://sheets.new")
            return "No encontré Microsoft Excel instalado en tu equipo, así que abrí una hoja de cálculo nueva en Google Sheets en tu navegador."
        except Exception as e:
            return f"Intenté abrir la hoja de cálculo pero ocurrió un error: {e}"

    # ─── 8. POWERPOINT Y PRESENTACIONES ───
    if any(x in q for x in ["abre powerpoint", "abre microsoft powerpoint", "crea una presentacion", "crea una diapositiva"]):
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
            webbrowser.open("https://slides.new")
            return "No encontré Microsoft PowerPoint en tu equipo, por lo que abrí una presentación nueva en Google Slides en tu navegador."
        except Exception as e:
            return f"Intenté abrir PowerPoint pero ocurrió un error: {e}"

    # ─── 9. SISTEMA: VOLUMEN, VENTANAS, BLOQUEO, HORA, FECHA ───
    if "sube el volumen" in q or "subir volumen" in q:
        pyautogui.press('volumeup', presses=5)
        return "He subido el volumen."
    if "baja el volumen" in q or "bajar volumen" in q:
        pyautogui.press('volumedown', presses=5)
        return "He bajado el volumen."
    if "silencia" in q or "quitar sonido" in q or "silencio" in q:
        pyautogui.press('volumemute')
        return "He cambiado el estado de silencio de los altavoces."
    if "minimiza las ventanas" in q or "muestra el escritorio" in q or "minimizar todo" in q:
        pyautogui.hotkey('win', 'd')
        return "He minimizado todas las ventanas para mostrar el escritorio."
    if "abre el explorador" in q or "abre carpetas" in q:
        pyautogui.hotkey('win', 'e')
        return "He abierto el Explorador de Archivos de Windows."
    if "bloquea la computadora" in q or "bloquea el equipo" in q or "bloquear pc" in q:
        pyautogui.hotkey('win', 'l')
        return "He bloqueado el equipo de inmediato."
        
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
        
    # ─── 10. CREAR PROYECTO ───
    if "crea un proyecto" in q or "crea una carpeta de proyecto" in q:
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

    return None

def analizar_aprendizaje_offline(query: str) -> str:
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

def check_internet() -> bool:
    try:
        urllib.request.urlopen("https://8.8.8.8", timeout=2)
        return True
    except Exception:
        return False

# ──────────────────────────────────────────────────────────────────────────────
#  Procesamiento Principal (Gemini / Offline DB + RAG)
# ──────────────────────────────────────────────────────────────────────────────
def procesar_peticion(peticion: str, nivel_acceso: str = "admin") -> str:
    if not peticion.strip():
        return "No te he escuchado con claridad. ¿Podrías repetirlo?"
        
    print(f"\n🧠 Procesando petición: «{peticion}» (Nivel: {nivel_acceso.upper()})")
    
    q_min = peticion.lower()

    # ─── RESTRICCIÓN DE MODO INVITADO ───
    if nivel_acceso == "invitado":
        comandos_basicos = ["hora", "fecha", "creador", "quien eres", "quién eres", "apágate", "apagate", "apagar", "apagar los sistemas", "hora es", "fecha es", "pagaste", "dime la hora", "dime la fecha", "que hora es", "que dia es hoy", "fecha de hoy"]
        
        # Si la orden no incluye alguna de estas palabras, se rechaza inmediatamente
        if not any(x in q_min for x in comandos_basicos):
            respuesta_restringida = "Lo siento. Actualmente solo estoy autorizado para indicarte la hora, la fecha o apagarme."
            guardar_historial_chat(peticion, respuesta_restringida)
            return respuesta_restringida
            
        # Si preguntó por su creador, responde en seco
        if any(x in q_min for x in ["creador", "quien eres", "quién eres", "que eres", "quién te creó", "quien te creó", "quien te creo"]):
            return "Fui desarrollado y programado en Python por MAOAZA king. Soy su asistente virtual y motor analítico personal."

    # ─── FLUJO NORMAL PARA EL ADMINISTRADOR (MAOAZA king) ───
    # A partir de aquí, el código fluye normal porque pasó el filtro o es admin
    
    # ─── 1. BUSCAR EN MEMORIA DINÁMICA (Prioridad Alta) ───
    # Si lo aprendiste, es la prioridad #1.
    comando_aprendido = buscar_y_ejecutar_comando_dinamico(peticion)
    if comando_aprendido:
        guardar_historial_chat(peticion, comando_aprendido)
        return comando_aprendido

    # ─── 2. COMANDOS HARDCODED (Prioridad Media) ───
    # Si no es un comando aprendido, revisa si es una orden de sistema (Apagar, etc)
    accion_msg = ejecutar_accion_sistema(peticion)
    if accion_msg:
        guardar_historial_chat(peticion, accion_msg)
        return accion_msg
        
    aprendizaje_msg = analizar_aprendizaje_offline(peticion)
    if aprendizaje_msg:
        guardar_historial_chat(peticion, aprendizaje_msg)
        return aprendizaje_msg
        
    contexto_local = buscar_conocimiento_local(peticion)
    historial = obtener_historial_chat(3)
    perfil_usuario = obtener_perfil_usuario()
    
    api_key = os.environ.get("GEMINI_API_KEY")
    hay_internet = check_internet()
    online = hay_internet and api_key is not None
    
    if online:
        print("🌐 Modo ONLINE activo (Conectando vía google-genai con Búsqueda en Internet...)")
        try:
            client = genai.Client(api_key=api_key)
            
            prompt = f"""Eres ATH1, el asistente virtual autónomo de MAOAZA king. Tienes acceso a internet.

CONOCIMIENTO LOCAL DEL USUARIO:
{contexto_local}

HISTORIAL DE CHAT:
{historial}

PETICIÓN DEL USUARIO:
"{peticion}"

REGLAS DE ACTUACIÓN (Súper Importante):
1. Si el usuario te pide abrir una página, aplicación o servicio que tú no conoces (ej. "Abre Gmail"), DEBES BUSCAR LA URL en internet. 
   Tu respuesta DEBE incluir obligatoriamente esta etiqueta exacta:
   [ACTION] OPEN_URL | https://la-url-que-encontraste.com
   Y luego dices algo como "Abriendo el sitio para ti."

2. Si el usuario te está enseñando una nueva forma de responder o actuar, DEBES extraer ese conocimiento y devolver esta etiqueta:
   [LEARN_CMD] frase disparadora | ACCION | Respuesta con variables como {{hora}}
   Ejemplo: Si te dice "pregunta: 'hora con segundos' respuesta: 'los segundos pasan rápido, son las (time)'"
   Tú debes devolver: [LEARN_CMD] hora con segundos | NINGUNA | Los segundos pasan muy rápido, por esto te doy la hora solo con minutos. Actualmente son las {{hora}}.

3. Si el usuario te enseña un concepto general, usa:
   [LEARN] categoria | palabra_clave | Hecho aprendido.

4. Si el usuario te habla sobre sus metas o perfil, usa:
   [PROFILE] clave_corta | Explicación del rasgo.

No uses estas etiquetas a menos que debas ejecutar una acción o aprender algo. ¡Usa la herramienta de búsqueda de Google si no sabes algo!

Respuesta:"""

            # Activamos la búsqueda en internet de Gemini
            from google.genai import types # Asegúrate de que esto se importe arriba en el archivo
            
            response = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[{"google_search": {}}] 
                )
            )
            texto_respuesta = response.text.strip()
            respuesta_limpia = []
            
            # --- MOTOR DE INTERPRETACIÓN Y APRENDIZAJE TOTAL ---
            for linea in texto_respuesta.split("\n"):
                if "[LEARN_CMD]" in linea:
                    partes = linea.replace("[LEARN_CMD]", "").split("|")
                    if len(partes) >= 3:
                        trigger = partes[0].strip()
                        accion = partes[1].strip()
                        respuesta_txt = partes[2].strip()
                        guardar_comando_dinamico(trigger, accion, respuesta_txt)
                        print(f"💾 ¡NUEVA HABILIDAD APRENDIDA! Cuando escuche '{trigger}', haré '{accion}'.")
                
                elif "[ACTION]" in linea:
                    accion = linea.replace("[ACTION]", "").strip()
                    if accion.startswith("OPEN_URL"):
                        url = accion.split("|")[1].strip()
                        import webbrowser
                        webbrowser.open(url)
                        print(f"🌍 Ejecutando acción autónoma: Abriendo {url}")
                
                elif "[LEARN]" in linea:
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
            
            texto_final = "\n".join(respuesta_limpia).strip()
            guardar_historial_chat(peticion, texto_final)
            return texto_final
            
        except Exception as e:
            print(f"⚠️ Error en canal GenAI: {e}. Desviando a contingencia...")
            
    # ──────────────────────────────────────────────────────────────────────────
    # 🛡️ MODO FALLBACK / OFFLINE SEGURO (Anti-Brechas de Seguridad)
    # ──────────────────────────────────────────────────────────────────────────
    q_min = peticion.lower()
    
    if hay_internet:
        respuesta_offline = "No he entendio tu solicitud, intenta de nuevo o con otras palabras mas claras."
    else:
        if contexto_local and not any(x in q_min for x in ["abre", "abras", "conéctes", "navegador", "desactívate", "apágate"]):
            respuesta_offline = f"Sin conexión a internet encontré esta información relevante en mi base de datos local:\n{contexto_local}"
        else:
            respuesta_offline = "Actualmente estoy operando en modo offline y no dispongo de una instrucción o conocimiento exacto en mi base de datos para ejecutar esa acción."
        
    guardar_historial_chat(peticion, respuesta_offline)
    return respuesta_offline

init_db()
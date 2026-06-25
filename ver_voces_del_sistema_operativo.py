import pyttsx3

engine = pyttsx3.init()
voices = engine.getProperty("voices")

for i, v in enumerate(voices):
    print(f"\n--- VOZ {i} ---")
    print("Nombre:", v.name)
    print("ID:", v.id)
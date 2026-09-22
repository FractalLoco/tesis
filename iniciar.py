import os
import subprocess
import sys
import time
import webbrowser

RAIZ = os.path.dirname(os.path.abspath(__file__))
DEPS = ["fastapi", "uvicorn[standard]", "psycopg[binary]", "python-dotenv"]
PUERTO = 8000

def asegurar_dependencias():
    try:
        import fastapi, uvicorn, psycopg, dotenv
    except ImportError:
        print(">> Instalando dependencias (solo la primera vez)...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", *DEPS])

def iniciar_servidor():
    # Un solo proceso: FastAPI sirve la API y también el frontend estático
    # (ver backend/main.py), tanto en local como en el servidor de despliegue.
    print(f">> Servidor -> http://localhost:{PUERTO}")
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app",
         "--host", "0.0.0.0", "--port", str(PUERTO)],
        cwd=RAIZ,
    )

def main():
    print("=" * 48)
    print(" Optimizador SQL con Machine Learning")
    print("=" * 48)
    asegurar_dependencias()
    servidor = iniciar_servidor()
    time.sleep(2)
    url = f"http://localhost:{PUERTO}"
    try:
        webbrowser.open(url)
    except Exception:
        pass
    print(f"\nListo. Abre {url} en tu navegador.")
    print("Para detener todo: Ctrl + C\n")
    try:
        servidor.wait()
    except KeyboardInterrupt:
        print("\nDeteniendo...")
        servidor.terminate()

if __name__ == "__main__":
    main()

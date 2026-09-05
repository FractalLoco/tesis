import functools
import os
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

RAIZ = os.path.dirname(os.path.abspath(__file__))
DEPS = ["fastapi", "uvicorn[standard]", "psycopg[binary]", "python-dotenv"]

def asegurar_dependencias():
    try:
        import fastapi, uvicorn, psycopg, dotenv              
    except ImportError:
        print(">> Instalando dependencias (solo la primera vez)...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", *DEPS])

def iniciar_backend():
    print(">> Backend  -> http://localhost:8000")
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app",
         "--host", "127.0.0.1", "--port", "8000"],
        cwd=RAIZ,
    )

def servir_frontend():
    handler = functools.partial(SimpleHTTPRequestHandler,
                                directory=os.path.join(RAIZ, "frontend"))
    servidor = ThreadingHTTPServer(("127.0.0.1", 5500), handler)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    print(">> Frontend -> http://localhost:5500")
    return servidor

def main():
    print("=" * 48)
    print(" Optimizador SQL con Machine Learning")
    print("=" * 48)
    asegurar_dependencias()
    backend = iniciar_backend()
    servir_frontend()
    time.sleep(2)
    url = "http://localhost:5500"
    try:
        webbrowser.open(url)
    except Exception:
        pass
    print(f"\nListo. Abre {url} en tu navegador.")
    print("Para detener todo: Ctrl + C\n")
    try:
        backend.wait()
    except KeyboardInterrupt:
        print("\nDeteniendo...")
        backend.terminate()

if __name__ == "__main__":
    main()

"""
Entry point for the bundled .exe.
Starts the Flask server, opens the browser, and waits for the user to close.
"""

import logging
import os
import sys
import threading
import time
import webbrowser

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)
log = logging.getLogger(__name__)

PORT = 5050
URL = f"http://localhost:{PORT}"


def open_browser():
    time.sleep(1.5)
    log.info("Abrindo navegador em %s", URL)
    webbrowser.open(URL)


def main():
    print("=" * 56)
    print("  Calculadora de Aprovacao de Desconto")
    print("=" * 56)
    print()
    print(f"  O app vai abrir no navegador em {URL}")
    print("  Mantenha esta janela aberta enquanto estiver usando.")
    print("  Para sair, feche esta janela ou pressione Ctrl+C.")
    print()

    from app import start_app

    threading.Thread(target=open_browser, daemon=True).start()

    try:
        start_app(port=PORT)
    except KeyboardInterrupt:
        print("\nEncerrando...")
        sys.exit(0)


if __name__ == "__main__":
    main()

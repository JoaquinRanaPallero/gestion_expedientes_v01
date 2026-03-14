"""Punto de entrada de la aplicacion de Gestion de Expedientes."""

import sys
import os
import platform

# DPI awareness para Windows - evita que se vea borroso en pantallas de alta resolucion
if platform.system() == "Windows":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

# Asegurar que el directorio del script este en el path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database as db
from ui.app import App


def main():
    db.init_db()
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()

"""Importa expedientes desde un archivo CSV con columnas: caratula, tipo de proceso."""

import csv
import sys

import database as db
from models import Expediente


def importar(ruta_csv: str) -> None:
    db.init_db()
    count = 0
    with open(ruta_csv, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)  # saltar encabezado
        print(f"Columnas detectadas: {header}")
        for i, row in enumerate(reader, start=2):
            if len(row) < 2:
                print(f"  Fila {i}: saltada (faltan columnas)")
                continue
            caratula = row[0].strip()
            tipo_proceso = row[1].strip()
            if not caratula:
                print(f"  Fila {i}: saltada (caratula vacia)")
                continue
            exp = Expediente(caratula=caratula, tipo_proceso=tipo_proceso)
            db.crear_expediente(exp)
            count += 1
    print(f"\nImportacion completa: {count} expedientes creados.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python importar_csv.py <archivo.csv>")
        sys.exit(1)
    importar(sys.argv[1])

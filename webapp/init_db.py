import sys
from db import inicializar_db, ErrorConexionBD
import time

def init():
    max_retries = 5
    for i in range(max_retries):
        try:
            print("Intentando inicializar la base de datos...")
            inicializar_db()
            print("Base de datos inicializada correctamente.")
            return
        except ErrorConexionBD as e:
            print(f"Error conectando a BD: {e}")
            if i < max_retries - 1:
                print(f"Reintentando en 3 segundos... ({i+1}/{max_retries})")
                time.sleep(3)
            else:
                print("No se pudo conectar a la BD despues de varios intentos.")
                sys.exit(1)
        except Exception as e:
            print(f"Error inesperado inicializando BD: {e}")
            sys.exit(1)

if __name__ == '__main__':
    init()

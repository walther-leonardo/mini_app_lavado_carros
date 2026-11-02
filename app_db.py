import duckdb

# Pega aquí el token exacto que copiaste de la página de MotherDuck
MOTHERDUCK_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6IndhbHRoZXJsZW9uYXJkb0BnbWFpbC5jb20iLCJtZFJlZ2lvbiI6ImF3cy11cy13ZXN0LTIiLCJzZXNzaW9uIjoid2FsdGhlcmxlb25hcmRvLmdtYWlsLmNvbSIsInBhdCI6ImVhZFNNUjIzY0VuUElUUjFLRW5ldXVvYS1NWnhKZWRPWTJwakNiczBRcEEiLCJ1c2VySWQiOiJhMzI5OWZlYi00MDVlLTRlYmEtODc0Yi1hYzY4NzNmZDMwNTAiLCJpc3MiOiJtZF9wYXQiLCJyZWFkT25seSI6ZmFsc2UsInRva2VuVHlwZSI6InJlYWRfd3JpdGUiLCJpYXQiOjE3Nzk3NDUwMjN9.MXW1EOLJjc3fDOlItbQURKdn_DhZ6aUp1UZ5Ei6HC8M"

def conectar_bd():
    """
    Abre y devuelve una conexión a la base de datos MotherDuck en la nube.
    """
    try:
        # La cadena 'md:' le indica a DuckDB que debe conectarse a los servidores de MotherDuck
        cadena_conexion = f"md:?motherduck_token={MOTHERDUCK_TOKEN}"
        return duckdb.connect(cadena_conexion)
    
    except Exception as e:
        print(f"Error crítico al conectar con la nube (MotherDuck): {e}")
        raise


"""
import os
import sys
import duckdb

# Nombre del archivo físico que contendrá nuestra base de datos local
DB_NAME = "sap_master.db"

def obtener_ruta_base():
    if getattr(sys, 'frozen', False):
        # Si el programa está compilado (.exe), usamos la ruta del ejecutable
        return os.path.dirname(sys.executable)
    else:
        # Si estamos ejecutando desde VS Code (.py), usamos la ruta del script
        return os.path.dirname(os.path.abspath(__file__))

def get_db_path():
    ruta_base = obtener_ruta_base()
    return os.path.join(ruta_base, DB_NAME)

def conectar_bd():
    ruta_bd = get_db_path()
    
    try:
        # Retorna el objeto de conexión
        # Nota para el futuro: Si pasas a MotherDuck, aquí cambiarás la ruta 
        # por f"md:?motherduck_token={TU_TOKEN}"
        return duckdb.connect(ruta_bd)
    
    except Exception as e:
        print(f"Error crítico al conectar con la base de datos: {e}")
        # Propagamos el error para que la UI pueda mostrar un mensaje si falla
        raise

"""

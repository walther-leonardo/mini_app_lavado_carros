import pandas as pd
import app_db
import os

def actualizar_placas(ruta_adddata):
    """
    Actualiza completamente la tabla VLCADDDATA (Placas).

    IMPORTANTE:
    - Conserva placas duplicadas reales de SAP.
    - El ID único vehículo sigue siendo PRIMARY KEY.
    - La tabla se recarga completamente cada vez.
    """

    try:
        con = app_db.conectar_bd()

        print("Procesando VLCADDDATA (Formato Excel)...")

        # ==========================================
        # LEER EXCEL
        # ==========================================
        df_adddata = pd.read_excel(
            ruta_adddata,
            dtype=str
        )

        # Limpiar nombres de columnas
        df_adddata.columns = df_adddata.columns.str.strip()

        # ==========================================
        # FILTRAR SOLO PLACAS
        # ==========================================
        df_placas = df_adddata[
            df_adddata['Cualificador'] == 'PLAC'
        ].copy()

        # ==========================================
        # SELECCIONAR COLUMNAS NECESARIAS
        # ==========================================
        df_placas = df_placas[
            ['ID único vehículo', 'ParticulCualificador']
        ].rename(
            columns={
                'ParticulCualificador': 'Placa'
            }
        )

        # ==========================================
        # LIMPIEZA DE DATOS
        # ==========================================
        df_placas['ID único vehículo'] = (
            df_placas['ID único vehículo']
            .astype(str)
            .str.strip()
        )

        df_placas['Placa'] = (
            df_placas['Placa']
            .astype(str)
            .str.strip()
            .str.upper()
        )

        # Eliminar vacíos
        df_placas = df_placas[
            df_placas['Placa'].notna()
        ]

        df_placas = df_placas[
            df_placas['Placa'] != ''
        ]

        # ==========================================
        # CREAR TABLA SI NO EXISTE
        # ==========================================
        con.execute("""
            CREATE TABLE IF NOT EXISTS maestro_placas (
                "ID único vehículo" VARCHAR PRIMARY KEY,
                "Placa" VARCHAR
            )
        """)

        # ==========================================
        # RECARGA COMPLETA
        # ==========================================
        con.execute("""
            DELETE FROM maestro_placas
        """)

        # ==========================================
        # INSERTAR DATA NUEVA
        # ==========================================
        con.register(
            'temp_placas',
            df_placas
        )

        con.execute("""
            INSERT INTO maestro_placas
            SELECT * FROM temp_placas
        """)

        con.close()

        print(
            f"VLCADDDATA actualizada correctamente. "
            f"Registros cargados: {len(df_placas)}"
        )

        return True

    except Exception as e:

        print(f"Error en VLCADDDATA: {e}")

        return False

def actualizar_vin(ruta_vehicle):
    """Actualiza la tabla VLCVEHICLE (VIN) de forma independiente."""
    try:
        con = app_db.conectar_bd()
        print("Procesando VLCVEHICLE (Formato Excel)...")
        df_vehicle = pd.read_excel(ruta_vehicle, dtype=str)
        df_vehicle.columns = df_vehicle.columns.str.strip()
        
        df_vin = df_vehicle[['ID único vehículo', 'NºIdentVehículo']].rename(
            columns={'NºIdentVehículo': 'VIN'}
        ).drop_duplicates(subset=['ID único vehículo'], keep='last')
        
        con.execute("""
            CREATE TABLE IF NOT EXISTS maestro_vin (
                "ID único vehículo" VARCHAR PRIMARY KEY,
                "VIN" VARCHAR
            )
        """)
        con.register('temp_vin', df_vin)
        con.execute("""
            INSERT INTO maestro_vin SELECT * FROM temp_vin
            ON CONFLICT ("ID único vehículo") DO UPDATE SET "VIN" = EXCLUDED."VIN"
        """)
        con.close()
        return True
    except Exception as e:
        print(f"Error en VLCVEHICLE: {e}")
        return False

def actualizar_ordenes(ruta_crm):
    """
    MODIFICADO: Incluye dinámicamente la columna 'ID de categoría.1' 
    manteniendo la limpieza del esquema de SAP.
    """
    try:
        # Añadida la columna duplicada mapeada por pandas (.1)
        cols_importantes = [
            'Tipo de operación comercial', 'ID de operación', 'Valor bruto', 'Valor neto',
            'Val.prod.esperado', 'Impte.impto.total', 'Valor neto sin porte', 'ID único objeto',
            'Clase de operación', 'Fe.contabilización', 'Descrip.operación', 'Creado por',
            'Modificado por', 'Esquema', 'Canal de distribución', 'Sector',
            'Organización ventas', 'Solicitante', 'Dest.mercancías', 'Destinatario factura',
            'Responsable pago', 'Empleado responsable', 'Persona de contacto', 'Tipo de cambio',
            'ID de categoría', 'ID de categoría.1' 
        ]

        print("Procesando CRMS4D_SERV_H (Mapeando ID de categoría.1)...")
        df_crm = pd.read_excel(ruta_crm, dtype=str)
        df_crm.columns = df_crm.columns.str.strip()
        
        # Vaciamos columnas no listadas
        for col in df_crm.columns:
            if col not in cols_importantes:
                df_crm[col] = None

        df_crm['Descrip.operación'] = df_crm['Descrip.operación'].fillna('')
        df_crm['Placa_Extraida'] = df_crm['Descrip.operación'].astype(str).str.strip().str[:6].str.upper()
        df_crm = df_crm.drop_duplicates(subset=['ID de operación'], keep='last')
        
        con = app_db.conectar_bd()
        columnas_sql = []
        update_set_sql = []
        
        for col in df_crm.columns:
            if col == 'ID de operación':
                columnas_sql.append(f'"{col}" VARCHAR PRIMARY KEY')
            else:
                columnas_sql.append(f'"{col}" VARCHAR')
                update_set_sql.append(f'"{col}" = EXCLUDED."{col}"')
        
        query_tabla = f'CREATE TABLE IF NOT EXISTS ordenes_servicio ({", ".join(columnas_sql)})'
        con.execute(query_tabla)
        
        con.register('temp_crm', df_crm)
        query_upsert = f"""
            INSERT INTO ordenes_servicio SELECT * FROM temp_crm
            ON CONFLICT ("ID de operación") DO UPDATE SET {", ".join(update_set_sql)}
        """
        con.execute(query_upsert)
        con.close()
        return True
        
    except Exception as e:
        print(f"Error en CRMS4D_SERV_H: {e}")
        return False

def procesar_logica_usuario(ruta_excel, fecha_inicio, fecha_fin):
    """
    MODIFICADO: Ejecuta el cruce priorizando por fecha más reciente 
    Y desempatando a favor de registros con valor en 'ID de categoría.1'.
    """
    try:
        print("Iniciando procesamiento con nueva regla de prioridad...")
        df_usuario = pd.read_excel(ruta_excel, dtype=str)
        
        if 'PLACA' in df_usuario.columns:
            df_usuario['PLACA'] = df_usuario['PLACA'].astype(str).str.strip().str.upper()
            df_usuario['PLACA'] = df_usuario['PLACA'].replace(['NAN', 'NAT', 'NONE', ''], None)
        else:
            print("Error: No se encontró la columna 'PLACA'.")
            return False

        f_ini = pd.to_datetime(fecha_inicio, dayfirst=True).strftime('%Y-%m-%d')
        f_fin = pd.to_datetime(fecha_fin, dayfirst=True).strftime('%Y-%m-%d')

        con = app_db.conectar_bd()
        con.register('temp_usuario', df_usuario)
        
        # MODIFICACIÓN EN EL ORDER BY DE LA WINDOW FUNCTION (ROW_NUMBER):
        # 1. Ordena por fecha descendente (más recientes primero)
        # 2. Usa un CASE WHEN para otorgar prioridad alta (1) si "ID de categoría.1" NO es nulo ni vacío.
        # 3. Usa el ID de operación descendente como último criterio de desempate.
        query = f"""
            WITH Vehiculo_VIN AS (
                SELECT
                    p."Placa",
                    MIN(v."VIN") AS "VIN"
                FROM maestro_placas p
                INNER JOIN maestro_vin v
                    ON p."ID único vehículo" = v."ID único vehículo"
                GROUP BY p."Placa"
            ),
            Ordenes_Validas AS (
                SELECT 
                    "Placa_Extraida",
                    "ID de operación" AS ORDEN,
                    CAST(SUBSTRING("Fe.contabilización", 1, 10) AS DATE) AS Fecha2,
                    ROW_NUMBER() OVER (
                        PARTITION BY "Placa_Extraida" 
                        ORDER BY 
                            CAST(SUBSTRING("Fe.contabilización", 1, 10) AS DATE) DESC,
                            CASE 
                                WHEN "ID de categoría.1" IS NOT NULL AND "ID de categoría.1" != '' THEN 1 
                                ELSE 2 
                            END ASC,
                            "ID de operación" DESC
                    ) as rn
                FROM ordenes_servicio
                WHERE "Tipo de operación comercial" != 'BUS2000112'
                  AND "Tipo de operación comercial" IS NOT NULL
                  AND "Placa_Extraida" IS NOT NULL
                  AND LEFT("ID de operación", 1) IN ('6', '7')
                  AND CAST(SUBSTRING("Fe.contabilización", 1, 10) AS DATE) BETWEEN CAST('{f_ini}' AS DATE) AND CAST('{f_fin}' AS DATE)
            ),
            Ultima_Orden AS (
                SELECT "Placa_Extraida", ORDEN, Fecha2 
                FROM Ordenes_Validas 
                WHERE rn = 1
            )
            SELECT 
                u.*,
                v."VIN",
                o.ORDEN,
                o.Fecha2
            FROM temp_usuario u
            LEFT JOIN Vehiculo_VIN v ON u.PLACA = v."Placa"
            LEFT JOIN Ultima_Orden o ON u.PLACA = o."Placa_Extraida"
        """
        
        df_resultado = con.execute(query).df()
        con.close()
        
        nombre_base, extension = os.path.splitext(ruta_excel)
        ruta_salida = f"{nombre_base}_RESULTADO{extension}"
        df_resultado.to_excel(ruta_salida, index=False)
        
        return ruta_salida
        
    except Exception as e:
        print(f"Error procesando la lógica del usuario: {e}")
        return False

def validar_placas_usuario(ruta_excel):
    """
    Valida si las placas del usuario:
    - EXISTEN
    - ESTÁN DUPLICADAS
    - FALTAN CREAR

    Genera un nuevo Excel enriquecido.
    """

    try:

        print("Iniciando validación de placas...")

        # ==========================================
        # LEER EXCEL USUARIO
        # ==========================================
        df_usuario = pd.read_excel(
            ruta_excel,
            dtype=str
        )

        # ==========================================
        # DETECTAR COLUMNA PLACA
        # ==========================================
        columnas_originales = list(df_usuario.columns)

        columnas_normalizadas = {
            col.lower().strip(): col
            for col in columnas_originales
        }

        columna_placa = None

        for posible in ['placa', 'placas']:

            if posible in columnas_normalizadas:

                columna_placa = columnas_normalizadas[posible]
                break

        if not columna_placa:

            print("No se encontró columna PLACA.")
            return False

        # ==========================================
        # LIMPIAR PLACAS USUARIO
        # ==========================================
        df_usuario[columna_placa] = (
            df_usuario[columna_placa]
            .astype(str)
            .str.strip()
            .str.upper()
        )

        # ==========================================
        # CONECTAR DUCKDB
        # ==========================================
        con = app_db.conectar_bd()

        # ==========================================
        # TRAER CONTEO DE PLACAS
        # ==========================================
        query = """
            SELECT
                "Placa",
                COUNT(*) AS cantidad
            FROM maestro_placas
            GROUP BY "Placa"
        """

        df_maestro = con.execute(query).df()

        con.close()

        # ==========================================
        # CONVERTIR A DICCIONARIO
        # ==========================================
        dict_placas = dict(
            zip(
                df_maestro['Placa'],
                df_maestro['cantidad']
            )
        )

        # ==========================================
        # FUNCIÓN VALIDACIÓN
        # ==========================================
        def validar_placa(valor):

            if pd.isna(valor):
                return "VACÍO"

            valor = str(valor).strip().upper()

            if valor == "":
                return "VACÍO"

            cantidad = dict_placas.get(valor, 0)

            if cantidad == 0:
                return "FALTA CREAR"

            elif cantidad == 1:
                return "EXISTE"

            else:
                return "DUPLICADO"

        # ==========================================
        # CREAR COLUMNA RESULTADO
        # ==========================================
        df_usuario['ESTADO_PLACA'] = (
            df_usuario[columna_placa]
            .apply(validar_placa)
        )

        # ==========================================
        # GUARDAR RESULTADO
        # ==========================================
        nombre_base, extension = os.path.splitext(
            ruta_excel
        )

        ruta_salida = (
            f"{nombre_base}_VALIDADO{extension}"
        )

        df_usuario.to_excel(
            ruta_salida,
            index=False
        )

        print(
            f"Validación completada: {ruta_salida}"
        )

        return ruta_salida

    except Exception as e:

        print(
            f"Error validando placas: {e}"
        )

        return False


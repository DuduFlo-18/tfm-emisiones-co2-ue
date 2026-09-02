"""
TFM — Emisiones de CO2 de vehiculos nuevos matriculados en la UE
================================================================
Script 01 — Adquisicion de las fuentes de datos (apartado "a" de Resultados)

Fuente : Agencia Europea de Medio Ambiente (EEA) — Discodata
         https://discodata.eea.europa.eu/sql
Dataset: Monitoring of CO2 emissions from passenger cars — Reg. (UE) 2019/631
Tabla  : [CO2Emission].[latest].[co2cars_2024Fv30]  (ano 2024, version Final)
Volumen: 10.782.314 registros x 43 variables (verificado el 19/08/2026)

Proceso: (1) detecta el tamano de pagina admitido por la API, (2) descarga los
agregados de poblacion calculados en el servidor y (3) descarga el detalle a
nivel de vehiculo, por bloques, en formato Parquet.

Uso
---
    python 01_extraccion.py                 # muestra del 10 % (~1.078.000 filas)
    python 01_extraccion.py --fraccion 5    # muestra del 20 % (~2.156.000 filas)
    python 01_extraccion.py --modo completo # los 10,7 M de registros

Eduardo Flores Carralero — Master en Big Data y Data Science, IMF Smart Education
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# CONFIGURACION
# ---------------------------------------------------------------------------

BASE_URL = "https://discodata.eea.europa.eu/sql"
ESQUEMA = "[CO2Emission].[latest]"

# Version FINAL unicamente. Se excluye 2025 (provisional) y 2020 (anterior a la
# implantacion plena del WLTP, no comparable).
TABLAS = {
    2021: "co2cars_2021Fv24",
    2022: "co2cars_2022Fv26",
    2023: "co2cars_2023Fv28",
    2024: "co2cars_2024Fv30",
}
ANIO_NUCLEO = 2024

DIR_DATOS = Path(__file__).resolve().parent.parent / "datos"
DIR_CRUDO = DIR_DATOS / "crudo"
DIR_AGREGADOS = DIR_DATOS / "agregados"

# Se descartan los identificadores administrativos (VFN, TAN, MMS, T, Va, Ve,
# RLFI, Version_file): no aportan capacidad predictiva y multiplican el volumen
# de transferencia. Los nombres con espacios y parentesis exigen corchetes.
COLUMNAS = [
    "ID",                 # identificador unico del registro
    "MS",                 # Member State: pais de matriculacion
    "Mp",                 # pool de fabricantes
    "Mh",                 # fabricante segun homologacion
    "Man",                # nombre del fabricante
    "Mk",                 # marca comercial
    "Cn",                 # denominacion comercial (modelo)
    "Ct",                 # categoria del vehiculo (M1, N1...)
    "Cr",                 # categoria en el registro
    "[M (kg)]",           # masa en orden de marcha
    "Mt",                 # masa de ensayo WLTP
    "[Ewltp (g/km)]",     # VARIABLE OBJETIVO: emisiones CO2 bajo WLTP
    "[Enedc (g/km)]",     # emisiones bajo metodologia NEDC
    "[W (mm)]",           # distancia entre ejes
    "[At1 (mm)]",         # ancho de via eje 1
    "[At2 (mm)]",         # ancho de via eje 2
    "Ft",                 # tipo de combustible
    "Fm",                 # modo de alimentacion (M/H/P/B...)
    "[Ec (cm3)]",         # cilindrada
    "[Ep (KW)]",          # potencia del motor
    "[Z (Wh/km)]",        # consumo de energia electrica
    "IT",                 # tecnologia innovadora aplicada
    "[Erwltp (g/km)]",    # reduccion de emisiones por eco-innovacion
    "Fc",                 # consumo de combustible
    "Ech",                # autonomia electrica declarada
    "Dr",                 # fecha de matriculacion
    "Year",               # ano
    "Status",             # F = Final / P = Provisional
]

TAMANOS_CANDIDATOS = [100_000, 50_000, 20_000, 10_000, 5_000, 1_000, 500, 100]

# Muestreo pseudoaleatorio reproducible. Se hashea el ID con MD5 en lugar de
# aplicar ID % n: el modulo directo es un muestreo sistematico y quedaria
# sesgado si los identificadores se hubieran asignado por bloques de pais,
# fabricante o lote de carga. El hash reparte de forma uniforme y sigue siendo
# determinista, por lo que la misma consulta devuelve siempre las mismas filas.
FILTRO_MUESTRA = (
    "WHERE ABS(CHECKSUM(HASHBYTES('MD5', CAST(ID AS NVARCHAR(20))))) % {n} = 0"
)

REINTENTOS = 4
ESPERA_REINTENTO = 5  # segundos


# ---------------------------------------------------------------------------
# ACCESO A LA API
# ---------------------------------------------------------------------------

def consulta_api(sql: str, pagina: int = 1, filas: int = 1_000,
                 timeout: int = 600) -> list[dict]:
    """Lanza una consulta SQL contra Discodata y devuelve las filas como
    lista de diccionarios. Reintenta ante fallos transitorios."""
    parametros = {
        "query": sql,
        "p": pagina,
        "nrOfHits": filas,
        "mail": "null",
        "schema": "null",
    }

    ultimo_error: Exception | None = None
    for intento in range(1, REINTENTOS + 1):
        try:
            respuesta = requests.get(BASE_URL, params=parametros, timeout=timeout)
            respuesta.raise_for_status()
            datos = respuesta.json()

            # En caso de exito la API devuelve una lista. Un dict puede ser el
            # envoltorio {"results": [...]} o un error.
            if isinstance(datos, dict):
                if "results" in datos:
                    return datos["results"]
                raise RuntimeError(f"La API devolvio un error: {datos}")
            return datos

        except Exception as exc:  # noqa: BLE001 - se reintenta cualquier fallo
            ultimo_error = exc
            if intento < REINTENTOS:
                print(f"    aviso: intento {intento}/{REINTENTOS} fallido "
                      f"({type(exc).__name__}). Reintentando en "
                      f"{ESPERA_REINTENTO}s...")
                time.sleep(ESPERA_REINTENTO)

    raise RuntimeError(f"La consulta fallo tras {REINTENTOS} intentos: "
                       f"{ultimo_error}")


def detectar_tamano_pagina(tabla: str) -> int:
    """Devuelve el mayor tamano de pagina que admite la API, probando de mayor
    a menor. Determina cuantas peticiones exige la descarga completa."""
    print("\n[1/3] Detectando el tamano maximo de pagina admitido por la API...")
    for tamano in TAMANOS_CANDIDATOS:
        sql = f"SELECT TOP {tamano} ID FROM {ESQUEMA}.[{tabla}]"
        try:
            filas = consulta_api(sql, pagina=1, filas=tamano, timeout=300)
            if len(filas) >= min(tamano, 100):
                print(f"      OK -> la API admite {tamano:,} filas por peticion "
                      f"(devolvio {len(filas):,}).".replace(",", "."))
                return tamano
            print(f"      {tamano:,} solicitadas pero solo devolvio "
                  f"{len(filas):,}; probando un tamano menor..."
                  .replace(",", "."))
        except Exception as exc:  # noqa: BLE001
            print(f"      {tamano:,} no admitido ({type(exc).__name__}); "
                  f"probando un tamano menor...".replace(",", "."))

    raise RuntimeError("No se pudo determinar un tamano de pagina valido.")


# ---------------------------------------------------------------------------
# AGREGADOS DE POBLACION (GROUP BY ejecutado en el servidor)
# ---------------------------------------------------------------------------

def descargar_agregados() -> None:
    """Descarga tablas agregadas mediante GROUP BY en origen. Recorren los
    10,7 M de registros pero devuelven pocos cientos de filas, y sirven de
    referencia para validar despues la representatividad de la muestra."""
    print("\n[2/3] Descargando agregados de poblacion (GROUP BY en servidor)...")
    DIR_AGREGADOS.mkdir(parents=True, exist_ok=True)

    # --- 1. Resumen por ano y tipo de combustible (serie de tendencia) ------
    partes = []
    for anio, tabla in TABLAS.items():
        print(f"      - resumen {anio} por tipo de combustible...")
        sql = f"""
            SELECT
                {anio} AS Anio,
                Ft AS Combustible,
                COUNT(*) AS Vehiculos,
                AVG(CAST([Ewltp (g/km)] AS FLOAT)) AS CO2_medio_wltp,
                AVG(CAST([M (kg)]       AS FLOAT)) AS Masa_media_kg,
                AVG(CAST([Ep (KW)]      AS FLOAT)) AS Potencia_media_kw,
                AVG(CAST([Ec (cm3)]     AS FLOAT)) AS Cilindrada_media_cm3,
                MIN(CAST([Ewltp (g/km)] AS FLOAT)) AS CO2_minimo,
                MAX(CAST([Ewltp (g/km)] AS FLOAT)) AS CO2_maximo
            FROM {ESQUEMA}.[{tabla}]
            GROUP BY Ft
        """
        partes.append(pd.DataFrame(consulta_api(sql, filas=10_000)))

    tendencia = pd.concat(partes, ignore_index=True)
    tendencia.to_csv(DIR_AGREGADOS / "tendencia_anio_combustible.csv",
                     index=False, encoding="utf-8")
    print(f"      -> guardado: tendencia_anio_combustible.csv "
          f"({len(tendencia)} filas)")

    # --- 2. Resumen por pais (ano nucleo) ----------------------------------
    print(f"      - resumen {ANIO_NUCLEO} por pais de matriculacion...")
    sql_pais = f"""
        SELECT
            MS AS Pais,
            COUNT(*) AS Vehiculos,
            AVG(CAST([Ewltp (g/km)] AS FLOAT)) AS CO2_medio_wltp,
            AVG(CAST([M (kg)]       AS FLOAT)) AS Masa_media_kg,
            AVG(CAST([Ep (KW)]      AS FLOAT)) AS Potencia_media_kw
        FROM {ESQUEMA}.[{TABLAS[ANIO_NUCLEO]}]
        GROUP BY MS
    """
    por_pais = pd.DataFrame(consulta_api(sql_pais, filas=10_000))
    por_pais.to_csv(DIR_AGREGADOS / "resumen_por_pais.csv",
                    index=False, encoding="utf-8")
    print(f"      -> guardado: resumen_por_pais.csv ({len(por_pais)} filas)")

    # --- 3. Resumen por marca (ano nucleo) ---------------------------------
    print(f"      - resumen {ANIO_NUCLEO} por marca...")
    sql_marca = f"""
        SELECT
            Mk AS Marca,
            COUNT(*) AS Vehiculos,
            AVG(CAST([Ewltp (g/km)] AS FLOAT)) AS CO2_medio_wltp,
            AVG(CAST([M (kg)]       AS FLOAT)) AS Masa_media_kg,
            AVG(CAST([Ep (KW)]      AS FLOAT)) AS Potencia_media_kw
        FROM {ESQUEMA}.[{TABLAS[ANIO_NUCLEO]}]
        GROUP BY Mk
    """
    por_marca = pd.DataFrame(consulta_api(sql_marca, filas=10_000))
    por_marca.to_csv(DIR_AGREGADOS / "resumen_por_marca.csv",
                     index=False, encoding="utf-8")
    print(f"      -> guardado: resumen_por_marca.csv ({len(por_marca)} filas)")

    # --- 4. Estadisticos globales (referencia para validar la muestra) -----
    print(f"      - estadisticos globales {ANIO_NUCLEO}...")
    sql_global = f"""
        SELECT
            COUNT(*) AS Total_vehiculos,
            COUNT([Ewltp (g/km)]) AS Con_ewltp,
            AVG(CAST([Ewltp (g/km)] AS FLOAT)) AS CO2_medio_wltp,
            AVG(CAST([M (kg)]       AS FLOAT)) AS Masa_media_kg,
            AVG(CAST([Ep (KW)]      AS FLOAT)) AS Potencia_media_kw,
            AVG(CAST([Ec (cm3)]     AS FLOAT)) AS Cilindrada_media_cm3
        FROM {ESQUEMA}.[{TABLAS[ANIO_NUCLEO]}]
    """
    globales = pd.DataFrame(consulta_api(sql_global, filas=10))
    globales.to_csv(DIR_AGREGADOS / "estadisticos_globales.csv",
                    index=False, encoding="utf-8")
    print("      -> guardado: estadisticos_globales.csv")
    print("\n      Estadisticos de poblacion del ano nucleo:")
    print(globales.to_string(index=False))


# ---------------------------------------------------------------------------
# DATOS A NIVEL DE VEHICULO
# ---------------------------------------------------------------------------

def descargar_detalle(tabla: str, tamano_pagina: int, modo: str,
                      fraccion: int) -> Path:
    """Descarga los registros individuales y los guarda en Parquet por bloques.

    modo="completo" descarga los 10,7 M de registros; modo="muestra" aplica el
    filtro hash de FILTRO_MUESTRA y toma aproximadamente 1 de cada `fraccion`.
    Verificado el 24/08/2026 con fraccion=10: 1.076.533 filas, un 0,16 % por
    debajo del decimo exacto, desviacion coherente con un reparto uniforme.
    """
    print(f"\n[3/3] Descargando detalle a nivel de vehiculo (modo: {modo})...")
    DIR_CRUDO.mkdir(parents=True, exist_ok=True)

    columnas_sql = ", ".join(COLUMNAS)
    filtro = "" if modo == "completo" else FILTRO_MUESTRA.format(n=fraccion)
    sql = f"SELECT {columnas_sql} FROM {ESQUEMA}.[{tabla}] {filtro}"

    if modo == "muestra":
        print(f"      Muestreo pseudoaleatorio reproducible (hash MD5 sobre "
              f"el ID):")
        print(f"      aproximadamente 1 de cada {fraccion} registros "
              f"(~{10_782_314 // fraccion:,} filas estimadas)."
              .replace(",", "."))

    pagina = 1
    total_filas = 0
    bloque: list[dict] = []
    n_parte = 0
    ficheros: list[Path] = []
    inicio = time.time()

    while True:
        filas = consulta_api(sql, pagina=pagina, filas=tamano_pagina)
        if not filas:
            break

        bloque.extend(filas)
        total_filas += len(filas)

        transcurrido = time.time() - inicio
        print(f"      pagina {pagina:>5} | {len(filas):>7,} filas | "
              f"acumulado {total_filas:>10,} | {transcurrido/60:5.1f} min"
              .replace(",", "."))

        # Volcado a disco cada ~500.000 filas para no agotar la RAM
        if len(bloque) >= 500_000:
            n_parte += 1
            ficheros.append(_guardar_parte(bloque, n_parte))
            bloque = []

        # Ultima pagina: la API devolvio menos filas de las pedidas
        if len(filas) < tamano_pagina:
            break

        pagina += 1

    if bloque:
        n_parte += 1
        ficheros.append(_guardar_parte(bloque, n_parte))

    print("\n      Consolidando bloques en un unico fichero Parquet...")
    completo = pd.concat([pd.read_parquet(f) for f in ficheros],
                         ignore_index=True)

    sufijo = "completo" if modo == "completo" else f"muestra1de{fraccion}"
    destino = DIR_CRUDO / f"co2cars_{ANIO_NUCLEO}_{sufijo}.parquet"
    completo.to_parquet(destino, index=False, compression="snappy")

    for fichero in ficheros:
        fichero.unlink()

    tamano_mb = destino.stat().st_size / (1024 * 1024)
    print(f"      -> guardado: {destino.name}")
    print(f"         {len(completo):,} filas x {len(completo.columns)} columnas "
          f"| {tamano_mb:.1f} MB".replace(",", "."))

    return destino


def _guardar_parte(bloque: list[dict], n_parte: int) -> Path:
    """Vuelca un bloque de filas a un fichero Parquet temporal."""
    ruta = DIR_CRUDO / f"_parte_{n_parte:03d}.parquet"
    pd.DataFrame(bloque).to_parquet(ruta, index=False, compression="snappy")
    print(f"      >> volcado temporal: {ruta.name} ({len(bloque):,} filas)"
          .replace(",", "."))
    return ruta


# ---------------------------------------------------------------------------
# TRAZABILIDAD
# ---------------------------------------------------------------------------

def guardar_metadatos(tabla: str, tamano_pagina: int, modo: str,
                      fraccion: int, fichero: Path) -> None:
    """Registra fecha, origen y parametros exactos de la descarga, de modo que
    el proceso sea reproducible y trazable si la EEA republica los datos."""
    metadatos = {
        "fecha_descarga_utc": datetime.now(timezone.utc).isoformat(),
        "fuente": "Agencia Europea de Medio Ambiente (EEA) — Discodata",
        "endpoint": BASE_URL,
        "esquema": ESQUEMA,
        "tabla_origen": tabla,
        "anio_nucleo": ANIO_NUCLEO,
        "estado_dato": "Final (Status = F)",
        "reglamento": "Reglamento (UE) 2019/631",
        "modo_descarga": modo,
        "fraccion_muestreo": fraccion if modo == "muestra" else None,
        "metodo_muestreo": (
            "pseudoaleatorio reproducible mediante hash MD5 del identificador"
            if modo == "muestra" else None
        ),
        "filtro_sql_muestreo": (
            FILTRO_MUESTRA.format(n=fraccion) if modo == "muestra" else None
        ),
        "tamano_pagina_api": tamano_pagina,
        "columnas_solicitadas": COLUMNAS,
        "fichero_generado": fichero.name,
        "tablas_serie_temporal": TABLAS,
    }
    ruta = DIR_DATOS / "metadatos_extraccion.json"
    ruta.write_text(json.dumps(metadatos, indent=2, ensure_ascii=False),
                    encoding="utf-8")
    print(f"\n      -> trazabilidad guardada en {ruta.name}")


# ---------------------------------------------------------------------------
# PUNTO DE ENTRADA
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Adquisicion de datos EEA — emisiones CO2 turismos UE")
    parser.add_argument("--modo", choices=["muestra", "completo"],
                        default="muestra",
                        help="'muestra' (por defecto) o 'completo' (10,7 M filas)")
    parser.add_argument("--fraccion", type=int, default=10,
                        help="en modo muestra, toma 1 de cada N registros "
                             "(por defecto 10 -> ~1.078.000 filas)")
    parser.add_argument("--saltar-agregados", action="store_true",
                        help="no volver a descargar los agregados")
    args = parser.parse_args()

    print("=" * 74)
    print(" TFM — ADQUISICION DE DATOS: emisiones de CO2 de turismos nuevos (UE)")
    print(" Fuente: Agencia Europea de Medio Ambiente (EEA) — Discodata")
    print("=" * 74)

    DIR_DATOS.mkdir(parents=True, exist_ok=True)
    tabla = TABLAS[ANIO_NUCLEO]

    try:
        tamano_pagina = detectar_tamano_pagina(tabla)

        if args.modo == "completo":
            peticiones = 10_782_314 // tamano_pagina + 1
            print(f"\n      AVISO: el modo completo requiere unas "
                  f"{peticiones:,} peticiones.".replace(",", "."))
            time.sleep(5)

        if not args.saltar_agregados:
            descargar_agregados()

        fichero = descargar_detalle(tabla, tamano_pagina, args.modo,
                                    args.fraccion)
        guardar_metadatos(tabla, tamano_pagina, args.modo, args.fraccion,
                          fichero)

        print("\n" + "=" * 74)
        print(" EXTRACCION COMPLETADA")
        print(f" Datos en: {DIR_DATOS}")
        print("=" * 74)
        return 0

    except KeyboardInterrupt:
        print("\n\n      Proceso cancelado por el usuario.")
        return 130
    except Exception as exc:  # noqa: BLE001
        print(f"\n\n      ERROR: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

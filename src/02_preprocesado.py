"""
TFM — Emisiones de CO2 de vehiculos nuevos matriculados en la UE
================================================================
Script 02 — PREPROCESADO (apartado "d" de Resultados)

Entrada : datos/crudo/co2cars_2024_muestra1de10.parquet
Salida  : datos/procesado/co2cars_2024_limpio.parquet
          datos/procesado/informe_preprocesado.json

Aplica las decisiones registradas en la bitacora del trabajo (D-08 a D-16) y
deja constancia del numero de registros afectado por cada una, de modo que
cada exclusion sea verificable y no haya que creerse ninguna cifra.

Uso
---
    python 02_preprocesado.py
    python 02_preprocesado.py --entrada datos/crudo/otro.parquet

Eduardo Flores Carralero — Master en Big Data y Data Science, IMF Smart Education
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
DIR_CRUDO = RAIZ / "datos" / "crudo"
DIR_SALIDA = RAIZ / "datos" / "procesado"

EWLTP = "Ewltp (g/km)"
MASA = "M (kg)"
CILIND = "Ec (cm3)"
POTEN = "Ep (KW)"
ELECTR = "Z (Wh/km)"
ERWLTP = "Erwltp (g/km)"

# D-08: vacias en el 100 % de los registros de 2024
COLUMNAS_VACIAS = ["Enedc (g/km)", "W (mm)", "At1 (mm)", "At2 (mm)"]

# D-09: etiquetas de control de la EEA en el campo de fabricante
CENTINELAS = ["DUPLICATE", "OUT OF SCOPE", "UNKNOWN", "AA-IVA", "N/A"]

# D-13: rango de masa de la categoria M1
MASA_MIN, MASA_MAX = 800, 3500

# D-12: por debajo de este umbral la potencia declarada corresponde al motor
# electrico de asistencia de un hibrido ligero, no al motor termico
POTENCIA_MINIMA = 15

# D-14: regimenes tecnologicos
CERO = ("electric", "hydrogen")
ENCHUFE = ("petrol/electric", "diesel/electric")

# D-16: normalizacion de marca
CANONICAS = sorted(
    ["MERCEDES", "VOLKSWAGEN", "ALFA ROMEO", "LAND ROVER", "GREAT WALL",
     "MITSUBISHI", "SSANGYONG", "ASTON MARTIN", "ROLLS ROYCE", "MG",
     "CITROEN", "FORD", "OPEL", "TOYOTA", "SKODA", "RENAULT", "BMW",
     "PEUGEOT", "DACIA", "AUDI", "HYUNDAI", "KIA", "VOLVO", "TESLA",
     "FIAT", "SEAT", "NISSAN", "CUPRA", "SUZUKI", "MAZDA", "JEEP",
     "MINI", "PORSCHE", "LEXUS", "HONDA", "LANCIA", "SMART", "POLESTAR",
     "SUBARU", "JAGUAR", "BYD", "NIO", "LEAPMOTOR", "XPENG", "OMODA",
     "GENESIS", "MASERATI", "FERRARI", "BENTLEY", "LOTUS"],
    key=len, reverse=True)
EXCEPCIONES_MARCA = {"CITROEN DS": "DS"}


def normaliza_marca(valor) -> str:
    """Marca canonica. La barra separa fabricante de carrocero en las
    conversiones; el prefijo resuelve las variantes de una misma marca."""
    s = str(valor).strip().upper()
    if not s or s == "NAN":
        return "SIN MARCA"
    s = " ".join(s.split("/")[0].split())
    if s in EXCEPCIONES_MARCA:
        return EXCEPCIONES_MARCA[s]
    for c in CANONICAS:
        if s.startswith(c):
            return c
    return s.split(" ")[0]


def regimen_de(ft: str) -> str:
    if ft in CERO:
        return "Cero emisiones"
    if ft in ENCHUFE:
        return "Híbrido enchufable"
    return "Combustión"


def main() -> int:
    parser = argparse.ArgumentParser(description="Preprocesado del conjunto EEA")
    parser.add_argument("--entrada", type=str,
                        default=str(DIR_CRUDO / "co2cars_2024_muestra1de10.parquet"))
    args = parser.parse_args()

    entrada = Path(args.entrada)
    if not entrada.exists():
        print(f"ERROR: no se encuentra {entrada}")
        return 1

    print("=" * 74)
    print(" TFM — PREPROCESADO DEL CONJUNTO DE DATOS")
    print("=" * 74)

    df = pd.read_parquet(entrada)
    n0 = len(df)
    registro: list[dict] = []
    print(f"\nRegistros de entrada: {n0:,}".replace(",", "."))

    def paso(etiqueta, mascara_a_eliminar, decision):
        """Elimina las filas marcadas y anota cuantas eran."""
        nonlocal df
        n = int(mascara_a_eliminar.sum())
        df = df.loc[~mascara_a_eliminar].copy()
        registro.append({"paso": etiqueta, "decision": decision,
                         "filas_eliminadas": n, "filas_restantes": len(df)})
        print(f"  [{decision}] {etiqueta}: -{n:,} -> {len(df):,}".replace(",", "."))

    # --- Eliminacion de columnas sin contenido ---------------------------
    presentes = [c for c in COLUMNAS_VACIAS if c in df.columns]
    df = df.drop(columns=presentes)
    registro.append({"paso": f"columnas vacias eliminadas: {presentes}",
                     "decision": "D-08", "filas_eliminadas": 0,
                     "filas_restantes": len(df)})
    print(f"\n  [D-08] columnas eliminadas: {', '.join(presentes)}")

    # --- Exclusiones de filas --------------------------------------------
    print()
    paso("etiquetas de control en el campo de fabricante",
         df["Mh"].astype(str).str.upper().str.strip().isin(CENTINELAS), "D-09")

    paso("registros sin valor de emisiones", df[EWLTP].isna(), "H-04")

    paso(f"masa fuera del rango M1 ({MASA_MIN}-{MASA_MAX} kg)",
         (df[MASA] < MASA_MIN) | (df[MASA] > MASA_MAX), "D-13")

    # --- Correcciones sobre campos concretos -----------------------------
    print()
    corregidas = int((df[POTEN] < POTENCIA_MINIMA).sum())
    df["ep_no_fiable"] = df[POTEN] < POTENCIA_MINIMA
    df.loc[df["ep_no_fiable"], POTEN] = np.nan
    registro.append({"paso": "potencia anulada en hibridos ligeros",
                     "decision": "D-12", "filas_eliminadas": 0,
                     "campos_anulados": corregidas, "filas_restantes": len(df)})
    print(f"  [D-12] potencia anulada (fila conservada): {corregidas:,}"
          .replace(",", "."))

    sin_ecoinnov = int(df[ERWLTP].isna().sum())
    df[ERWLTP] = df[ERWLTP].fillna(0)
    registro.append({"paso": "ecoinnovacion ausente recodificada a 0",
                     "decision": "D-10", "filas_eliminadas": 0,
                     "campos_recodificados": sin_ecoinnov,
                     "filas_restantes": len(df)})
    print(f"  [D-10] ecoinnovacion ausente -> 0: {sin_ecoinnov:,}"
          .replace(",", "."))

    sin_pool = int((df["Mp"].isna() | (df["Mp"].astype(str).str.strip() == "")).sum())
    df["Mp"] = df["Mp"].astype(str).str.strip().replace({"": "SIN AGRUPACION",
                                                         "nan": "SIN AGRUPACION"})
    registro.append({"paso": "pool vacio recodificado como categoria",
                     "decision": "D-11", "filas_eliminadas": 0,
                     "campos_recodificados": sin_pool, "filas_restantes": len(df)})
    print(f"  [D-11] pool vacio -> 'SIN AGRUPACION': {sin_pool:,}"
          .replace(",", "."))

    # --- Variables derivadas ---------------------------------------------
    print()
    df["ft_norm"] = df["Ft"].astype(str).str.lower().str.strip()
    df["regimen"] = df["ft_norm"].map(regimen_de)
    df["marca_norm"] = df["Mk"].map(normaliza_marca)
    n_marcas_antes = df["Mk"].nunique()
    n_marcas = df["marca_norm"].nunique()
    registro.append({"paso": "normalizacion de combustible y marca",
                     "decision": "D-16 / H-01", "filas_eliminadas": 0,
                     "marcas_antes": int(n_marcas_antes),
                     "marcas_despues": int(n_marcas),
                     "filas_restantes": len(df)})
    print(f"  [D-16] marcas: {n_marcas_antes} -> {n_marcas}")
    print(f"  [H-01] combustible normalizado a minusculas")

    # --- Guardado ---------------------------------------------------------
    DIR_SALIDA.mkdir(parents=True, exist_ok=True)
    destino = DIR_SALIDA / "co2cars_2024_limpio.parquet"
    df.to_parquet(destino, index=False, compression="snappy")

    informe = {
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "fichero_entrada": entrada.name,
        "fichero_salida": destino.name,
        "registros_entrada": n0,
        "registros_salida": len(df),
        "porcentaje_conservado": round(100 * len(df) / n0, 3),
        "pasos": registro,
        "reparto_por_regimen": df["regimen"].value_counts().to_dict(),
    }
    (DIR_SALIDA / "informe_preprocesado.json").write_text(
        json.dumps(informe, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n" + "=" * 74)
    print(f" Registros conservados: {len(df):,} de {n0:,} "
          f"({100 * len(df) / n0:.2f} %)".replace(",", "."))
    print("\n Reparto por regimen tecnologico:")
    for r, n in df["regimen"].value_counts().items():
        print(f"   {r:<22} {n:>9,}".replace(",", "."))
    print(f"\n Guardado: {destino}")
    print(f" Informe:  {DIR_SALIDA / 'informe_preprocesado.json'}")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())

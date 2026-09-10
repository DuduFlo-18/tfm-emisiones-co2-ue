"""Prepara los ficheros que alimentan el cuadro de mando en Power BI.

Genera en datos/powerbi/ un conjunto de CSV pequeños y ya agregados, más una
muestra estratificada a nivel de vehículo para los gráficos de dispersión.
Power BI importa CSV sin conectores adicionales y el volumen resultante cabe
holgadamente en memoria, cosa que no ocurriria con los 839.684 registros.

Uso:  python src/03_datos_powerbi.py
"""

from pathlib import Path
import importlib.util
import json
import sys

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PROCESADO = RAIZ / "datos" / "procesado"
AGREGADOS = RAIZ / "datos" / "agregados"
MODELOS = RAIZ / "modelos"
SALIDA = RAIZ / "datos" / "powerbi"

SEMILLA = 42
TAM_MUESTRA = 60_000

EWLTP, MASA, POTENCIA, CILINDRADA = "Ewltp (g/km)", "M (kg)", "Ep (KW)", "Ec (cm3)"

# Los 95 g/km del Reglamento estan expresados en NEDC y todo este conjunto es
# WLTP. La referencia comparable es la senda WLTP: 110 g/km en 2021 y un 15 %
# menos desde 2025.
REFERENCIA_2021 = 110.0
OBJETIVO_2025 = 93.6

SENDA = [
    {"periodo": "2021-2024", "reduccion_pct": 0, "objetivo_wltp": REFERENCIA_2021,
     "nota": "Referencia de flota, equivalencia WLTP de los 95 g/km NEDC"},
    {"periodo": "2025-2029", "reduccion_pct": 15, "objetivo_wltp": OBJETIVO_2025,
     "nota": "Reglamento (UE) 2019/631"},
    {"periodo": "2030-2034", "reduccion_pct": 55, "objetivo_wltp": 49.5,
     "nota": "Reglamento (UE) 2023/851"},
    {"periodo": "2035 en adelante", "reduccion_pct": 100, "objetivo_wltp": 0.0,
     "nota": "Reglamento (UE) 2023/851"},
]

PERFILES = [
    "Urbano compacto",
    "Generalista",
    "Diésel de tamaño medio-alto",
    "Altas prestaciones",
]


def ponderada(valores, pesos):
    """Media ponderada que ignora los huecos.

    Algunas grafias de una misma marca llegan sin emision media. Sumarlas al
    promedio con numpy devolveria un hueco para toda la marca, que es lo que
    ocurria con Volkswagen y BMW.
    """
    valido = valores.notna() & pesos.notna()
    if not valido.any():
        return float("nan")
    return float(np.average(valores[valido], weights=pesos[valido]))


def normalizador():
    """Reutiliza la normalizacion de marca de 02_preprocesado.py.

    El agregado de poblacion llega sin normalizar y Toyota aparece por delante de
    Volkswagen, que viene repartida en diecisiete grafias. Duplicar aqui la regla
    invitaria a que las dos versiones divergieran; se importa la original.
    """
    origen = Path(__file__).resolve().parent / "02_preprocesado.py"
    spec = importlib.util.spec_from_file_location("preprocesado", origen)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo.normaliza_marca


def exige(ruta):
    if not ruta.exists():
        sys.exit(f"Falta {ruta.relative_to(RAIZ)}. Ejecuta antes el cuaderno que lo genera.")
    return ruta


def escribe(df, nombre):
    destino = SALIDA / nombre
    df.to_csv(destino, index=False, encoding="utf-8-sig", float_format="%.4f")
    print(f"  {nombre:28} {len(df):>7,} filas".replace(",", "."))


def tabla_segmentos(comb, grupos):
    """Reetiqueta los grupos de K-means por emisión media ascendente.

    Las etiquetas que devuelve K-means son arbitrarias y cambian entre
    ejecuciones. Ordenarlas por CO₂ fija la correspondencia con los grupos 1 a 4
    de la memoria y evita que el cuadro de mando y el documento se contradigan.
    """
    datos = comb.join(grupos["grupo_4"], how="inner")
    datos = datos[datos["grupo_4"].notna()]

    orden = datos.groupby("grupo_4")[EWLTP].mean().sort_values()
    mapa = {viejo: nuevo for nuevo, viejo in enumerate(orden.index, start=1)}
    datos["segmento"] = datos["grupo_4"].map(mapa).astype(int)
    datos["perfil"] = datos["segmento"].map(dict(enumerate(PERFILES, start=1)))

    resumen = (datos.groupby(["segmento", "perfil"])
               .agg(vehiculos=(EWLTP, "size"),
                    co2_medio=(EWLTP, "mean"),
                    co2_mediana=(EWLTP, "median"),
                    masa_media=(MASA, "mean"),
                    potencia_media=(POTENCIA, "mean"),
                    cilindrada_media=(CILINDRADA, "mean"))
               .reset_index())
    resumen["cuota_pct"] = resumen["vehiculos"] / resumen["vehiculos"].sum() * 100
    resumen["sobre_objetivo_2025"] = resumen["co2_medio"] - OBJETIVO_2025

    dominante = (datos.groupby(["segmento", "marca_norm"]).size()
                 .reset_index(name="n")
                 .sort_values(["segmento", "n"], ascending=[True, False])
                 .groupby("segmento").first()["marca_norm"]
                 .rename("marca_dominante"))
    resumen = resumen.merge(dominante, on="segmento")

    combustible = (datos.groupby(["segmento", "ft_norm"]).size()
                   .reset_index(name="vehiculos"))

    return datos, resumen, combustible


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)

    limpio = pd.read_parquet(exige(PROCESADO / "co2cars_2024_limpio.parquet"))
    grupos = pd.read_parquet(exige(PROCESADO / "grupos_kmeans.parquet"))
    comparativa = json.loads(exige(MODELOS / "comparativa_final.json").read_text(encoding="utf-8"))
    tendencia = pd.read_csv(exige(AGREGADOS / "tendencia_anio_combustible.csv"))
    paises = pd.read_csv(exige(AGREGADOS / "resumen_por_pais.csv"))
    marcas = pd.read_csv(exige(AGREGADOS / "resumen_por_marca.csv"))
    globales = pd.read_csv(exige(AGREGADOS / "estadisticos_globales.csv"))

    comb = limpio[limpio["regimen"] == "Combustión"]
    print(f"Muestra limpia: {len(limpio):,} registros, {len(comb):,} de combustión".replace(",", "."))

    print("\nEscribiendo en datos/powerbi/")

    # --- senda regulatoria -------------------------------------------------
    escribe(pd.DataFrame(SENDA), "objetivos.csv")

    # --- evolucion 2021-2024 ----------------------------------------------
    t = tendencia.copy()
    t["Combustible"] = t["Combustible"].str.lower().str.strip()
    t = t.dropna(subset=["CO2_medio_wltp"])
    CERO = ["electric", "hydrogen"]
    ENCHUFE = ["petrol/electric", "diesel/electric"]
    t["regimen"] = np.where(t["Combustible"].isin(CERO), "Cero emisiones",
                     np.where(t["Combustible"].isin(ENCHUFE), "Híbrido enchufable", "Combustión"))

    por_regimen = (t.groupby(["Anio", "regimen"])
                   .apply(lambda g: pd.Series({
                       "vehiculos": g["Vehiculos"].sum(),
                       "co2_medio": np.average(g["CO2_medio_wltp"], weights=g["Vehiculos"]),
                   }), include_groups=False)
                   .reset_index())
    por_regimen["cuota_pct"] = (por_regimen["vehiculos"]
                                / por_regimen.groupby("Anio")["vehiculos"].transform("sum") * 100)
    escribe(por_regimen.rename(columns={"Anio": "anio"}), "evolucion_regimen.csv")

    flota = (t.groupby("Anio")
             .apply(lambda g: pd.Series({
                 "vehiculos": g["Vehiculos"].sum(),
                 "co2_flota": np.average(g["CO2_medio_wltp"], weights=g["Vehiculos"]),
                 "masa_media": np.average(g["Masa_media_kg"], weights=g["Vehiculos"]),
             }), include_groups=False)
             .reset_index().rename(columns={"Anio": "anio"}))
    flota["objetivo_2025"] = OBJETIVO_2025
    flota["distancia_objetivo_pct"] = (flota["co2_flota"] / OBJETIVO_2025 - 1) * 100
    escribe(flota, "evolucion_flota.csv")

    # --- geografia y fabricantes ------------------------------------------
    p = paises.rename(columns={"Pais": "pais", "Vehiculos": "vehiculos",
                               "CO2_medio_wltp": "co2_medio",
                               "Masa_media_kg": "masa_media",
                               "Potencia_media_kw": "potencia_media"})
    p["cumple_objetivo_2025"] = p["co2_medio"] <= OBJETIVO_2025
    escribe(p.sort_values("co2_medio"), "paises.csv")

    m = marcas.rename(columns={"Marca": "marca", "Vehiculos": "vehiculos",
                               "CO2_medio_wltp": "co2_medio",
                               "Masa_media_kg": "masa_media",
                               "Potencia_media_kw": "potencia_media"})
    m = m[m["marca"].notna()]
    m["marca"] = m["marca"].map(normalizador())
    m = m[~m["marca"].astype(str).str.strip().str.isdigit()]
    m = (m.groupby("marca")
         .apply(lambda g: pd.Series({
             "vehiculos": g["vehiculos"].sum(),
             "co2_medio": ponderada(g["co2_medio"], g["vehiculos"]),
             "masa_media": ponderada(g["masa_media"], g["vehiculos"]),
             "potencia_media": ponderada(g["potencia_media"], g["vehiculos"]),
         }), include_groups=False)
         .reset_index())
    # Corte en las 25 de mayor volumen, el mismo de la figura 6 de la memoria.
    m = m.sort_values("vehiculos", ascending=False).head(25)
    m["cumple_objetivo_2025"] = m["co2_medio"] <= OBJETIVO_2025
    escribe(m, "marcas.csv")

    # --- segmentacion ------------------------------------------------------
    detalle, segmentos, seg_combustible = tabla_segmentos(comb, grupos)
    escribe(segmentos, "segmentos.csv")
    escribe(seg_combustible, "segmentos_combustible.csv")

    # La dispersión potencia-emisiones necesita nivel de vehículo. Una muestra
    # estratificada por segmento conserva la forma de la nube y reduce el
    # fichero de unos 70 MB a menos de 5.
    fraccion = min(1.0, TAM_MUESTRA / len(detalle))
    muestra = (detalle.groupby("segmento", group_keys=False)
               .sample(frac=fraccion, random_state=SEMILLA))
    muestra = muestra[["segmento", "perfil", "marca_norm", "MS", "ft_norm",
                       EWLTP, MASA, POTENCIA, CILINDRADA]].copy()
    muestra.columns = ["segmento", "perfil", "marca", "pais", "combustible",
                       "co2", "masa", "potencia", "cilindrada"]
    # Identificador de fila: el grafico de dispersion necesita un campo de
    # cardinalidad alta para dibujar un punto por vehiculo. Sin el, Power BI
    # agrega y pinta un solo punto por segmento.
    muestra.insert(0, "id", range(1, len(muestra) + 1))
    escribe(muestra, "vehiculos_muestra.csv")

    # --- modelos -----------------------------------------------------------
    mod = pd.DataFrame(comparativa["modelos"]).rename(columns={
        "modelo": "modelo", "MAE": "mae", "RMSE": "rmse", "R2": "r2",
        "error relativo %": "error_relativo_pct"})
    mod["elegido"] = mod["modelo"] == "LightGBM ajustado"
    escribe(mod, "modelos.csv")

    # --- indicadores de cabecera -------------------------------------------
    g = globales.iloc[0]
    ultimo = flota.loc[flota["anio"].idxmax()]
    previo = flota.loc[flota["anio"] == ultimo["anio"] - 1].iloc[0]
    elegido = mod[mod["elegido"]].iloc[0]

    kpi = pd.DataFrame([
        ("Emisión media de la flota 2024", round(float(ultimo["co2_flota"]), 2), "g/km"),
        ("Variación frente a 2023", round(float(ultimo["co2_flota"] - previo["co2_flota"]), 2), "g/km"),
        ("Distancia al objetivo de 2025", round(float(ultimo["distancia_objetivo_pct"]), 1), "%"),
        ("Vehículos matriculados 2024", int(g["Total_vehiculos"]), "unidades"),
        ("Masa media del vehículo 2024", round(float(g["Masa_media_kg"]), 1), "kg"),
        ("Error del modelo (MAE)", round(float(elegido["mae"]), 3), "g/km"),
        ("Precisión del modelo (R²)", round(float(elegido["r2"]), 4), ""),
        ("Países que cumplen el objetivo", int(p["cumple_objetivo_2025"].sum()), "de %d" % len(p)),
    ], columns=["indicador", "valor", "unidad"])
    escribe(kpi, "kpi.csv")

    print(f"\nListo. {len(list(SALIDA.glob('*.csv')))} ficheros en datos/powerbi/")


if __name__ == "__main__":
    main()

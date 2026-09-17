# Predicción y segmentación de las emisiones de CO₂ de los vehículos nuevos matriculados en la Unión Europea

Trabajo Fin de Máster — Máster en Big Data y Data Science
IMF Smart Education

**Autor:** Eduardo Flores Carralero
**Tutor:** Juan Manuel Moreno Lamparero

---

## Objetivo

Modelizar las emisiones de CO₂ bajo ciclo WLTP de los turismos nuevos
matriculados en la Unión Europea a partir de sus características técnicas,
mediante aprendizaje automático supervisado y no supervisado, con el fin de
identificar los factores determinantes de dichas emisiones y segmentar el
mercado según su perfil de cumplimiento del Reglamento (UE) 2019/631.

## Datos

| | |
|---|---|
| Fuente | Agencia Europea de Medio Ambiente (EEA) — base de datos pública Discodata |
| Punto de acceso | `https://discodata.eea.europa.eu/sql` (SQL REST, sin registro) |
| Tabla | `[CO2Emission].[latest].[co2cars_2024Fv30]` — año 2024, versión Final |
| Población | 10.782.314 registros × 43 variables |
| Muestra de trabajo | 1.076.533 registros (10 %, muestreo pseudoaleatorio reproducible por hash MD5 sobre el identificador) |
| Variable objetivo | `Ewltp (g/km)` — emisiones específicas de CO₂ |

Los datos completos no se incluyen en el repositorio: se regeneran de forma
íntegra ejecutando la cadena de `src/`. Sí se versionan los agregados ligeros,
el fichero `datos/metadatos_extraccion.json` —que registra la fecha, la tabla
de origen y los parámetros exactos de la descarga— y el informe de preprocesado
con el recuento de registros afectados por cada regla de depuración.

## Resultado

El modelo seleccionado es LightGBM con hiperparámetros ajustados, con un error
absoluto medio de **1,230 g/km** y un coeficiente de determinación de **0,994**
sobre 167.937 vehículos no empleados en el entrenamiento. Las variables físicas
concentran el 86,7 % de la contribución a las predicciones, frente al 13,3 % de
la identidad comercial y geográfica.

La memoria completa está en `documentos/`.

## Estructura

```
tfm-emisiones-co2-ue/
├── src/
│   ├── 01_extraccion.py             Adquisición desde el endpoint de la EEA
│   ├── 02_preprocesado.py           Depuración, con informe de trazabilidad
│   └── 03_datos_powerbi.py          Agregados para el cuadro de mando
├── notebooks/
│   ├── estilo.py                    Paleta y estilo común de las figuras
│   ├── 02_estructura_datos.ipynb    Estructura y calidad del conjunto
│   ├── 03_eda_distribuciones.ipynb  Distribuciones y valores atípicos
│   ├── 04_eda_temporal_geografico.ipynb  Serie 2021-2024, países y marcas
│   ├── 05_preprocesado_contrastes.ipynb  Selección de variables y contrastes
│   ├── 06_modelado.ipynb            Partición, modelos de referencia y ablación
│   ├── 07_ajuste_segmentacion.ipynb Hiperparámetros y K-medias
│   └── 08_evaluacion_interpretabilidad.ipynb  Error, SHAP y comparativa
├── figuras/                         Las 19 figuras de la memoria, en PNG
├── datos/
│   ├── agregados/                   Estadísticos de población, en CSV
│   ├── metadatos_extraccion.json    Trazabilidad de la descarga
│   └── procesado/informe_preprocesado.json  Recuento por regla de depuración
├── modelos/                         Métricas e hiperparámetros, en JSON
├── documentos/                      Memoria y cuadro de mando
├── requirements.txt
└── INSTALACION.md                   Guía de montaje del entorno en Windows
```

Cada cuaderno alimenta un apartado concreto de la memoria, de modo que el
código que respalda cada sección sea localizable sin explicación adicional.

## Reproducción

Desarrollado y ejecutado con **Python 3.13**. Los pasos detallados están en
`INSTALACION.md`.

```bash
python -m venv .venv
.\.venv\Scripts\activate          # Windows
pip install -r requirements.txt
python src\01_extraccion.py       # descarga agregados y muestra del 10 %
python src\02_preprocesado.py     # depuración e informe de trazabilidad
```

Los cuadernos se ejecutan después, en orden numérico.

`requirements.txt` es una congelación completa del entorno de trabajo, de modo
que incluye también dependencias transitivas y alguna biblioteca que se instaló
durante la exploración inicial y no llegó a emplearse en el análisis final. Las
efectivamente utilizadas son DuckDB, pandas, NumPy, SciPy, statsmodels,
scikit-learn, LightGBM, SHAP, Matplotlib y requests.

## Entorno

Windows nativo, sin máquina virtual ni infraestructura en la nube. El
procesamiento analítico se resuelve con **DuckDB**, motor SQL embebido que
consulta los ficheros Parquet directamente, sin servidor. La decisión de
descartar Spark y Hadoop está justificada en el apartado 3.2 de la memoria.

## Licencia y uso de los datos

Los datos originales son propiedad de la Agencia Europea de Medio Ambiente y se
publican como datos abiertos. El código y la memoria de este repositorio son
obra del autor y forman parte de un trabajo académico; se publican para
consulta, sin licencia de reutilización asignada.

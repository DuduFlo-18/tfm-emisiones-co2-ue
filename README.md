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

Los datos no se incluyen en el repositorio: se regeneran de forma íntegra
ejecutando el script de extracción. El fichero `datos/metadatos_extraccion.json`
registra la fecha, la tabla de origen y los parámetros exactos de la descarga.

## Estructura

```
tfm-emisiones-co2-ue/
├── src/
│   └── 01_extraccion.py        Adquisición desde el endpoint de la EEA
├── notebooks/
│   ├── estilo.py               Paleta y estilo común de las figuras
│   ├── 02_estructura_datos.ipynb    Estructura y calidad del conjunto
│   └── 03_eda_distribuciones.ipynb  Distribuciones y valores atípicos
├── figuras/                    Figuras generadas, en PNG a 200 ppp
├── datos/                      Datos descargados (no versionados)
├── documentos/                 Memoria y documentación del trabajo
├── requirements.txt
└── INSTALACION.md              Guía de montaje del entorno en Windows
```

Cada cuaderno alimenta un apartado concreto de la memoria, de modo que el
código que respalda cada sección sea localizable sin explicación adicional.

## Reproducción

Requiere Python 3.11 o superior. Los pasos detallados están en
`INSTALACION.md`.

```bash
python -m venv .venv
.\.venv\Scripts\activate          # Windows
pip install -r requirements.txt
python src\01_extraccion.py       # descarga agregados y muestra del 10 %
```

Los cuadernos se ejecutan después, en orden numérico.

## Entorno

Windows nativo, sin máquina virtual ni infraestructura en la nube. El
procesamiento analítico se resuelve con **DuckDB**, motor SQL embebido que
consulta los ficheros Parquet directamente, sin servidor. La decisión de
descartar Spark y Hadoop está justificada en el apartado 3.2 de la memoria.

## Licencia y uso de los datos

Los datos originales son propiedad de la Agencia Europea de Medio Ambiente y
se publican como datos abiertos. Este repositorio es privado y su contenido
forma parte de un trabajo académico.

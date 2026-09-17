# Instalación del entorno (Windows, sin máquina virtual)

Guía de montaje del entorno de trabajo. Tiempo estimado: 15-20 minutos.

---

## Paso 1 — Instalar Python

1. Ir a **https://www.python.org/downloads/windows/**
2. Descargar **Python 3.13**, instalador de 64 bits. Es la versión con la que se
   desarrolló el proyecto y a la que están fijadas las dependencias.
3. Ejecutar el instalador y marcar la casilla **"Add python.exe to PATH"**, que
   aparece al final de la primera pantalla. Es el paso crítico: sin esa casilla
   Windows no localiza el intérprete.
4. Pulsar "Install Now" y esperar a que termine.

**Comprobación.** En el símbolo del sistema:

```
python --version
```

La respuesta debe ser `Python 3.13.x`. Si el comando no se reconoce, la casilla
del PATH no quedó marcada y procede reinstalar.

---

## Paso 2 — Instalar Visual Studio Code

1. Ir a **https://code.visualstudio.com/**
2. Descargar e instalar la versión para Windows con las opciones por defecto.
3. Abrir VS Code.
4. En la barra lateral izquierda, en el icono de **Extensiones**, instalar:
   - **Python** (Microsoft)
   - **Jupyter** (Microsoft)

---

## Paso 3 — Instalar Git

El anteproyecto declara control de versiones con Git y GitHub, y la normativa
pide documentarlo en el apartado de material y métodos. Aporta además trazas de
cada cambio y permite revertir cualquier versión.

1. Descargar Git desde **https://git-scm.com/download/win**
2. Instalar con las opciones por defecto.
3. Comprobar en una terminal nueva:

```
git --version
```

4. Configurar la identidad del autor, una sola vez:

```
git config --global user.name "Nombre Apellidos"
git config --global user.email "correo@ejemplo.com"
```

> El repositorio permanece privado mientras dura el desarrollo y se abre al
> público en la entrega, para que el enlace citado en el apartado 3.5 de la
> memoria sea consultable. El código se deposita además en la plataforma de
> entrega del máster.

---

## Paso 4 — Crear la carpeta del proyecto

1. Crear una carpeta para el trabajo, por ejemplo
   `C:\Users\<usuario>\Documents\TFM`.
2. Clonar el repositorio en esa ruta, o descomprimir ahí el contenido del
   proyecto, de forma que la estructura quede así:

```
TFM\
├── requirements.txt
├── INSTALACION.md
├── src\
│   ├── 01_extraccion.py
│   ├── 02_preprocesado.py
│   └── 03_datos_powerbi.py
├── notebooks\
└── datos\          (se crea al ejecutar la extracción)
```

3. En VS Code: **Archivo → Abrir carpeta...** y seleccionar la carpeta `TFM`.

---

## Paso 5 — Crear el entorno virtual e instalar las librerías

Un entorno virtual es un directorio aislado con las librerías de este proyecto,
independiente de cualquier otra instalación del sistema.

1. Abrir el terminal integrado: **Terminal → Nuevo terminal**.
2. Ejecutar los dos comandos siguientes, esperando a que termine cada uno:

```powershell
python -m venv .venv
```

```powershell
.\.venv\Scripts\activate
```

Tras el segundo comando aparece `(.venv)` al principio de la línea, lo que
indica que el entorno está activo.

> **Error de permisos al activar.** Ejecutar primero el comando siguiente y
> repetir la activación:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```

3. Instalar las librerías. El proceso tarda varios minutos:

```powershell
pip install -r requirements.txt
```

---

## Paso 6 — Ejecutar la extracción de datos

Con el entorno activo `(.venv)`:

```powershell
python src\01_extraccion.py
```

El script realiza tres operaciones e informa por pantalla de cada una:

1. **Detecta** cuántas filas admite la API de la EEA por petición.
2. **Descarga los agregados** de población (medias por año, país, marca y
   combustible), calculados por el servidor sobre los 10,7 millones de registros.
3. **Descarga una muestra** de ~1.076.000 vehículos individuales, el 10 % de la
   población, y la guarda en formato Parquet.

La estructura resultante es:

```
datos\
├── agregados\
│   ├── tendencia_anio_combustible.csv
│   ├── resumen_por_pais.csv
│   ├── resumen_por_marca.csv
│   └── estadisticos_globales.csv
├── crudo\
│   └── co2cars_2024_muestra1de10.parquet
└── metadatos_extraccion.json
```

A continuación se ejecuta `python src\02_preprocesado.py`, que aplica las reglas
de depuración y deja constancia del recuento de registros afectados por cada una
en `datos/procesado/informe_preprocesado.json`. Los cuadernos se ejecutan
después, en orden numérico.

---

## Variantes de ejecución

| Comando | Qué hace |
|---|---|
| `python src\01_extraccion.py` | Muestra del 10 % (~1.076.000 filas). **Recomendado.** |
| `python src\01_extraccion.py --fraccion 20` | Muestra del 5 % (~539.000 filas), más ligera. |
| `python src\01_extraccion.py --fraccion 5` | Muestra del 20 % (~2.156.000 filas). |
| `python src\01_extraccion.py --modo completo` | Los 10,7 millones. Puede tardar horas. |
| `python src\01_extraccion.py --saltar-agregados` | Repite solo el detalle, sin volver a descargar los agregados. |

El 10 % es el volumen de trabajo del análisis. La curva de aprendizaje calculada
en el cuaderno 06 evalúa si ese tamaño es suficiente; para ampliarlo basta con
volver a ejecutar el script cambiando `--fraccion`.

### Cómo se toma la muestra

El muestreo es **pseudoaleatorio pero reproducible**: se aplica una función hash
(MD5) sobre el identificador de cada registro y se selecciona según el resto de
la división. El reparto es uniforme e independiente de cómo se hayan asignado
los identificadores, y a la vez determinista: la misma consulta devuelve siempre
exactamente las mismas filas.

Se descartó el muestreo sistemático (`ID % 10 = 0`) porque quedaría sesgado si
los identificadores se hubieran asignado por bloques de país, fabricante o lote
de carga.

Verificado el 24/08/2026 contra el servidor de la EEA: con fracción 10 devuelve
**1.076.533 filas**, un 0,16 % por debajo del décimo exacto, desviación
coherente con un reparto uniforme.

---

## Incidencias habituales en Windows

El script reintenta de forma automática los fallos de red. Un aviso de
"reintentando" por pantalla no indica un problema: es el comportamiento
esperado. Ante cualquier otro fallo, el mensaje completo del terminal identifica
la causa.

| Síntoma | Causa y solución |
|---|---|
| `'python' no se reconoce como un comando` | No se marcó "Add python.exe to PATH". Reinstalar Python marcando la casilla. |
| Error de permisos al activar el entorno virtual | Ejecutar `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` y repetir la activación. |
| Falla la instalación de `lightgbm` o `shap` | Suele deberse a la ausencia de las herramientas de compilación de C++. Ejecutar `pip install --upgrade pip setuptools wheel` y repetir la instalación resuelve la mayoría de los casos. |

---

## Componentes adicionales

- **Power BI Desktop** — necesario para abrir y editar el cuadro de mando
  `documentos/cuadro_mando_co2.pbix`. Gratuito, desde Microsoft Store o desde la
  web de Microsoft. El fichero `documentos/cuadro_mando.pdf` reproduce las tres
  páginas del informe sin necesidad de instalarlo.
- **OBS Studio** — necesario únicamente para grabar un vídeo demostrativo. No es
  un entregable obligatorio: la rúbrica se limita a valorarlo positivamente.

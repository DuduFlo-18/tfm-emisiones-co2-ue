# Instalación del entorno (Windows, sin máquina virtual)

Guía paso a paso. Tiempo estimado: 15-20 minutos.

---

## Paso 1 — Instalar Python

1. Ve a **https://www.python.org/downloads/windows/**
2. Descarga **Python 3.12** (o 3.11), instalador de 64 bits.
3. Ejecuta el instalador y — **esto es lo más importante** — marca la casilla
   **"Add python.exe to PATH"** que aparece abajo del todo en la primera pantalla.
   Si no la marcas, Windows no encontrará Python después.
4. Pulsa "Install Now" y espera a que termine.

**Comprobación:** abre el menú Inicio, escribe `cmd`, abre "Símbolo del sistema"
y escribe:

```
python --version
```

Debe responder algo como `Python 3.12.x`. Si dice que no reconoce el comando,
reinstala marcando la casilla del PATH.

---

## Paso 2 — Instalar Visual Studio Code

1. Ve a **https://code.visualstudio.com/**
2. Descarga e instala la versión para Windows (acepta las opciones por defecto).
3. Abre VS Code.
4. En la barra lateral izquierda, pulsa el icono de **Extensiones**
   (cuatro cuadraditos) e instala estas dos, buscándolas por nombre:
   - **Python** (de Microsoft)
   - **Jupyter** (de Microsoft)

---

## Paso 2b — Instalar Git

El anteproyecto declara control de versiones con Git y GitHub, y la normativa
pide documentarlo en "Material y métodos". Además te sirve de red de seguridad:
si algo se rompe, vuelves a la versión anterior.

1. Descarga Git desde **https://git-scm.com/download/win**
2. Instálalo aceptando todas las opciones por defecto (son correctas).
3. Comprueba en una terminal nueva:

```
git --version
```

4. Si no tienes cuenta, créala en **https://github.com** (gratuita).
5. Configura tu identidad (una sola vez, con tus datos):

```
git config --global user.name "Eduardo Flores Carralero"
git config --global user.email "tu-correo@ejemplo.com"
```

> El repositorio lo crearemos **privado**. El código se entrega al final por la
> plataforma de depósito; GitHub es para tu control interno, no para publicarlo.

---

## Paso 3 — Crear la carpeta del proyecto

1. Crea una carpeta para el TFM donde te resulte cómodo, por ejemplo:
   `C:\Users\TuUsuario\Documents\TFM`
2. Descomprime ahí dentro el contenido del proyecto, de forma que quede así:

```
TFM\
├── requirements.txt
├── INSTALACION.md
├── src\
│   └── 01_extraccion.py
└── datos\          (se crea sola al ejecutar)
```

3. En VS Code: **Archivo → Abrir carpeta...** y selecciona la carpeta `TFM`.

---

## Paso 4 — Crear el entorno virtual e instalar las librerías

Un "entorno virtual" es una carpeta aislada con las librerías de este proyecto,
para que no se mezclen con otras cosas que tengas instaladas en el ordenador.

1. En VS Code abre el terminal: menú **Terminal → Nuevo terminal**.
2. Escribe estos comandos, uno a uno, esperando a que termine cada uno:

```powershell
python -m venv .venv
```

```powershell
.\.venv\Scripts\activate
```

Tras el segundo comando debe aparecer `(.venv)` al principio de la línea.
Eso significa que el entorno está activo.

> **Si da error de permisos** al activar, ejecuta primero esto y vuelve a
> intentarlo:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```

3. Instala las librerías (tarda unos minutos, es normal):

```powershell
pip install -r requirements.txt
```

---

## Paso 5 — Ejecutar la extracción de datos

Con el entorno activo `(.venv)`, ejecuta:

```powershell
python src\01_extraccion.py
```

El script hará tres cosas y te irá informando por pantalla:

1. **Detecta** cuántas filas admite la API de la EEA por petición.
2. **Descarga los agregados** de población (medias por año, país, marca y
   combustible), calculados por el servidor sobre los 10,7 millones de registros.
3. **Descarga una muestra** de ~539.000 vehículos individuales y la guarda en
   formato Parquet.

Al terminar tendrás:

```
datos\
├── agregados\
│   ├── tendencia_anio_combustible.csv
│   ├── resumen_por_pais.csv
│   ├── resumen_por_marca.csv
│   └── estadisticos_globales.csv
├── crudo\
│   └── co2cars_2024_muestra1de20.parquet
└── metadatos_extraccion.json
```

---

## Variantes de ejecución

| Comando | Qué hace |
|---|---|
| `python src\01_extraccion.py` | Muestra del 10 % (~1.076.000 filas). **Recomendado.** |
| `python src\01_extraccion.py --fraccion 20` | Muestra del 5 % (~539.000 filas), más ligera. |
| `python src\01_extraccion.py --fraccion 5` | Muestra del 20 % (~2.156.000 filas). |
| `python src\01_extraccion.py --modo completo` | Los 10,7 millones. Puede tardar horas. |
| `python src\01_extraccion.py --saltar-agregados` | Repite solo el detalle, sin volver a bajar los agregados. |

> El 10 % es el punto de partida. La **curva de aprendizaje** que se calculará más
> adelante dirá si ese volumen es suficiente o conviene ampliarlo; en ese caso
> basta con volver a ejecutar el script cambiando `--fraccion`.

### Cómo se toma la muestra

El muestreo es **pseudoaleatorio pero reproducible**: se aplica una función hash
(MD5) sobre el identificador de cada registro y se selecciona según el resto de
la división. Esto reparte los registros de forma uniforme e independiente de
cómo se hayan asignado los identificadores, pero de manera determinista — la
misma consulta devuelve siempre exactamente las mismas filas.

Se descartó el muestreo sistemático (`ID % 10 = 0`) porque quedaría sesgado si
los identificadores se hubieran asignado por bloques de país, fabricante o lote
de carga.

Verificado el 24/08/2026 contra el servidor de la EEA: con fracción 10 devuelve
**1.076.533 filas**, un 0,16 % por debajo del décimo exacto — desviación
coherente con un reparto uniforme.

---

## Si algo falla

Copia el mensaje de error completo tal cual aparece en el terminal y pásamelo.
El script reintenta automáticamente los fallos de red, así que si ves algún
aviso de "reintentando" no es un problema: es el comportamiento esperado.

**Los tres tropiezos más habituales en Windows:**

| Síntoma | Causa y solución |
|---|---|
| `'python' no se reconoce como un comando` | No se marcó "Add python.exe to PATH". Reinstala Python marcando la casilla. |
| Error de permisos al activar el entorno virtual | Ejecuta `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` y vuelve a intentarlo. |
| Falla la instalación de `xgboost`, `lightgbm` o `shap` | Suele ser falta de las herramientas de compilación de C++. Prueba primero `pip install --upgrade pip setuptools wheel` y repite. Si sigue fallando, pásame el error: hay alternativas. |

---

## Instalar más adelante (no hace falta hoy)

- **Power BI Desktop** — para el cuadro de mando de la última fase. Gratuito,
  desde Microsoft Store o desde la web de Microsoft.
- **OBS Studio** — solo si finalmente grabas el vídeo demo, que es opcional
  aunque la rúbrica lo valora positivamente.

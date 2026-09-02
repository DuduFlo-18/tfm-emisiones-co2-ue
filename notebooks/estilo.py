"""
Estilo visual comun de las figuras del TFM.

Centraliza paleta, tipografia y proporciones para que todas las figuras de la
memoria sean coherentes entre si.

    import estilo
    estilo.aplicar()
"""

import matplotlib as mpl
import matplotlib.pyplot as plt
from pathlib import Path

# Ruta relativa a este fichero, no al directorio de trabajo
DIR_FIGURAS = Path(__file__).resolve().parent.parent / "figuras"
DIR_FIGURAS.mkdir(exist_ok=True)

# Paleta categorica de ocho tonos, con separacion suficiente para ser
# distinguibles tambien con deficiencia en la vision del color.
PALETA = [
    "#2a78d6",  # 0 azul
    "#eb6834",  # 1 naranja
    "#1baf7a",  # 2 aguamarina
    "#eda100",  # 3 amarillo
    "#e87ba4",  # 4 magenta
    "#008300",  # 5 verde
    "#4a3aa7",  # 6 violeta
    "#e34948",  # 7 rojo
]

# Asignacion fija por combustible: cada categoria conserva su color en todas
# las figuras, de modo que el lector aprende el codigo una sola vez. Los
# electrificados ocupan tonos frios; los fosiles, tonos calidos.
COLOR_COMBUSTIBLE = {
    "electric":        PALETA[5],
    "petrol/electric": PALETA[2],
    "diesel/electric": PALETA[6],
    "petrol":          PALETA[0],
    "diesel":          PALETA[1],
    "lpg":             PALETA[3],
    "ng":              PALETA[4],
    "e85":             PALETA[7],
    "hydrogen":        "#52514e",  # gris: volumen residual
    "unknown":         "#a3a29c",  # gris claro: sin informacion
}

GRIS_TEXTO = "#0b0b0b"
GRIS_EJES = "#52514e"
GRIS_REJILLA = "#d8d8d4"


def aplicar():
    """Configura matplotlib para figuras de calidad de impresion."""
    mpl.rcParams.update({
        # Calibri es la tipografia de la memoria; las demas son alternativas
        "font.family": "sans-serif",
        "font.sans-serif": ["Calibri", "Arial", "DejaVu Sans"],
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.labelsize": 10,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,

        # Ejes y rejilla discretos: orientan sin competir con los datos
        "axes.edgecolor": GRIS_EJES,
        "axes.labelcolor": GRIS_EJES,
        "xtick.color": GRIS_EJES,
        "ytick.color": GRIS_EJES,
        "axes.grid": True,
        "grid.color": GRIS_REJILLA,
        "grid.linewidth": 0.6,
        "axes.axisbelow": True,
        "axes.spines.top": False,
        "axes.spines.right": False,

        "figure.dpi": 110,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
        "figure.facecolor": "white",
        "savefig.facecolor": "white",

        "axes.prop_cycle": mpl.cycler(color=PALETA),
    })


def color_de(combustible):
    """Color asignado a un combustible; gris si no esta mapeado."""
    return COLOR_COMBUSTIBLE.get(combustible, "#a3a29c")


def guardar(nombre):
    """Guarda la figura activa en figuras/ como PNG."""
    ruta = DIR_FIGURAS / f"{nombre}.png"
    plt.savefig(ruta)
    print(f"Figura guardada: {ruta.name}")
    return ruta

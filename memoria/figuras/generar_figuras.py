"""Genera las figuras de la memoria (PDF vectorial) en memoria/figuras/.

    python memoria/figuras/generar_figuras.py

Usa los resultados del estudio (data/resultados/) y los datos de la web (web/data/: contorno, red de autovías y trazado real de
las rutas entre ciudades). Las rutas de la figura de ejemplo se calculan con el mismo código de los notebooks (Anexo C).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection

RAIZ = Path(__file__).resolve().parent.parent.parent
SALIDA = RAIZ / "memoria" / "figuras"
WEB = RAIZ / "web" / "data"
RES = RAIZ / "data" / "resultados"

# Paleta categórica (la misma del notebook y de la web), un color fijo por algoritmo
NOMBRE = {"fuerza_bruta": "Fuerza bruta", "held_karp": "Held–Karp", "dfj": "DFJ", "vecino_mas_cercano": "Vecino más cercano",
          "dos_opt": "2-opt", "christofides": "Christofides", "genetico": "Genético", "recocido_simulado": "Recocido simulado"}
FAMILIAS = {"Exactos": ["fuerza_bruta", "held_karp", "dfj"], "Heurísticos": ["vecino_mas_cercano", "dos_opt", "christofides"],
            "Metaheurísticas": ["genetico", "recocido_simulado"]}
COLOR = {"fuerza_bruta": "#2a78d6", "held_karp": "#eb6834", "dfj": "#1baf7a", "vecino_mas_cercano": "#eda100",
         "dos_opt": "#e87ba4", "christofides": "#008300", "genetico": "#6250d6", "recocido_simulado": "#e34948"}
MARCADOR = {"Exactos": "s", "Heurísticos": "^", "Metaheurísticas": "o"}
FAMILIA_DE = {a: f for f, lista in FAMILIAS.items() for a in lista}

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.titlesize": 10, "axes.titleweight": "bold", "axes.labelsize": 9,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": "#e1e0d9", "grid.linewidth": 0.7,
                     "axes.axisbelow": True, "legend.frameon": False, "legend.fontsize": 8, "pdf.fonttype": 42, "savefig.bbox": "tight",
                     "axes.edgecolor": "#8a8a85", "xtick.color": "#444", "ytick.color": "#444"})


def guardar(fig, nombre):
    fig.savefig(SALIDA / f"{nombre}.pdf")
    plt.close(fig)
    print("figura", nombre)


# ── Datos de la web ────────────────────────────────────────────────────────────
def decodificar(texto):
    pts, i, lat, lon = [], 0, 0, 0
    while i < len(texto):
        for eje in (0, 1):
            r = s = 0
            while True:
                b = ord(texto[i]) - 63
                i += 1
                r |= (b & 0x1F) << s
                s += 5
                if b < 0x20:
                    break
            d = ~(r >> 1) if r & 1 else r >> 1
            if eje == 0:
                lat += d
            else:
                lon += d
        pts.append((lon / 1e4, lat / 1e4))
    return pts


CIUDADES = json.loads((WEB / "ciudades.json").read_text(encoding="utf-8"))
NOMBRES = [c["nombre"] for c in CIUDADES]
CONTORNO = json.loads((WEB / "contorno.json").read_text(encoding="utf-8"))
FONDO = json.loads((WEB / "red_fondo.json").read_text(encoding="utf-8"))
RUTAS = json.loads((WEB / "rutas.json").read_text(encoding="utf-8"))
KX = np.cos(np.radians(40.0))


def mapa_base(ax, red=True):
    for pais, lista in CONTORNO.items():
        for anillo in lista:
            a = np.array(anillo)
            ax.fill(a[:, 0], a[:, 1], color="#f3f2ee" if pais == "Spain" else "#e6e6e1", zorder=1, lw=0)
            ax.plot(a[:, 0], a[:, 1], color="#9a9a95", lw=0.5 if pais != "Spain" else 0.8, zorder=2)
    if red:
        ax.add_collection(LineCollection([[(x1, y1), (x2, y2)] for x1, y1, x2, y2 in FONDO], colors="#b8bfcc", linewidths=0.25, zorder=3))
    ax.set_xlim(-9.75, 3.75)
    ax.set_ylim(35.85, 44.0)
    ax.set_aspect(1 / KX)
    ax.axis("off")
    ax.grid(False)


def geometria(a, b):
    i, j = (a, b) if a < b else (b, a)
    g = decodificar(RUTAS[f"{i}-{j}"])
    return g if a < b else g[::-1]


def dibujar_ruta(ax, ruta, color, lw=1.7, cerrada=True):
    seg = []
    n = len(ruta)
    for k in range(n if cerrada else n - 1):
        seg += geometria(NOMBRES.index(ruta[k]), NOMBRES.index(ruta[(k + 1) % n]))
        seg.append((np.nan, np.nan))
    a = np.array(seg)
    ax.plot(a[:, 0], a[:, 1], color=color, lw=lw, zorder=5, solid_capstyle="round", solid_joinstyle="round")


# ── 1. Red de carreteras y ciudades ───────────────────────────────────────────
def fig_red():
    fig, ax = plt.subplots(figsize=(6.4, 5.0))
    mapa_base(ax)
    cap = [c for c in CIUDADES if c["capital"]]
    otr = [c for c in CIUDADES if not c["capital"]]
    ax.scatter([c["lon"] for c in otr], [c["lat"] for c in otr], s=14, facecolor="white", edgecolor="#d1603d", linewidth=0.9, zorder=6, label="Municipios de más de 100.000 hab. (28)")
    ax.scatter([c["lon"] for c in cap], [c["lat"] for c in cap], s=18, color="#2a78d6", zorder=7, label="Capitales de provincia (47)")
    for nombre, dx, dy in [("Madrid", 0.15, 0.12), ("Barcelona", 0.15, 0.1), ("Sevilla", 0.1, -0.3), ("Valencia", 0.18, -0.05), ("A Coruña", 0.0, 0.2), ("Bilbao", 0.1, 0.12)]:
        c = CIUDADES[NOMBRES.index(nombre)]
        ax.text(c["lon"] + dx, c["lat"] + dy, nombre, fontsize=7.5, color="#222", zorder=8)
    ax.legend(loc="upper center", fontsize=7.5, bbox_to_anchor=(0.5, 0.0), ncol=2, handletextpad=0.3, columnspacing=1.4)
    guardar(fig, "red_ciudades")


# ── 2. Tres rutas de las 47 capitales sobre las carreteras reales ─────────────
def fig_rutas():
    sys.path.insert(0, str(RAIZ / "anexos"))
    import ejecutar_estudio as e
    e._iniciar()
    K = e.NS["cargar_version"]("completo", "capitales", "espana", "km", "grafo_dirigido")
    import contextlib
    import io
    resultados = {}
    with contextlib.redirect_stdout(io.StringIO()):
        for clave in ("vecino_mas_cercano", "dos_opt", "dfj"):
            resultados[clave] = e.FUNCIONES[clave](K, inicio="Madrid")
    fig, ejes = plt.subplots(1, 3, figsize=(10.2, 3.6))
    titulos = {"vecino_mas_cercano": "Vecino más cercano", "dos_opt": "2-opt (desde el vecino más cercano)", "dfj": "DFJ (óptimo)"}
    opt = resultados["dfj"][1]
    for ax, clave in zip(ejes, resultados):
        ruta, coste = resultados[clave]
        mapa_base(ax, red=False)
        dibujar_ruta(ax, ruta, COLOR[clave])
        ax.scatter([CIUDADES[NOMBRES.index(c)]["lon"] for c in ruta], [CIUDADES[NOMBRES.index(c)]["lat"] for c in ruta], s=6, color="#222", zorder=6)
        extra = "" if clave == "dfj" else f" (+{(coste / opt - 1) * 100:.1f} %)".replace(".", ",")
        ax.set_title(f"{titulos[clave]}\n{coste:,.1f} km{extra}".replace(",", "§").replace(".", ",").replace("§", "."), fontsize=9)
    fig.tight_layout()
    guardar(fig, "rutas_47")


# ── 3. Gráficas del estudio ───────────────────────────────────────────────────
def cargar_estudio():
    estudio = pd.read_csv(RES / "estudio_resultados.csv")
    serie = pd.read_csv(RES / "tiempos_serie.csv")
    clave = ["estudio", "aristas", "nodos", "ambito", "peso", "general", "n", "instancia"]
    optimo = estudio[estudio.algoritmo == "dfj"].groupby(clave).coste.first().rename("optimo")
    estudio = estudio.merge(optimo, on=clave)
    estudio["desviacion"] = (estudio.coste / estudio.optimo - 1) * 100
    return estudio, serie


def curvas(serie, columna, ylabel, nombre, general="grafo_dirigido"):
    fig, ejes = plt.subplots(1, 3, figsize=(10.2, 3.5), sharey=True)
    for eje, (familia, algs) in zip(ejes, FAMILIAS.items()):
        for a in algs:
            g = "grafo_simple_no_dirigido" if a == "christofides" else general
            s = serie[(serie.algoritmo == a) & (serie.general == g)].groupby("n")[columna].median()
            if len(s):
                eje.plot(s.index, s.values, color=COLOR[a], marker=MARCADOR[familia], markersize=4, lw=1.5,
                         label=NOMBRE[a] + (" (no dirigido)" if a == "christofides" else ""))
        eje.set_yscale("log")
        eje.set_title(familia)
        eje.set_xlabel("ciudades ($n$)")
    arriba = max(e.get_ylim()[1] for e in ejes)
    ejes[0].set_ylim(top=arriba * 80)
    for e_ in ejes:
        e_.legend(loc="upper left")
    ejes[0].set_ylabel(ylabel)
    fig.tight_layout()
    guardar(fig, nombre)


def fig_desviacion(estudio):
    fig, ejes = plt.subplots(1, 2, figsize=(9.4, 3.6), sharey=True)
    B = estudio[(estudio.estudio == "B") & ~estudio.algoritmo.isin(["fuerza_bruta", "held_karp", "dfj"])]
    for eje, general, titulo in zip(ejes, ["grafo_dirigido", "grafo_simple_no_dirigido"], ["Grafo dirigido", "Grafo no dirigido"]):
        for a in ["vecino_mas_cercano", "dos_opt", "christofides", "genetico", "recocido_simulado"]:
            s = B[(B.algoritmo == a) & (B.general == general)].groupby("n").desviacion.mean()
            if len(s):
                eje.plot(s.index, s.values, color=COLOR[a], marker=MARCADOR[FAMILIA_DE[a]], markersize=4, lw=1.5, label=NOMBRE[a])
        eje.set_title(titulo)
        eje.set_xlabel("ciudades ($n$)")
        eje.legend(loc="upper left")
    ejes[0].set_ylabel("desviación respecto al óptimo (%)")
    fig.tight_layout()
    guardar(fig, "desviacion")


def fig_calidad_tiempo(estudio, serie):
    fig, ejes = plt.subplots(1, 2, figsize=(10.0, 4.0))
    B = estudio[estudio.estudio == "B"]
    for eje, n in zip(ejes, (11, 75)):
        for a in NOMBRE:
            g = "grafo_simple_no_dirigido" if a == "christofides" else "grafo_dirigido"
            t = serie[(serie.algoritmo == a) & (serie.n == n) & (serie.general == g)].segundos.median()
            d = B[(B.algoritmo == a) & (B.n == n) & (B.general == g)].desviacion.mean()
            if np.isnan(t) or np.isnan(d):
                continue
            eje.scatter(t, d, color=COLOR[a], marker=MARCADOR[FAMILIA_DE[a]], s=60, edgecolor="white", linewidth=0.8, zorder=3)
            eje.annotate(NOMBRE[a], (t, d), xytext=(0, 7), textcoords="offset points", ha="center", fontsize=7.5, color="#333")
        eje.set_xscale("log")
        eje.set_ylim(-1.8, eje.get_ylim()[1] * 1.1)
        eje.set_xlabel("tiempo de cálculo (s, escala logarítmica)")
        eje.set_title(f"{n} ciudades")
    ejes[0].set_ylabel("desviación respecto al óptimo (%)")
    fig.tight_layout()
    guardar(fig, "calidad_tiempo")


def fig_dispersion(estudio):
    fig, ejes = plt.subplots(1, 2, figsize=(7.6, 3.4), sharey=True)
    S = estudio[(estudio.estudio == "B") & (estudio.general == "grafo_dirigido") & estudio.algoritmo.isin(["genetico", "recocido_simulado"])]
    rng = np.random.default_rng(42)
    for eje, n in zip(ejes, (47, 75)):
        for i, a in enumerate(["genetico", "recocido_simulado"]):
            v = S[(S.algoritmo == a) & (S.n == n)].desviacion.values
            eje.scatter(i + rng.uniform(-0.12, 0.12, len(v)), v, color=COLOR[a], s=26, alpha=0.85, edgecolor="white", linewidth=0.6, zorder=3)
            eje.hlines(np.median(v), i - 0.25, i + 0.25, color="#111", lw=1.8, zorder=4)
        eje.set_xticks([0, 1])
        eje.set_xticklabels(["Genético", "Recocido simulado"])
        eje.set_xlim(-0.6, 1.6)
        eje.set_title(f"{n} ciudades")
    ejes[0].set_ylabel("desviación respecto al óptimo (%)")
    fig.tight_layout()
    guardar(fig, "dispersion")


def recortar_capturas():
    """Recorta las capturas de la web (quita el panel lateral de ciudades) para que se lean mejor impresas."""
    from PIL import Image
    origen = RAIZ / "web" / "capturas"
    for nombre in ("05_dfj_circuitos_sueltos", "06_dfj_optimo_47_capitales", "10_carrera"):
        f = origen / f"{nombre}.png"
        if f.exists():
            im = Image.open(f)
            im.crop((268, 0, im.width, im.height)).save(SALIDA / f"web_{nombre}.png")
            print("captura", nombre)


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    recortar_capturas()
    fig_red()
    fig_rutas()
    estudio, serie = cargar_estudio()
    curvas(serie, "segundos", "tiempo (s, escala logarítmica)", "curvas_tiempo")
    curvas(serie, "memoria_mb", "pico de memoria (MB, escala logarítmica)", "curvas_memoria")
    fig_desviacion(estudio)
    fig_calidad_tiempo(estudio, serie)
    fig_dispersion(estudio)


if __name__ == "__main__":
    main()

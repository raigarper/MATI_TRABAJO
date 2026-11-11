"""Prepara los datos de la web (carpeta web/data/) a partir del grafo del trabajo.

    python web/herramientas/preparar_datos.py

Necesita el grafo grande (`data/espana_red_maestra_secundarias.graphml`, ver anexos A y B) y unos 4 GB de memoria libre.
Genera, en `web/data/`:

    ciudades.json    las 75 ciudades (nombre, coordenadas, población, comunidad, si es capital)
    matrices.json    distancias entre ciudades: km y tiempo, con sentidos únicos (dirigido) y sin ellos (no dirigido)
    rutas.json       trazado REAL por carretera entre cada par de ciudades (camino mínimo en el grafo, simplificado y codificado)
    red_fondo.json   autovías y vías rápidas, para dibujarlas de fondo
    contorno.json    contorno de la península y de los países vecinos

El resultado se guarda en el repositorio: la web no necesita el grafo para funcionar.
"""
from __future__ import annotations

import csv
import json
import math
import sys
import urllib.request
from pathlib import Path

import networkx as nx
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree
from shapely.geometry import LineString, Polygon, box

RAIZ = Path(__file__).resolve().parent.parent.parent
SALIDA = RAIZ / "web" / "data"
KM_LON = 111.32 * math.cos(math.radians(40.4))
KM_LAT = 110.57
X_KM = 10                       # igual que en la Parte 2: una ciudad a más de 10 km de la red queda fuera
TOL_RUTAS = 0.004               # tolerancia de simplificación de las rutas (grados ≈ 400 m)
MARCO = box(-11, 34.5, 5.5, 45)  # marco del mapa (lon, lat)
PRECISION = 1e4                 # las coordenadas se guardan con 4 decimales (≈ 11 m)


def codificar(puntos: list[tuple[float, float]]) -> str:
    """Codificación de polilíneas de Google (lat, lon) con 4 decimales: unos 5 caracteres por punto."""
    salida, ultima = [], (0, 0)
    for lon, lat in puntos:
        actual = (round(lat * PRECISION), round(lon * PRECISION))
        for valor in (actual[0] - ultima[0], actual[1] - ultima[1]):
            valor = ~(valor << 1) if valor < 0 else valor << 1
            while valor >= 0x20:
                salida.append(chr((0x20 | (valor & 0x1F)) + 63))
                valor >>= 5
            salida.append(chr(valor + 63))
        ultima = actual
    return "".join(salida)


def leer_tabla(ruta: Path):
    with open(ruta, encoding="utf-8") as f:
        nombres = f.readline().strip().split(",")
    return np.loadtxt(ruta, delimiter=",", skiprows=1, encoding="utf-8"), nombres


def ciudades_y_matrices():
    with open(RAIZ / "data" / "ciudades.csv", encoding="utf-8") as f:
        filas = {r["nombre"]: r for r in csv.DictReader(f)}
    tablas = {}
    for peso in ("km", "tiempo"):
        for sentido in ("dirigido", "no_dirigido"):
            D, nombres = leer_tabla(RAIZ / "data" / "versiones" / f"completo__{peso}__{sentido}.csv")
            tablas[f"{peso}_{sentido}"] = D
    ciudades = [{"nombre": n, "lat": float(filas[n]["lat"]), "lon": float(filas[n]["lon"]), "poblacion": int(filas[n]["poblacion_2025"]),
                 "capital": filas[n]["capital_provincia"] == "True", "comunidad": filas[n]["comunidad"]} for n in nombres]
    matrices = {"ciudades": nombres,
                "km_dirigido": np.round(tablas["km_dirigido"], 3).tolist(), "km_no_dirigido": np.round(tablas["km_no_dirigido"], 3).tolist(),
                "tiempo_dirigido": np.round(tablas["tiempo_dirigido"]).astype(int).tolist(),
                "tiempo_no_dirigido": np.round(tablas["tiempo_no_dirigido"]).astype(int).tolist()}
    return ciudades, matrices


def rutas_y_red(ciudades):
    print("Cargando el grafo (≈ 25 s y varios GB de memoria)...", flush=True)
    G = nx.read_graphml(RAIZ / "data" / "espana_red_maestra_secundarias.graphml", node_type=int)
    nodos = list(G.nodes)
    indice = {n: i for i, n in enumerate(nodos)}
    xs = np.array([G.nodes[n]["x"] for n in nodos])
    ys = np.array([G.nodes[n]["y"] for n in nodos])

    # Asociar cada ciudad con su nodo más cercano (como en la Parte 2)
    arbol = cKDTree(np.column_stack([xs * KM_LON, ys * KM_LAT]))
    origenes = []
    for c in ciudades:
        d, i = arbol.query([c["lon"] * KM_LON, c["lat"] * KM_LAT])
        assert d <= X_KM, f"{c['nombre']} está a {d:.1f} km de la red"
        origenes.append(int(i))

    # Matriz de adyacencia dirigida con la longitud mínima entre cada par de nodos (grafo simple)
    mejor = {}
    fondo = set()
    for u, v, d in G.edges(data=True):
        par = (indice[u], indice[v])
        if par not in mejor or d["length"] < mejor[par]:
            mejor[par] = d["length"]
        if d["highway"] in ("motorway", "trunk"):                 # autovías y vías rápidas para el fondo
            fondo.add((min(par), max(par)))
    M = csr_matrix((list(mejor.values()), ([p[0] for p in mejor], [p[1] for p in mejor])), shape=(len(nodos), len(nodos)))
    print(f"{len(nodos)} nodos, {len(mejor)} aristas. Calculando caminos mínimos desde {len(origenes)} ciudades...", flush=True)
    _, pred = dijkstra(M, directed=True, indices=origenes, return_predecessors=True)

    n = len(ciudades)
    rutas = {}
    for i in range(n):
        for j in range(i + 1, n):
            camino, k = [], origenes[j]
            while k != origenes[i] and k >= 0:
                camino.append(k)
                k = pred[i, k]
            camino.append(origenes[i])
            camino.reverse()
            puntos = [(ciudades[i]["lon"], ciudades[i]["lat"])] + [(xs[k], ys[k]) for k in camino] + [(ciudades[j]["lon"], ciudades[j]["lat"])]
            simple = list(LineString(puntos).simplify(TOL_RUTAS).coords) if len(puntos) > 2 else puntos
            rutas[f"{i}-{j}"] = codificar(simple)
        if i % 10 == 0:
            print(f"  ciudad {i + 1}/{n}", flush=True)

    segmentos = [[round(float(xs[a]), 2), round(float(ys[a]), 2), round(float(xs[b]), 2), round(float(ys[b]), 2)] for a, b in sorted(fondo)]
    return rutas, segmentos


def contorno():
    """Contorno de la península y países vecinos, a partir de Natural Earth (world-atlas), simplificado."""
    url = "https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-50m.json"
    print("Descargando contornos...", flush=True)
    topo = json.load(urllib.request.urlopen(url, timeout=60))
    esc, tra = topo["transform"]["scale"], topo["transform"]["translate"]
    arcos = []
    for arco in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arco:
            x += dx
            y += dy
            pts.append((x * esc[0] + tra[0], y * esc[1] + tra[1]))
        arcos.append(pts)

    def anillo(indices):
        pts = []
        for a in indices:
            tramo = arcos[a] if a >= 0 else arcos[~a][::-1]
            pts.extend(tramo if not pts else tramo[1:])
        return pts

    resultado = {}
    for g in topo["objects"]["countries"]["geometries"]:
        nombre = g["properties"]["name"]
        if nombre not in ("Spain", "Portugal", "France", "Andorra", "Morocco", "Algeria"):
            continue
        poligonos = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        lista = []
        for poligono in poligonos:
            pol = Polygon(anillo(poligono[0]))
            if nombre == "Spain" and pol.area < 5:             # de España, solo la península (sin islas ni Ceuta y Melilla)
                continue
            recorte = pol.simplify(0.01).intersection(MARCO)   # lo que cae dentro del marco del mapa
            for parte in ([recorte] if recorte.geom_type == "Polygon" else list(getattr(recorte, "geoms", []))):
                if parte.geom_type == "Polygon" and parte.area > 0.01:
                    lista.append([[round(x, 2), round(y, 2)] for x, y in parte.exterior.coords])
        if lista:
            resultado[nombre] = lista
    return resultado


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    ciudades, matrices = ciudades_y_matrices()
    (SALIDA / "ciudades.json").write_text(json.dumps(ciudades, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (SALIDA / "matrices.json").write_text(json.dumps(matrices, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (SALIDA / "contorno.json").write_text(json.dumps(contorno(), separators=(",", ":")), encoding="utf-8")
    rutas, segmentos = rutas_y_red(ciudades)
    (SALIDA / "rutas.json").write_text(json.dumps(rutas, separators=(",", ":")), encoding="utf-8")
    (SALIDA / "red_fondo.json").write_text(json.dumps(segmentos, separators=(",", ":")), encoding="utf-8")
    for f in sorted(SALIDA.glob("*.json")):
        print(f"{f.name}: {f.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()

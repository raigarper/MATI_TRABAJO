"""ANEXO B. Construcción del grafo de la red vial de la España peninsular.

Entrada:  data/spain-latest.osm.pbf        (se obtiene con el Anexo A, `descargar_red.py`)
Salida:   data/espana_red_maestra.graphml  (grafo dirigido, cargable con NetworkX puro)

Pasos:
  1. Leer del extracto las vías `highway` = motorway, trunk, primary (y sus enlaces `_link`).
  2. Construir el grafo (nodos = intersecciones, aristas = tramos) con OSMnx.
  3. Quedarse con la componente principal (península), simplificar la topología y
     garantizar la conectividad fuerte.
  4. Calcular velocidad (`speed_kph`) y tiempo de viaje (`travel_time`) de cada tramo y limpiar
     los atributos.
  5. Guardar en GraphML con tipos reales (números, booleanos) y comprobar que se puede releer.

Si el grafo ya existe, lo avisa y termina (salvo `--forzar`).

Uso:
    python anexos/construir_grafo.py
    python anexos/construir_grafo.py --forzar
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from collections import Counter
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from typing import Any, Iterator

import networkx as nx
import osmium
import osmnx as ox
from osmnx import graph as ox_graph

LOG = logging.getLogger("construir_grafo")

RAIZ = Path(__file__).resolve().parent.parent          # carpeta del proyecto
URL_ESPANA = "https://download.geofabrik.de/europe/spain-latest.osm.pbf"
NOMBRE_GRAFO = "espana_red_maestra.graphml"

# Tipos de vía que se conservan, de mayor a menor importancia. Se usa este orden para
# elegir UN único `highway` cuando la simplificación fusiona tramos de tipos distintos.
JERARQUIA: tuple[str, ...] = (
    "motorway", "motorway_link",
    "trunk", "trunk_link",
    "primary", "primary_link",
)


def ruta_visible(ruta: Path) -> str:
    try:
        return str(ruta.resolve().relative_to(RAIZ))
    except ValueError:
        return str(ruta)


def _fmt(segundos: float) -> str:
    return str(timedelta(seconds=int(segundos)))


@contextmanager
def cronometro(descripcion: str) -> Iterator[None]:
    LOG.info("▶ %s...", descripcion)
    t0 = time.perf_counter()
    try:
        yield
    finally:
        LOG.info("✔ %s (%.1f s)", descripcion, time.perf_counter() - t0)


# ── 1. Lectura del extracto ──────────────────────────────────────────────────

def leer_carreteras(pbf: Path) -> dict[str, Any]:
    """Dos pasadas con pyosmium: 1) vías (ways) de los tipos elegidos, 2) coordenadas de sus nodos.

    Devuelve un dict con la misma forma que una respuesta de la API Overpass, para poder
    reutilizar la construcción de grafos de OSMnx.
    """
    filtro_vias = osmium.filter.TagFilter(*[("highway", tipo) for tipo in JERARQUIA])

    ways: list[dict[str, Any]] = []
    ids_nodos: set[int] = set()
    with cronometro("Pasada 1/2: leyendo vías"):
        for w in osmium.FileProcessor(str(pbf), osmium.osm.WAY).with_filter(filtro_vias):
            refs = [n.ref for n in w.nodes]
            ways.append({"type": "way", "id": w.id, "nodes": refs,
                         "tags": {t.k: t.v for t in w.tags}})
            ids_nodos.update(refs)
    LOG.info("Vías encontradas: %d | nodos referenciados: %d", len(ways), len(ids_nodos))

    nodos: dict[int, dict[str, Any]] = {}
    with cronometro("Pasada 2/2: leyendo coordenadas de nodos"):
        for n in osmium.FileProcessor(str(pbf), osmium.osm.NODE).with_filter(
                osmium.filter.IdFilter(ids_nodos)):
            if n.location.valid():
                nodos[n.id] = {"type": "node", "id": n.id,
                               "lat": n.location.lat, "lon": n.location.lon}

    # El extracto está recortado en la frontera: se descartan referencias a nodos ausentes.
    validas: list[dict[str, Any]] = []
    for w in ways:
        w["nodes"] = [r for r in w["nodes"] if r in nodos]
        if len(w["nodes"]) >= 2:
            validas.append(w)
    LOG.info("Vías válidas tras recorte: %d | nodos con coordenadas: %d", len(validas), len(nodos))
    return {"elements": list(nodos.values()) + validas}


# ── 2-3. Construcción del grafo ──────────────────────────────────────────────

def construir_grafo(respuesta: dict[str, Any]) -> nx.MultiDiGraph:
    """Mismo procesamiento que `ox.graph_from_polygon` (simplificar, quedarse con la componente principal)."""
    with cronometro("Construyendo el grafo"):
        G = ox_graph._create_graph([respuesta], bidirectional=False)
    with cronometro("Quedándose con la componente principal (península)"):
        # Baleares, Canarias, Ceuta y Melilla son componentes disjuntas y mucho menores.
        G = ox.truncate.largest_component(G, strongly=False)
    with cronometro("Simplificando la topología"):
        G = ox.simplify_graph(G)
        nx.set_node_attributes(G, ox.stats.count_streets_per_node(G), "street_count")
    with cronometro("Garantizando la conectividad fuerte"):
        G = ox.truncate.largest_component(G, strongly=True)
    return G


# ── 4. Atributos ─────────────────────────────────────────────────────────────

def _valores(x: Any) -> list[str]:
    """Convierte un atributo (None, texto o lista) en lista de textos no vacíos."""
    if x is None:
        return []
    return [str(v).strip() for v in (x if isinstance(x, (list, tuple, set)) else [x]) if str(v).strip()]


def _unir(x: Any, separador: str) -> str | None:
    """Une los valores de un atributo en un solo texto, sin repetidos (sin distinguir mayúsculas)."""
    vistos: dict[str, str] = {}
    for v in _valores(x):
        vistos.setdefault(v.upper(), v)
    return separador.join(vistos.values()) or None


def _highway_principal(x: Any) -> str:
    candidatos = _valores(x)
    for tipo in JERARQUIA:
        if tipo in candidatos:
            return tipo
    return candidatos[0]


def preparar_atributos(G: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """Calcula velocidades y tiempos y deja SOLO los atributos que se van a usar, ya con tipos simples.

    Aristas: highway, ref, name, oneway, length, speed_kph, travel_time.
    Nodos:   x, y, street_count.
    """
    with cronometro("Calculando velocidades (speed_kph) y tiempos (travel_time)"):
        G = ox.add_edge_speeds(G)          # usa `maxspeed`; si falta, la media de su tipo de vía
        G = ox.add_edge_travel_times(G)    # segundos = length / velocidad

    with cronometro("Limpiando atributos"):
        for _, _, _, d in G.edges(keys=True, data=True):
            limpio: dict[str, Any] = {
                "highway": _highway_principal(d["highway"]),
                "oneway": bool(d["oneway"]),
                "length": float(d["length"]),
                "speed_kph": float(d["speed_kph"]),
                "travel_time": float(d["travel_time"]),
            }
            ref = _unir(d.get("ref"), ";")        # código de la carretera: AP-7, A-4, N-340...
            nombre = _unir(d.get("name"), " / ")  # nombre en lenguaje natural
            if ref:
                limpio["ref"] = ref
            if nombre:
                limpio["name"] = nombre
            d.clear()
            d.update(limpio)
        for _, d in G.nodes(data=True):
            x, y, calles = float(d["x"]), float(d["y"]), int(d["street_count"])
            d.clear()
            d.update(x=x, y=y, street_count=calles)
        G.graph = {k: (v if isinstance(v, (str, int, float, bool)) else str(v))
                   for k, v in G.graph.items()}
    return G


# ── 5. Guardado, resumen y validación ────────────────────────────────────────

def guardar_grafo(G: nx.MultiDiGraph, ruta: Path) -> None:
    """Guarda con NetworkX: el GraphML declara los tipos reales (double, long, boolean)."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    nx.write_graphml(G, ruta)


def mostrar_resumen(G: nx.MultiDiGraph, ruta: Path) -> None:
    aristas = [d for _, _, d in G.edges(data=True)]
    km_total = sum(d["length"] for d in aristas) / 1000
    LOG.info("─── RESUMEN ───")
    LOG.info("Nodos:   %d", G.number_of_nodes())
    LOG.info("Aristas: %d (%.0f km contando cada sentido)", len(aristas), km_total)
    LOG.info("Aristas por tipo de vía (nº aristas | km):")
    n_tipo, km_tipo = Counter(d["highway"] for d in aristas), Counter()
    for d in aristas:
        km_tipo[d["highway"]] += d["length"] / 1000
    for tipo, n in n_tipo.most_common():
        LOG.info("  %-15s %7d | %8.0f km", tipo, n, km_tipo[tipo])
    sentido = Counter(d["oneway"] for d in aristas)
    LOG.info("Sentido único (oneway=True): %d | doble sentido: %d", sentido[True], sentido[False])
    paralelas = sum(1 for u, v in {(u, v) for u, v in G.edges()} if G.number_of_edges(u, v) > 1)
    LOG.info("Pares de nodos con aristas paralelas: %d", paralelas)
    LOG.info("Nodos por street_count (calles que confluyen): %s",
             dict(sorted(Counter(d["street_count"] for _, d in G.nodes(data=True)).items())))
    con_ref = sum(d["length"] for d in aristas if "ref" in d) / 1000
    con_nombre = sum(d["length"] for d in aristas if "name" in d) / 1000
    LOG.info("Cobertura de `ref`: %.1f %% de los km | de `name`: %.1f %%",
             100 * con_ref / km_total, 100 * con_nombre / km_total)
    LOG.info("Archivo: %s (%.1f MB)", ruta_visible(ruta), ruta.stat().st_size / 1024**2)


def validar_grafo(ruta: Path) -> bool:
    """Relee el GraphML con NetworkX puro y comprueba tipos, atributos y conectividad."""
    try:
        with cronometro(f"Validando {ruta_visible(ruta)} con nx.read_graphml"):
            H = nx.read_graphml(ruta, node_type=int)
            if not isinstance(H, nx.MultiDiGraph) or H.number_of_edges() == 0:
                raise ValueError("no es un MultiDiGraph con aristas")
            for _, d in H.nodes(data=True):
                if not (isinstance(d["x"], float) and isinstance(d["y"], float)
                        and isinstance(d["street_count"], int)):
                    raise TypeError(f"tipos de nodo incorrectos: {d}")
            for _, _, d in H.edges(data=True):
                if not (isinstance(d["length"], float) and d["length"] > 0
                        and isinstance(d["travel_time"], float)
                        and isinstance(d["speed_kph"], float)
                        and isinstance(d["oneway"], bool)
                        and d["highway"] in JERARQUIA):
                    raise TypeError(f"tipos o valores de arista incorrectos: {d}")
            if not nx.is_strongly_connected(H):
                raise ValueError("el grafo no es fuertemente conexo")
        LOG.info("Validación OK: %d nodos, %d aristas, tipos correctos y fuertemente conexo",
                 H.number_of_nodes(), H.number_of_edges())
        return True
    except (OSError, KeyError, TypeError, ValueError, nx.NetworkXError) as exc:
        LOG.error("Validación FALLIDA: %s: %s", type(exc).__name__, exc)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--forzar", action="store_true",
                        help="reconstruir aunque el grafo ya exista")
    parser.add_argument("--datos", type=Path, default=RAIZ / "data",
                        help="carpeta de datos (por defecto, data/); útil para pruebas")
    parser.add_argument("--pbf-url", default=URL_ESPANA,
                        help="URL del extracto usado en el Anexo A (solo para saber el nombre del archivo)")
    args = parser.parse_args()

    carpeta_log = args.datos.resolve().parent / "docs"
    carpeta_log.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(), logging.FileHandler(carpeta_log / "construccion.log", encoding="utf-8")],
    )
    ox.settings.use_cache = False   # no se hacen peticiones web: no hace falta carpeta de caché

    grafo = args.datos / NOMBRE_GRAFO
    pbf = args.datos / Path(args.pbf_url).name

    if grafo.exists() and not args.forzar:
        LOG.info("El grafo ya está construido en el archivo %s (usa --forzar para reconstruirlo)",
                 ruta_visible(grafo))
        return 0
    if not pbf.exists():
        LOG.error("Falta el extracto %s. Ejecuta primero: python anexos/descargar_red.py", ruta_visible(pbf))
        return 1

    t0 = time.perf_counter()
    try:
        respuesta = leer_carreteras(pbf)
        G = construir_grafo(respuesta)
        del respuesta
        G = preparar_atributos(G)
        with cronometro(f"Guardando {ruta_visible(grafo)}"):
            guardar_grafo(G, grafo)
    except Exception:
        LOG.exception("Error durante la construcción")
        return 1

    mostrar_resumen(G, grafo)
    ok = validar_grafo(grafo)
    LOG.info("Tiempo total: %s", _fmt(time.perf_counter() - t0))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

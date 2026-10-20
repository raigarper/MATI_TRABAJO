"""ANEXO B. Construcción del grafo de la red vial de la España peninsular.

Entrada:  data/spain-latest.osm.pbf                      (se obtiene con el Anexo A, `descargar_red.py`)
Salida:   data/espana_red_maestra_secundarias.graphml    (grafo BASE del trabajo; dirigido, cargable
          con NetworkX puro). Con `--ligero`: data/espana_red_maestra.graphml (sin secundarias).

Pasos:
  1. Leer del extracto las vías `highway` = motorway, trunk, primary y secondary (y sus enlaces
     `_link`). Con `--ligero` se omiten las secundarias (grafo más pequeño: 108.050 nodos).
  2. Construir el grafo (nodos = intersecciones, aristas = tramos) y simplificarlo.
  3. Quedarse con la componente principal (península) y garantizar la conectividad fuerte.
  4. Calcular velocidad (`speed_kph`) y tiempo de viaje (`travel_time`) de cada tramo y limpiar
     los atributos.
  5. Guardar en GraphML con tipos reales (números, booleanos) y comprobar que se puede releer.

La construcción y la simplificación se hacen con arrays (NumPy) y aplican las mismas reglas que
`osmnx.simplify_graph`, pero sin crear antes un grafo de NetworkX con millones de nodos: gasta
mucha menos memoria (la versión con secundarias no cabría de la otra forma).

Si el grafo ya existe, lo avisa y termina (salvo `--forzar`).

Uso:
    python anexos/construir_grafo.py            # grafo base: con secundarias
    python anexos/construir_grafo.py --ligero   # grafo ligero: solo motorway, trunk y primary
    python anexos/construir_grafo.py --forzar   # reconstruir aunque ya exista
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from array import array
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterator, NamedTuple

import networkx as nx
import numpy as np
import osmium
import osmnx as ox
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

LOG = logging.getLogger("construir_grafo")

RAIZ = Path(__file__).resolve().parent.parent          # carpeta del proyecto
URL_ESPANA = "https://download.geofabrik.de/europe/spain-latest.osm.pbf"

# Tipos de vía que se conservan, de mayor a menor importancia. Se usa este orden para
# elegir UN único `highway` cuando la simplificación fusiona tramos de tipos distintos.
JERARQUIA: tuple[str, ...] = (
    "motorway", "motorway_link",
    "trunk", "trunk_link",
    "primary", "primary_link",
)
JERARQUIA_SECUNDARIAS: tuple[str, ...] = JERARQUIA + ("secondary", "secondary_link")

# Valores de la etiqueta `oneway` de OSM (los mismos que usa OSMnx)
ONEWAY = {"yes", "true", "1", "-1", "reverse", "T", "F"}   # la vía es de sentido único
INVERTIDA = {"-1", "reverse", "T"}                         # ... y va contra el orden de sus nodos


def nombre_grafo(ligero: bool) -> str:
    return "espana_red_maestra.graphml" if ligero else "espana_red_maestra_secundarias.graphml"


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

class Vias(NamedTuple):
    """Vías leídas del extracto, en arrays compactos."""
    ids: np.ndarray            # ids (OSM) de los nodos usados, ordenados
    lat: np.ndarray            # latitud de cada nodo (NaN si falta en el extracto)
    lon: np.ndarray            # longitud de cada nodo
    nodos: np.ndarray          # nodos de todas las vías seguidos, como posiciones en `ids`
    fin: np.ndarray            # fin[k] = posición en `nodos` donde acaba la vía k
    etiquetas: list[tuple]     # por vía: (highway, oneway, junction, maxspeed, name, ref)


def leer_vias(pbf: Path, tipos: tuple[str, ...]) -> Vias:
    """Dos pasadas con pyosmium: 1) vías de los tipos elegidos, 2) coordenadas de sus nodos."""
    filtro = osmium.filter.TagFilter(*[("highway", t) for t in tipos])
    refs, fin = array("q"), array("q")
    etiquetas: list[tuple] = []
    with cronometro("Pasada 1/2: leyendo vías"):
        for w in osmium.FileProcessor(str(pbf), osmium.osm.WAY).with_filter(filtro):
            t = w.tags
            etiquetas.append((t["highway"], t.get("oneway"), t.get("junction"),
                              t.get("maxspeed"), t.get("name"), t.get("ref")))
            refs.extend(n.ref for n in w.nodes)
            fin.append(len(refs))
    refs_np = np.frombuffer(refs, dtype=np.int64)
    ids = np.unique(refs_np)
    LOG.info("Vías encontradas: %d | nodos distintos: %d", len(etiquetas), len(ids))

    lat, lon = np.full(len(ids), np.nan), np.full(len(ids), np.nan)
    with cronometro("Pasada 2/2: leyendo coordenadas de nodos"):
        for n in osmium.FileProcessor(str(pbf), osmium.osm.NODE).with_filter(
                osmium.filter.IdFilter(ids.tolist())):
            if n.location.valid():
                i = np.searchsorted(ids, n.id)
                lat[i], lon[i] = n.location.lat, n.location.lon
    LOG.info("Nodos con coordenadas: %d (el extracto está recortado en la frontera)",
             int(np.sum(~np.isnan(lat))))
    return Vias(ids, lat, lon, np.searchsorted(ids, refs_np), np.frombuffer(fin, dtype=np.int64), etiquetas)


# ── 2-3. Construcción y simplificación ───────────────────────────────────────

def _aristas_crudas(v: Vias) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Aristas dirigidas entre nodos consecutivos de cada vía (como en `osmnx.graph_from_*`).

    Una vía de sentido único da aristas en un solo sentido; una de doble sentido, en los dos.
    Devuelve (origen, destino, vía de la que procede), con nodos como posiciones en `v.ids`.
    """
    con_coordenadas = ~np.isnan(v.lat)
    us, vs, ws = [], [], []
    ini = 0
    for k, (_, ow, junc, *_) in enumerate(v.etiquetas):
        nd, ini = v.nodos[ini:v.fin[k]], int(v.fin[k])
        nd = nd[con_coordenadas[nd]]                           # fuera: nodos sin coordenadas
        if len(nd) > 1:
            nd = nd[np.r_[True, nd[1:] != nd[:-1]]]            # fuera: nodos repetidos seguidos
        if len(nd) < 2:
            continue
        sentido_unico = ow in ONEWAY or junc == "roundabout"
        if sentido_unico and ow in INVERTIDA:
            nd = nd[::-1]
        a, b = nd[:-1], nd[1:]
        us.append(a); vs.append(b); ws.append(np.full(len(a), k, dtype=np.int32))
        if not sentido_unico:
            us.append(b); vs.append(a); ws.append(np.full(len(a), k, dtype=np.int32))
    return np.concatenate(us), np.concatenate(vs), np.concatenate(ws)


def _es_extremo(eu: np.ndarray, ev: np.ndarray, n: int) -> np.ndarray:
    """Nodos que son extremo "de verdad" de una arista (reglas de `osmnx.simplification`).

    Un nodo NO es extremo (es solo un punto intermedio del trazado) si tiene exactamente dos
    vecinos, 2 o 4 aristas en total, y ninguna es un bucle; todos los demás (intersecciones,
    finales de carretera, cambios de sentido único a doble...) son extremos.
    """
    salientes, entrantes = np.bincount(eu, minlength=n), np.bincount(ev, minlength=n)
    grado = salientes + entrantes
    bucle = np.zeros(n, bool)
    bucle[eu[eu == ev]] = True
    sin_bucle = eu != ev
    a, b = np.minimum(eu[sin_bucle], ev[sin_bucle]), np.maximum(eu[sin_bucle], ev[sin_bucle])
    pares = np.unique(a.astype(np.int64) * n + b)              # pares de vecinos distintos
    vecinos = np.bincount(pares // n, minlength=n) + np.bincount(pares % n, minlength=n)
    intermedio = (vecinos == 2) & ((grado == 2) | (grado == 4)) & ~bucle & (salientes > 0) & (entrantes > 0)
    return ~intermedio


def _unico_o_lista(valores: set[Any]) -> Any:
    """Un solo valor si todos coinciden; si no, lista ordenada (como hace OSMnx al fusionar)."""
    return next(iter(valores)) if len(valores) == 1 else sorted(valores, key=str)


def construir_grafo(v: Vias) -> nx.MultiDiGraph:
    """Construye y simplifica el grafo con arrays; equivale a `graph_from_*` + `simplify_graph`."""
    with cronometro("Creando las aristas dirigidas"):
        eu, ev, ew = _aristas_crudas(v)
        LOG.info("Aristas antes de simplificar: %d", len(eu))

    with cronometro("Quedándose con la componente principal (península)"):
        # Baleares, Canarias, Ceuta y Melilla son componentes disjuntas y mucho menores.
        n = len(v.ids)
        _, comp = connected_components(coo_matrix((np.ones(len(eu), np.int8), (eu, ev)), shape=(n, n)),
                                       directed=True, connection="weak")
        dentro = (comp == np.bincount(comp).argmax())[eu]
        eu, ev, ew = eu[dentro], ev[dentro], ew[dentro]

    with cronometro("Calculando las longitudes (metros)"):
        largo = ox.distance.great_circle(v.lat[eu], v.lon[eu], v.lat[ev], v.lon[ev])
        largo[np.isnan(largo)] = 0

    with cronometro("Simplificando la topología"):
        extremo = _es_extremo(eu, ev, n)
        orden = np.argsort(eu, kind="stable")                  # aristas agrupadas por origen,
        su, sv, sw, sl = eu[orden], ev[orden], ew[orden], largo[orden]   # en el mismo orden de creación
        indptr = np.searchsorted(su, np.arange(n + 1))
        et = v.etiquetas

        def sucesores(x: int) -> dict[int, int]:
            """Sucesores distintos de x, cada uno con la posición de su primera arista."""
            a, b = int(indptr[x]), int(indptr[x + 1])
            d: dict[int, int] = {}
            for desp, y in enumerate(sv[a:b].tolist()):
                d.setdefault(y, a + desp)
            return d

        def camino(origen: int, primero: int, pos0: int) -> tuple[list[int], list[int]]:
            """Sigue la carretera desde un extremo hasta el siguiente (`osmnx._build_path`)."""
            ruta, posiciones = [origen, primero], [pos0]
            for este, p in sucesores(primero).items():
                if este not in ruta:
                    ruta.append(este); posiciones.append(p)
                    while not extremo[este]:
                        libres = [(y, q) for y, q in sucesores(este).items() if y not in ruta]
                        if len(libres) == 1:
                            este, q = libres[0]
                            ruta.append(este); posiciones.append(q)
                        elif not libres:
                            vuelta = sucesores(este).get(origen)
                            if vuelta is not None:             # carretera que se cierra sobre sí misma
                                ruta.append(origen); posiciones.append(vuelta)
                            return ruta, posiciones
                        else:
                            raise RuntimeError(f"Patrón de simplificación imposible cerca de {este}")
                    return ruta, posiciones
            return ruta, posiciones

        def atributos(vias: set[int], longitud: float) -> dict[str, Any]:
            """Atributos de una arista a partir de las vías que la forman."""
            valores: dict[str, set] = {"highway": set(), "maxspeed": set(), "name": set(), "ref": set(),
                                       "oneway": set()}
            for k in vias:
                hw, ow, junc, ms, nombre, ref = et[k]
                valores["highway"].add(hw)
                valores["oneway"].add(ow in ONEWAY or junc == "roundabout")
                for clave, valor in (("maxspeed", ms), ("name", nombre), ("ref", ref)):
                    if valor is not None:
                        valores[clave].add(valor)
            d = {k: _unico_o_lista(s) for k, s in valores.items() if s}
            d["length"] = longitud
            return d

        aristas: list[tuple[int, int, dict[str, Any]]] = []
        for x in np.flatnonzero(extremo & (np.bincount(eu, minlength=n) > 0)).tolist():
            for y, pos in sucesores(x).items():
                if extremo[y]:
                    continue                                    # arista directa: se trata abajo
                ruta, posiciones = camino(x, y, pos)
                aristas.append((ruta[0], ruta[-1],
                                atributos({int(sw[p]) for p in posiciones}, sum(sl[p] for p in posiciones))))
        # aristas entre dos extremos consecutivos: se conservan tal cual (también las paralelas)
        for p in np.flatnonzero(extremo[su] & extremo[sv]).tolist():
            aristas.append((int(su[p]), int(sv[p]), atributos({int(sw[p])}, float(sl[p]))))
        LOG.info("Aristas tras simplificar: %d", len(aristas))

    with cronometro("Montando el grafo de NetworkX"):
        G = nx.MultiDiGraph(created_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            created_with="anexos/construir_grafo.py (OSMnx " + ox.__version__ + ")",
                            crs="epsg:4326", simplified=True)
        usados = {x for u, w, _ in aristas for x in (u, w)}
        G.add_nodes_from((int(v.ids[i]), {"y": float(v.lat[i]), "x": float(v.lon[i])}) for i in usados)
        G.add_edges_from((int(v.ids[u]), int(v.ids[w]), d) for u, w, d in aristas)
        nx.set_node_attributes(G, ox.stats.count_streets_per_node(G), "street_count")
        LOG.info("Grafo: %d nodos, %d aristas", G.number_of_nodes(), G.number_of_edges())

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


def _highway_principal(x: Any, tipos: tuple[str, ...]) -> str:
    candidatos = _valores(x)
    for tipo in tipos:
        if tipo in candidatos:
            return tipo
    return candidatos[0]


def preparar_atributos(G: nx.MultiDiGraph, tipos: tuple[str, ...]) -> nx.MultiDiGraph:
    """Calcula velocidades y tiempos y deja SOLO los atributos que se van a usar, ya con tipos simples.

    Aristas: highway, ref, name, oneway, length, speed_kph, travel_time.
    Nodos:   x, y, street_count.
    """
    with cronometro("Calculando velocidades (speed_kph) y tiempos (travel_time)"):
        # Una arista que fusiona tramos de tipos distintos lleva una lista de `highway`; OSMnx se
        # quedaría con un elemento cualquiera para imputar la velocidad. Se elige el principal
        # (el de mayor jerarquía), así el resultado es siempre el mismo.
        for _, _, _, d in G.edges(keys=True, data=True):
            d["highway"] = _highway_principal(d["highway"], tipos)
        G = ox.add_edge_speeds(G)          # usa `maxspeed`; si falta, la media de su tipo de vía
        G = ox.add_edge_travel_times(G)    # segundos = length / velocidad

    with cronometro("Limpiando atributos"):
        for _, _, _, d in G.edges(keys=True, data=True):
            limpio: dict[str, Any] = {
                "highway": _highway_principal(d["highway"], tipos),
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


def validar_grafo(ruta: Path, tipos: tuple[str, ...]) -> bool:
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
                        and d["highway"] in tipos):
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
    parser.add_argument("--ligero", action="store_true",
                        help="grafo ligero, sin carreteras secundarias (archivo espana_red_maestra.graphml)")
    parser.add_argument("--datos", type=Path, default=RAIZ / "data",
                        help="carpeta de datos (por defecto, data/); útil para pruebas")
    parser.add_argument("--pbf-url", default=URL_ESPANA,
                        help="URL del extracto usado en el Anexo A (solo para saber el nombre del archivo)")
    args = parser.parse_args()

    carpeta_log = args.datos.resolve().parent / "docs"
    carpeta_log.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(),
                  logging.FileHandler(carpeta_log / ("construccion_ligero.log" if args.ligero
                                                     else "construccion.log"), encoding="utf-8")],
    )
    ox.settings.use_cache = False   # no se hacen peticiones web: no hace falta carpeta de caché

    tipos = JERARQUIA if args.ligero else JERARQUIA_SECUNDARIAS
    grafo = args.datos / nombre_grafo(args.ligero)
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
        vias = leer_vias(pbf, tipos)
        G = construir_grafo(vias)
        del vias
        G = preparar_atributos(G, tipos)
        with cronometro(f"Guardando {ruta_visible(grafo)}"):
            guardar_grafo(G, grafo)
    except Exception:
        LOG.exception("Error durante la construcción")
        return 1

    mostrar_resumen(G, grafo)
    ok = validar_grafo(grafo, tipos)
    LOG.info("Tiempo total: %s", _fmt(time.perf_counter() - t0))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

"""Descarga la red vial maestra de la España peninsular y la guarda en GraphML.

Uso:
    python descargar_red.py            # descarga, procesa, guarda y valida
    python descargar_red.py --validar  # solo valida el archivo existente
"""
from __future__ import annotations

import argparse
import logging
import re
import socket
import sys
import time
from collections import Counter, deque
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse

import networkx as nx
import osmnx as ox
import requests
from osmnx import _http, _overpass
from osmnx._errors import InsufficientResponseError, ResponseStatusCodeError
from shapely.geometry import MultiPolygon, Polygon

LOG = logging.getLogger("descargar_red")

RUTA_SALIDA = Path("data") / "espana_red_maestra.graphml"
REINTENTOS = 8              # reintentos de la descarga completa
REINTENTOS_PETICION = 20    # reintentos por subconsulta (espera 30 s → 5 min, creciente)
RUTA_LOG = Path("descarga.log")

# Jerarquía de mayor a menor importancia (se usa para elegir un único valor
# de `highway` cuando OSMnx simplifica y fusiona aristas con varios tipos).
JERARQUIA: tuple[str, ...] = (
    "motorway", "motorway_link",
    "trunk", "trunk_link",
    "primary", "primary_link",
)
CUSTOM_FILTER = f'["highway"~"^({"|".join(JERARQUIA)})$"]'

# Atributos de arista que se conservan (el resto se descarta para aligerar el archivo).
ATRIBUTOS_ARISTA: tuple[str, ...] = (
    "osmid", "highway", "name", "ref", "oneway", "maxspeed",
    "length", "speed_kph", "travel_time",
)


@contextmanager
def cronometro(descripcion: str) -> Iterator[None]:
    LOG.info("▶ %s...", descripcion)
    t0 = time.perf_counter()
    try:
        yield
    finally:
        LOG.info("✔ %s (%.1f s)", descripcion, time.perf_counter() - t0)


def obtener_poligono_peninsula() -> Polygon:
    """Polígono de la España peninsular: el mayor polígono de la frontera de España.

    Baleares, Canarias, Ceuta y Melilla son polígonos disjuntos y mucho menores,
    por lo que se descartan al quedarnos solo con el de mayor área.
    """
    gdf = ox.geocode_to_gdf("Spain")
    geom = gdf.geometry.iloc[0]
    if isinstance(geom, MultiPolygon):
        geom = max(geom.geoms, key=lambda g: g.area)
    if not isinstance(geom, Polygon):
        raise TypeError(f"Geometría inesperada para España: {type(geom).__name__}")
    # Simplificación (~1 km) para no saturar la consulta Overpass con miles de vértices.
    geom = geom.simplify(0.01, preserve_topology=True)
    LOG.info("Polígono peninsular: bounds=%s", tuple(round(b, 2) for b in geom.bounds))
    return geom


ERRORES_RED = (
    requests.exceptions.RequestException,
    InsufficientResponseError,
    ResponseStatusCodeError,
)


def es_reintentable(exc: Exception) -> bool:
    """Fallos de red o del servidor (429/5xx) son transitorios; un 4xx no lo es."""
    if isinstance(exc, ResponseStatusCodeError):
        return re.search(r"responded: (429|5\d\d)", str(exc)) is not None
    return True


_GETADDRINFO_ORIG = socket.getaddrinfo
_ULTIMA_IP: dict[str, str] = {}


def _acepta_tcp(ip: str, puerto: int = 443, timeout: float = 5.0) -> bool:
    try:
        with socket.create_connection((ip, puerto), timeout=timeout):
            return True
    except OSError:
        return False


def config_dns_robusto(url: str) -> None:
    """Sustituye a `osmnx._http._config_dns`.

    OSMnx fija UNA IP por host (la primera que devuelve el sistema) y la fuerza
    en cada petición. overpass-api.de tiene varias IPs; si la elegida cae, los
    reintentos nunca prueban las demás. Aquí se elige la primera IP que acepta
    una conexión TCP, de modo que cada reintento se adapta a la que responda.
    """
    host = urlparse(url).netloc.split(":")[0]
    try:
        ips = list(dict.fromkeys(
            i[4][0] for i in _GETADDRINFO_ORIG(host, 443, socket.AF_INET, socket.SOCK_STREAM)))
    except OSError as exc:
        raise requests.exceptions.ConnectionError(f"DNS de {host} no resuelve: {exc}") from exc
    ip = next((x for x in ips if _acepta_tcp(x)), None)
    if ip is None:
        raise requests.exceptions.ConnectionError(f"Ninguna IP de {host} acepta conexiones: {ips}")
    if _ULTIMA_IP.get(host) != ip:
        LOG.info("Servidor %s → usando IP %s (candidatas: %s)", host, ip, ", ".join(ips))
        _ULTIMA_IP[host] = ip

    def _getaddrinfo(*args: Any, **kwargs: Any) -> Any:
        if args and args[0] == host:
            return _GETADDRINFO_ORIG(ip, *args[1:], **kwargs)
        return _GETADDRINFO_ORIG(*args, **kwargs)

    socket.getaddrinfo = _getaddrinfo


def _fmt(segundos: float) -> str:
    return str(timedelta(seconds=int(segundos)))


class ProgresoDescarga:
    """Instrumenta las subconsultas Overpass de OSMnx.

    Muestra progreso (%), tiempo transcurrido y ETA, y reintenta cada subconsulta
    por separado con espera creciente (un corte de red no reinicia la descarga).
    Las respuestas correctas se guardan en la caché de OSMnx, de modo que si el
    script se interrumpe, al relanzarlo se reanuda donde se quedó.
    """

    def __init__(self) -> None:
        self.total = 0
        self.hechas = 0
        self.inicio = time.perf_counter()
        self.duraciones: deque[float] = deque(maxlen=20)
        self._coords_orig = _overpass._make_overpass_polygon_coord_strs
        self._request_orig = _overpass._overpass_request

    def instalar(self) -> None:
        _http._config_dns = config_dns_robusto
        _overpass._make_overpass_polygon_coord_strs = self._coords
        _overpass._overpass_request = self._request

    def _coords(self, polygon: Any) -> list[str]:
        coords = self._coords_orig(polygon)
        self.total, self.hechas = len(coords), 0
        LOG.info("La descarga se divide en %d subconsultas Overpass", self.total)
        return coords

    def _request(self, data: Any) -> dict[str, Any]:
        for intento in range(1, REINTENTOS_PETICION + 1):
            t0 = time.perf_counter()
            try:
                respuesta = self._request_orig(data)
                break
            except ERRORES_RED as exc:
                if not es_reintentable(exc):
                    raise
                espera = min(30 * 2 ** (intento - 1), 300)
                LOG.warning("Subconsulta %d/%d: intento %d/%d fallido (%s). Reintento en %d s",
                            self.hechas + 1, self.total, intento, REINTENTOS_PETICION,
                            type(exc).__name__, espera)
                if intento == REINTENTOS_PETICION:
                    raise
                time.sleep(espera)
        duracion = time.perf_counter() - t0
        self.hechas += 1
        if duracion > 1:  # las respuestas servidas desde caché no cuentan para el ETA
            self.duraciones.append(duracion)
        restantes = self.total - self.hechas
        eta = (_fmt(restantes * sum(self.duraciones) / len(self.duraciones))
               if self.duraciones else "n/d")
        LOG.info("[%3d/%d %5.1f%%] transcurrido %s | ETA %s | última subconsulta %.0f s",
                 self.hechas, self.total, 100 * self.hechas / max(self.total, 1),
                 _fmt(time.perf_counter() - self.inicio), eta, duracion)
        return respuesta


def descargar_grafo(poligono: Polygon) -> nx.MultiDiGraph:
    """Descarga la red filtrada. OSMnx simplifica la topología por defecto y
    conserva solo la mayor componente fuertemente conexa (retain_all=False)."""
    ProgresoDescarga().instalar()
    # Reintento global como red de seguridad; lo ya descargado está en caché.
    for intento in range(1, REINTENTOS + 1):
        try:
            return ox.graph_from_polygon(
                poligono,
                custom_filter=CUSTOM_FILTER,
                network_type="drive",
                simplify=True,
                retain_all=False,
                truncate_by_edge=True,
            )
        except ERRORES_RED as exc:
            LOG.warning("Descarga global: intento %d/%d fallido (%s)",
                        intento, REINTENTOS, type(exc).__name__)
            if intento == REINTENTOS or not es_reintentable(exc):
                raise
            time.sleep(60)
    raise RuntimeError("inalcanzable")


def _como_lista(valor: Any) -> list[Any]:
    return list(valor) if isinstance(valor, (list, tuple, set)) else [valor]


def _highway_principal(valor: Any) -> str:
    """Reduce `highway` (str o lista) a un único str según la jerarquía."""
    candidatos = [str(v) for v in _como_lista(valor)]
    for tipo in JERARQUIA:
        if tipo in candidatos:
            return tipo
    return candidatos[0]


def preparar_atributos(G: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """Imputa velocidades, calcula tiempos y deja atributos limpios y serializables."""
    with cronometro("Imputando velocidades (add_edge_speeds)"):
        G = ox.add_edge_speeds(G)
    with cronometro("Calculando tiempos de viaje (add_edge_travel_times)"):
        G = ox.add_edge_travel_times(G)

    with cronometro("Limpiando atributos de aristas"):
        for _, _, _, data in G.edges(keys=True, data=True):
            data["length"] = float(data["length"])
            data["speed_kph"] = float(data["speed_kph"])
            data["travel_time"] = float(data["travel_time"])
            data["highway"] = _highway_principal(data["highway"])
            for clave in list(data):
                if clave not in ATRIBUTOS_ARISTA:
                    del data[clave]
                elif isinstance(data[clave], (list, tuple, set)):
                    data[clave] = ";".join(str(v) for v in data[clave])
                elif isinstance(data[clave], bool):
                    data[clave] = str(data[clave])
    return G


def guardar_grafo(G: nx.MultiDiGraph, ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ox.save_graphml(G, filepath=ruta)


def mostrar_resumen(G: nx.MultiDiGraph, ruta: Path) -> None:
    tipos = Counter(d["highway"] for _, _, d in G.edges(data=True))
    km = sum(d["length"] for _, _, d in G.edges(data=True)) / 1000
    LOG.info("─── RESUMEN ───")
    LOG.info("Nodos:   %d", G.number_of_nodes())
    LOG.info("Aristas: %d (%.0f km dirigidos)", G.number_of_edges(), km)
    LOG.info("Tipos de vía (highway):")
    for tipo, n in tipos.most_common():
        LOG.info("  %-15s %d", tipo, n)
    LOG.info("Archivo: %s (%.1f MB)", ruta, ruta.stat().st_size / 1024**2)


def validar_grafo(ruta: Path) -> bool:
    """Lee el GraphML con networkx puro y comprueba `length` y `highway`."""
    try:
        with cronometro(f"Validando {ruta} con networkx.read_graphml"):
            H = nx.read_graphml(ruta)
            n_aristas = 0
            total_m = 0.0
            for _, _, d in H.edges(data=True):
                total_m += float(d["length"])
                if not d["highway"]:
                    raise ValueError("arista con 'highway' vacío")
                n_aristas += 1
            if n_aristas == 0:
                raise ValueError("el grafo no contiene aristas")
        LOG.info("Validación OK: %d nodos, %d aristas, %.0f km totales",
                 H.number_of_nodes(), n_aristas, total_m / 1000)
        return True
    except (OSError, KeyError, ValueError, nx.NetworkXError) as exc:
        LOG.error("Validación FALLIDA: %s: %s", type(exc).__name__, exc)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--validar", action="store_true",
                        help="solo validar el GraphML existente")
    parser.add_argument("--salida", type=Path, default=RUTA_SALIDA)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(), logging.FileHandler(RUTA_LOG, encoding="utf-8")],
    )
    if args.validar:
        return 0 if validar_grafo(args.salida) else 1

    ox.settings.use_cache = True
    ox.settings.log_console = False
    ox.settings.requests_timeout = 180
    t0 = time.perf_counter()
    try:
        with cronometro("Obteniendo polígono de la España peninsular"):
            poligono = obtener_poligono_peninsula()
        with cronometro("Descargando red OSM (puede tardar bastante)"):
            G = descargar_grafo(poligono)
        G = preparar_atributos(G)
        with cronometro(f"Guardando {args.salida}"):
            guardar_grafo(G, args.salida)
    except Exception:
        LOG.exception("Error durante la descarga/procesado")
        return 1

    mostrar_resumen(G, args.salida)
    ok = validar_grafo(args.salida)
    LOG.info("Tiempo total: %s", _fmt(time.perf_counter() - t0))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

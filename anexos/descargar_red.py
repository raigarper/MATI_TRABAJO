"""ANEXO A. Descarga de los datos de la red vial de España.

Fuente: OpenStreetMap, extracto de España publicado por Geofabrik
(https://download.geofabrik.de/europe/spain.html), archivo `spain-latest.osm.pbf` (~1,4 GB).

Qué hace:
  - Si el grafo ya existe en `data/espana_red_maestra_secundarias.graphml` (el grafo base del
    trabajo), lo avisa y termina. Con `--ligero` comprueba `data/espana_red_maestra.graphml`.
  - Si no, descarga el extracto a `data/`. La descarga se puede reanudar si se corta
    y no se repite si el archivo ya está.

Siguiente paso: `python anexos/construir_grafo.py` (Anexo B) convierte el extracto en el grafo.

Uso:
    python anexos/descargar_red.py
    python anexos/descargar_red.py --ligero      # comprobar el grafo ligero en vez del base
    python anexos/descargar_red.py --forzar      # volver a descargar aunque ya exista
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import timedelta
from pathlib import Path

import requests

LOG = logging.getLogger("descargar_red")

RAIZ = Path(__file__).resolve().parent.parent          # carpeta del proyecto
URL_ESPANA = "https://download.geofabrik.de/europe/spain-latest.osm.pbf"
NOMBRE_GRAFO = "espana_red_maestra_secundarias.graphml"     # grafo base
NOMBRE_GRAFO_LIGERO = "espana_red_maestra.graphml"          # sin carreteras secundarias
REINTENTOS = 100                                       # cortes de red tolerados


def ruta_visible(ruta: Path) -> str:
    """Ruta relativa al proyecto (si se puede), para que los mensajes sean cortos."""
    try:
        return str(ruta.resolve().relative_to(RAIZ))
    except ValueError:
        return str(ruta)


def _fmt(segundos: float) -> str:
    return str(timedelta(seconds=int(segundos)))


def descargar_pbf(url: str, destino: Path) -> None:
    """Descarga `url` en `destino` con reanudación (cabecera Range), progreso y reintentos."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    parcial = destino.with_name(destino.name + ".part")   # archivo a medias
    total = int(requests.head(url, allow_redirects=True, timeout=30).headers["Content-Length"])
    LOG.info("Tamaño del archivo: %.0f MB", total / 1024**2)

    for intento in range(1, REINTENTOS + 1):
        pos = parcial.stat().st_size if parcial.exists() else 0
        if pos >= total:
            break
        try:
            cabeceras = {"Range": f"bytes={pos}-"} if pos else {}
            with requests.get(url, headers=cabeceras, stream=True, timeout=60) as r:
                r.raise_for_status()
                if pos and r.status_code != 206:     # el servidor ignoró Range: empezar de cero
                    pos = 0
                inicio, ult_log, bytes_sesion = time.perf_counter(), 0.0, 0
                with open(parcial, "ab" if pos else "wb") as f:
                    for trozo in r.iter_content(chunk_size=1 << 20):
                        f.write(trozo)
                        bytes_sesion += len(trozo)
                        ahora = time.perf_counter()
                        if ahora - ult_log >= 10:
                            ult_log = ahora
                            hecho = pos + bytes_sesion
                            vel = bytes_sesion / (ahora - inicio)
                            eta = _fmt((total - hecho) / vel) if vel else "n/d"
                            LOG.info("[%5.1f%%] %.0f/%.0f MB | %.1f MB/s | quedan %s",
                                     100 * hecho / total, hecho / 1024**2, total / 1024**2,
                                     vel / 1024**2, eta)
        except requests.exceptions.RequestException as exc:
            LOG.warning("Descarga interrumpida (%s). Reintento %d/%d en 15 s; se reanuda en el byte %d",
                        type(exc).__name__, intento, REINTENTOS,
                        parcial.stat().st_size if parcial.exists() else 0)
            time.sleep(15)
    if not parcial.exists() or parcial.stat().st_size != total:
        raise RuntimeError("Descarga incompleta del archivo PBF")
    parcial.replace(destino)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--forzar", action="store_true",
                        help="descargar de nuevo aunque el grafo o el extracto ya existan")
    parser.add_argument("--ligero", action="store_true",
                        help="comprobar el grafo ligero (sin secundarias) en vez del grafo base")
    parser.add_argument("--datos", type=Path, default=RAIZ / "data",
                        help="carpeta de datos (por defecto, data/); útil para pruebas")
    parser.add_argument("--pbf-url", default=URL_ESPANA, help="URL del extracto (por defecto, España)")
    args = parser.parse_args()

    carpeta_log = args.datos.resolve().parent / "docs"
    carpeta_log.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(), logging.FileHandler(carpeta_log / "descarga.log", encoding="utf-8")],
    )

    grafo = args.datos / (NOMBRE_GRAFO_LIGERO if args.ligero else NOMBRE_GRAFO)
    pbf = args.datos / Path(args.pbf_url).name

    if grafo.exists() and not args.forzar:
        LOG.info("El grafo ya se ha descargado en el archivo %s", ruta_visible(grafo))
        return 0

    if pbf.exists() and not args.forzar:
        LOG.info("El extracto ya está descargado (%s, %.0f MB).", ruta_visible(pbf),
                 pbf.stat().st_size / 1024**2)
    else:
        if pbf.exists():
            pbf.unlink()                                  # --forzar: empezar de cero
        LOG.info("Descargando %s", args.pbf_url)
        t0 = time.perf_counter()
        try:
            descargar_pbf(args.pbf_url, pbf)
        except Exception:
            LOG.exception("Error durante la descarga (se puede volver a ejecutar: se reanuda)")
            return 1
        LOG.info("Descarga completada en %s: %s", _fmt(time.perf_counter() - t0), ruta_visible(pbf))

    LOG.info("Siguiente paso: python anexos/construir_grafo.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())

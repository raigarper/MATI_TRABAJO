"""Anexo C. Ejecuta el estudio empírico de la Parte 4 (todos los algoritmos sobre todas las versiones aplicables).

Los algoritmos NO se copian aquí: se extrae el código de los notebooks de `parte3/` (las celdas que hay entre la ficha y la
cabecera «🧪 PRUEBAS»), así lo que se mide es exactamente lo que se explica en el trabajo. Las tareas se reparten entre
varios procesos y cada resultado se guarda en cuanto llega, de modo que se puede interrumpir y reanudar.

    python anexos/ejecutar_estudio.py                  # 1) estudio completo, en paralelo (≈ 40 min con 6 procesos)
    python anexos/ejecutar_estudio.py --serie          # 2) tiempos y memoria fiables, en serie (≈ 10 min, con el equipo en reposo)
    python anexos/ejecutar_estudio.py --procesos 4     # menos procesos
    python anexos/ejecutar_estudio.py --prueba         # versión reducida (unos minutos) en data/resultados/_prueba/
    python anexos/ejecutar_estudio.py --forzar         # vuelve a calcular todo (por defecto, reanuda)

Por qué dos pasadas: el coste de una ruta no depende de la carga del equipo, pero el tiempo sí (con varios procesos a la vez
comparten núcleos, caché y reloj). Por eso los costes y las comparaciones de calidad salen de la pasada en paralelo y los
tiempos y la memoria de las curvas de complejidad, de la pasada en serie. `calibracion.csv` mide cuánto distorsiona el paralelo.

Salida (carpeta data/resultados/):
    estudio_resultados.csv   una fila por ejecución, en paralelo (algoritmo, versión, tamaño, semilla, coste, tiempo, memoria...)
    tiempos_serie.csv        el estudio B (escalado) repetido en serie, con tiempos y memoria fiables
    no_aplicables.csv        qué algoritmo NO se ejecuta en qué versión, y por qué
    calibracion.csv          tiempos de unas tareas repetidas en serie, para medir cuánto distorsiona la ejecución en paralelo
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import io
import json
import multiprocessing as mp
import os
import random
import sys
import time
import tracemalloc
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MARCA = "A PARTIR DE AQUÍ"
CABECERA_PRUEBAS = "**🧪 PRUEBAS**"

# ── Reglas de aplicabilidad (se explican en el notebook, Parte 4) ───────────────────────────────────────────
LIMITE_FUERZA_BRUTA = 11     # n! ciclos: 11 ciudades ≈ 6 s, 12 ≈ 70 s, 13 ≈ 30 min
LIMITE_HELD_KARP = 21        # memoria 8·(n−1)·2^(n−1) bytes: 21 ciudades ≈ 170 MB, 22 ≈ 740 MB
SEMILLAS_GENETICO = 3
SEMILLAS_RECOCIDO = 5
TAMANOS_B = [5, 6, 7, 8, 9, 10, 11, 12, 14, 16, 18, 20, 25, 30, 40, 47, 60, 75]
INSTANCIAS_B = 3
GENERALES = ("grafo_dirigido", "grafo_simple_no_dirigido")
CAMPOS = ["id", "estudio", "aristas", "nodos", "ambito", "peso", "general", "n", "instancia", "algoritmo", "semilla",
          "coste", "segundos", "memoria_mb", "ok", "error"]


def motivo_no_aplicable(algoritmo: str, n: int, general: str) -> str | None:
    """Devuelve por qué `algoritmo` no se puede ejecutar sobre un grafo de n ciudades (o None si sí se puede)."""
    if algoritmo == "fuerza_bruta" and n > LIMITE_FUERZA_BRUTA:
        return f"{n} ciudades: harían falta {n - 1}! ciclos (más de {LIMITE_FUERZA_BRUTA} ciudades tarda más de un minuto)"
    if algoritmo == "held_karp" and n > LIMITE_HELD_KARP:
        return f"{n} ciudades: la tabla de programación dinámica necesitaría más de 700 MB (límite {LIMITE_HELD_KARP})"
    if algoritmo == "christofides" and "no_dirigido" not in general:
        return "necesita distancias simétricas (grafo no dirigido) y desigualdad triangular"
    return None


# ── Código de los algoritmos, extraído de los notebooks ────────────────────────────────────────────────────

def _texto(celda: dict) -> str:
    return "".join(celda["source"])


def cargar_fichas() -> dict:
    datos = json.loads((RAIZ / "parte3" / "fichas.json").read_text(encoding="utf-8"))
    return {k: v for k, v in datos.items() if not k.startswith("_")}


def codigo_preparacion() -> list[str]:
    """Celdas de la plantilla que preparan todo (versiones del grafo, ayudas) menos el cambio de carpeta."""
    nb = json.loads((RAIZ / "parte3" / "_plantilla_algoritmo.ipynb").read_text(encoding="utf-8"))
    out = []
    for c in nb["cells"]:
        if c["cell_type"] == "markdown" and MARCA in _texto(c):
            break
        if c["cell_type"] == "code" and "os.chdir" not in _texto(c):
            out.append(_texto(c))
    return out


def codigo_algoritmo(clave: str) -> list[str]:
    """Celdas de código de un notebook de algoritmo que hay entre la marca ✂️ y la cabecera de pruebas."""
    nb = json.loads((RAIZ / "parte3" / f"{clave}.ipynb").read_text(encoding="utf-8"))
    celdas, dentro = [], False
    for c in nb["cells"]:
        t = _texto(c)
        if c["cell_type"] == "markdown" and MARCA in t:
            dentro = True
        elif c["cell_type"] == "markdown" and t.lstrip().startswith(CABECERA_PRUEBAS):
            break
        elif dentro and c["cell_type"] == "code":
            celdas.append(t)
    return celdas


def nombre_funcion(ficha: dict) -> str:
    return ficha["funcion"].split("(")[0].strip()


# ── Trabajador (un proceso) ────────────────────────────────────────────────────────────────────────────────
NS: dict = {}
FUNCIONES: dict = {}
CACHE: dict = {}


def _iniciar() -> None:
    """Se ejecuta una vez en cada proceso: prepara las versiones del grafo y define los algoritmos."""
    os.chdir(RAIZ)
    sys.path.insert(0, str(RAIZ))
    fichas = cargar_fichas()
    with contextlib.redirect_stdout(io.StringIO()):                # las celdas de preparación imprimen un resumen
        for codigo in codigo_preparacion():
            exec(codigo, NS)
        for clave, ficha in fichas.items():
            for codigo in codigo_algoritmo(clave):
                exec(codigo, NS)
            FUNCIONES[clave.rsplit("_", 1)[0]] = NS[nombre_funcion(ficha)]


def _grafo(t: dict):
    """Grafo de ciudades de una tarea (con caché). En el estudio B es un subconjunto aleatorio, reproducible."""
    clave = (t["aristas"], t["nodos"], t["ambito"], t["peso"], t["general"], t["n"], t["instancia"])
    if clave not in CACHE:
        if len(CACHE) > 40:
            CACHE.clear()
        base = (t["aristas"], t["nodos"], t["ambito"], t["peso"], t["general"])
        if base not in CACHE:
            CACHE[base] = NS["cargar_version"](*base)
        K = CACHE[base]
        if t["n"] is not None and t["n"] < K.number_of_nodes():
            azar = random.Random(f"estudio-{t['n']}-{t['instancia']}")
            K = K.subgraph(azar.sample(sorted(K.nodes), t["n"])).copy()
            K.graph.update(CACHE[base].graph)
        CACHE[clave] = K
    return CACHE[clave]


def _llamar(t: dict, K):
    nombre = t["algoritmo"]
    f = FUNCIONES[nombre]
    inicio = "Madrid" if "Madrid" in K else sorted(K.nodes)[0]
    opciones = {"inicio": inicio}
    if nombre == "genetico":
        opciones["semilla"] = t["semilla"]
    elif nombre == "recocido_simulado":
        random.seed(t["semilla"])
    with contextlib.redirect_stdout(io.StringIO()):
        t0 = time.perf_counter()
        ruta, coste = f(K, **opciones)
        segundos = time.perf_counter() - t0
    return ruta, coste, segundos, f, opciones


def _trabajar(t: dict) -> dict:
    fila = {k: t.get(k) for k in CAMPOS}
    try:
        K = _grafo(t)
        fila["n"] = K.number_of_nodes()
        ruta, coste, segundos, f, opciones = _llamar(t, K)
        NS["validar_ruta"](K, ruta)
        ok = abs(coste - NS["coste_ruta"](K, ruta)) < 1e-6 * max(1.0, abs(coste))
        if t["semilla"] is None and segundos < 0.05:            # muy rápido y determinista: se repite para quitar ruido
            segundos = min([segundos] + [_llamar(t, K)[2] for _ in range(4)])
        fila.update(coste=round(float(coste), 3), segundos=round(segundos, 5), ok=ok, error="" if ok else "el coste no coincide")
        if t["memoria"]:
            tracemalloc.start()
            with contextlib.redirect_stdout(io.StringIO()):
                if t["algoritmo"] == "recocido_simulado":
                    random.seed(t["semilla"])
                f(K, **opciones)
            fila["memoria_mb"] = round(tracemalloc.get_traced_memory()[1] / 1e6, 3)
            tracemalloc.stop()
    except Exception as e:                                       # un fallo no debe parar el estudio
        fila.update(ok=False, error=f"{type(e).__name__}: {e}"[:200])
    return fila


# ── Preparación de las tareas ──────────────────────────────────────────────────────────────────────────────

def coste_estimado(algoritmo: str, n: int) -> float:
    """Segundos aproximados de una tarea; solo sirve para lanzar primero las más largas."""
    base = {"fuerza_bruta": 6 * (n / 11) ** 12, "held_karp": 1.1 * 2 ** (n - 20) * (n / 20) ** 2,
            "dfj": 0.05 * n, "genetico": 1.5 + 0.12 * n, "recocido_simulado": 0.02 * n,
            "vecino_mas_cercano": 0.001, "dos_opt": 0.001 * n / 10, "christofides": 0.001 * n / 10}
    return base[algoritmo]


def crear_tareas(args) -> tuple[list[dict], list[dict]]:
    algoritmos = ["fuerza_bruta", "held_karp", "dfj", "vecino_mas_cercano", "dos_opt", "christofides", "recocido_simulado", "genetico"]
    tareas, no_aplicables = [], []

    def anadir(estudio, v, n, instancia, algoritmo):
        motivo = motivo_no_aplicable(algoritmo, n, v["general"])
        if motivo:
            if estudio == "A":
                no_aplicables.append({**{k: v[k] for k in ("aristas", "nodos", "ambito", "peso", "general")}, "n": n,
                                      "algoritmo": algoritmo, "motivo": motivo})
            return
        semillas = {"genetico": range(1, args.semillas_genetico + 1), "recocido_simulado": range(1, args.semillas_recocido + 1)}.get(algoritmo, [None])
        for s in semillas:
            memoria = estudio == "B" and instancia == 0 and s in (None, 1)          # memoria: solo una réplica por tamaño
            ident = "|".join(str(x) for x in (estudio, v["aristas"], v["nodos"], v["ambito"], v["peso"], v["general"], n, instancia, algoritmo, s))
            tareas.append({"id": ident, "estudio": estudio, **{k: v[k] for k in ("aristas", "nodos", "ambito", "peso", "general")},
                           "n": n if estudio == "B" else None, "instancia": instancia, "algoritmo": algoritmo, "semilla": s,
                           "memoria": memoria, "_n": n})

    # Estudio A: todas las versiones del catálogo (cada grafo de ciudades distinto, una vez: multigrafo = grafo simple)
    with open(RAIZ / "data" / "versiones" / "catalogo.csv", encoding="utf-8") as f:
        vistas = set()
        for fila in csv.DictReader(f):
            if fila["general"] not in GENERALES:
                continue
            clave = tuple(fila[k] for k in ("aristas", "nodos", "ambito", "peso", "general"))
            if clave in vistas:
                continue
            vistas.add(clave)
            n = int(fila["n_ciudades"])
            if args.prueba and (n > 6 or fila["peso"] != "km"):
                continue
            for a in algoritmos:
                anadir("A", fila, n, 0, a)

    # Estudio B: curva de escalado, con subconjuntos aleatorios de las 75 ciudades (completo, km)
    for general in GENERALES:
        for n in TAMANOS_B:
            if args.prueba and n > 9:
                continue
            for instancia in range(1 if n == 75 else INSTANCIAS_B):
                v = dict(aristas="completo", nodos="capitales_y_100k", ambito="espana", peso="km", general=general)
                for a in algoritmos:
                    anadir("B", v, n, instancia, a)

    if args.prueba:                                              # una sola semilla de cada algoritmo estocástico
        tareas = [t for t in tareas if t["semilla"] in (None, 1)]
    if args.serie:                                               # solo el escalado, una instancia y una semilla, con memoria
        tareas = [{**t, "memoria": True} for t in tareas if t["estudio"] == "B" and t["instancia"] == 0 and t["semilla"] in (None, 1)]
    tareas.sort(key=lambda t: -coste_estimado(t["algoritmo"], t["_n"]))
    return tareas, no_aplicables


# ── Programa principal ─────────────────────────────────────────────────────────────────────────────────────

def leer_hechas(ruta: Path) -> set:
    if not ruta.exists():
        return set()
    with open(ruta, encoding="utf-8") as f:
        return {fila["id"] for fila in csv.DictReader(f)}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--procesos", type=int, default=max(1, min(6, (os.cpu_count() or 2) - 2)),
                   help="procesos en paralelo (por defecto, 6 o los núcleos libres)")
    p.add_argument("--prueba", action="store_true", help="versión reducida para comprobar que todo funciona")
    p.add_argument("--forzar", action="store_true", help="no reanudar: volver a calcular todo")
    p.add_argument("--espera", type=float, default=15, help="minutos sin ningún resultado nuevo tras los que se da el estudio por atascado")
    p.add_argument("--serie", action="store_true", help="un solo proceso: repite el estudio de escalado para medir tiempos y memoria fiables")
    p.add_argument("--semillas-genetico", type=int, default=SEMILLAS_GENETICO)
    p.add_argument("--semillas-recocido", type=int, default=SEMILLAS_RECOCIDO)
    args = p.parse_args()

    salida = RAIZ / "data" / "resultados" / ("_prueba" if args.prueba else "")
    salida.mkdir(parents=True, exist_ok=True)
    ruta_csv = salida / ("tiempos_serie.csv" if args.serie else "estudio_resultados.csv")
    if args.forzar and ruta_csv.exists():
        ruta_csv.unlink()
    tareas, no_aplicables = crear_tareas(args)
    with open(salida / "no_aplicables.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["aristas", "nodos", "ambito", "peso", "general", "n", "algoritmo", "motivo"])
        w.writeheader()
        w.writerows(no_aplicables)
    if args.serie:
        args.procesos = 1
    hechas = leer_hechas(ruta_csv)
    pendientes = [t for t in tareas if t["id"] not in hechas]
    print(f"{len(tareas)} tareas ({len(hechas)} ya hechas, {len(pendientes)} pendientes) | {len(no_aplicables)} combinaciones no aplicables "
          f"| {args.procesos} procesos", flush=True)

    nuevo = not ruta_csv.exists()
    t0, hechas_ahora, fallos = time.perf_counter(), 0, 0
    if pendientes:
        with open(ruta_csv, "a", newline="", encoding="utf-8") as f, mp.get_context("spawn").Pool(args.procesos, initializer=_iniciar) as pool:
            w = csv.DictWriter(f, fieldnames=CAMPOS)
            if nuevo:
                w.writeheader()
            resultados = pool.imap_unordered(_trabajar, pendientes, chunksize=1)
            while hechas_ahora < len(pendientes):
                try:
                    fila = resultados.next(timeout=args.espera * 60)
                except mp.TimeoutError:                                   # algo se ha atascado: se corta y se puede reanudar
                    print(f"Sin ningún resultado nuevo en {args.espera} min: se detiene (los resultados hechos están guardados; "
                          f"vuelve a lanzar el programa para reanudar).", flush=True)
                    pool.terminate()
                    sys.exit(2)
                w.writerow(fila)
                f.flush()
                hechas_ahora += 1
                fallos += 0 if fila["ok"] else 1
                if hechas_ahora % 100 == 0 or hechas_ahora == len(pendientes):
                    gastado = time.perf_counter() - t0
                    resto = gastado / hechas_ahora * (len(pendientes) - hechas_ahora)
                    print(f"  {hechas_ahora}/{len(pendientes)} | {gastado / 60:.1f} min | quedan ≈ {resto / 60:.1f} min | fallos: {fallos}", flush=True)
    print(f"Estudio terminado en {(time.perf_counter() - t0) / 60:.1f} min. Resultados: {ruta_csv.relative_to(RAIZ)}", flush=True)
    if not args.serie:
        calibrar(salida, tareas)


def calibrar(salida: Path, tareas: list[dict]) -> None:
    """Repite en serie unas cuantas tareas y las compara con su tiempo en paralelo (el paralelo es algo más lento)."""
    with open(salida / "estudio_resultados.csv", encoding="utf-8") as f:
        previas = {fila["id"]: fila for fila in csv.DictReader(f)}
    elegidas, por_algoritmo = [], {}
    for t in tareas:
        fila = previas.get(t["id"])
        if not fila or fila["ok"] != "True" or t["semilla"] not in (None, 1):
            continue
        if 0.2 < float(fila["segundos"]) < 30 and por_algoritmo.get(t["algoritmo"], 0) < 3:
            por_algoritmo[t["algoritmo"]] = por_algoritmo.get(t["algoritmo"], 0) + 1
            elegidas.append(t)
    if not elegidas:
        return
    _iniciar()
    filas = []
    for t in elegidas:
        serie = _trabajar({**t, "memoria": False})
        paralelo = float(previas[t["id"]]["segundos"])
        filas.append({"id": t["id"], "algoritmo": t["algoritmo"], "n": serie["n"], "segundos_paralelo": paralelo,
                      "segundos_serie": serie["segundos"], "cociente": round(paralelo / serie["segundos"], 3) if serie["segundos"] else ""})
    with open(salida / "calibracion.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    mediana = sorted(float(x["cociente"]) for x in filas if x["cociente"] != "")[len(filas) // 2]
    print(f"Calibración: {len(filas)} tareas repetidas en serie; el paralelo tarda de media ×{mediana:.2f} (mediana)", flush=True)


if __name__ == "__main__":
    main()

"""Herramientas para trabajar en la Parte 3 (no forman parte del trabajo entregable).

Cada compañero programa su algoritmo en un notebook propio dentro de `parte3/`, copiado de la plantilla.
Estas dos órdenes evitan conflictos de git y reutilizan el código del notebook principal:

    python parte3/herramientas.py plantilla   # regenera parte3/_plantilla_algoritmo.ipynb a partir de
                                              # las celdas de la Parte 2 de trabajo_tsp.ipynb
    python parte3/herramientas.py integrar    # copia lo que hay bajo la marca ✂️ de cada notebook de
                                              # parte3/ a la Parte 3 de trabajo_tsp.ipynb

Solo usa la biblioteca estándar de Python.
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
import uuid
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MARCA = "✂️ A PARTIR DE AQUÍ SE INTEGRA EN EL TRABAJO"
PREFIJO_ORIGEN = "parte3/"

# Celdas de la Parte 2 del notebook principal que la plantilla reutiliza (se localizan por su primera línea)
CELDAS_PREPARACION = [
    "# Librerías que se usan en todo el notebook",
    "# ── Parámetros de las versiones (editables) ──",
    "# Lee la lista de ciudades",
    "def nombre_tabla(",
    "UNIDAD = {",
]

AYUDAS = '''# [AYUDA COMPARTIDA] Funciones comunes a todos los algoritmos
import time
import tracemalloc

def coste_ruta(K, ruta):
    # Coste total del ciclo: suma de las distancias entre ciudades consecutivas y de la última a la primera
    return sum(K[ruta[i]][ruta[(i + 1) % len(ruta)]]["peso"] for i in range(len(ruta)))

def validar_ruta(K, ruta):
    # Comprueba que la ruta visita cada ciudad de K exactamente una vez
    assert len(ruta) == K.number_of_nodes() and set(ruta) == set(K.nodes), "la ruta no visita cada ciudad una vez"

def medir(algoritmo, K, memoria=False, **opciones):
    # Ejecuta algoritmo(K, **opciones), comprueba el resultado y devuelve cuánto ha tardado
    # (con memoria=True mide también el pico de memoria en una segunda ejecución, porque medirla ralentiza)
    t0 = time.perf_counter()
    ruta, coste = algoritmo(K, **opciones)
    segundos = time.perf_counter() - t0
    validar_ruta(K, ruta)
    assert abs(coste - coste_ruta(K, ruta)) < 1e-6 * max(1.0, abs(coste)), "el coste devuelto no coincide con el de la ruta"
    resultado = {"algoritmo": algoritmo.__name__, "ciudades": K.number_of_nodes(), "coste": round(coste, 3),
                 "unidad": K.graph.get("unidad"), "segundos": round(segundos, 4)}
    if memoria:
        tracemalloc.start()
        algoritmo(K, **opciones)
        _, pico = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        resultado["memoria_mb"] = round(pico / 1e6, 2)
    return resultado'''


# ── utilidades de notebooks (JSON de nbformat 4.5) ───────────────────────────

def _fuente(texto: str) -> list[str]:
    lineas = texto.split("\n")
    return [l + "\n" for l in lineas[:-1]] + [lineas[-1]]


def celda_md(texto: str, **meta) -> dict:
    return {"cell_type": "markdown", "id": uuid.uuid4().hex[:8], "metadata": dict(meta), "source": _fuente(texto)}


def celda_codigo(texto: str, **meta) -> dict:
    return {"cell_type": "code", "id": uuid.uuid4().hex[:8], "metadata": dict(meta), "source": _fuente(texto),
            "outputs": [], "execution_count": None}


def caja(borde: str, fondo: str, titulo: str, cuerpo: str) -> str:
    """Caja de color idéntica a la de las prácticas."""
    return (f'<div style="border-left:5px solid {borde};background:{fondo};padding:10px 14px;'
            f'margin:10px 0;border-radius:4px;">\n\n**{titulo}**\n\n{cuerpo.strip()}\n\n</div>')


def leer(ruta: Path) -> dict:
    return json.loads(ruta.read_text(encoding="utf-8"))


def escribir(ruta: Path, nb: dict) -> None:
    ruta.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def texto(celda: dict) -> str:
    return "".join(celda["source"])


def limpiar(celda: dict, origen: str) -> dict:
    """Copia de una celda sin salidas y marcada con el notebook del que viene."""
    c = json.loads(json.dumps(celda))
    c["id"] = uuid.uuid4().hex[:8]
    c["metadata"] = {"origen": origen}
    if c["cell_type"] == "code":
        c["outputs"], c["execution_count"] = [], None
    return c


def notebook_vacio(celdas: list[dict]) -> dict:
    return {"cells": celdas, "metadata": {"kernelspec": {"display_name": "Python 3 (ipykernel)", "language": "python",
                                                        "name": "python3"}, "language_info": {"name": "python"}},
            "nbformat": 4, "nbformat_minor": 5}


# ── plantilla ────────────────────────────────────────────────────────────────

def crear_plantilla(raiz: Path) -> None:
    principal = leer(raiz / "trabajo_tsp.ipynb")
    prep = []
    for inicio in CELDAS_PREPARACION:
        hallada = [c for c in principal["cells"] if c["cell_type"] == "code" and texto(c).startswith(inicio)]
        if len(hallada) != 1:
            sys.exit(f"No encuentro (o hay varias) la celda de la Parte 2 que empieza por: {inicio!r}")
        prep.append(celda_codigo(texto(hallada[0])))

    celdas = [
        celda_md("""# Plantilla de algoritmo. Parte 3 (Problema del Viajante)

**Cómo usarla:** copia este archivo como `parte3/<algoritmo>_<tunombre>.ipynb` (por ejemplo, `parte3/fuerza_bruta_pablo.ipynb`) y trabaja solo **debajo de la línea ✂️**. Lo de arriba (preparación) es el mismo código de la Parte 2 del trabajo y sirve para cargar las versiones del grafo: **no lo modifiques**. La guía completa está en `CONTRIBUTING.md`.

> ⚙️ El notebook se ejecuta desde su carpeta (`parte3/`): la primera celda sube a la raíz del proyecto para que las rutas (`data/...`) funcionen."""),
        celda_codigo("""# Sube a la raíz del proyecto para que las rutas (data/ciudades.csv, data/versiones/...) funcionen
import os
from pathlib import Path
if Path.cwd().name == "parte3":
    os.chdir("..")"""),
        *prep,
        celda_codigo(AYUDAS),
        celda_md(f"---\n### {MARCA}\n\nTodo lo que escribas **debajo de esta línea** pasará al notebook principal (`trabajo_tsp.ipynb`, Parte 3). No modifiques esta celda."),
        celda_md("### Nombre del algoritmo"),
        celda_md(caja("#4C72B0", "#EEF2FA", "📚 TEORÍA", """
*[Explica en lenguaje llano cómo funciona el algoritmo y, después, de forma precisa: pseudocódigo o pasos, cómo se aplica al problema del viajante.]*

- **Tipo:** exacto / heurístico / aproximado / metaheurística.
- **Complejidad en tiempo:** ...  **en memoria:** ...
- **Propiedades:** ¿siempre encuentra el óptimo? ¿es determinista? ¿tiene garantía de calidad? ¿necesita distancias simétricas (grafo no dirigido)?
- **¿Hasta cuántas ciudades es razonable usarlo?**
""")),
        celda_md("""**💻 CÓDIGO**

*[Sustituye `mi_algoritmo` por tu algoritmo, con un nombre único (por ejemplo, `fuerza_bruta`). Debe cumplir el contrato: recibe el grafo de ciudades `K` y devuelve `(ruta, coste)`. Borra este texto entre corchetes.]*"""),
        celda_codigo('''def mi_algoritmo(K, inicio=None):
    # Contrato: recibe el grafo de ciudades K (K[a][b]["peso"] = distancia de a a b) y devuelve (ruta, coste):
    # `ruta` = lista con todas las ciudades, cada una una vez, en el orden en que se visitan (el viajante
    # vuelve después a la primera); `coste` = coste total del ciclo. Debe funcionar con K dirigido (nx.DiGraph)
    # y no dirigido (nx.Graph).
    ciudades = list(K.nodes)
    if inicio is not None:                       # empezar por la ciudad pedida
        ciudades.remove(inicio)
        ciudades.insert(0, inicio)
    ruta = ciudades                              # EJEMPLO MÍNIMO (sin pensar): visita en el orden de la lista
    return ruta, coste_ruta(K, ruta)'''),
        celda_md("""**Prueba rápida** con una versión pequeña (las 6 ciudades de Galicia).

*[Cambia los parámetros de `cargar_version` para probar otras versiones y borra este texto entre corchetes.]*"""),
        celda_codigo('''K = cargar_version(aristas="completo", nodos="capitales_y_100k", ambito="galicia", peso="km", general="grafo_dirigido")
ruta, coste = mi_algoritmo(K, inicio="Vigo")
validar_ruta(K, ruta)                            # comprueba que visita cada ciudad una vez
print(" → ".join(ruta), f"| coste: {coste:.1f} {K.graph['unidad']}")
print(medir(mi_algoritmo, K, memoria=True, inicio="Vigo"))'''),
        celda_md(caja("#55A868", "#EAF6ED", "🧮 RESULTADOS", """
*[Tabla con lo medido: versión, nº de ciudades, coste, tiempo y memoria. Hasta cuántas ciudades ha funcionado. Observaciones.]*
""")),
        celda_md("---"),
    ]
    destino = raiz / "parte3" / "_plantilla_algoritmo.ipynb"
    destino.parent.mkdir(exist_ok=True)
    escribir(destino, notebook_vacio(celdas))
    print(f"Plantilla escrita en {destino.relative_to(raiz)} ({len(celdas)} celdas)")


# ── integración ──────────────────────────────────────────────────────────────

def _funciones(celdas: list[dict]) -> set[str]:
    nombres = set()
    for c in celdas:
        if c["cell_type"] == "code":
            try:
                nombres |= {n.name for n in ast.parse(texto(c)).body if isinstance(n, ast.FunctionDef)}
            except SyntaxError:
                pass
    return nombres


def integrar(raiz: Path) -> None:
    ruta_principal = raiz / "trabajo_tsp.ipynb"
    nb = leer(ruta_principal)
    previas = sum(1 for c in nb["cells"] if c["metadata"].get("origen", "").startswith(PREFIJO_ORIGEN))
    nb["cells"] = [c for c in nb["cells"] if not c["metadata"].get("origen", "").startswith(PREFIJO_ORIGEN)]
    propias = _funciones(nb["cells"])

    bloques, vistas = [], {}
    for ruta in sorted((raiz / "parte3").glob("*.ipynb")):
        if ruta.name.startswith("_"):
            continue
        celdas = leer(ruta)["cells"]
        marcas = [i for i, c in enumerate(celdas) if c["cell_type"] == "markdown" and MARCA in texto(c)]
        if len(marcas) != 1:
            sys.exit(f"{ruta.name}: debe tener exactamente una celda con la marca «{MARCA}» (tiene {len(marcas)}).")
        cuerpo = celdas[marcas[0] + 1:]
        for c in cuerpo:
            if c["cell_type"] == "code":
                try:
                    ast.parse("\n".join(l for l in texto(c).splitlines() if not l.lstrip().startswith(("%", "!"))))
                except SyntaxError as e:
                    sys.exit(f"{ruta.name}: error de sintaxis en una celda: {e}")
        for f in _funciones(cuerpo):
            if f in propias:
                print(f"AVISO: {ruta.name} define `{f}`, que ya existe en el notebook principal")
            if f in vistas:
                print(f"AVISO: `{f}` está definida en {vistas[f]} y en {ruta.name}: la segunda pisará a la primera")
            vistas[f] = ruta.name
        bloques.append((ruta.name, cuerpo))
    if not bloques:
        sys.exit("No hay notebooks de algoritmos en parte3/ (los que empiezan por «_» se ignoran).")

    nuevas = []
    tiene_cabecera = any(c["cell_type"] == "markdown" and texto(c).startswith("## Parte 3") for c in nb["cells"])
    if not tiene_cabecera:
        nuevas.append(celda_md("## Parte 3. Algoritmos para el Problema del Viajante", origen=PREFIJO_ORIGEN + "cabecera"))
        nuevas.append(celda_md("Cada algoritmo se explica (teoría, complejidad y propiedades), se programa y se prueba sobre el grafo de "
                               "ciudades `K` que devuelve `cargar_version(...)` (Parte 2). Todos cumplen el mismo contrato: reciben `K` y "
                               "devuelven `(ruta, coste)`.", origen=PREFIJO_ORIGEN + "cabecera"))
    if "coste_ruta" not in propias:
        nuevas.append(celda_md("**Funciones comunes a todos los algoritmos.** `coste_ruta` calcula el coste de un recorrido, `validar_ruta` "
                               "comprueba que visita cada ciudad una vez y `medir` ejecuta un algoritmo y anota tiempo y memoria.",
                               origen=PREFIJO_ORIGEN + "ayudas"))
        nuevas.append(celda_codigo(AYUDAS, origen=PREFIJO_ORIGEN + "ayudas"))
    for nombre, cuerpo in bloques:
        nuevas += [limpiar(c, PREFIJO_ORIGEN + nombre) for c in cuerpo]

    posicion = next((i for i, c in enumerate(nb["cells"]) if c["cell_type"] == "markdown" and texto(c).startswith("## Parte 4")),
                    len(nb["cells"]))
    nb["cells"][posicion:posicion] = nuevas
    escribir(ruta_principal, nb)
    print(f"Integrados {len(bloques)} notebook(s): {', '.join(n for n, _ in bloques)}")
    print(f"{len(nuevas)} celdas nuevas en trabajo_tsp.ipynb" + (f" (se sustituyeron {previas} integradas antes)" if previas else ""))
    print("Para ver los resultados: ejecutar el notebook entero (Kernel → Restart & Run All).")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("orden", choices=["plantilla", "integrar"])
    p.add_argument("--raiz", type=Path, default=RAIZ, help="carpeta del proyecto (por defecto, la de este repositorio)")
    a = p.parse_args()
    (crear_plantilla if a.orden == "plantilla" else integrar)(a.raiz.resolve())


if __name__ == "__main__":
    main()

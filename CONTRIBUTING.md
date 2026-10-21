# Cómo colaborar en la Parte 3 (algoritmos del viajante)

Guía corta para el equipo. Cada uno programa **su algoritmo en un notebook propio** (dentro de `parte3/`), partiendo de una
plantilla. Después, Raimundo los **integra** automáticamente en el notebook principal (`trabajo_tsp.ipynb`). Así nadie se pisa
con git y el código sigue viviendo en notebooks.

## En 6 pasos

```bash
# 1. Ponte en tu rama y trae lo último de main (versiones del grafo, plantilla...)
git checkout <tu-rama>            # dev-pablo, dev_juan, dev_jiahao...
git pull origin main

# 2. Copia la plantilla con el nombre de tu algoritmo
cp parte3/_plantilla_algoritmo.ipynb parte3/fuerza_bruta_pablo.ipynb      # en Windows: copy

# 3. Abre el notebook y trabaja SOLO debajo de la línea ✂️ (ver abajo)

# 4. Sube tu notebook a tu rama
git add parte3/fuerza_bruta_pablo.ipynb
git commit -m "Fuerza bruta (Pablo)"
git push origin <tu-rama>

# 5. En GitHub: abre un Pull Request de tu rama a main. Raimundo lo revisa y lo acepta.
# 6. Para el siguiente algoritmo: vuelve al paso 1 (git pull origin main antes de empezar).
```

Instalación (una vez): `pip install -r requirements.txt`. **No necesitas el grafo grande** (108 MB): las versiones del grafo ya están
calculadas en `data/versiones/`.

## Qué se programa

| Algoritmo | Tipo | Complejidad (tiempo) | Límite orientativo | Responsable |
|---|---|---|---|---|
| Fuerza bruta | exacto | O(n!) | ≈ 10 ciudades | |
| Held–Karp (programación dinámica) | exacto | O(n²·2ⁿ) | ≈ 20 ciudades | |
| DFJ: programación entera + restricciones de subciclo | exacto | exponencial en el peor caso | 47 ciudades (por comprobar) | |
| Vecino más cercano | voraz | O(n²) | todas | |
| 2-opt (cambiar cruces) | mejora local | O(n²) por pasada | todas | |
| Christofides / MST 2-aproximado | aproximado con garantía | O(n²)–O(n³) | todas (**solo grafo no dirigido**) | |
| Genético | metaheurística | según parámetros | todas | Raimundo |

Cada uno elige al menos uno (y puede hacer más). Apunta tu nombre en la tabla en el Pull Request.

> **Dijkstra no está en la lista:** calcula el camino más corto entre dos puntos, no un recorrido que visite todas las ciudades. Ya se usa
> en la Parte 2 para construir las tablas de distancias. El algoritmo del viajante equivalente a «ir siempre a lo más cercano» es el
> **vecino más cercano** (voraz).

## El contrato de un algoritmo

```python
def mi_algoritmo(K, inicio=None):
    ...
    return ruta, coste
```

- `K` es el grafo de ciudades: nodos = ciudades; `K[a][b]["peso"]` = distancia de `a` a `b` (km o segundos, según la versión).
  Es **completo**: todas las ciudades están unidas con todas.
- `ruta` = lista con **todas** las ciudades, cada una **una vez**, en el orden en que se visitan (el viajante vuelve después a la primera).
- `coste` = coste total del ciclo, **incluida la vuelta** a la primera ciudad.
- Debe funcionar con `K` **dirigido** (`nx.DiGraph`: la distancia de a a b puede no ser la de b a a) y **no dirigido** (`nx.Graph`). Si tu
  algoritmo necesita distancias simétricas (Christofides), compruébalo con `K.is_directed()` y avisa con un error claro.
- Funciones listas para usar (ya están en la plantilla): `coste_ruta(K, ruta)`, `validar_ruta(K, ruta)` y `medir(algoritmo, K, memoria=True)`.

## Cómo pedir una versión del grafo

```python
K = cargar_version(aristas="completo", nodos="capitales", ambito="espana", peso="km", general="grafo_dirigido")
```

| Parámetro | Valores |
|---|---|
| `aristas` | `completo` · `autovias_principales` · `solo_autovias` · `sin_autovias` |
| `nodos` | `capitales` (47) · `capitales_y_100k` (75) |
| `ambito` | `espana` o una comunidad: `andalucia`, `castilla_y_leon`, `castilla_la_mancha`, `cataluna`, `galicia`, `madrid`, `comunidad_valenciana`, `pais_vasco`... |
| `peso` | `km` · `tiempo` (en segundos) |
| `general` | `grafo_dirigido` · `grafo_simple_no_dirigido` (los `multigrafo_*` dan el mismo resultado) |

- **Para probar rápido:** versiones por comunidad (`ambito="galicia"`: 6 ciudades; `"andalucia"`: 13).
- **Para los algoritmos exactos con pocas ciudades:** coge un trozo de `K` con `K.subgraph(lista_de_ciudades)` (como `K` es completo, el
  trozo también lo es). Por ejemplo, `K.subgraph(list(K.nodes)[:10])`.
- Todas las versiones disponibles están en `data/versiones/catalogo.csv`.

## Qué escribir en tu notebook (debajo de ✂️)

Las notas en *cursiva entre corchetes* de la plantilla son instrucciones: **bórralas** cuando rellenes cada parte.

1. **📚 TEORÍA:** cómo funciona el algoritmo, en lenguaje llano y después con precisión (pasos o pseudocódigo); su **complejidad en tiempo y
   en memoria**; y sus **propiedades**: ¿exacto?, ¿determinista?, ¿tiene garantía de calidad?, ¿necesita simetría?, hasta cuántas ciudades sirve.
2. **💻 CÓDIGO:** tu función, con **un comentario por bloque lógico** pensado para alguien sin mucha soltura con Python. Si usas azar,
   fija una semilla (`SEED = 42`) para que los resultados se puedan repetir.
3. **Prueba rápida** con una versión pequeña, comprobando la ruta con `validar_ruta`.
4. **🧮 RESULTADOS:** una tabla con lo medido (versión, nº de ciudades, coste, tiempo, memoria) y hasta cuántas ciudades ha funcionado.

Usa solo librerías que ya están en `requirements.txt` (`networkx`, `numpy`, `scipy`...). Para el DFJ, `scipy.optimize.milp`.

## Reglas del repositorio

- Trabaja siempre en **tu rama**, nunca directamente en `main`. No renombres las ramas.
- **Un notebook por algoritmo**, en `parte3/`, con el nombre `algoritmo_tunombre.ipynb`.
- **No edites** `trabajo_tsp.ipynb`, `data/`, `anexos/` ni `parte3/_plantilla_algoritmo.ipynb` (así no hay conflictos). Si ves un error ahí, avisa.
- **No crees archivos `.py` propios** con el código del algoritmo: el código va en el notebook.
- **No modifiques las celdas de preparación** de la plantilla (las de encima de ✂️).
- Dale a cada función un **nombre único** (`fuerza_bruta`, `held_karp`...), para que no choque con las de los demás cuando se integren.
- Si usas IA, **apunta qué le has pedido**: hay que registrarlo en el trabajo.
- Si git te dice que hay un **conflicto** o algo no cuadra, no lo fuerces: avisa a Raimundo.

## Cómo se integra (para Raimundo)

```bash
python parte3/herramientas.py integrar     # copia lo que hay bajo ✂️ de cada notebook de parte3/ a la Parte 3 de trabajo_tsp.ipynb
# después: abrir trabajo_tsp.ipynb y Kernel → Restart & Run All
```

- Es repetible: cada vez que se ejecuta **sustituye** las celdas integradas antes (no las duplica).
- Avisa si dos notebooks definen una función con el mismo nombre y si alguno tiene errores de sintaxis.
- Si cambia el código de la Parte 2 del notebook principal, hay que regenerar la plantilla: `python parte3/herramientas.py plantilla`.

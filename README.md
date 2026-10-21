# MATI_TRABAJO — Red vial de España para el TSP

Modelo de la red de carreteras de la España peninsular para evaluar algoritmos del
Problema del Viajante (TSP) sobre distintas selecciones de ciudades (capitales
peninsulares, ciudades de más de 100.000 habitantes...).

La arquitectura es una **única red "maestra"** guardada en local (GraphML), de la que
se derivan versiones filtradas y grafos de ciudades en memoria con NetworkX.

> **Estado:** Parte 1 (construir el grafo) y Parte 2 (versiones del grafo) **hechas**. Pendientes: Parte 3 (algoritmos
> del viajante), Parte 4 (estudio con datos) y Parte 5 (conclusiones). El trabajo se desarrolla en el notebook
> `trabajo_tsp.ipynb`; solo el código que descarga los datos y construye el grafo se entrega aparte, como **anexos**.

## Estructura del proyecto

| Archivo | Para qué sirve |
|---|---|
| **`trabajo_tsp.ipynb`** | **El trabajo.** Notebook principal (estilo de las prácticas de MATI). Ahora mismo, la Parte 1. |
| **`data/espana_red_maestra_secundarias.graphml`** | **El grafo base** (con carreteras secundarias; 108 MB). **No está en git** (GitHub rechaza archivos de más de 100 MB): se genera con los anexos. |
| `data/espana_red_maestra.graphml` | Grafo **ligero**, sin secundarias (63 MB). Es un subconjunto del base; se conserva como referencia. |
| **`data/versiones/`** | **Las versiones del grafo** (Parte 2): 16 tablas de distancias entre ciudades + catálogo. 19 archivos, 0,9 MB; **sí va a git**. Ver la sección «Parte 2». |
| **`parte3/`** | Notebooks de los algoritmos del viajante (uno por persona, a partir de `_plantilla_algoritmo.ipynb`) y `herramientas.py`, que regenera la plantilla e integra esos notebooks en el principal. |
| `CONTRIBUTING.md` | Guía para el equipo: cómo colaborar en la Parte 3 (pasos de git, contrato de un algoritmo, reglas). |
| **`data/ciudades.csv`** | 75 ciudades (47 capitales peninsulares + 28 municipios peninsulares de más de 100.000 hab.). Ver más abajo. |
| **`anexos/descargar_red.py`** | **Anexo A.** Descarga el extracto de OpenStreetMap de España. |
| **`anexos/construir_grafo.py`** | **Anexo B.** Convierte el extracto en el grafo. |
| `tsp_utils.py` | Funciones compartidas por el notebook (dibujo de la red, `SEED`), como `mati_utils.py` en las prácticas. |
| `requirements.txt` | Dependencias. |
| `docs/construccion.log` | Log de la construcción del grafo base (tiempos y recuentos). |
| `docs/descarga_pbf.log` | Log de la construcción del grafo ligero con la primera versión del Anexo B. |
| `docs/intento_overpass/` | Primer enfoque (API Overpass) y su log; **descartado**, ver «Decisiones». |

`data/spain-latest.osm.pbf` (1,4 GB, el extracto de OpenStreetMap) también se guarda en `data/`, pero no va a git y
solo hace falta para volver a construir el grafo.

## Puesta en marcha

Para **usar** el grafo solo hace falta el notebook (`networkx` y `matplotlib`):

```powershell
pip install -r requirements.txt
jupyter lab trabajo_tsp.ipynb
```

**¿Vas a programar un algoritmo (Parte 3)?** Lee `CONTRIBUTING.md`.

**¿Solo vas a programar los algoritmos (Partes 3 y 4)?** No necesitas el grafo grande ni los anexos: las versiones ya
están calculadas en `data/versiones/`. Abre el notebook, **salta la Parte 1** y ejecuta desde la Parte 2 (la celda que
calcula las tablas se salta sola si ya existen).

Para **generar** el grafo base (hace falta si no se tiene el archivo `.graphml`, que no está en git), desde la
carpeta del proyecto y con las librerías de los anexos instaladas (`requirements.txt`):

```powershell
python anexos/descargar_red.py     # Anexo A: descarga el extracto (~1,4 GB, ~7 min, reanudable)
python anexos/construir_grafo.py   # Anexo B: construye el grafo base (~4 min, ~2,3 GB de RAM)
```

- Si el grafo ya existe, **ambos avisan y no hacen nada** (`--forzar` para repetir el proceso).
- `--ligero` (en los dos) trabaja con el grafo ligero, sin secundarias (`espana_red_maestra.graphml`, ~2 min).
- El Anexo B construye y simplifica el grafo con arrays (NumPy), no con un grafo de NetworkX gigante: pico medido
  de ~2,2 GB de RAM con secundarias (~2,1 GB en el ligero).

---

## El grafo base: `data/espana_red_maestra_secundarias.graphml`

### Qué es
La red de carreteras de la España peninsular, de autopistas a carreteras secundarias: **179.594 nodos** y
**309.250 aristas dirigidas** (≈183.000 km, contando cada sentido), en un archivo de 108 MB. Está
**simplificada** y es **fuertemente conexa**: existe camino dirigido entre cualquier par de nodos.

### Formato
**GraphML**, un formato estándar de grafos basado en XML (texto plano). Lo escribe `nx.write_graphml`
(NetworkX) y se lee con **`nx.read_graphml`**, como en las prácticas. Estructura (resumida):

```xml
<graphml>
  <key id="d9"  for="edge" attr.name="length" attr.type="double"/>    <!-- declaración de atributos, con su tipo -->
  <key id="d6"  for="node" attr.name="street_count" attr.type="long"/>
  ...
  <graph edgedefault="directed">                                       <!-- grafo DIRIGIDO -->
    <node id="342164">                                                 <!-- un nodo -->
      <data key="d4">-2.4493513</data>   <!-- x (longitud) -->
      <data key="d5">43.1900462</data>   <!-- y (latitud)  -->
      <data key="d6">3</data>            <!-- street_count -->
    </node>
    <edge source="342164" target="26386169" id="0">                    <!-- una arista; id = clave -->
      <data key="d7">motorway</data>     <!-- highway -->
      <data key="d9">5895.57</data>      <!-- length (m) -->
      ...
    </edge>
  </graph>
</graphml>
```

El archivo **declara el tipo real de cada atributo** (`double`, `long`, `boolean`, `string`), así que
al cargarlo con NetworkX los números llegan como números y los booleanos como booleanos:

```python
import networkx as nx
G = nx.read_graphml("data/espana_red_maestra_secundarias.graphml", node_type=int)   # node_type=int: ids de nodo como enteros
```

### Modelo de datos
Al cargarlo se obtiene un `networkx.MultiDiGraph`:

- **Dirigido**: cada arista tiene origen y destino. Una carretera de doble sentido se representa con
  **dos aristas**, una en cada dirección. Una autovía con calzadas separadas son dos aristas distintas.
- **Multigrafo**: puede haber **varias aristas entre los mismos dos nodos** (carreteras paralelas
  que unen las mismas intersecciones). Cada arista se identifica con la terna `(u, v, clave)`;
  la clave es 0 para la primera y 1, 2... para las paralelas (hay 3.349 pares con más de una).
- **Simplificado**: los nodos son solo **intersecciones y extremos de carretera**. Los puntos
  intermedios del trazado se han fusionado: **una arista es un tramo entero** entre dos
  intersecciones, con su longitud total, no un segmento recto.

### Atributos del grafo (metadatos)
| Atributo | Ejemplo | Significado |
|---|---|---|
| `created_date` | `2026-10-20 15:28:41` | Fecha de creación. |
| `created_with` | `anexos/construir_grafo.py (OSMnx 2.0.7)` | Programa y versión de OSMnx con que se construyó. |
| `crs` | `epsg:4326` | Sistema de coordenadas: latitud/longitud WGS84 (grados). |
| `simplified` | `True` | La topología está simplificada. |

### Nodos (179.594)
El **identificador del nodo** es el id del nodo en OpenStreetMap (entero). **Los nodos no tienen nombre**
(OpenStreetMap no nombra intersecciones): los nombres de ciudad se asocian a un nodo en la Parte 2.

| Atributo | Tipo | Significado |
|---|---|---|
| `x` | float | **Longitud** en grados (negativa al oeste de Greenwich). |
| `y` | float | **Latitud** en grados. |
| `street_count` | int | Número de calles que confluyen en el nodo. |

Tipos de nodo según `street_count`: **1** → 1.058 extremos (fin de carretera o corte en la frontera);
**2** → 4.612 empalmes entre dos vías distintas de OSM; **3** → 161.516 bifurcaciones o incorporaciones
(entradas y salidas de autovía); **4** → 10.332 cruces de cuatro ramas; **5 o más** → 2.076 nudos complejos.

### Aristas (309.250)
Cada arista es un tramo de carretera dirigido de `u` a `v`.

| Atributo | Tipo | Presencia | Significado |
|---|---|---|---|
| `length` | float | 100 % | **Longitud del tramo en metros** (suma de los segmentos del trazado original). Peso para distancias. |
| `travel_time` | float | 100 % | **Tiempo de viaje en segundos** = `length` / velocidad (`speed_kph`). Peso para tiempos. |
| `speed_kph` | float | 100 % | Velocidad usada (km/h): la velocidad máxima de OSM (media si hay varias); **si falta, la media de su tipo de vía**. |
| `highway` | str | 100 % | Tipo de vía (un único valor): `motorway`, `trunk`, `primary`, `secondary` o sus enlaces `*_link`. |
| `oneway` | bool | 100 % | `True` si es de **sentido único** (solo existe esta dirección); `False` si es de doble sentido (existe también la arista inversa). 227.446 y 81.804 aristas respectivamente. |
| `ref` | str | **90,3 % de los km** | Código de la carretera: `AP-7`, `A-4`, `N-340`... Si hay varios, separados por `;`. Ausente en casi todos los enlaces. |
| `name` | str | 72,0 % de los km | Nombre en lenguaje natural («Autovía del Mediterráneo»); a veces nombre de calle en travesías. Si hay varios, separados por ` / `. |

`ref` y `name` solo se escriben cuando existen (no hay textos vacíos).

Ejemplo real de arista (tramo de la AP-8):
```
highway=motorway  ref=AP-8  oneway=True  length=5895.57 m  speed_kph=100.0  travel_time=212.24 s
```
Comprobación: 5895,57 m ÷ (100 km/h ÷ 3,6) = 212,24 s.

Reparto por tipo de vía:

| `highway` | Qué es | Aristas | Km |
|---|---|---|---|
| `motorway` | autopista y autovía | 17.618 | 31.485 |
| `trunk` | vía rápida o carretera desdoblada | 52.029 | 31.438 |
| `primary` | carretera de la red principal | 75.467 | 40.454 |
| `secondary` | carretera de la red secundaria | 100.495 | 69.150 |
| `*_link` | enlaces y accesos de los cuatro anteriores | 63.641 | 10.233 |

### Atributos que NO se han incluido (y por qué)
- **`osmid`** (id de las vías de OSM de origen): era una *lista* en buena parte de las aristas, no sirve
  para trabajar ni para narrar rutas, y GraphML no admite listas.
- **`maxspeed`** (velocidad máxima tal cual está en OSM): traía listas y valores no numéricos
  (`ES:urban`, `50 mph`, `50|30`). Su información ya está resuelta en `speed_kph`.
- Los atributos que OSM da como lista (`ref`, `name`) se han unido en un único texto.

### Cosas a tener en cuenta
- **Peso para el TSP:** usar `weight="length"` (metros) o `weight="travel_time"` (segundos).
- **Velocidades de coche:** `speed_kph` y `travel_time` son de coche. En una red pensada para ir a pie o en bici
  solo tiene sentido la distancia.
- **Sin geometría:** al estar simplificadas, las aristas no guardan su forma; dibujadas son
  líneas rectas entre intersecciones. Las distancias **no** se ven afectadas.
- **Península únicamente:** Baleares, Canarias, Ceuta y Melilla no están.
- **Asimetría:** por las vías de sentido único, la distancia de A a B puede no ser igual a la de B a A.

### Grafo ligero: `data/espana_red_maestra.graphml`
Mismo formato y atributos, pero solo con `motorway`, `trunk`, `primary` y sus enlaces: **108.050 nodos** y
**181.006 aristas** (≈110.000 km), 63 MB. Es un subconjunto del base. Se construyó con la primera versión del
Anexo B; el Anexo B actual reproduce sus nodos, aristas y longitudes (ver «Decisiones», punto 6).

---

## Ciudades: `data/ciudades.csv`

75 filas: las **47 capitales de provincia peninsulares** y los **28 municipios peninsulares de más de 100.000
habitantes que no son capitales** (de los 62 que hay en la península, 34 ya son capitales). Se excluyen las
capitales insulares (Palma, Las Palmas de Gran Canaria, Santa Cruz de Tenerife) y los municipios de más de
100.000 habitantes de las islas (La Laguna, Telde).

| Columna | Significado |
|---|---|
| `nombre` | Nombre usado en el trabajo (p. ej. «A Coruña», «Alicante»). |
| `nombre_ine` | Nombre oficial del INE (p. ej. `Coruña, A`, `Alacant/Alicante`). |
| `capital_provincia` | `True` si es capital de provincia. |
| `comunidad` | Comunidad autónoma (verificada con las tablas por provincia del INE). |
| `poblacion_2025` | Habitantes a 1 de enero de 2025. |
| `lat`, `lon` | Coordenadas (grados). |
| `fuente_coordenadas` | Nodo `place=city` de OpenStreetMap del que salen (con su id). |

**Fuentes.** Lista de capitales y población: **INE**, *Cifras oficiales de población de los municipios españoles:
Revisión del Padrón Municipal* (datos a 1/1/2025, publicados el 11/12/2025; tablas 29005 y 2911 de la API del INE;
[BOE-A-2025-25362](https://www.boe.es/boe/dias/2025/12/11/pdfs/BOE-A-2025-25362.pdf)). **Coordenadas:** nodos
`place=city/town` de OpenStreetMap (el centro de cada núcleo urbano); **no son una fuente oficial**.

---

## Cómo usar el grafo

```python
import networkx as nx

G = nx.read_graphml("data/espana_red_maestra_secundarias.graphml", node_type=int)   # ~17-20 s

def nodo_mas_cercano(G, lon, lat):      # aproximado: distancia euclídea en grados
    return min(G.nodes, key=lambda n: (G.nodes[n]["x"] - lon) ** 2 + (G.nodes[n]["y"] - lat) ** 2)

madrid, sevilla = nodo_mas_cercano(G, -3.70, 40.42), nodo_mas_cercano(G, -5.99, 37.39)
nx.shortest_path_length(G, madrid, sevilla, weight="travel_time")   # segundos
nx.shortest_path_length(G, madrid, sevilla, weight="length")        # metros

# Narrar una ruta: tramos consecutivos con el mismo `ref` (códigos de carretera)
camino = nx.shortest_path(G, madrid, sevilla, weight="travel_time")
for u, v in zip(camino, camino[1:]):
    d = min(G[u][v].values(), key=lambda e: e["travel_time"])    # arista elegida si hay paralelas
    print(d.get("ref") or d.get("name"), round(d["length"] / 1000, 1), "km")
```

El dibujo del grafo completo está en el notebook (`dibujar_red(G)` de `tsp_utils.py`).

---

## Parte 2: versiones del grafo

Una **versión** del grafo se define con cuatro elecciones. Todo el código vive en la Parte 2 del notebook.

| Parámetro | Valores |
|---|---|
| `aristas` (carreteras) | `completo` (8 tipos de vía) · `autovias_principales` (sin secundarias) · `solo_autovias` · `sin_autovias` |
| `nodos` (ciudades) | `capitales` (47) · `capitales_y_100k` (75) |
| `ambito` | `espana` o una de las 15 comunidades autónomas peninsulares (`galicia`, `andalucia`, `castilla_y_leon`...) |
| `peso` | `km` (kilómetros) · `tiempo` (el registrado en el grafo, **en segundos**; de coche) |
| `general` | `multigrafo_dirigido` · `grafo_dirigido` · `multigrafo_no_dirigido` · `grafo_simple_no_dirigido` |
| `X_KM` | 10 km: una ciudad a más de 10 km de la red de una versión se deja fuera y se registra |
| `N_MIN` | 4: una versión por comunidad necesita al menos 4 ciudades |

**Cómo funciona.** Al viajante no le hace falta el mapa, sino una tabla de distancias entre ciudades. Se calculan
**16 tablas** de 75×75 con Dijkstra (4 carreteras × 2 pesos × dirigido o no dirigido) y se guardan; cada versión es un
**trozo de una tabla** (las ciudades que correspondan). Resultado: **480 versiones** en el catálogo, que corresponden a
**240 grafos de ciudades distintos** (`multigrafo` y `grafo simple` dan la misma tabla).

**Qué hay en `data/versiones/`:** las 16 tablas (`<carreteras>__<peso>__<dirigido|no_dirigido>.csv`, con los nombres de las
ciudades en la primera fila; se abren con Excel), `catalogo.csv` (las 480 versiones con su número de ciudades),
`excluidas.csv` (ciudades dejadas fuera y a qué distancia estaban) y `resumen_carreteras.csv`.

**Cómo se pide una versión** (devuelve un grafo de NetworkX `K`: nodos = ciudades, con `lat` y `lon`;
`K[a][b]["peso"]` = distancia de `a` a `b`; `K.graph` guarda los parámetros, la unidad y las ciudades que quedaron fuera):

```python
K = cargar_version(aristas="solo_autovias", nodos="capitales", ambito="espana", peso="km", general="grafo_dirigido")
K["Madrid"]["Sevilla"]["peso"]      # km
```

`dirigido` → `nx.DiGraph` (la distancia de ida y la de vuelta pueden diferir; Madrid→Sevilla 502 km, Sevilla→Madrid 517 km);
no dirigido → `nx.Graph` (se ignoran los sentidos únicos; una arista por par).

**Lo que queda en cada versión de carreteras** (medido al calcular las tablas):

| Versión | Nodos | Aristas | Km | Nodos descartados (fuera de la mayor componente) | Ciudades fuera (> 10 km) |
|---|---|---|---|---|---|
| `completo` | 179.594 | 309.250 | 182.760 | 0 | 0 |
| `autovias_principales` | 115.476 | 190.221 | 111.121 | 5.885 | 0 |
| `solo_autovias` | 19.239 | 24.450 | 28.921 | 14.027 | **3**: Salamanca (62,7 km), Badajoz (50,5 km), Cuenca (39,6 km) |
| `sin_autovias` | 146.903 | 256.301 | 140.040 | 8.464 | 0 |

**Decisiones de diseño.**
- **`multigrafo` = `grafo simple` en el grafo de ciudades.** Entre dos nodos el camino mínimo solo usa la arista más barata, así que
  quedarse con una no cambia ninguna distancia.
- **Bici y andando no son versiones aparte.** Con velocidad constante, tiempo = distancia / velocidad: el camino más corto y el
  recorrido óptimo son los mismos que con `km`. El caso «a pie o en bici» es `sin_autovias` con `km`; para horas se divide
  (`km / 20` en bici, `km / 5` andando).
- **Las versiones por comunidad usan toda la red**: el mejor camino entre dos ciudades de la comunidad puede salir de ella.
  Con `N_MIN = 4` salen 5 conjuntos de capitales (Andalucía, Castilla y León, Castilla-La Mancha, Cataluña, Galicia) y 8 de
  capitales + >100.000 (esas más Madrid, Comunidad Valenciana y País Vasco).
- **`solo_autovias`:** Salamanca, Badajoz y Cuenca quedan fuera. Como con las islas, en un primer intento no se puede plantear el
  viajante con ellas (por ejemplo, Castilla y León pasa de 9 a 8 capitales).
- **Distancias de acceso:** la distancia de cada ciudad al nodo de carretera más cercano **no** se suma a la tabla.
- **No dirigido:** se ignoran los sentidos únicos y cada tramo vale lo que la más barata de sus dos direcciones. Un atajo por una
  rampa en contradirección es un efecto pequeño, pero existe.

**Comprobaciones** (una celda del notebook): distancias finitas y no negativas; diagonal 0; tabla no dirigida simétrica; no dirigido
nunca mayor que dirigido; desigualdad triangular. Además se cargaron las 480 versiones del catálogo sin error.

**Cómo recalcular las tablas** (si se cambia `X_KM`, por ejemplo): `RECALCULAR = True` en la celda de parámetros; hace falta el grafo
base (Parte 1). Tarda ~2 minutos.

---

## Datos y licencia

- **Fuente de las carreteras:** OpenStreetMap, extracto de España de [Geofabrik](https://download.geofabrik.de/europe/spain.html)
  (`spain-latest.osm.pbf`, 1,4 GB, modificado el 19/10/2026). **No es una fuente oficial** (datos colaborativos).
- **Licencia:** ODbL. Citar siempre «© OpenStreetMap contributors».
- **Filtro:** `highway` ∈ {`motorway`, `trunk`, `primary`, `secondary`} y sus `*_link`.
- **`length`** es la longitud geométrica del trazado en OSM, no el kilometraje oficial.
- **`travel_time`** es una estimación: no incluye tráfico, peajes ni semáforos, y muchas velocidades están imputadas
  (la velocidad máxima solo está etiquetada en parte de las aristas).

## Decisiones y justificación

1. **Overpass descartado.** El primer enfoque (`docs/intento_overpass/`) descargaba la red
   con `ox.graph_from_polygon` mediante 324 consultas a `overpass-api.de`. En ~11 h solo
   se completaron 19 (6 %), por errores `ConnectTimeout` y `502 Bad Gateway` del servidor
   público (saturado; una de sus dos IPs no aceptaba conexiones y OSMnx fija una sola IP
   por host). El log queda como evidencia.
2. **Extracto de Geofabrik + filtrado local.** Un único archivo reanudable de 1,4 GB;
   se filtra con `pyosmium` en dos pasadas (vías y coordenadas de sus nodos).
3. **Grafo base con carreteras secundarias.** Con solo `motorway`/`trunk`/`primary`, una red *sin autovías* queda
   llena de agujeros (Almería a 142 km de la red, Madrid–Sevilla 761 km en vez de 510). Con las secundarias es
   utilizable, y además las ciudades vecinas quedan mucho más cerca entre sí (en la red sin secundarias,
   Terrassa–Sabadell salía un 193 % más lejos). Las versiones más pequeñas se obtienen filtrando aristas. No supone problema de cómputo: se carga en
   ~17 s y las distancias entre 75 ciudades salen en segundos.
4. **Conectividad fuerte.** Se conserva la mayor componente fuertemente conexa para
   garantizar camino dirigido entre cualquier par de nodos (vías de sentido único). Esto
   también descarta las islas.
5. **Archivo tipado y cargable con NetworkX puro.** Se guarda con `nx.write_graphml`, que
   declara los tipos reales, para que el notebook solo necesite NetworkX (como las prácticas) y
   no OSMnx. A cambio, GraphML no admite listas: de ahí la limpieza de atributos (`osmid` y
   `maxspeed` fuera; `ref` y `name` unidos en un texto).
6. **Construcción con poca memoria.** El grafo con secundarias no cabía con `ox.graph_from_*` (se estimaban ~12 GB).
   El Anexo B reimplementa con arrays las reglas de simplificación de OSMnx. Se comprobó contra el grafo ligero
   entregado: mismos 108.050 nodos (mismos ids), mismas 181.006 aristas y mismas longitudes (110.128,4 km). Solo
   cambian ligeramente las velocidades imputadas (diferencia media 0,05 km/h; 136 aristas difieren más de 1 km/h),
   porque el método anterior elegía de forma arbitraria el tipo de vía de las aristas mixtas y el nuevo usa el de
   mayor jerarquía.
7. **Ciudades.** Lista y población del INE (oficial); coordenadas de OpenStreetMap (no oficiales). Una primera
   geocodificación con Nominatim devolvía la provincia en lugar del municipio para algunas capitales (Guadalajara,
   Palencia...) y el centro del término municipal en otras (Almería, 14 km desplazada); se sustituyó por los nodos
   `place=city/town` del propio extracto.
8. **Versiones como tablas de distancias.** Guardar 480 grafos de carreteras ocuparía decenas de GB. Como las distancias
   entre ciudades se calculan sobre toda la red, basta con 16 tablas de 75×75 (0,9 MB) de las que cada versión es un trozo.
   Así los compañeros que programan los algoritmos no necesitan el grafo grande.
9. **Comunidad de cada ciudad.** Se asignó con las tablas por provincia del INE (cada ciudad aparece en una única provincia
   con la misma población) y la división provincia → comunidad autónoma.
10. **Validación.** El Anexo B relee el archivo con `nx.read_graphml` y comprueba tipos, valores
   y conectividad fuerte.

## Hoja de ruta (partes del notebook)

1. **Construcción del grafo** — hecha (grafo base con secundarias).
2. **Versiones del grafo** — hecha: 4 versiones de carreteras, 2 conjuntos de ciudades (en toda España y por comunidad),
   2 pesos y 4 tipos de grafo → 480 versiones, cargables con `cargar_version(...)`.
3. **Algoritmos para el TSP** — *en curso.* Teoría y eficiencia (exactos y heurísticos); cada algoritmo recibe un grafo `K`
   y devuelve `(ruta, coste)`. Cada persona programa el suyo en un notebook de `parte3/` (ver `CONTRIBUTING.md`) y se
   integran en `trabajo_tsp.ipynb` con `python parte3/herramientas.py integrar`.
4. **Estudio experimental** — *pendiente.* Tiempos y calidad de las soluciones al variar el nº de ciudades, el algoritmo, el peso
   y la versión de carreteras. Un estudio de escala por comunidades autónomas (con las versiones regionales) queda para más adelante.
5. **Conclusiones** — *pendiente.*

Pendiente además: sustituir en el notebook el resumen del enunciado por el enunciado literal del trabajo, y añadir
el registro de uso de IA y las insignias de autoría que exige la asignatura.

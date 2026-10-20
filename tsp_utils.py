"""
tsp_utils.py — funciones compartidas por el notebook del trabajo (análogo a mati_utils.py de las prácticas).

Por qué existe este archivo: dibujar la red de carreteras de España (181.000 aristas) con
Matplotlib no se puede hacer con `nx.draw` (sería lentísimo). Aquí se deja UNA vez el código
de dibujo, comentado, y en el notebook basta con:

    from tsp_utils import dibujar_red, SEED
"""

import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

# Semilla fija para todo lo aleatorio del trabajo (selección de ciudades, heurísticas...),
# de modo que los resultados sean reproducibles entre ejecuciones.
SEED = 42

# Color y grosor de cada tipo de vía (`highway`), de menos a más importante (8 tipos del grafo base):
# se dibuja en este orden, así lo importante queda encima.
ESTILO = {
    "secondary": ("#cfd5dc", 0.2), "secondary_link": ("#cfd5dc", 0.2),  # carretera secundaria (gris claro)
    "primary": ("#9aa5b1", 0.3), "primary_link": ("#9aa5b1", 0.3),   # carretera principal (gris)
    "trunk": ("#e08a1e", 0.5), "trunk_link": ("#e08a1e", 0.5),       # vía rápida (naranja)
    "motorway": ("#c0392b", 0.7), "motorway_link": ("#c0392b", 0.7),  # autopista/autovía (rojo)
}


def dibujar_red(G, titulo="", ax=None, figsize=(9, 8)):
    """Dibuja el grafo de carreteras G coloreado por tipo de vía.

    Parámetros:
        G: grafo con atributos de nodo `x` (longitud) e `y` (latitud) y de arista `highway`.
        titulo: texto que aparece encima del dibujo.
        ax: eje de Matplotlib donde dibujar. Si no se indica, se crea una figura nueva y se
            muestra directamente (plt.show()); si se indica, se dibuja ahí y se devuelve el eje.
        figsize: tamaño de la figura (solo si no se indica `ax`).

    Cada arista se dibuja como una línea recta entre sus dos nodos (las aristas simplificadas
    no guardan la forma de la carretera; las distancias no se ven afectadas).
    """
    propio = ax is None
    if propio:
        _, ax = plt.subplots(figsize=figsize)

    # Se agrupan los segmentos por tipo de vía y se dibujan todos de una vez por tipo
    segmentos = {tipo: [] for tipo in ESTILO}
    for u, v, d in G.edges(data=True):
        segmentos[d["highway"]].append(((G.nodes[u]["x"], G.nodes[u]["y"]),
                                        (G.nodes[v]["x"], G.nodes[v]["y"])))
    for tipo, segs in segmentos.items():
        color, ancho = ESTILO[tipo]
        ax.add_collection(LineCollection(segs, colors=color, linewidths=ancho))

    ax.autoscale()
    ax.set_aspect(1 / 0.76)   # corrección aproximada de longitud/latitud a la latitud de España
    ax.axis("off")
    if titulo:
        ax.set_title(titulo)
    if propio:
        plt.show()
        return None   # la figura ya se ha mostrado: no se devuelve nada para que Jupyter no escriba <Axes...>
    return ax

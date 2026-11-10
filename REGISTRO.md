# Registro del equipo

Quién ha hecho cada parte, con qué ayuda y en qué estado está el trabajo. Es el documento de referencia para la memoria
(apartados de autoría y de uso de IA). **Si cambia algo, actualízalo en el mismo Pull Request.**

## Equipo

| Persona | Rama de trabajo | Responsable de |
|---|---|---|
| Raimundo | `dev-raimundo` | Partes 1 y 2 (grafo y versiones), herramientas de la Parte 3, 4 algoritmos, coordinación e integración |
| Pablo | `dev-pablo` | Fuerza bruta, vecino más cercano |
| Jiahao | `dev_jiahao` | DFJ |
| Juan | `dev_juan` | Recocido simulado (MCMC) |

Las ramas conservan su nombre original. Todo el trabajo se integra en `main`.

## Autoría de cada parte

| Parte | Qué es | Autoría | Fichero |
|---|---|---|---|
| 1 | Construcción del grafo de carreteras (OSM) | Raimundo | `anexos/`, `trabajo_tsp.ipynb` |
| 2 | Versiones del grafo (480 versiones, 16 tablas) | Raimundo | `trabajo_tsp.ipynb`, `data/versiones/` |
| 3 | Fuerza bruta | Pablo | `parte3/fuerza_bruta_pablo.ipynb` |
| 3 | Vecino más cercano | Pablo | `parte3/vecino_mas_cercano_pablo.ipynb` |
| 3 | DFJ | Jiahao | `parte3/dfj_jiahao.ipynb` |
| 3 | Recocido simulado (MCMC) | Juan | `parte3/recocido_simulado_juan.ipynb` |
| 3 | Held–Karp | Raimundo | `parte3/held_karp_raimundo.ipynb` |
| 3 | 2-opt | Raimundo | `parte3/dos_opt_raimundo.ipynb` |
| 3 | Christofides | Raimundo | `parte3/christofides_raimundo.ipynb` |
| 3 | Algoritmo genético | Raimundo | `parte3/genetico_raimundo.ipynb` |
| 4 | Estudio empírico | Raimundo | pendiente |
| 5 | Conclusiones | Equipo | pendiente |

## Uso de IA

| Parte | Herramienta | Para qué | Revisión |
|---|---|---|---|
| Partes 1 y 2, herramientas de `parte3/`, guía del equipo | Claude Code (Anthropic) | Escribir y probar los scripts de descarga y construcción del grafo, el código del notebook, la plantilla y la herramienta de integración | Raimundo ejecutó y revisó el resultado |
| Held–Karp, 2-opt, Christofides y genético | Claude Code (Anthropic) | Teoría, código, pruebas y redacción de resultados | Raimundo; cada algoritmo se contrastó con la fuerza bruta (y con DFJ en 47 ciudades) |
| Fuerza bruta, vecino más cercano | **Pendiente de indicar por Pablo** | | |
| DFJ | **Pendiente de indicar por Jiahao** | | |
| Recocido simulado | **Pendiente de indicar por Juan** | | |

> Cada autor debe completar su fila (qué herramienta usó y para qué) y poner lo mismo en el campo `"ia"` de su entrada
> en `parte3/fichas.json`.

## Estado

| Parte | Estado |
|---|---|
| 1. Grafo | Hecha |
| 2. Versiones | Hecha |
| 3. Algoritmos | Hecha (8 algoritmos, formato unificado) |
| 4. Estudio empírico | Siguiente |
| 5. Conclusiones | Pendiente |
| Web interactiva | Pendiente (un único `index.html` publicable en GitHub Pages) |
| Memoria | Pendiente (LaTeX → PDF) |

## Cambios en las aportaciones de los compañeros al unificar el formato

Para que todo el trabajo quede homogéneo se han hecho estos retoques, sin tocar la lógica de los algoritmos:

- **Todos:** nombre de fichero `algoritmo_autor.ipynb`; ficha común al inicio (`parte3/fichas.json`); cabecera «🧪 PRUEBAS»;
  kernel estándar (`python3`).
- **Pablo:** títulos sin el nombre del autor (la autoría está en la ficha).
- **Jiahao:** título propio en lugar del de la plantilla; borradas las notas de la plantilla y dos celdas sueltas de prueba; el código
  de `dfj` ya no depende de la versión de PuLP (usa `LpStatus` y `pulp.value`), el `!pip install` pasó a `requirements.txt`
  y se corrigieron erratas del texto.
- **Juan:** títulos internos de la teoría como texto en negrita; pseudocódigo corregido (`mientras T > T_min`); añadido el apartado
  «Propiedades»; semilla fija `random.seed(42)` antes de las pruebas; cifras de la comparativa y de la tabla de resultados
  sustituidas por las medidas al ejecutar el notebook.

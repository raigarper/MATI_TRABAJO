# Web del viajante · Laboratorio de algoritmos

Visualización interactiva de los 8 algoritmos del trabajo sobre la red de carreteras de España: se ve cómo cada uno construye
su ruta paso a paso (con su pseudocódigo resaltado y una explicación), y se pueden comparar en una **carrera**. Pensada como
apoyo visual para la presentación.

## Cómo abrirla

La web necesita un servidor (los navegadores no permiten abrir `index.html` directamente por seguridad):

- **Windows:** doble clic en `iniciar_web.bat` (arranca el servidor y abre el navegador).
- **Cualquier sistema:** en esta carpeta, `python -m http.server 8000` y abre <http://localhost:8000>.
- **Publicada:** con GitHub Pages (ver abajo) queda en una dirección permanente.

No hace falta internet: las dos librerías externas (HiGHS y el emparejamiento de Edmonds, licencia MIT) van en `vendor/`.

## Qué tiene

| Vista | Para qué |
|---|---|
| **Laboratorio** | Elegir algoritmo, ciudades (pulsando el mapa o la lista) y versión (km o tiempo; con o sin sentidos únicos). Reproductor con *Ejecutar*, *paso a paso*, *paso atrás*, *saltar al final* y velocidad. |
| **Carrera** | Varios algoritmos sobre las mismas ciudades a la vez. Cada uno avanza el mismo tiempo de cálculo; los que no se pueden aplicar se descartan con su motivo, igual que en el estudio del trabajo. |
| **Acerca de** | Qué es y cómo se usa. |

Atajos: `Espacio` ejecuta/pausa, `←` y `→` retroceden/avanzan un paso. Rueda del ratón = zoom; arrastrar = mover el mapa.
Botón ⛶ = pantalla completa (para presentar) y ◐ = tema oscuro/claro.

Límites de la animación (iguales a la lógica del estudio, algo menores): fuerza bruta hasta 10 ciudades, Held–Karp hasta 18,
Christofides solo sin sentidos únicos; el resto, hasta las 75 ciudades.

## Estructura

```
web/
├── index.html          página única (Laboratorio, Carrera, Acerca de)
├── css/estilo.css      tema oscuro (mapa nocturno) y claro
├── js/
│   ├── algoritmos.js   los 8 algoritmos como generadores: cada `yield` es un fotograma de la animación
│   ├── meta.js         ficha, explicación y pseudocódigo de cada algoritmo; reglas de aplicabilidad
│   ├── solver.js       HiGHS (DFJ) y emparejamiento de Edmonds (Christofides)
│   ├── mapa.js         mapa esquemático, zoom y dibujo de rutas sobre el trazado real
│   ├── datos.js        carga de data/ y matrices de distancias
│   ├── app.js          estado, panel de ciudades, Laboratorio y reproductor
│   └── carrera.js      la carrera
├── data/               datos ya preparados (ver abajo)
├── vendor/             HiGHS (WebAssembly) y blossom
├── tests/probar.mjs    pruebas de los algoritmos con Node
├── herramientas/preparar_datos.py   genera data/ a partir del grafo del trabajo
└── capturas/           capturas de pantalla (para la memoria y la presentación)
```

## Datos (`data/`)

Se generan **una sola vez** con `python web/herramientas/preparar_datos.py` (necesita el grafo grande y ≈ 4 GB de memoria; ver
los anexos A y B del trabajo) y se guardan en el repositorio, así que la web no necesita el grafo para funcionar:

| Archivo | Contenido |
|---|---|
| `ciudades.json` | 75 ciudades (nombre, coordenadas, población, comunidad, si es capital) |
| `matrices.json` | distancias entre ciudades: km y tiempo, con y sin sentidos únicos (las mismas tablas de la Parte 2) |
| `rutas.json` | trazado **real por carretera** entre cada par de ciudades (camino mínimo sobre el grafo, simplificado) |
| `red_fondo.json` | autovías y vías rápidas, para el fondo |
| `contorno.json` | contorno de la península y países vecinos (Natural Earth) |

## Pruebas

Los algoritmos de JavaScript se comprueban contra los resultados de Python (mismos datos y costes del trabajo):

```bash
npm install highs@1.8.0 --prefix /ruta/temporal          # solo para la prueba de DFJ con Node
node web/tests/probar.mjs /ruta/temporal
```

Comprueba, por ejemplo, que fuerza bruta, Held–Karp y DFJ dan el mismo óptimo, que el vecino más cercano y el 2-opt dan el
mismo coste que en Python (6.772,1 y 6.326,0 km con las 47 capitales) y que DFJ resuelve las 75 ciudades (6.146,165 km).

## Publicar en GitHub Pages

El repositorio incluye la acción `.github/workflows/web.yml`. Para activarla, **el propietario del repositorio** debe ir a
*Settings → Pages → Build and deployment → Source: GitHub Actions*. Después, cada cambio en `web/` que llegue a `main` se
publica solo.

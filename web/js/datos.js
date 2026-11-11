// Carga de los datos de la web (carpeta data/) y utilidades para usarlos.

export async function cargarDatos() {
  const pedir = (f) => fetch(`data/${f}`).then((r) => { if (!r.ok) throw new Error(`No se pudo cargar data/${f}`); return r.json(); });
  const [ciudades, mat, contorno, fondo, rutasCod] = await Promise.all(['ciudades.json', 'matrices.json', 'contorno.json', 'red_fondo.json', 'rutas.json'].map(pedir));
  const cache = new Map();
  const datos = {
    ciudades, mat, contorno, fondo, rutasCod,
    nombres: ciudades.map((c) => c.nombre),
    // Trazado real por carretera entre las ciudades i y j: lista de [lon, lat]
    geometria(i, j) {
      const clave = i < j ? `${i}-${j}` : `${j}-${i}`;
      let g = cache.get(clave);
      if (!g) { g = decodificar(rutasCod[clave]); cache.set(clave, g); }
      return i < j ? g : g.slice().reverse();
    },
  };
  return datos;
}

// Decodifica una polilínea (formato de Google con 4 decimales) a [[lon, lat], ...]
export function decodificar(texto) {
  const pts = []; let i = 0, lat = 0, lon = 0;
  while (i < texto.length) {
    for (const eje of [0, 1]) {
      let resultado = 0, desplazamiento = 0, b;
      do { b = texto.charCodeAt(i++) - 63; resultado |= (b & 0x1f) << desplazamiento; desplazamiento += 5; } while (b >= 0x20);
      const d = resultado & 1 ? ~(resultado >> 1) : resultado >> 1;
      if (eje === 0) lat += d; else lon += d;
    }
    pts.push([lon / 1e4, lat / 1e4]);
  }
  return pts;
}

// Matriz de costes para una lista de ciudades (índices globales). En «tiempo» se pasa a horas.
export function matrizDe(datos, seleccion, peso, dirigido) {
  const M = datos.mat[`${peso}_${dirigido ? 'dirigido' : 'no_dirigido'}`];
  const k = peso === 'tiempo' ? 1 / 3600 : 1;
  return seleccion.map((a) => seleccion.map((b) => M[a][b] * k));
}

export const UNIDAD = { km: 'km', tiempo: 'h' };

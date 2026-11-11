// Dos herramientas «pesadas» que necesitan algunos algoritmos:
//   · un solver de programación entera (HiGHS, compilado a WebAssembly) para DFJ
//   · el emparejamiento de coste mínimo de Edmonds (algoritmo «blossom») para Christofides
// Se cargan de la carpeta vendor/ (no hace falta internet). En las pruebas con Node se inyectan con `inyectar`.

let highs = null, blossom = null;

export function inyectar(o) {
  if (o.highs) highs = o.highs;
  if (o.blossom) blossom = o.blossom;
}

function cargarScript(src) {
  return new Promise((ok, error) => {
    const s = document.createElement('script');
    s.src = src; s.onload = ok; s.onerror = () => error(new Error('No se pudo cargar ' + src));
    document.head.appendChild(s);
  });
}

async function obtenerHighs() {
  if (highs) return highs;
  await cargarScript('vendor/highs.js');
  // eslint-disable-next-line no-undef
  highs = await Module({ locateFile: (f) => 'vendor/' + f });
  return highs;
}

// Resuelve un problema escrito en formato LP y devuelve {objetivo, valores: {variable: valor}}
export async function resolverEntero(lp) {
  const h = await obtenerHighs();
  await new Promise((r) => setTimeout(r, 30));          // deja que el navegador pinte «resolviendo...» antes de bloquearse
  const sol = h.solve(lp);
  if (sol.Status !== 'Optimal') throw new Error('El solver no encontró solución óptima: ' + sol.Status);
  const valores = {};
  for (const [nombre, col] of Object.entries(sol.Columns)) valores[nombre] = col.Primal;
  return { objetivo: sol.ObjectiveValue, valores };
}

// Emparejamiento perfecto de coste mínimo entre `nodos` (lista de índices; número par), con coste(a, b)
export function emparejamientoMinimo(nodos, coste) {
  const f = blossom ?? (typeof window !== 'undefined' ? window.edmondsBlossom : null);
  if (!f) throw new Error('Falta la librería de emparejamiento (vendor/blossom.global.js)');
  let max = 0;
  for (let i = 0; i < nodos.length; i++) for (let j = i + 1; j < nodos.length; j++) max = Math.max(max, coste(nodos[i], nodos[j]));
  const aristas = [];
  for (let i = 0; i < nodos.length; i++) for (let j = i + 1; j < nodos.length; j++) aristas.push([i, j, Math.round((max + 1 - coste(nodos[i], nodos[j])) * 100)]);   // coste mínimo = peso máximo invertido
  const mate = f(aristas, true);
  const pares = [];
  for (let i = 0; i < nodos.length; i++) if (mate[i] > i) pares.push([nodos[i], nodos[mate[i]]]);
  return pares;
}

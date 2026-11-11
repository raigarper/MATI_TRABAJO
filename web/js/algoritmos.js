// Algoritmos del viajante escritos como GENERADORES: cada `yield` es un «fotograma» de la animación.
//
// Un fotograma es un objeto con (todos opcionales salvo `l` y `t`):
//   l          línea del pseudocódigo que se está ejecutando (índice)
//   t          explicación del paso, en lenguaje llano (admite <b>, <i>)
//   ruta       camino que se está construyendo (lista de índices de ciudad)
//   cerrada    true si la ruta es un ciclo completo (se dibuja la vuelta al inicio)
//   aristas    [{a, b, c}] aristas a resaltar; c = clase de estilo ('cand', 'elegida', 'quitar', 'poner', 'arbol', 'empar', 'euler', 'asig')
//   nodos      {índice: clase} ciudades a resaltar
//   coste      coste de `ruta` (o del dato principal del paso)
//   mejor      mejor coste encontrado hasta ahora
//   info       {etiqueta: valor} contadores para el panel de datos
//   serie      número que se añade a la gráfica de evolución
//   importante true si el reproductor no debe saltarse este fotograma
//   fin        true en el último fotograma (contiene la ruta final)
//
// Todos reciben un contexto `ctx = {n, W, inicio, nombres, simetrico}` donde W[i][j] es el coste de ir de i a j.

import { resolverEntero, emparejamientoMinimo } from './solver.js';

export const costeCiclo = (W, ruta) => {
  let s = 0;
  for (let i = 0; i < ruta.length; i++) s += W[ruta[i]][ruta[(i + 1) % ruta.length]];
  return s;
};

const nom = (ctx, i) => `<b>${ctx.nombres[i]}</b>`;
const fmt = (x) => x.toLocaleString('es-ES', { maximumFractionDigits: 1 });

// Generador de números aleatorios con semilla (mulberry32): mismo resultado con la misma semilla
export function crearAzar(semilla) {
  let a = semilla >>> 0;
  const azar = () => {
    a = (a + 0x6D2B79F5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  azar.entero = (n) => Math.floor(azar() * n);
  return azar;
}

// Ruta del vecino más cercano (sin fotogramas), para los algoritmos que parten de ella
export function rutaVecinoMasCercano(ctx) {
  const { n, W, inicio } = ctx;
  const ruta = [inicio], vis = new Array(n).fill(false);
  vis[inicio] = true;
  while (ruta.length < n) {
    const a = ruta[ruta.length - 1];
    let mejor = -1, mc = Infinity;
    for (let j = 0; j < n; j++) if (!vis[j] && W[a][j] < mc) { mc = W[a][j]; mejor = j; }
    ruta.push(mejor); vis[mejor] = true;
  }
  return ruta;
}

// ───────────────────────────── 1. Fuerza bruta ─────────────────────────────
export function* fuerzaBruta(ctx) {
  const { n, W, inicio } = ctx;
  const otras = [];
  for (let i = 0; i < n; i++) if (i !== inicio) otras.push(i);
  const m = otras.length;
  let total = 1;
  for (let i = 2; i <= m; i++) total *= i;
  yield { l: 0, t: `Hay ${nom(ctx, inicio)} de partida y ${m} ciudades más por ordenar: ${m}! = <b>${total.toLocaleString('es-ES')}</b> rutas posibles. Se prueban todas.`, ruta: [inicio], info: { 'rutas posibles': total } };
  // Permutaciones por el algoritmo de Heap (iterativo)
  const perm = otras.slice();
  const c = new Array(m).fill(0);
  let mejor = Infinity, mejorRuta = null, probadas = 0;
  const ruta = [inicio, ...perm];
  const evaluar = function* () {
    probadas++;
    for (let i = 0; i < m; i++) ruta[i + 1] = perm[i];
    const coste = costeCiclo(W, ruta);
    if (coste < mejor - 1e-9) {
      mejor = coste; mejorRuta = ruta.slice();
      yield { l: 4, t: `Ruta nº ${probadas.toLocaleString('es-ES')}: cuesta <b>${fmt(coste)}</b>, <b>mejor que todas las anteriores</b>. Pasa a ser la mejor.`, ruta: ruta.slice(), cerrada: true, coste, mejor, importante: true, info: { 'rutas probadas': probadas, 'de': total, 'progreso': probadas / total }, serie: mejor };
    } else {
      yield { l: 3, t: `Ruta nº ${probadas.toLocaleString('es-ES')}: cuesta ${fmt(coste)}. No mejora la mejor (${fmt(mejor)}).`, ruta, cerrada: true, coste, mejor, info: { 'rutas probadas': probadas, 'de': total, 'progreso': probadas / total } };
    }
  };
  yield* evaluar();
  let i = 1;
  while (i < m) {
    if (c[i] < i) {
      const k = i % 2 === 0 ? 0 : c[i];
      [perm[k], perm[i]] = [perm[i], perm[k]];
      yield* evaluar();
      c[i]++; i = 1;
    } else { c[i] = 0; i++; }
  }
  yield { l: 6, t: `Probadas las ${total.toLocaleString('es-ES')} rutas: la mejor cuesta <b>${fmt(mejor)}</b>. Es el <b>óptimo</b>.`, ruta: mejorRuta, cerrada: true, coste: mejor, mejor, fin: true, importante: true, info: { 'rutas probadas': probadas, 'de': total, 'progreso': 1 } };
}

// ───────────────────────────── 2. Vecino más cercano ─────────────────────────────
export function* vecinoMasCercano(ctx) {
  const { n, W, inicio } = ctx;
  const ruta = [inicio], vis = new Array(n).fill(false);
  vis[inicio] = true;
  let coste = 0;
  yield { l: 1, t: `Salimos de ${nom(ctx, inicio)}.`, ruta: ruta.slice(), coste, importante: true };
  while (ruta.length < n) {
    const a = ruta[ruta.length - 1];
    let mejor = -1, mc = Infinity;
    const cand = [];
    for (let j = 0; j < n; j++) if (!vis[j]) { cand.push({ a, b: j, c: 'cand' }); if (W[a][j] < mc) { mc = W[a][j]; mejor = j; } }
    yield { l: 3, t: `Desde ${nom(ctx, a)} se miran todas las ciudades que faltan (${cand.length}).`, ruta: ruta.slice(), aristas: cand, coste, nodos: { [a]: 'actual' } };
    yield { l: 4, t: `La más cercana es ${nom(ctx, mejor)} (${fmt(mc)}). Se va allí.`, ruta: ruta.slice(), aristas: [{ a, b: mejor, c: 'elegida' }], coste, nodos: { [a]: 'actual', [mejor]: 'elegida' } };
    ruta.push(mejor); vis[mejor] = true; coste += mc;
    yield { l: 5, t: `Visitada ${nom(ctx, mejor)}. Coste acumulado: ${fmt(coste)}.`, ruta: ruta.slice(), coste, serie: coste, info: { visitadas: `${ruta.length} de ${n}` } };
  }
  const vuelta = W[ruta[n - 1]][inicio];
  coste += vuelta;
  yield { l: 7, t: `No quedan ciudades: se vuelve a ${nom(ctx, inicio)} (${fmt(vuelta)}). Coste total: <b>${fmt(coste)}</b>. Nunca se ha mirado atrás.`, ruta, cerrada: true, coste, mejor: coste, fin: true, importante: true };
}

// ───────────────────────────── 3. 2-opt ─────────────────────────────
export function* dosOpt(ctx) {
  const { n, W, inicio } = ctx;
  let t = rutaVecinoMasCercano(ctx);
  let coste = costeCiclo(W, t);
  yield { l: 0, t: `Se parte de una ruta cualquiera: aquí, la del <b>vecino más cercano</b> (${fmt(coste)}).`, ruta: t.slice(), cerrada: true, coste, mejor: coste, importante: true, serie: coste };
  let vueltas = 0;
  while (n > 3) {
    // Sumas acumuladas del coste de recorrer la ruta hacia delante (F) y hacia atrás (B)
    const F = new Float64Array(n), B = new Float64Array(n);
    for (let k = 1; k < n; k++) { F[k] = F[k - 1] + W[t[k - 1]][t[k]]; B[k] = B[k - 1] + W[t[k]][t[k - 1]]; }
    let mejorDelta = -1e-9, bi = -1, bj = -1;
    for (let i = 0; i < n - 1; i++) {
      for (let j = i + 1; j < n; j++) {
        if (i === 0 && j === n - 1) continue;
        const a = t[i], b = t[(i + 1) % n], c = t[j], d = t[(j + 1) % n];
        const delta = W[a][c] + W[b][d] - W[a][b] - W[c][d] + (B[j] - B[i + 1]) - (F[j] - F[i + 1]);
        if (delta < mejorDelta) { mejorDelta = delta; bi = i; bj = j; }
      }
    }
    vueltas++;
    if (bi < 0) break;
    const a = t[bi], b = t[bi + 1], c = t[bj], d = t[(bj + 1) % n];
    yield { l: 3, t: `Vuelta ${vueltas}: de todos los pares de tramos, el mejor cambio quita <b>${fmt(-mejorDelta)}</b> de coste. Se quitan los tramos ${nom(ctx, a)}→${nom(ctx, b)} y ${nom(ctx, c)}→${nom(ctx, d)}.`,
      ruta: t.slice(), cerrada: true, coste, mejor: coste, aristas: [{ a, b, c: 'quitar' }, { a: c, b: d, c: 'quitar' }], nodos: { [a]: 'actual', [b]: 'actual', [c]: 'actual', [d]: 'actual' }, info: { vueltas } };
    const tramo = t.slice(bi + 1, bj + 1).reverse();
    t.splice(bi + 1, tramo.length, ...tramo);
    coste += mejorDelta;
    yield { l: 4, t: `Se unen ${nom(ctx, a)}→${nom(ctx, c)} y ${nom(ctx, b)}→${nom(ctx, d)} invirtiendo el tramo del medio. Coste: <b>${fmt(coste)}</b>.`,
      ruta: t.slice(), cerrada: true, coste, mejor: coste, aristas: [{ a, b: c, c: 'poner' }, { a: b, b: d, c: 'poner' }], importante: true, serie: coste, info: { vueltas } };
  }
  const real = costeCiclo(W, t);
  yield { l: 6, t: `Ningún cambio de dos tramos mejora ya la ruta: es un <b>óptimo local</b>. Coste final: <b>${fmt(real)}</b> tras ${vueltas - 1} mejoras.`, ruta: t, cerrada: true, coste: real, mejor: real, fin: true, importante: true, serie: real, info: { vueltas: vueltas - 1 } };
}

// ───────────────────────────── 4. Held–Karp ─────────────────────────────
export function* heldKarp(ctx) {
  const { n, W, inicio } = ctx;
  const orden = [inicio]; for (let i = 0; i < n; i++) if (i !== inicio) orden.push(i);
  const m = n - 1, N = 1 << m;
  if (m < 1) { yield { l: 0, t: 'Hace falta más de una ciudad.', ruta: [inicio], fin: true, cerrada: true, coste: 0, mejor: 0 }; return; }
  const w = (a, b) => W[orden[a]][orden[b]];
  const dp = new Float64Array(N * m).fill(Infinity);
  const padre = new Int8Array(N * m).fill(-1);
  yield { l: 0, t: `Se fija ${nom(ctx, inicio)} como salida. Hay ${m} ciudades más; sus subconjuntos posibles son 2<sup>${m}</sup> = <b>${N.toLocaleString('es-ES')}</b>. Para cada subconjunto y ciudad final se guarda el <b>mejor camino parcial</b>.`, ruta: [inicio], importante: true, info: { estados: `${(N * m).toLocaleString('es-ES')} posibles` } };
  for (let j = 0; j < m; j++) dp[(1 << j) * m + j] = w(0, j + 1);
  // Subconjuntos agrupados por tamaño
  const capas = Array.from({ length: m + 1 }, () => []);
  for (let s = 1; s < N; s++) { let c = 0, x = s; while (x) { c += x & 1; x >>= 1; } capas[c].push(s); }
  const camino = (s, j) => { const r = []; while (s) { r.push(orden[j + 1]); const p = padre[s * m + j]; s ^= 1 << j; j = p; } r.push(orden[0]); return r.reverse(); };
  yield { l: 2, t: `Subconjuntos de <b>1 ciudad</b>: el mejor camino es ir directo desde ${nom(ctx, inicio)}.`, ruta: [inicio], aristas: Array.from({ length: m }, (_, j) => ({ a: orden[0], b: orden[j + 1], c: 'cand' })), info: { 'estados calculados': m } };
  let estados = m;
  for (let k = 2; k <= m; k++) {
    let ejemplo = null, mejorCapa = Infinity, mejorEstado = null;
    for (const s of capas[k]) {
      for (let j = 0; j < m; j++) {
        if (!((s >> j) & 1)) continue;
        const prev = s ^ (1 << j);
        let mejor = Infinity, arg = -1;
        for (let i = 0; i < m; i++) {
          if (!((prev >> i) & 1)) continue;
          const v = dp[prev * m + i] + w(i + 1, j + 1);
          if (v < mejor) { mejor = v; arg = i; }
        }
        dp[s * m + j] = mejor; padre[s * m + j] = arg;
        if (!ejemplo) ejemplo = { s, j, prev };
        if (mejor < mejorCapa) { mejorCapa = mejor; mejorEstado = { s, j }; }
      }
      estados += k;
    }
    if (k === 3 && ejemplo) {
      const { s, j, prev } = ejemplo;
      const cands = []; for (let i = 0; i < m; i++) if ((prev >> i) & 1) cands.push({ a: orden[i + 1], b: orden[j + 1], c: 'cand' });
      yield { l: 5, t: `Ejemplo: para llegar a ${nom(ctx, orden[j + 1])} habiendo pasado por ${k} ciudades, se prueba venir desde cada una de las otras ${k - 1}, reutilizando lo ya guardado, y se queda con la más barata.`, ruta: camino(prev, padre[s * m + j]), aristas: cands, nodos: { [orden[j + 1]]: 'elegida' }, info: { 'estados calculados': estados } };
    }
    yield { l: 5, t: `Subconjuntos de <b>${k} ciudades</b> terminados (${capas[k].length.toLocaleString('es-ES')} subconjuntos). El mejor camino parcial de este tamaño cuesta ${fmt(mejorCapa)}.`, ruta: camino(mejorEstado.s, mejorEstado.j), coste: mejorCapa, info: { 'estados calculados': estados, 'tamaño': `${k} de ${m}` }, serie: mejorCapa, importante: k === m };
  }
  const full = N - 1;
  let mejor = Infinity, jf = -1;
  for (let j = 0; j < m; j++) { const v = dp[full * m + j] + w(j + 1, 0); if (v < mejor) { mejor = v; jf = j; } }
  yield { l: 7, t: `Con todas las ciudades, se elige la última que, sumando la vuelta a ${nom(ctx, inicio)}, sale más barata: <b>${nom(ctx, orden[jf + 1])}</b>. Coste total: <b>${fmt(mejor)}</b>.`, ruta: camino(full, jf), coste: mejor, mejor, aristas: [{ a: orden[jf + 1], b: orden[0], c: 'elegida' }], importante: true };
  // Reconstrucción hacia atrás
  const inv = []; let s = full, j = jf;
  while (s) { inv.push(j + 1); const p = padre[s * m + j]; s ^= 1 << j; j = p; }
  const ruta = [orden[0], ...inv.reverse().map((x) => orden[x])];
  yield { l: 8, t: `Se reconstruye la ruta hacia atrás, siguiendo para cada estado de dónde venía el mejor camino: <b>óptima</b>.`, ruta, cerrada: true, coste: mejor, mejor, fin: true, importante: true, serie: mejor, info: { 'estados calculados': estados } };
}

// ───────────────────────────── 5. Genético ─────────────────────────────
export function* genetico(ctx, op = {}) {
  const { n, W, inicio } = ctx;
  const P = op.poblacion ?? 150, G = op.generaciones ?? 500, pm = op.mutacion ?? 0.5, torneo = 3, elite = 2, q = 10, paciencia = op.paciencia ?? 150;
  const azar = crearAzar(op.semilla ?? 42);
  const orden = [inicio]; for (let i = 0; i < n; i++) if (i !== inicio) orden.push(i);
  const m = n - 1;
  if (m <= 3) { // con pocas ciudades se prueban todas las rutas
    const rs = [];
    const rec = (p, resto) => { if (!resto.length) rs.push(p); else resto.forEach((x, k) => rec([...p, x], resto.filter((_, kk) => kk !== k))); };
    rec([inicio], orden.slice(1));
    let b = rs[0]; for (const r of rs) if (costeCiclo(W, r) < costeCiclo(W, b)) b = r;
    const c = costeCiclo(W, b);
    yield { l: 0, t: 'Con tan pocas ciudades se prueban todas las rutas.', ruta: b, cerrada: true, coste: c, mejor: c, fin: true, importante: true };
    return;
  }
  const coste = (ind) => { let s = W[inicio][ind[0]]; for (let i = 0; i < m - 1; i++) s += W[ind[i]][ind[i + 1]]; return s + W[ind[m - 1]][inicio]; };
  const aRuta = (ind) => [inicio, ...ind];
  const permAzar = () => { const a = orden.slice(1); for (let i = m - 1; i > 0; i--) { const k = azar.entero(i + 1); [a[i], a[k]] = [a[k], a[i]]; } return a; };
  const cruce = (p1, p2) => {
    let a = azar.entero(m + 1), b = azar.entero(m + 1); if (a > b) [a, b] = [b, a]; if (a === b) b = Math.min(m, b + 1);
    const tramo = p1.slice(a, b), en = new Set(tramo);
    const resto = []; for (let k = 0; k < m; k++) { const x = p2[(b + k) % m]; if (!en.has(x)) resto.push(x); }
    const hijo = new Array(m); for (let k = a; k < b; k++) hijo[k] = p1[k];
    let r = 0; for (let k = 0; k < m - (b - a); k++) hijo[(b + k) % m] = resto[r++];
    return { hijo, a, b };
  };
  const mutar = (ind) => {
    const cur = coste(ind); let mejorC = cur, mejorI = null;
    for (let k = 0; k < q; k++) {
      let i = azar.entero(m - 1), j = i + 1 + azar.entero(m - 1 - i);
      const cand = ind.slice(); for (let x = i, y = j; x < y; x++, y--) [cand[x], cand[y]] = [cand[y], cand[x]];
      const cc = coste(cand); if (cc < mejorC) { mejorC = cc; mejorI = cand; }
    }
    return mejorI ?? ind;
  };
  let pob = Array.from({ length: P }, permAzar);
  let cs = pob.map(coste);
  let mejorC = Math.min(...cs), mejor = pob[cs.indexOf(mejorC)].slice(), sinMejora = 0;
  const media = () => cs.reduce((x, y) => x + y, 0) / P;
  const muestra = () => pob.slice(0, 8).map(aRuta);
  yield { l: 1, t: `Se crean <b>${P} rutas al azar</b>. La mejor cuesta ${fmt(mejorC)}; la media, ${fmt(media())}. Son terribles, pero de ahí se parte.`, ruta: aRuta(mejor), cerrada: true, coste: mejorC, mejor: mejorC, fondo: muestra(), importante: true, serie: mejorC, info: { generación: 0, 'mejor': fmt(mejorC), 'media': fmt(media()) } };
  for (let g = 1; g <= G; g++) {
    const orde = cs.map((c, i) => [c, i]).sort((x, y) => x[0] - y[0]);
    const padres = Array.from({ length: P }, () => { let b = azar.entero(P); for (let k = 1; k < torneo; k++) { const c = azar.entero(P); if (cs[c] < cs[b]) b = c; } return pob[b]; });
    const nueva = orde.slice(0, elite).map(([, i]) => pob[i].slice());
    let demo = null;
    while (nueva.length < P) {
      const k = azar.entero(P);
      const { hijo, a, b } = cruce(padres[k], padres[(k + 1) % P]);
      const muta = azar() < pm;
      const fin = muta ? mutar(hijo) : hijo;
      if (g <= 2 && !demo) demo = { p1: padres[k], p2: padres[(k + 1) % P], hijo: hijo.slice(), fin: fin.slice(), a, b, muta };
      nueva.push(fin);
    }
    if (demo) {
      yield { l: 5, t: `<b>Selección</b> (generación ${g}): se eligen dos padres por torneo: gana la más corta de 3 al azar. Padre 1 cuesta ${fmt(coste(demo.p1))} y padre 2, ${fmt(coste(demo.p2))}.`, ruta: aRuta(demo.p1), cerrada: true, coste: coste(demo.p1), fondo: [aRuta(demo.p2)], mejor: mejorC, info: { generación: g } };
      yield { l: 6, t: `<b>Cruce</b>: el hijo hereda de un padre un tramo seguido y el resto de ciudades en el orden del otro padre. Cuesta ${fmt(coste(demo.hijo))}.`, ruta: aRuta(demo.hijo), cerrada: true, coste: coste(demo.hijo), mejor: mejorC, info: { generación: g } };
      yield { l: 7, t: demo.muta ? `<b>Mutación</b>: se prueban 10 inversiones de un tramo y solo se acepta la mejor, si mejora. Ahora cuesta ${fmt(coste(demo.fin))}.` : '<b>Mutación</b>: este hijo no muta en esta ocasión.', ruta: aRuta(demo.fin), cerrada: true, coste: coste(demo.fin), mejor: mejorC, info: { generación: g } };
    }
    pob = nueva; cs = pob.map(coste);
    const gen = Math.min(...cs);
    let mejoro = false;
    if (gen < mejorC - 1e-9) { mejorC = gen; mejor = pob[cs.indexOf(gen)].slice(); sinMejora = 0; mejoro = true; } else sinMejora++;
    const fin = sinMejora >= paciencia || g === G;
    yield { l: 8, t: `Generación <b>${g}</b>: la mejor ruta cuesta <b>${fmt(mejorC)}</b>${mejoro ? ' (mejora)' : ''}; la media de la población, ${fmt(media())}.${fin ? ' ' + (sinMejora >= paciencia ? `Lleva ${paciencia} generaciones sin mejorar: se para.` : 'Última generación.') : ''}`, ruta: aRuta(mejor), cerrada: true, coste: mejorC, mejor: mejorC, fondo: muestra(), importante: mejoro || fin, serie: mejorC, fin, info: { generación: g, 'mejor': fmt(mejorC), 'media': fmt(media()), 'sin mejorar': sinMejora } };
    if (fin) return;
  }
}

// ───────────────────────────── 6. Recocido simulado ─────────────────────────────
export function* recocido(ctx, op = {}) {
  const { n, W, inicio } = ctx;
  const azar = crearAzar(op.semilla ?? 42);
  if (n < 4) { const t = rutaVecinoMasCercano(ctx); const c = costeCiclo(W, t); yield { l: 0, t: 'Con tan pocas ciudades no hace falta.', ruta: t, cerrada: true, coste: c, mejor: c, fin: true, importante: true }; return; }
  const alpha = op.alpha ?? 0.95, Tmin = 0.05;
  let actual = Array.from({ length: n }, (_, i) => i);
  for (let i = n - 1; i > 0; i--) { const k = azar.entero(i + 1); [actual[i], actual[k]] = [actual[k], actual[i]]; }
  const val = (r) => { let s = 0; for (let k = 0; k < n; k++) s += W[r[(k - 1 + n) % n]][r[k]]; return s; };
  let va = val(actual), mejor = actual.slice(), vm = va;
  const T0 = va * 0.15; let T = T0;
  const aRuta = (r) => { const idx = r.indexOf(inicio); return [...r.slice(idx), ...r.slice(0, idx)]; };
  yield { l: 1, t: `Se parte de una ruta <b>al azar</b> (${fmt(va)}) y una temperatura alta T = ${fmt(T)} (15 % del coste inicial).`, ruta: aRuta(actual), cerrada: true, coste: va, mejor: vm, importante: true, serie: va, info: { temperatura: fmt(T), 'aceptadas': 0, 'rechazadas': 0 } };
  let nivel = 0, acepT = 0, recT = 0, empT = 0;
  while (T > Tmin) {
    nivel++;
    const niter = Math.floor(n * 5 * Math.min(3, T0 / T));
    let ac = 0, re = 0, em = 0, mostrado = 0;
    for (let it = 0; it < niter; it++) {
      const i = azar.entero(n); const j = azar.entero(n);
      if (i === j || Math.abs(j - i) === n - 1) continue;
      const [lo, hi] = i < j ? [i, j] : [j, i];
      const uPrev = actual[(lo - 1 + n) % n], u = actual[lo], v = actual[hi], vNext = actual[(hi + 1) % n];
      const delta = W[uPrev][v] + W[u][vNext] - W[uPrev][u] - W[v][vNext];
      let aceptar = false;
      if (delta <= 0 || azar() < Math.exp(-delta / T)) {
        const cand = actual.slice(0, lo).concat(actual.slice(lo, hi + 1).reverse(), actual.slice(hi + 1));
        const vc = val(cand), dF = vc - va;
        if (dF <= 0 || azar() < Math.exp(-dF / T)) {
          aceptar = true;
          if (nivel <= 2 && mostrado < 3) { mostrado++; yield { l: dF > 0 ? 7 : 6, t: dF > 0 ? `Cambio propuesto: <b>empeora</b> la ruta en ${fmt(dF)}, pero con T = ${fmt(T)} se acepta con probabilidad ${(Math.exp(-dF / T) * 100).toFixed(0)} %.` : `Cambio propuesto: <b>mejora</b> la ruta en ${fmt(-dF)}. Se acepta siempre.`, ruta: aRuta(cand), cerrada: true, coste: vc, mejor: vm, aristas: [{ a: uPrev, b: u, c: 'quitar' }, { a: v, b: vNext, c: 'quitar' }], info: { temperatura: fmt(T) } }; }
          actual = cand; va = vc; ac++; if (dF > 0) em++;
          if (va < vm - 1e-9) { vm = va; mejor = actual.slice(); }
        }
      }
      if (!aceptar) { re++; }
    }
    acepT += ac; recT += re; empT += em;
    yield { l: 9, t: `Nivel ${nivel}: T = ${fmt(T)}. De ${niter} intentos, se aceptan ${ac} (${em} de ellos empeoran la ruta). Mejor ruta hasta ahora: <b>${fmt(vm)}</b>. Se enfría: T × ${alpha}.`, ruta: aRuta(mejor), cerrada: true, coste: vm, mejor: vm, fondo: [aRuta(actual)], serie: vm, importante: nivel % 10 === 0, info: { temperatura: fmt(T), 'aceptadas': acepT, 'rechazadas': recT, 'empeoramientos aceptados': empT, nivel } };
    T *= alpha;
  }
  yield { l: 11, t: `La temperatura ya es mínima (0,05): casi solo se aceptan mejoras. Ruta final: <b>${fmt(vm)}</b>.`, ruta: aRuta(mejor), cerrada: true, coste: vm, mejor: vm, fin: true, importante: true, serie: vm, info: { temperatura: '≈ 0', nivel } };
}

// ───────────────────────────── 7. Christofides ─────────────────────────────
export function* christofides(ctx) {
  const { n, W, inicio } = ctx;
  if (n < 3) { const t = rutaVecinoMasCercano(ctx); const c = costeCiclo(W, t); yield { l: 0, t: 'Con tan pocas ciudades no hace falta.', ruta: t, cerrada: true, coste: c, mejor: c, fin: true, importante: true }; return; }
  // 1. Árbol de expansión mínimo (Prim)
  const enArbol = new Array(n).fill(false), dist = new Array(n).fill(Infinity), padre = new Array(n).fill(-1);
  dist[inicio] = 0; const arbol = []; let costeArbol = 0;
  yield { l: 1, t: `<b>Paso 1.</b> Se conectan todas las ciudades con la menor carretera total posible y sin ciclos: el <b>árbol de expansión mínimo</b>. Se construye añadiendo siempre la conexión más barata hacia una ciudad nueva.`, ruta: [], importante: true };
  for (let k = 0; k < n; k++) {
    let u = -1; for (let j = 0; j < n; j++) if (!enArbol[j] && (u < 0 || dist[j] < dist[u])) u = j;
    enArbol[u] = true;
    if (padre[u] >= 0) { arbol.push({ a: padre[u], b: u, c: 'arbol' }); costeArbol += W[padre[u]][u]; yield { l: 2, t: `Se añade ${nom(ctx, u)} unida a ${nom(ctx, padre[u])} (${fmt(W[padre[u]][u])}).`, aristas: arbol.slice(), info: { 'coste del árbol': fmt(costeArbol), 'aristas': `${arbol.length} de ${n - 1}` } }; }
    for (let j = 0; j < n; j++) if (!enArbol[j] && W[u][j] < dist[j]) { dist[j] = W[u][j]; padre[j] = u; }
  }
  const grado = new Array(n).fill(0); arbol.forEach(({ a, b }) => { grado[a]++; grado[b]++; });
  const impares = []; for (let i = 0; i < n; i++) if (grado[i] % 2 === 1) impares.push(i);
  yield { l: 3, t: `<b>Paso 2.</b> Árbol terminado (${fmt(costeArbol)}, una cota inferior del óptimo). Hay <b>${impares.length}</b> ciudades con un número impar de conexiones (resaltadas); siempre hay un número par.`, aristas: arbol.slice(), nodos: Object.fromEntries(impares.map((i) => [i, 'impar'])), importante: true, info: { 'coste del árbol': fmt(costeArbol), 'ciudades impares': impares.length } };
  // 3. Emparejamiento perfecto de coste mínimo entre las impares
  const pares = emparejamientoMinimo(impares, (a, b) => W[a][b]);
  const empar = pares.map(([a, b]) => ({ a, b, c: 'empar' }));
  let costeEmp = 0;
  for (let k = 0; k < pares.length; k++) {
    costeEmp += W[pares[k][0]][pares[k][1]];
    yield { l: 4, t: `<b>Paso 3.</b> Emparejamiento de coste mínimo entre las ciudades impares: ${nom(ctx, pares[k][0])} con ${nom(ctx, pares[k][1])} (${fmt(W[pares[k][0]][pares[k][1]])}).`, aristas: [...arbol, ...empar.slice(0, k + 1)], nodos: Object.fromEntries(impares.map((i) => [i, 'impar'])), info: { 'coste del árbol': fmt(costeArbol), 'coste del emparejamiento': fmt(costeEmp) } };
  }
  // 4. Circuito euleriano (Hierholzer) sobre el multigrafo árbol + emparejamiento
  const ady = Array.from({ length: n }, () => []);
  const todas = [...arbol, ...empar]; todas.forEach(({ a, b }, id) => { ady[a].push([b, id]); ady[b].push([a, id]); });
  const usada = new Array(todas.length).fill(false), pila = [inicio], circuito = [];
  const ptr = new Array(n).fill(0);
  while (pila.length) {
    const u = pila[pila.length - 1];
    while (ptr[u] < ady[u].length && usada[ady[u][ptr[u]][1]]) ptr[u]++;
    if (ptr[u] === ady[u].length) { circuito.push(pila.pop()); } else { const [v, id] = ady[u][ptr[u]]; usada[id] = true; pila.push(v); }
  }
  circuito.reverse();
  yield { l: 5, t: `<b>Paso 4.</b> Árbol + emparejamiento: ahora <b>todas las ciudades tienen un número par de conexiones</b>, así que existe un recorrido que pasa por cada carretera exactamente una vez (circuito euleriano). Tiene ${circuito.length - 1} tramos y coste ${fmt(costeArbol + costeEmp)}, pero repite ciudades.`, ruta: circuito.slice(0, -1), cerrada: true, aristas: todas, coste: costeArbol + costeEmp, info: { 'coste del circuito': fmt(costeArbol + costeEmp) }, importante: true };
  // 5. Atajos
  const vistos = new Set(), ruta = [];
  for (const u of circuito) {
    if (vistos.has(u)) continue;
    vistos.add(u); ruta.push(u);
    if (ruta.length >= 2 && (ruta.length % Math.max(1, Math.floor(n / 6)) === 0 || ruta.length === n)) yield { l: 7, t: `<b>Paso 5.</b> Se recorre el circuito y se <b>salta cada ciudad ya visitada</b> (ir directo nunca cuesta más que dar el rodeo). Llevamos ${ruta.length} de ${n}.`, ruta: ruta.slice(), coste: undefined, info: { visitadas: `${ruta.length} de ${n}` } };
  }
  const c = costeCiclo(W, ruta);
  yield { l: 8, t: `Ruta final: <b>${fmt(c)}</b>. Está garantizada a menos de 1,5 × el óptimo (cota inferior del árbol: ${fmt(costeArbol)}).`, ruta, cerrada: true, coste: c, mejor: c, fin: true, importante: true, serie: c, info: { 'coste': fmt(c), 'cota del árbol': fmt(costeArbol) } };
}

// ───────────────────────────── 8. DFJ ─────────────────────────────
export async function* dfj(ctx) {
  const { n, W, inicio } = ctx;
  if (n < 3) { const t = rutaVecinoMasCercano(ctx); const c = costeCiclo(W, t); yield { l: 0, t: 'Con tan pocas ciudades no hace falta.', ruta: t, cerrada: true, coste: c, mejor: c, fin: true, importante: true }; return; }
  const v = (i, j) => `x_${i}_${j}`;
  const cortes = [];
  const lp = () => {
    let s = 'Minimize\n obj: ';
    const terms = []; for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) if (i !== j) terms.push(`${W[i][j].toFixed(3)} ${v(i, j)}`);
    s += terms.join(' + ') + '\nSubject To\n';
    for (let i = 0; i < n; i++) {
      s += ` sal_${i}: ` + Array.from({ length: n }, (_, j) => j).filter((j) => j !== i).map((j) => v(i, j)).join(' + ') + ' = 1\n';
      s += ` ent_${i}: ` + Array.from({ length: n }, (_, j) => j).filter((j) => j !== i).map((j) => v(j, i)).join(' + ') + ' = 1\n';
    }
    cortes.forEach((S, k) => { const t = []; for (const i of S) for (let j = 0; j < n; j++) if (!S.includes(j)) t.push(v(i, j)); s += ` corte_${k}: ${t.join(' + ')} >= 1\n`; });
    s += 'Binary\n ';
    const bin = []; for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) if (i !== j) bin.push(v(i, j));
    return s + bin.join(' ') + '\nEnd\n';
  };
  yield { l: 0, t: `<b>Idea:</b> se resuelve primero una versión <b>más fácil</b> del problema: «de cada ciudad sale una sola carretera y a cada ciudad llega una sola», sin exigir que todo forme un único circuito.`, ruta: [], importante: true };
  let iter = 0, objetivo = 0;
  while (true) {
    iter++;
    yield { l: 3, t: `Resolviendo el problema de programación entera (iteración ${iter}${cortes.length ? `, con ${cortes.length} restricciones de conectividad` : ''})...`, ruta: [], info: { iteración: iter, restricciones: cortes.length }, espera: true };
    const sol = await resolverEntero(lp());
    objetivo = sol.objetivo;
    const sig = new Array(n).fill(-1);
    for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) if (i !== j && (sol.valores[v(i, j)] ?? 0) > 0.5) sig[i] = j;
    // Componentes (ciclos de la permutación)
    const comp = new Array(n).fill(-1), comps = [];
    for (let i = 0; i < n; i++) if (comp[i] < 0) { const c = []; let x = i; while (comp[x] < 0) { comp[x] = comps.length; c.push(x); x = sig[x]; } comps.push(c); }
    const aristas = []; for (let i = 0; i < n; i++) aristas.push({ a: i, b: sig[i], c: 'asig', grupo: comp[i] });
    const nodos = Object.fromEntries(comp.map((c, i) => [i, 'grupo' + (c % 8)]));
    if (comps.length === 1) {
      const ruta = [inicio]; let x = sig[inicio]; while (x !== inicio) { ruta.push(x); x = sig[x]; }
      yield { l: 7, t: `Iteración ${iter}: la solución es <b>un único circuito</b> que pasa por todas las ciudades. Es el <b>óptimo</b>: <b>${fmt(objetivo)}</b>.`, ruta, cerrada: true, coste: objetivo, mejor: objetivo, fin: true, importante: true, serie: objetivo, info: { iteración: iter, restricciones: cortes.length, 'circuitos': 1 } };
      return;
    }
    yield { l: 5, t: `Iteración ${iter}: coste ${fmt(objetivo)}, pero la solución se parte en <b>${comps.length} circuitos sueltos</b> (cada uno de un color). Eso no es una ruta.`, ruta: [], aristas, nodos, coste: objetivo, mejor: objetivo, serie: objetivo, importante: true, info: { iteración: iter, restricciones: cortes.length, 'circuitos': comps.length } };
    comps.forEach((S) => cortes.push(S));
    yield { l: 6, t: `Se añade una regla por cada circuito: <b>«cada grupo debe tener al menos una carretera que salga hacia el resto»</b>. Se vuelve a resolver con ${cortes.length} restricciones.`, ruta: [], aristas, nodos, coste: objetivo, info: { iteración: iter, restricciones: cortes.length } };
  }
}

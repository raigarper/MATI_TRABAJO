// Pruebas de los algoritmos de la web con Node: mismos datos que el trabajo, resultados comparados con los de Python.
//   node web/tests/probar.mjs <carpeta donde está node_modules/highs>
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { inyectar } from '../js/solver.js';
import * as A from '../js/algoritmos.js';

const aqui = path.dirname(fileURLToPath(import.meta.url));
const raiz = path.resolve(aqui, '..', '..');
const requerir = createRequire(path.join(process.argv[2] ?? '.', 'x.js'));
const highsFactory = requerir('highs');
inyectar({ highs: await highsFactory({ locateFile: (f) => path.join(process.argv[2] ?? '.', 'node_modules', 'highs', 'build', f) }) });
const mod = { exports: {} };
new Function('module', fs.readFileSync(path.join(aqui, '..', 'vendor', 'blossom.js'), 'utf8'))(mod);
inyectar({ blossom: mod.exports });

// ── datos del trabajo (ciudades y tablas de distancias) ──
const leerTabla = (f) => { const l = fs.readFileSync(path.join(raiz, 'data', 'versiones', f), 'utf8').trim().split(/\r?\n/); return { nombres: l[0].split(','), M: l.slice(1).map((r) => r.split(',').map(Number)) }; };
const separarCsv = (l) => { const c = []; let x = '', q = false; for (const ch of l) { if (ch === '"') q = !q; else if (ch === ',' && !q) { c.push(x); x = ''; } else x += ch; } c.push(x); return c; };
const ciudades = fs.readFileSync(path.join(raiz, 'data', 'ciudades.csv'), 'utf8').trim().split(/\r?\n/).slice(1).map((l) => { const c = separarCsv(l); return { nombre: c[0], capital: c[2] === 'True', comunidad: c[3] }; });
const tablas = { dirigido: leerTabla('completo__km__dirigido.csv'), no_dirigido: leerTabla('completo__km__no_dirigido.csv') };

function instancia(nombres, sentido, inicioNombre) {
  const t = tablas[sentido];
  const idx = nombres.map((n) => t.nombres.indexOf(n));
  const W = idx.map((a) => idx.map((b) => t.M[a][b]));
  const inicio = Math.max(0, nombres.indexOf(inicioNombre ?? nombres[0]));
  return { n: nombres.length, W, inicio, nombres, simetrico: sentido === 'no_dirigido' };
}
async function ejecutar(gen, ctx, ...resto) {
  let ult = null, frames = 0;
  const it = gen(ctx, ...resto);
  while (true) { const r = await it.next(); if (r.done) break; ult = r.value; frames++; }
  return { coste: ult.coste, ruta: ult.ruta, frames, fin: ult.fin };
}
let fallos = 0;
const comprobar = (nombre, valor, esperado, tol = 0.002) => {
  const ok = Math.abs(valor - esperado) <= tol * Math.max(1, Math.abs(esperado));
  if (!ok) fallos++;
  console.log(`${ok ? 'OK ' : 'FALLO'} ${nombre.padEnd(48)} ${valor.toFixed(3).padStart(10)}  (esperado ${esperado.toFixed(3)})`);
};
const validar = (ctx, r, nombre) => {
  const ok = r.ruta.length === ctx.n && new Set(r.ruta).size === ctx.n && Math.abs(A.costeCiclo(ctx.W, r.ruta) - r.coste) < 0.01 * Math.max(1, r.coste);
  if (!ok) { fallos++; console.log(`FALLO ${nombre}: la ruta no es válida o su coste no coincide`, r.ruta.length, A.costeCiclo(ctx.W, r.ruta), r.coste); }
};

const galicia = ciudades.filter((c) => c.comunidad === 'Galicia').map((c) => c.nombre);
const andalucia = ciudades.filter((c) => c.comunidad === 'Andalucía').map((c) => c.nombre);
const capitales = ciudades.filter((c) => c.capital).map((c) => c.nombre);
console.log(`Galicia ${galicia.length} · Andalucía ${andalucia.length} · capitales ${capitales.length}\n`);

// Valores de referencia (Python, notebooks y estudio): ver la Parte 3 y la Parte 4 del trabajo
let G = instancia(galicia, 'dirigido', 'Vigo');
for (const [nombre, gen, esperado] of [['Galicia fuerza bruta', A.fuerzaBruta, 460.438], ['Galicia Held–Karp', A.heldKarp, 460.438], ['Galicia DFJ', A.dfj, 460.438],
  ['Galicia vecino más cercano (Vigo)', A.vecinoMasCercano, 465.817], ['Galicia 2-opt (Vigo)', A.dosOpt, 465.817]]) {
  const r = await ejecutar(gen, G); validar(G, r, nombre); comprobar(nombre, r.coste, esperado);
}
for (const [nombre, gen] of [['Galicia genético', A.genetico], ['Galicia recocido', A.recocido]]) {
  const r = await ejecutar(gen, G); validar(G, r, nombre); comprobar(nombre, r.coste, 460.438, 0.02);
}
let And = instancia(andalucia, 'dirigido', 'Sevilla');
for (const [nombre, gen, esperado] of [['Andalucía Held–Karp', A.heldKarp, 1251.307], ['Andalucía DFJ', A.dfj, 1251.307]]) {
  const r = await ejecutar(gen, And); validar(And, r, nombre); comprobar(nombre, r.coste, esperado);
}
let C47 = instancia(capitales, 'dirigido', 'Madrid');
let t0 = performance.now();
for (const [nombre, gen, esperado, tol] of [['47 capitales dirigido DFJ (óptimo)', A.dfj, 5917.562, 0.002], ['47 capitales vecino más cercano', A.vecinoMasCercano, 6772.1, 0.002], ['47 capitales 2-opt', A.dosOpt, 6326.0, 0.002]]) {
  const r = await ejecutar(gen, C47); validar(C47, r, nombre); comprobar(nombre, r.coste, esperado, tol);
}
console.log(`   (tiempo ${(performance.now() - t0).toFixed(0)} ms)`);
for (const [nombre, gen] of [['47 capitales genético', A.genetico], ['47 capitales recocido', A.recocido]]) {
  t0 = performance.now(); const r = await ejecutar(gen, C47); validar(C47, r, nombre);
  const gap = (r.coste / 5917.562 - 1) * 100; console.log(`${gap >= -0.1 && gap < 12 ? 'OK ' : 'FALLO'} ${nombre.padEnd(48)} ${r.coste.toFixed(1).padStart(10)}  (+${gap.toFixed(1)} % sobre el óptimo, ${(performance.now() - t0).toFixed(0)} ms)`); if (!(gap >= -0.1 && gap < 12)) fallos++;
}
let N47 = instancia(capitales, 'no_dirigido', 'Madrid');
{
  const opt = await ejecutar(A.dfj, N47); validar(N47, opt, 'DFJ no dirigido'); comprobar('47 capitales no dirigido DFJ (óptimo)', opt.coste, 5875.3, 0.002);
  const d2 = await ejecutar(A.dosOpt, N47); validar(N47, d2, '2-opt no dirigido'); comprobar('47 capitales no dirigido 2-opt', d2.coste, 6267.3, 0.002);
  const ch = await ejecutar(A.christofides, N47); validar(N47, ch, 'Christofides');
  const razon = ch.coste / opt.coste; const ok = razon <= 1.5 && razon >= 1;
  if (!ok) fallos++;
  console.log(`${ok ? 'OK ' : 'FALLO'} Christofides 47 no dirigido: ${ch.coste.toFixed(1)} km = ×${razon.toFixed(3)} el óptimo (garantía ≤ 1,5; Python dio 6892,7)`);
}
// Fuerza bruta y Held–Karp en 9 ciudades de Andalucía (dirigido): deben coincidir
const sub = andalucia.slice(0, 9); const S9 = instancia(sub, 'dirigido', sub[0]);
const fb = await ejecutar(A.fuerzaBruta, S9), hk = await ejecutar(A.heldKarp, S9), dd = await ejecutar(A.dfj, S9);
comprobar('9 ciudades: fuerza bruta = Held–Karp', fb.coste, hk.coste, 1e-6); comprobar('9 ciudades: DFJ = Held–Karp', dd.coste, hk.coste, 1e-6);
// 75 ciudades con DFJ (mismo coste que Python: 6146.165 dirigido)
const todas = ciudades.map((c) => c.nombre);
let T75 = instancia(todas, 'dirigido', 'Madrid'); t0 = performance.now();
const r75 = await ejecutar(A.dfj, T75); validar(T75, r75, 'DFJ 75'); comprobar('75 ciudades dirigido DFJ (óptimo)', r75.coste, 6146.165, 0.002);
console.log(`   (DFJ con 75 ciudades: ${(performance.now() - t0).toFixed(0)} ms, ${r75.frames} fotogramas)`);
console.log(fallos ? `\n${fallos} FALLO(S)` : '\nTodo correcto');
process.exit(fallos ? 1 : 0);

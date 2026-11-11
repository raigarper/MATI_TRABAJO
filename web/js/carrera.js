// Carrera: varios algoritmos resuelven las mismas ciudades a la vez. Cada uno avanza por turnos durante el mismo tiempo de cálculo,
// así que el que termina antes es de verdad el más rápido. Los que no se pueden aplicar se descartan con su motivo.
import { ALGORITMOS, ORDEN, motivoNoAplicable } from './meta.js';
import { miniMapa } from './mapa.js';
import { UNIDAD } from './datos.js';
import { construirContexto, crearGenerador, claveInstancia, E } from './app.js';

const $ = (s) => document.querySelector(s);
const fmt = (x) => x.toLocaleString('es-ES', { maximumFractionDigits: 1 });
const tiempo = (ms) => (ms < 1 ? '< 1 ms' : ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(2)} s`);
const OPTIMOS = ['fuerza_bruta', 'held_karp', 'dfj'];

export function iniciarCarrera(_E, registrarCambio) {
  let corriendo = false, cancelar = false;
  const elegidos = new Set(ORDEN);
  let tarjetas = {};

  function pintarElegir() {
    $('#r-elegir').innerHTML = ORDEN.map((id) => `<label style="border-color:${elegidos.has(id) ? ALGORITMOS[id].color : ''}"><input type="checkbox" data-id="${id}" ${elegidos.has(id) ? 'checked' : ''}><i style="width:9px;height:9px;border-radius:50%;background:${ALGORITMOS[id].color}"></i>${ALGORITMOS[id].nombre}</label>`).join('');
    $('#r-elegir').onchange = (e) => { const id = e.target.dataset.id; e.target.checked ? elegidos.add(id) : elegidos.delete(id); pintarElegir(); construirTarjetas(); };
  }

  function construirTarjetas() {
    const n = E.sel.size, { global, ctx } = n ? construirContexto() : { global: [], ctx: null };
    tarjetas = {};
    $('#r-tarjetas').innerHTML = ORDEN.filter((id) => elegidos.has(id)).map((id) => {
      const a = ALGORITMOS[id], motivo = motivoNoAplicable(id, n, E.dirigido);
      return `<article class="tarjeta ${motivo ? 'descartada' : ''}" data-id="${id}"><header><i style="background:${a.color}"></i><b>${a.nombre}</b><small>${a.familia}</small></header>
        <div class="mini"></div><footer>${motivo ? `<div class="estado">🚫 No aplicable: ${motivo}</div>` : `<span>Coste</span><b class="v-coste">—</b><span>Tiempo de cálculo</span><b class="v-tiempo">—</b><div class="estado">En la parrilla de salida</div>`}</footer></article>`;
    }).join('');
    $('#r-tarjetas').querySelectorAll('.tarjeta').forEach((t) => {
      const id = t.dataset.id, m = miniMapa(E.datos, t.querySelector('.mini'));
      if (ctx) m.ciudades(global, ctx.inicio);
      tarjetas[id] = { el: t, mapa: m, coste: t.querySelector('.v-coste'), tiempo: t.querySelector('.v-tiempo'), estado: t.querySelector('.estado') };
    });
    $('#r-tabla').hidden = true;
  }

  async function salida() {
    if (corriendo || !E.sel.size) return;
    const { global, ctx } = construirContexto();
    const ids = ORDEN.filter((id) => elegidos.has(id) && !motivoNoAplicable(id, ctx.n, E.dirigido));
    if (!ids.length) return;
    corriendo = true; cancelar = false; construirTarjetas();
    $('#r-salida').disabled = true;
    const corredores = ids.map((id) => ({ id, gen: crearGenerador(id, ctx, E.semilla), ms: 0, fin: false, fr: null, error: null }));
    for (const r of corredores) tarjetas[r.id].estado.textContent = 'Calculando…';
    while (!cancelar && corredores.some((r) => !r.fin)) {
      for (const r of corredores) {
        if (r.fin) continue;
        const t0 = performance.now();
        try {
          while (performance.now() - t0 < 8) {
            const res = await r.gen.next();
            if (res.done) { r.fin = true; break; }
            r.fr = res.value;
            if (r.fr.fin) { r.fin = true; break; }
            if (r.fr.espera) break;
          }
        } catch (e) { r.fin = true; r.error = e.message; }
        r.ms += performance.now() - t0;
        const t = tarjetas[r.id], fr = r.fr;
        if (fr) { t.mapa.ruta(global, fr.ruta, fr.cerrada, ALGORITMOS[r.id].color); const c = fr.mejor ?? fr.coste; if (c !== undefined) t.coste.textContent = `${fmt(c)} ${UNIDAD[E.peso]}`; }
        t.tiempo.textContent = tiempo(r.ms);
        if (r.fin) t.estado.textContent = r.error ? `Error: ${r.error}` : '✅ Terminado';
      }
      await new Promise((r) => requestAnimationFrame(r));
    }
    corriendo = false; $('#r-salida').disabled = false;
    if (!cancelar) resultados(corredores);
  }

  function resultados(corredores) {
    const hechos = corredores.filter((r) => r.fr?.fin && !r.error).map((r) => ({ id: r.id, coste: r.fr.coste, ms: r.ms }));
    if (!hechos.length) return;
    const mejor = Math.min(...hechos.map((h) => h.coste)), rapido = Math.min(...hechos.map((h) => h.ms)), maxMs = Math.max(...hechos.map((h) => h.ms));
    const res = E.resultados.get(claveInstancia()) ?? {};
    hechos.forEach((h) => { res[h.id] = h.coste; }); E.resultados.set(claveInstancia(), res);
    const opt = OPTIMOS.map((id) => res[id]).filter((x) => x !== undefined).sort((a, b) => a - b)[0] ?? mejor;
    hechos.sort((a, b) => a.coste - b.coste || a.ms - b.ms);
    hechos.forEach((h) => { if (h.coste <= mejor * 1.0000001) tarjetas[h.id].el.classList.add('gana'); });
    const u = UNIDAD[E.peso];
    $('#r-tabla').innerHTML = `<table><thead><tr><th>Algoritmo</th><th>Coste</th><th>Frente al mejor</th><th>Tiempo de cálculo</th><th></th></tr></thead><tbody>${hechos.map((h) => {
      const a = ALGORITMOS[h.id], gap = (h.coste / opt - 1) * 100;
      return `<tr style="--c:${a.color}"><td><b style="color:${a.color}">●</b> ${a.nombre}${h.coste <= mejor * 1.0000001 ? ' 🏆' : ''}${h.ms === rapido ? ' ⚡' : ''}</td><td>${fmt(h.coste)} ${u}</td><td>${gap < 0.005 ? '<b>óptimo</b>' : `+${gap.toLocaleString('es-ES', { maximumFractionDigits: 1 })} %`}</td><td>${tiempo(h.ms)}</td>
        <td style="width:30%"><div class="barra-mini" style="width:${Math.max(1, (Math.log10(h.ms + 1) / Math.log10(maxMs + 1)) * 100)}%"></div></td></tr>`;
    }).join('')}</tbody></table><p class="ayuda" style="margin-top:8px">🏆 mejor coste · ⚡ el más rápido · la barra muestra el tiempo en escala logarítmica. «Frente al mejor» compara con ${OPTIMOS.some((id) => res[id] !== undefined) ? 'el óptimo (algoritmo exacto)' : 'la mejor ruta de esta carrera (no hay algoritmo exacto: no se sabe si es el óptimo)'}.</p>`;
    $('#r-tabla').hidden = false;
  }

  $('#r-salida').onclick = () => salida();
  $('#r-parar').onclick = () => { cancelar = true; corriendo = false; $('#r-salida').disabled = false; construirTarjetas(); };
  registrarCambio(() => { if (!corriendo && !$('#vista-carrera').hidden) construirTarjetas(); });
  return { mostrar() { pintarElegir(); construirTarjetas(); } };
}

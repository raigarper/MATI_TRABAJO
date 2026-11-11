// Controlador de la web: estado, panel de ciudades, Laboratorio (reproductor paso a paso) y pestañas.
import { cargarDatos, matrizDe, UNIDAD } from './datos.js';
import { Mapa } from './mapa.js';
import { ALGORITMOS, ORDEN, LEYENDA, motivoNoAplicable } from './meta.js';
import * as A from './algoritmos.js';
import { iniciarCarrera } from './carrera.js';

export const FUNCIONES = { fuerza_bruta: A.fuerzaBruta, held_karp: A.heldKarp, dfj: A.dfj, vecino_mas_cercano: A.vecinoMasCercano, dos_opt: A.dosOpt, christofides: A.christofides, recocido_simulado: A.recocido, genetico: A.genetico };
export const crearGenerador = (id, ctx, semilla) => (id === 'genetico' || id === 'recocido_simulado' ? FUNCIONES[id](ctx, { semilla }) : FUNCIONES[id](ctx));

const $ = (s) => document.querySelector(s);
const fmt = (x) => x.toLocaleString('es-ES', { maximumFractionDigits: 1 });
const OPTIMOS = ['fuerza_bruta', 'held_karp', 'dfj'];

export const E = { datos: null, sel: new Set(), inicio: 0, peso: 'km', dirigido: true, alg: 'vecino_mas_cercano', semilla: 42, vel: 5, mapa: null, rep: null, resultados: new Map() };

// Contexto de un algoritmo para la instancia actual (ciudades seleccionadas, ordenadas por índice)
export function construirContexto() {
  const global = [...E.sel].sort((a, b) => a - b);
  const W = matrizDe(E.datos, global, E.peso, E.dirigido);
  const inicio = Math.max(0, global.indexOf(E.inicio));
  return { global, ctx: { n: global.length, W, inicio, nombres: global.map((g) => E.datos.nombres[g]), simetrico: !E.dirigido } };
}
export const claveInstancia = () => `${[...E.sel].sort((a, b) => a - b).join(',')}|${E.peso}|${E.dirigido}`;

// ───────────────────────────── Reproductor ─────────────────────────────
const RETARDO = [1500, 1000, 650, 400, 250, 150, 90, 50, 25, 0];
const SALTOS_FB = [1, 1, 1, 1, 3, 40, 500, 6000, 60000, 400000];
const SALTOS_SUAVE = [1, 1, 1, 1, 1, 1, 2, 4, 8, 16];

class Reproductor {
  constructor(gen, saltos, alFotograma) {
    this.gen = gen; this.saltos = saltos; this.alFotograma = alFotograma;
    this.hist = []; this.pos = -1; this.fin = false; this.jugando = false; this.ocupado = false; this.cancelado = false; this.ms = 0; this.serie = [];
  }
  get alFinalDelHistorial() { return this.pos === this.hist.length - 1; }
  get terminado() { return this.fin && this.alFinalDelHistorial; }
  async siguiente(n = 1) {
    if (this.cancelado) return;
    if (!this.alFinalDelHistorial) { this.pos++; this.#mostrar(); return; }
    if (this.fin || this.ocupado) return;
    this.ocupado = true;
    let ult = null;
    try {
      for (let k = 0; k < n; k++) {
        const t0 = performance.now();
        const r = await this.gen.next();
        this.ms += performance.now() - t0;
        if (r.done) { this.fin = true; break; }
        ult = r.value;
        if (ult.serie !== undefined) this.serie.push(ult.serie);
        if (ult.fin) { this.fin = true; break; }
        if (ult.importante && k > 0) break;               // al saltar fotogramas, se para en los importantes
        if (ult.espera) break;
      }
    } catch (e) { this.ocupado = false; this.fin = true; throw e; }
    this.ocupado = false;
    if (ult && !this.cancelado) {
      this.hist.push({ ...ult, ruta: ult.ruta?.slice(), nserie: this.serie.length, ms: this.ms });
      if (this.hist.length > 3000) { this.hist.shift(); }
      this.pos = this.hist.length - 1;
      this.#mostrar();
    }
  }
  atras() { if (this.pos > 0) { this.pos--; this.#mostrar(); } }
  #mostrar() { const f = this.hist[this.pos]; this.alFotograma(f, this.serie.slice(0, f.nserie), this.terminado); }
  async jugar(onParada) {
    if (this.jugando) return;
    this.jugando = true;
    while (this.jugando && !this.cancelado) {
      if (this.terminado) break;
      const t0 = performance.now();
      await this.siguiente(this.saltos());
      const espera = RETARDO[E.vel - 1] - (performance.now() - t0);
      await new Promise((r) => (espera > 4 ? setTimeout(r, espera) : requestAnimationFrame(r)));
    }
    this.jugando = false; onParada?.();
  }
  pausar() { this.jugando = false; }
  cancelar() { this.cancelado = true; this.jugando = false; }
  async alFinal(onParada) {
    this.jugando = false; this.cancelado = false;
    while (!this.fin && !this.cancelado) { await this.siguiente(250000); await new Promise((r) => requestAnimationFrame(r)); }
    if (!this.alFinalDelHistorial) { this.pos = this.hist.length - 1; this.#mostrar(); }
    onParada?.();
  }
}

// ───────────────────────────── Panel de ciudades ─────────────────────────────
function iniciarInstancia() {
  const d = E.datos;
  const porCom = (c) => d.ciudades.map((x, i) => [x, i]).filter(([x]) => x.comunidad === c).map(([, i]) => i);
  const presets = [
    ['Galicia', () => porCom('Galicia')], ['Castilla y León', () => porCom('Castilla y León')], ['Andalucía', () => porCom('Andalucía')],
    ['Capitales de provincia', () => d.ciudades.map((x, i) => [x, i]).filter(([x]) => x.capital).map(([, i]) => i)], ['Las 75', () => d.ciudades.map((_, i) => i)],
    ['8 al azar', () => { const t = d.ciudades.map((_, i) => i); for (let i = t.length - 1; i > 0; i--) { const k = Math.floor(Math.random() * (i + 1)); [t[i], t[k]] = [t[k], t[i]]; } return t.slice(0, 8); }],
    ['Vaciar', () => []],
  ];
  $('#presets').innerHTML = presets.map(([n, f], k) => `<button data-k="${k}">${n}${k < 5 ? ` <small>${f().length}</small>` : ''}</button>`).join('');
  $('#presets').onclick = (e) => { const b = e.target.closest('button'); if (!b) return; E.sel = new Set(presets[+b.dataset.k][1]()); E.inicio = -1; refrescar(); E.mapa.encuadrar([...E.sel]); };
  const orden = d.ciudades.map((c, i) => [c, i]).sort((a, b) => a[0].nombre.localeCompare(b[0].nombre, 'es'));
  $('#lista').innerHTML = orden.map(([c, i]) => `<li data-i="${i}"><input type="checkbox" tabindex="-1"><span>${c.nombre}</span><span class="com">${c.comunidad.slice(0, 14)}</span></li>`).join('');
  $('#lista').onclick = (e) => { const li = e.target.closest('li'); if (li) alternar(+li.dataset.i); };
  $('#buscar').oninput = (e) => { const q = e.target.value.trim().toLowerCase(); $('#lista').querySelectorAll('li').forEach((li) => { li.hidden = q && !li.textContent.toLowerCase().includes(q); }); };
  const seg = (id, clave) => { $(id).onclick = (e) => { const b = e.target.closest('button'); if (!b) return; E[clave] = clave === 'dirigido' ? b.dataset.v === 'dirigido' : b.dataset.v; $(id).querySelectorAll('button').forEach((x) => x.classList.toggle('activa', x === b)); reiniciar(); alCambiarInstancia?.(); }; };
  seg('#seg-peso', 'peso'); seg('#seg-sentido', 'dirigido');
  $('#sel-inicio').onchange = (e) => { E.inicio = +e.target.value; reiniciar(); alCambiarInstancia?.(); };
}
let alCambiarInstancia = null;
export function alternar(i) { E.sel.has(i) ? E.sel.delete(i) : E.sel.add(i); refrescar(); }
function refrescar() {
  const d = E.datos, sel = [...E.sel].sort((a, b) => a - b);
  $('#contador').textContent = `${sel.length} elegidas`;
  $('#lista').querySelectorAll('li').forEach((li) => { li.querySelector('input').checked = E.sel.has(+li.dataset.i); });
  if (!E.sel.has(E.inicio)) E.inicio = sel.includes(d.nombres.indexOf('Madrid')) ? d.nombres.indexOf('Madrid') : (sel[0] ?? 0);
  $('#sel-inicio').innerHTML = sel.map((i) => `<option value="${i}" ${i === E.inicio ? 'selected' : ''}>${d.nombres[i]}</option>`).join('');
  reiniciar(); alCambiarInstancia?.();
}

// ───────────────────────────── Laboratorio ─────────────────────────────
function iniciarChips() {
  $('#chips').innerHTML = ORDEN.map((id) => { const a = ALGORITMOS[id]; return `<button class="chip" role="tab" data-id="${id}" style="--c:${a.color}"><i style="background:${a.color}"></i>${a.nombre}</button>`; }).join('');
  $('#chips').onclick = (e) => { const b = e.target.closest('.chip'); if (!b) return; E.alg = b.dataset.id; panelAlgoritmo(); reiniciar(); };
}

function panelAlgoritmo() {
  const a = ALGORITMOS[E.alg];
  $('#chips').querySelectorAll('.chip').forEach((c) => c.classList.toggle('activa', c.dataset.id === E.alg));
  document.documentElement.style.setProperty('--c', a.color);
  $('#alg-nombre').textContent = a.nombre; $('#alg-autor').textContent = `${a.familia} · hecho por ${a.autor}`;
  $('#alg-idea').innerHTML = a.idea;
  $('#pseudo').innerHTML = a.pseudo.map((l, i) => `<li data-l="${i}">${l.replace(/&/g, '&amp;').replace(/</g, '&lt;')}</li>`).join('');
  $('#ficha').innerHTML = [['Tipo', a.tipo], ['Garantía', a.garantia], ['Tiempo', a.tiempo], ['Memoria', a.memoria], ['Distancias simétricas', a.simetria]].map(([k, v]) => `<tr><td>${k}</td><td>${v}</td></tr>`).join('');
  $('#leyenda').innerHTML = (LEYENDA[E.alg] ?? []).map(([c, t]) => `<span><i style="border-color:${c}"></i>${t}</span>`).join('');
}

let ultimoCoste = {};
function limpiarPanel() {
  $('#paso').innerHTML = 'Pulsa <b>Ejecutar</b> para empezar.';
  $('#c-actual').textContent = '—'; $('#c-mejor').textContent = '—'; $('#info').innerHTML = ''; $('#progreso').hidden = true; $('#resultado').hidden = true; $('#grafica-pie').hidden = true;
  $('#pseudo').querySelectorAll('li').forEach((li) => li.classList.remove('on'));
  const c = $('#grafica'); c.getContext('2d').clearRect(0, 0, c.width, c.height);
  ultimoCoste = {};
}

function grafica(serie, color) {
  const c = $('#grafica'), dpr = window.devicePixelRatio || 1, w = c.clientWidth, h = c.clientHeight;
  if (c.width !== w * dpr) { c.width = w * dpr; c.height = h * dpr; }
  const g = c.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, w, h);
  $('#grafica-pie').hidden = serie.length < 2;
  if (serie.length < 2) return;
  const lo = Math.min(...serie), hi = Math.max(...serie), pad = 5, span = hi - lo || 1;
  const css = getComputedStyle(document.documentElement);
  g.strokeStyle = css.getPropertyValue('--linea'); g.lineWidth = 1; g.beginPath(); g.moveTo(0, h - 0.5); g.lineTo(w, h - 0.5); g.stroke();
  g.strokeStyle = color; g.lineWidth = 2; g.lineJoin = 'round'; g.beginPath();
  const paso = Math.max(1, Math.floor(serie.length / 400));
  serie.forEach((v, i) => { if (i % paso && i !== serie.length - 1) return; const x = (i / (serie.length - 1)) * (w - 2) + 1, y = pad + (1 - (v - lo) / span) * (h - 2 * pad); i ? g.lineTo(x, y) : g.moveTo(x, y); });
  g.stroke();
  g.fillStyle = css.getPropertyValue('--texto2'); g.font = '10px system-ui'; g.fillText(fmt(hi), 3, 11); g.fillText(fmt(lo), 3, h - 4);
}

function mostrarFotograma(fr, serie, terminado) {
  const a = ALGORITMOS[E.alg], { global } = E.contexto;
  const sel = [...E.sel];
  E.mapa.dibujarFotograma(fr, global, a.color, sel, E.inicio);
  $('#pseudo').querySelectorAll('li').forEach((li) => li.classList.toggle('on', +li.dataset.l === fr.l));
  $('#paso').innerHTML = fr.t;
  const u = UNIDAD[E.peso];
  if (fr.coste !== undefined) ultimoCoste.actual = fr.coste;
  if (fr.mejor !== undefined) ultimoCoste.mejor = fr.mejor;
  $('#c-actual').textContent = fr.coste !== undefined ? `${fmt(fr.coste)} ${u}` : ultimoCoste.actual !== undefined ? `${fmt(ultimoCoste.actual)} ${u}` : '—';
  $('#c-mejor').textContent = ultimoCoste.mejor !== undefined ? `${fmt(ultimoCoste.mejor)} ${u}` : '—';
  const { progreso, ...resto } = fr.info ?? {};
  $('#info').innerHTML = Object.entries(resto).map(([k, v]) => `<dt>${k}</dt><dd>${typeof v === 'number' ? v.toLocaleString('es-ES') : v}</dd>`).join('');
  $('#progreso').hidden = progreso === undefined; if (progreso !== undefined) $('#progreso div').style.width = `${(progreso * 100).toFixed(2)}%`;
  grafica(serie, a.color);
  if (terminado && fr.fin) mostrarResultado(fr);
  else $('#resultado').hidden = true;
  actualizarBotones();
}

function mostrarResultado(fr) {
  const u = UNIDAD[E.peso], clave = claveInstancia();
  const res = E.resultados.get(clave) ?? {}; res[E.alg] = fr.coste; E.resultados.set(clave, res);
  const opt = OPTIMOS.map((id) => res[id]).filter((x) => x !== undefined).sort((x, y) => x - y)[0];
  let extra = '';
  if (OPTIMOS.includes(E.alg)) extra = ' · es el <b>óptimo</b>';
  else if (opt !== undefined) extra = ` · el óptimo es ${fmt(opt)} ${u}: queda a <b>+${((fr.coste / opt - 1) * 100).toFixed(1)} %</b>`;
  else extra = ' · <i>ejecuta DFJ o Held–Karp para ver cuánto se aleja del óptimo</i>';
  const ms = E.rep.ms;
  $('#resultado').innerHTML = `Ruta final: <b>${fmt(fr.coste)} ${u}</b> · ${ms < 1 ? '< 1' : ms < 1000 ? Math.round(ms) : (ms / 1000).toFixed(1) + ' '}${ms < 1000 ? ' ms' : 's'} de cálculo${extra}`;
  $('#resultado').hidden = false;
}

function actualizarBotones() {
  const r = E.rep, aplic = !motivoNoAplicable(E.alg, E.sel.size, E.dirigido);
  const jugando = r?.jugando;
  $('#b-jugar').textContent = jugando ? '⏸ Pausar' : r?.terminado ? '↻ Repetir' : r?.hist.length ? '▶ Continuar' : '▶ Ejecutar';
  for (const id of ['#b-jugar', '#b-paso', '#b-final', '#b-atras', '#b-reiniciar']) $(id).disabled = !aplic;
  $('#b-atras').disabled = !aplic || !r || r.pos <= 0;
}

export function reiniciar() {
  E.rep?.cancelar(); E.rep = null;
  if (!E.datos) return;
  const motivo = motivoNoAplicable(E.alg, E.sel.size, E.dirigido);
  const av = $('#aviso');
  av.hidden = !motivo;
  if (motivo) {
    av.innerHTML = `<span>⚠️ <b>${ALGORITMOS[E.alg].nombre}</b>: ${motivo}</span>${ALGORITMOS[E.alg].soloNoDirigido && E.dirigido ? '<button id="a-sin">Usar «Sin sentidos únicos»</button>' : ''}`;
    $('#a-sin')?.addEventListener('click', () => { E.dirigido = false; $('#seg-sentido').querySelectorAll('button').forEach((x) => x.classList.toggle('activa', x.dataset.v === 'no_dirigido')); reiniciar(); alCambiarInstancia?.(); });
  }
  E.contexto = construirContexto();
  E.mapa.limpiar([...E.sel], E.inicio);
  limpiarPanel(); actualizarBotones();
}

function crearReproductor() {
  const { ctx } = E.contexto;
  const gen = crearGenerador(E.alg, ctx, E.semilla);
  const masivo = E.alg === 'fuerza_bruta' ? SALTOS_FB : E.alg === 'genetico' || E.alg === 'recocido_simulado' ? SALTOS_SUAVE : null;
  E.rep = new Reproductor(gen, () => (masivo ? masivo[E.vel - 1] : 1), mostrarFotograma);
}

async function alternarReproduccion() {
  if (motivoNoAplicable(E.alg, E.sel.size, E.dirigido)) return;
  if (E.rep?.terminado) { reiniciar(); }
  if (!E.rep) crearReproductor();
  if (E.rep.jugando) { E.rep.pausar(); actualizarBotones(); return; }
  actualizarBotones();
  const p = E.rep.jugar(actualizarBotones);
  actualizarBotones();
  await p;
}

function iniciarControles() {
  $('#b-jugar').onclick = () => alternarReproduccion().catch(errorAlgoritmo);
  $('#b-reiniciar').onclick = () => reiniciar();
  $('#b-paso').onclick = async () => { if (motivoNoAplicable(E.alg, E.sel.size, E.dirigido)) return; if (!E.rep) crearReproductor(); E.rep.pausar(); try { await E.rep.siguiente(1); } catch (e) { errorAlgoritmo(e); } actualizarBotones(); };
  $('#b-atras').onclick = () => { E.rep?.pausar(); E.rep?.atras(); actualizarBotones(); };
  $('#b-final').onclick = async () => { if (motivoNoAplicable(E.alg, E.sel.size, E.dirigido)) return; if (!E.rep) crearReproductor(); try { await E.rep.alFinal(actualizarBotones); } catch (e) { errorAlgoritmo(e); } };
  $('#vel').oninput = (e) => { E.vel = +e.target.value; $('#vel-txt').textContent = E.vel; };
  $('#semilla').onchange = (e) => { E.semilla = Math.max(1, +e.target.value || 42); reiniciar(); };
  document.addEventListener('keydown', (e) => {
    if (['INPUT', 'SELECT', 'TEXTAREA'].includes(e.target.tagName) || $('#vista-lab').hidden) return;
    if (e.code === 'Space') { e.preventDefault(); $('#b-jugar').click(); } else if (e.code === 'ArrowRight') $('#b-paso').click(); else if (e.code === 'ArrowLeft') $('#b-atras').click();
  });
}
function errorAlgoritmo(e) { console.error(e); $('#aviso').hidden = false; $('#aviso').innerHTML = `⚠️ Ha ocurrido un error al ejecutar el algoritmo: ${e.message}`; }

// ───────────────────────────── Pestañas y tema ─────────────────────────────
function iniciarPestanas() {
  let carrera = null;
  document.querySelector('.pestanas').onclick = (e) => {
    const b = e.target.closest('button'); if (!b) return;
    document.querySelectorAll('.pestanas button').forEach((x) => x.classList.toggle('activa', x === b));
    for (const v of ['lab', 'carrera', 'acerca']) $(`#vista-${v}`).hidden = v !== b.dataset.vista;
    $('.instancia').style.display = b.dataset.vista === 'acerca' ? 'none' : '';
    document.querySelector('main').style.gridTemplateColumns = b.dataset.vista === 'acerca' ? '1fr' : '';
    if (b.dataset.vista === 'carrera') { carrera ??= iniciarCarrera(E, (f) => { alCambiarInstancia = f; }); carrera.mostrar(); }
    if (b.dataset.vista === 'lab') { E.rep?.pausar(); setTimeout(() => window.dispatchEvent(new Event('resize')), 0); }
  };
  $('#pantalla').onclick = () => { document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen?.(); };
  const tema = localStorage.getItem('tema') ?? 'oscuro';
  document.documentElement.dataset.tema = tema;
  $('#tema').onclick = () => { const t = document.documentElement.dataset.tema === 'oscuro' ? 'claro' : 'oscuro'; document.documentElement.dataset.tema = t; try { localStorage.setItem('tema', t); } catch (e) { /* sin almacenamiento */ } E.mapa.pintarFondo(); };
}

async function main() {
  try {
    E.datos = await cargarDatos();
  } catch (e) {
    $('#cargando').hidden = true; $('#error').hidden = false;
    $('#error').innerHTML = `<b>No se han podido cargar los datos.</b><br>${e.message}<br><br>Esta web necesita un servidor (no se puede abrir el archivo directamente). Ejecuta <code>python -m http.server</code> en la carpeta <code>web/</code> y abre <code>http://localhost:8000</code>.`;
    return;
  }
  $('#cargando').hidden = true; document.querySelector('main').hidden = false;
  E.mapa = new Mapa($('#mapa'), E.datos, { alClicCiudad: alternar });
  iniciarPestanas(); iniciarInstancia(); iniciarChips(); iniciarControles(); panelAlgoritmo();
  E.sel = new Set(E.datos.ciudades.map((c, i) => [c, i]).filter(([c]) => c.comunidad === 'Galicia').map(([, i]) => i));
  refrescar();
  E.mapa.encuadrar([...E.sel]);
  window.E = E;                                           // para depurar desde la consola
}
main();

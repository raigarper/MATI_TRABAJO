// Mapa esquemático de la península: contorno, red de autovías de fondo, ciudades y rutas sobre el trazado real de carreteras.
import { COLORES_GRUPO } from './meta.js';

const LON0 = -9.75, LON1 = 3.75, LAT0 = 35.85, LAT1 = 44.0, KX = Math.cos(40 * Math.PI / 180) * 100, KY = 100;
export const ANCHO = (LON1 - LON0) * KX, ALTO = (LAT1 - LAT0) * KY;
export const proyectar = (lon, lat) => [(lon - LON0) * KX, (LAT1 - lat) * KY];
const f1 = (x) => x.toFixed(1);

// Estilos de las aristas resaltadas (el color real sale de variables CSS para respetar el tema)
const ESTILO = {
  cand: 'estilo-cand', elegida: 'estilo-elegida', quitar: 'estilo-quitar', poner: 'estilo-poner', arbol: 'estilo-arbol', empar: 'estilo-empar', euler: 'estilo-euler', asig: 'estilo-asig',
};

export class Mapa {
  constructor(contenedor, datos, { alClicCiudad } = {}) {
    this.datos = datos; this.alClic = alClicCiudad;
    this.cacheD = new Map();
    contenedor.innerHTML = `<div class="lienzo"><canvas></canvas>
      <svg viewBox="0 0 ${f1(ANCHO)} ${f1(ALTO)}" preserveAspectRatio="xMidYMid meet">
        <g class="capa-fondo"></g><g class="capa-aristas"></g><g class="capa-ruta"></g><g class="capa-ciudades"></g></svg></div>
      <div class="zoom"><button data-z="1" title="Acercar">+</button><button data-z="-1" title="Alejar">−</button><button data-z="enc" title="Encuadrar las ciudades elegidas">⌖</button><button data-z="0" title="Ver toda la península">⌂</button></div>`;
    this.lienzo = contenedor.querySelector('.lienzo');
    this.canvas = contenedor.querySelector('canvas');
    this.svg = contenedor.querySelector('svg');
    this.capa = { fondo: this.svg.querySelector('.capa-fondo'), aristas: this.svg.querySelector('.capa-aristas'), ruta: this.svg.querySelector('.capa-ruta'), ciudades: this.svg.querySelector('.capa-ciudades') };
    this.escala = 1; this.dx = 0; this.dy = 0;
    this.#ajustarZoom(contenedor);
    this.pintarFondo();
    new ResizeObserver(() => this.#encajar()).observe(contenedor);
    this.contenedor = contenedor;
    this.#encajar();
  }

  #encajar() {                      // el lienzo ocupa el contenedor manteniendo la proporción del mapa
    const w = this.contenedor.clientWidth, h = this.contenedor.clientHeight;
    if (!w || !h) return;
    const k = Math.min(w / ANCHO, h / ALTO);
    this.lienzo.style.width = `${ANCHO * k}px`; this.lienzo.style.height = `${ALTO * k}px`;
    this.base = { w: ANCHO * k, h: ALTO * k, dispW: w, dispH: h };
    this.#aplicarTransformacion();
  }

  #aplicarTransformacion() {
    if (!this.base) return;
    const maxX = Math.max(0, (this.base.w * this.escala - this.base.dispW) / 2 + 80), maxY = Math.max(0, (this.base.h * this.escala - this.base.dispH) / 2 + 80);
    this.dx = Math.max(-maxX, Math.min(maxX, this.dx)); this.dy = Math.max(-maxY, Math.min(maxY, this.dy));
    this.lienzo.style.transform = `translate(calc(-50% + ${this.dx}px), calc(-50% + ${this.dy}px)) scale(${this.escala})`;
    this.svg.style.setProperty('--iz', (1 / this.escala).toFixed(3));                    // las etiquetas y los puntos no crecen con el zoom
    this.svg.style.setProperty('--rz', (1 / Math.sqrt(this.escala)).toFixed(3));
  }

  #ajustarZoom(contenedor) {
    let arrastre = null;
    contenedor.addEventListener('wheel', (e) => { e.preventDefault(); this.zoom(e.deltaY < 0 ? 1.15 : 1 / 1.15); }, { passive: false });
    contenedor.addEventListener('pointerdown', (e) => { if (e.target.closest('.zoom')) return; arrastre = { x: e.clientX, y: e.clientY, dx: this.dx, dy: this.dy, movido: false }; });
    window.addEventListener('pointermove', (e) => {
      if (!arrastre) return;
      const ddx = e.clientX - arrastre.x, ddy = e.clientY - arrastre.y;
      if (Math.abs(ddx) + Math.abs(ddy) > 4) arrastre.movido = true;
      if (arrastre.movido) { this.dx = arrastre.dx + ddx; this.dy = arrastre.dy + ddy; this.#aplicarTransformacion(); }
    });
    window.addEventListener('pointerup', () => { setTimeout(() => { arrastre = null; }, 0); });
    contenedor.addEventListener('click', (e) => { if (arrastre?.movido) e.stopPropagation(); }, true);
    contenedor.querySelector('.zoom').addEventListener('click', (e) => {
      const z = e.target.dataset.z; if (z === undefined) return;
      if (z === '0') { this.#animar(); this.escala = 1; this.dx = this.dy = 0; this.#aplicarTransformacion(); } else if (z === 'enc') this.encuadrar(this.seleccionActual); else this.zoom(z === '1' ? 1.4 : 1 / 1.4);
    });
  }
  #animar() { this.lienzo.classList.add('anim'); clearTimeout(this.tAnim); this.tAnim = setTimeout(() => this.lienzo.classList.remove('anim'), 650); }
  // Acerca el mapa para que quepan justo las ciudades indicadas (índices globales)
  encuadrar(indices) {
    if (!this.base || !indices?.length) return;
    const pts = indices.map((i) => this.punto(i));
    const x0 = Math.min(...pts.map((p) => p[0])), x1 = Math.max(...pts.map((p) => p[0])), y0 = Math.min(...pts.map((p) => p[1])), y1 = Math.max(...pts.map((p) => p[1]));
    const margen = 70, k = this.base.w / ANCHO;
    const s = Math.min(this.base.dispW / ((x1 - x0 + 2 * margen) * k), this.base.dispH / ((y1 - y0 + 2 * margen) * k));
    this.#animar();
    this.escala = Math.max(1, Math.min(8, s));
    this.dx = -((x0 + x1) / 2 - ANCHO / 2) * k * this.escala; this.dy = -((y0 + y1) / 2 - ALTO / 2) * k * this.escala;
    this.#aplicarTransformacion();
  }
  zoom(f) { this.escala = Math.max(1, Math.min(8, this.escala * f)); this.#aplicarTransformacion(); }

  // ── Fondo (canvas): contorno de la península, países vecinos y autovías ──
  pintarFondo() {
    const css = getComputedStyle(document.documentElement);
    const c = this.canvas, k = 2.4;
    c.width = ANCHO * k; c.height = ALTO * k;
    const g = c.getContext('2d'); g.scale(k, k);
    g.clearRect(0, 0, ANCHO, ALTO);
    g.fillStyle = css.getPropertyValue('--mar'); g.fillRect(0, 0, ANCHO, ALTO);
    const poli = (anillo) => { g.beginPath(); anillo.forEach(([lon, lat], i) => { const [x, y] = proyectar(lon, lat); i ? g.lineTo(x, y) : g.moveTo(x, y); }); g.closePath(); };
    for (const [pais, lista] of Object.entries(this.datos.contorno)) {
      for (const anillo of lista) {
        poli(anillo);
        g.fillStyle = css.getPropertyValue(pais === 'Spain' ? '--tierra' : '--vecinos'); g.fill();
        g.lineWidth = pais === 'Spain' ? 1.1 : 0.6; g.strokeStyle = css.getPropertyValue('--borde-mapa'); g.stroke();
      }
    }
    g.strokeStyle = css.getPropertyValue('--red'); g.lineWidth = 0.55; g.lineCap = 'round';
    g.beginPath();
    for (const [x1, y1, x2, y2] of this.datos.fondo) { const a = proyectar(x1, y1), b = proyectar(x2, y2); g.moveTo(a[0], a[1]); g.lineTo(b[0], b[1]); }
    g.stroke();
  }

  // ── Texto del trazado de una arista a→b sobre carretera real (con caché) ──
  d(a, b) {
    const clave = `${a}-${b}`;
    let s = this.cacheD.get(clave);
    if (!s) {
      const g = this.datos.geometria(a, b);
      s = g.map(([lon, lat], i) => { const [x, y] = proyectar(lon, lat); return `${i ? 'L' : 'M'}${f1(x)} ${f1(y)}`; }).join('');
      this.cacheD.set(clave, s);
    }
    return s;
  }
  punto(i) { const c = this.datos.ciudades[i]; return proyectar(c.lon, c.lat); }

  // ── Ciudades ──
  dibujarCiudades(seleccion, inicio, nodos = {}, mapaLocal = null) {
    const sel = new Set(seleccion); this.seleccionActual = [...seleccion];
    let h = '';
    this.datos.ciudades.forEach((c, i) => {
      const [x, y] = this.punto(i);
      const en = sel.has(i), r = en ? 2.6 + Math.sqrt(c.poblacion / 1e6) * 1.9 : 2.1;
      const loc = mapaLocal ? mapaLocal.get(i) : undefined;
      const clase = loc !== undefined && nodos[loc] ? nodos[loc] : '';
      const relleno = ` style="--r:${f1(r)}${clase.startsWith('grupo') ? `;fill:${COLORES_GRUPO[+clase.slice(5)]}` : ''}"`;
      h += `<g class="ciudad ${en ? 'sel' : 'nosel'} ${i === inicio ? 'inicio' : ''} ${clase.startsWith('grupo') ? 'grupo' : clase}" data-i="${i}"><circle class="zona" cx="${f1(x)}" cy="${f1(y)}" r="7"/>
        <circle class="punto" cx="${f1(x)}" cy="${f1(y)}" r="${f1(r)}"${relleno}/>${en ? `<text x="${f1(x + 4.5)}" y="${f1(y + 3)}">${c.nombre}</text>` : ''}<title>${c.nombre} · ${(c.poblacion / 1000).toLocaleString('es-ES', { maximumFractionDigits: 0 })} mil hab.${en ? '' : ' (pulsa para añadir)'}</title></g>`;
    });
    this.capa.ciudades.innerHTML = h;
    this.capa.ciudades.onclick = (e) => { const g = e.target.closest('.ciudad'); if (g && this.alClic) this.alClic(+g.dataset.i); };
  }

  // ── Un fotograma del algoritmo: `global[i]` convierte el índice local en el de la ciudad ──
  dibujarFotograma(fr, global, color, seleccion, inicio) {
    const loc = new Map(global.map((g, i) => [g, i]));
    // Rutas de la población (genético, recocido): líneas finas rectas entre ciudades
    let fondo = '';
    for (const r of fr.fondo ?? []) fondo += `<polygon points="${r.map((i) => this.punto(global[i]).map(f1).join(',')).join(' ')}"/>`;
    this.capa.fondo.innerHTML = fondo;
    // Aristas resaltadas
    let ar = '';
    for (const e of fr.aristas ?? []) {
      const cls = ESTILO[e.c] ?? 'estilo-cand';
      const est = e.c === 'asig' ? ` style="stroke:${COLORES_GRUPO[e.grupo % 8]}"` : '';
      ar += `<path class="${cls}"${est} d="${this.d(global[e.a], global[e.b])}"/>`;
    }
    this.capa.aristas.innerHTML = ar;
    // Ruta que se está construyendo
    let ruta = '';
    const r = fr.ruta ?? [];
    if (r.length >= 2) {
      let d = '';
      for (let k = 0; k + 1 < r.length; k++) d += this.d(global[r[k]], global[r[k + 1]]);
      if (fr.cerrada) d += this.d(global[r[r.length - 1]], global[r[0]]);
      ruta = `<path class="ruta-halo" d="${d}"/><path class="ruta ${fr.fin ? 'final' : ''}" style="stroke:${color}" d="${d}"/>`;
    }
    this.capa.ruta.innerHTML = ruta;
    this.dibujarCiudades(seleccion, inicio, fr.nodos ?? {}, loc);
  }

  limpiar(seleccion, inicio) {
    this.capa.fondo.innerHTML = ''; this.capa.aristas.innerHTML = ''; this.capa.ruta.innerHTML = '';
    this.dibujarCiudades(seleccion, inicio);
  }
}

// Mapa pequeño (solo SVG) para las tarjetas de la carrera
export function miniMapa(datos, contenedor) {
  const css = getComputedStyle(document.documentElement);
  let contorno = '';
  for (const [pais, lista] of Object.entries(datos.contorno)) for (const anillo of lista) {
    contorno += `<polygon class="${pais === 'Spain' ? 'mini-es' : 'mini-vec'}" points="${anillo.map(([lon, lat]) => proyectar(lon, lat).map(f1).join(',')).join(' ')}"/>`;
  }
  contenedor.innerHTML = `<svg viewBox="0 0 ${f1(ANCHO)} ${f1(ALTO)}">${contorno}<g class="mini-ruta"></g><g class="mini-ciud"></g></svg>`;
  const capaRuta = contenedor.querySelector('.mini-ruta'), capaCiud = contenedor.querySelector('.mini-ciud');
  const cache = new Map();
  const d = (a, b) => { const k = `${a}-${b}`; let s = cache.get(k); if (!s) { s = datos.geometria(a, b).map(([lon, lat], i) => { const [x, y] = proyectar(lon, lat); return `${i ? 'L' : 'M'}${f1(x)} ${f1(y)}`; }).join(''); cache.set(k, s); } return s; };
  return {
    ciudades(global, inicio) {
      // Encuadra el mapa pequeño en las ciudades elegidas (con margen y sin perder la proporción)
      const pts = global.map((g) => proyectar(datos.ciudades[g].lon, datos.ciudades[g].lat));
      const x0 = Math.min(...pts.map((p) => p[0])), x1 = Math.max(...pts.map((p) => p[0])), y0 = Math.min(...pts.map((p) => p[1])), y1 = Math.max(...pts.map((p) => p[1]));
      const prop = ANCHO / ALTO, m = 60;
      let w = Math.max(x1 - x0 + 2 * m, 220), h = Math.max(y1 - y0 + 2 * m, 220 / prop);
      if (w / h > prop) h = w / prop; else w = h * prop;
      const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
      contenedor.querySelector('svg').setAttribute('viewBox', `${f1(Math.max(-200, cx - w / 2))} ${f1(Math.max(-200, cy - h / 2))} ${f1(w)} ${f1(h)}`);
      capaCiud.innerHTML = global.map((g) => { const c = datos.ciudades[g]; const [x, y] = proyectar(c.lon, c.lat); return `<circle cx="${f1(x)}" cy="${f1(y)}" r="${g === global[inicio] ? 5 : 3.4}"/>`; }).join(''); },
    ruta(global, ruta, cerrada, color) {
      if (!ruta || ruta.length < 2) { capaRuta.innerHTML = ''; return; }
      let t = ''; for (let k = 0; k + 1 < ruta.length; k++) t += d(global[ruta[k]], global[ruta[k + 1]]);
      if (cerrada) t += d(global[ruta[ruta.length - 1]], global[ruta[0]]);
      capaRuta.innerHTML = `<path d="${t}" style="stroke:${color}"/>`;
    },
  };
}

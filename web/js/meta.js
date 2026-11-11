// Datos de cada algoritmo para la interfaz: ficha, explicación llana, pseudocódigo (las líneas se resaltan según el fotograma `l`).
// Los colores son los mismos que en las figuras del notebook (paleta categórica en orden fijo).

export const ALGORITMOS = {
  fuerza_bruta: {
    nombre: 'Fuerza bruta', familia: 'Exactos', color: '#2a78d6', autor: 'Pablo', limite: 10,
    tipo: 'Exacto', garantia: 'Siempre el óptimo', tiempo: 'O((n−1)!·n)', memoria: 'O(n)', simetria: 'No la necesita',
    idea: 'Prueba <b>todas</b> las rutas posibles y se queda con la más corta. Seguro que acierta, pero con 11 ciudades ya hay casi 4 millones de rutas y con 13 son demasiadas.',
    pseudo: ['mejor ← ∞', 'para cada ordenación de las n−1 ciudades restantes:', '    ruta ← [inicio] + ordenación', '    coste ← suma de las distancias de la ruta (con la vuelta)',
      '    si coste < mejor:  mejor ← coste ; guardar la ruta', 'fin para', 'devolver la mejor ruta'],
  },
  held_karp: {
    nombre: 'Held–Karp', familia: 'Exactos', color: '#eb6834', autor: 'Raimundo', limite: 18,
    tipo: 'Exacto · programación dinámica', garantia: 'Siempre el óptimo', tiempo: 'O(n²·2ⁿ)', memoria: 'O(n·2ⁿ)', simetria: 'No la necesita',
    idea: 'Es la fuerza bruta <b>con memoria</b>. Muchas rutas comparten tramos, así que guarda el mejor camino para cada grupo de ciudades y lo reutiliza en vez de recalcularlo. Siempre da la mejor ruta y es muchísimo más rápido, pero su memoria se duplica con cada ciudad.',
    pseudo: ['fijar la ciudad de salida', 'dp[S][j] = coste del mejor camino que sale de inicio, visita las ciudades de S y acaba en j', 'para cada ciudad j:  dp[{j}][j] ← distancia(inicio, j)',
      'para k de 2 hasta n−1:                      (tamaño del subconjunto)', '    para cada subconjunto S de tamaño k y cada j en S:', '        dp[S][j] ← mínimo sobre i en S∖{j} de  dp[S∖{j}][i] + distancia(i, j)',
      'fin para', 'j* ← la j que minimiza  dp[todas][j] + distancia(j, inicio)', 'reconstruir la ruta hacia atrás desde j*'],
  },
  dfj: {
    nombre: 'DFJ', familia: 'Exactos', color: '#1baf7a', autor: 'Jiahao', limite: 75,
    tipo: 'Exacto · programación entera', garantia: 'Siempre el óptimo', tiempo: 'O(2ⁿ) en el peor caso', memoria: 'O(n²) en la práctica', simetria: 'No la necesita',
    idea: 'Primero resuelve una versión <b>más fácil</b>: cada ciudad con una sola salida y una sola entrada. La solución suele salir en <b>varios circuitos sueltos</b>. Entonces añade una regla («este grupo debe conectarse con el resto») y vuelve a resolver, hasta que sale un único circuito. Es lo que se usa en la práctica con muchas ciudades.',
    pseudo: ['DFJ(K):  resolver primero el problema de asignación', '    cada ciudad: una salida y una entrada  (variables x_ij ∈ {0,1})', '    minimizar el coste total', 'repetir:  resolver el problema entero (con un solver)',
      '    circuitos ← componentes de la solución', '    si hay más de un circuito:', '        para cada circuito S:  añadir   Σ x_ij (i∈S, j∉S) ≥ 1', '    si no:  devolver la ruta (es el óptimo)'],
  },
  vecino_mas_cercano: {
    nombre: 'Vecino más cercano', familia: 'Heurísticos', color: '#eda100', autor: 'Pablo', limite: 75,
    tipo: 'Heurístico · voraz', garantia: 'Ninguna', tiempo: 'O(n²)', memoria: 'O(n)', simetria: 'No la necesita',
    idea: 'Es la ruta del que <b>no planifica</b>: desde donde estás, ir siempre a la ciudad más cercana que no hayas visitado. Es instantáneo, pero a veces te deja una ciudad lejana para el final y el último tramo sale carísimo.',
    pseudo: ['VECINO_MÁS_CERCANO(inicio):', 'ruta ← [inicio] ; pendientes ← todas las demás', 'mientras queden pendientes:', '    mirar la distancia a cada ciudad pendiente', '    siguiente ← la más cercana',
      '    ir a siguiente ; quitarla de pendientes', 'fin mientras', 'volver a inicio ; devolver la ruta'],
  },
  dos_opt: {
    nombre: '2-opt', familia: 'Heurísticos', color: '#e87ba4', autor: 'Raimundo', limite: 75,
    tipo: 'Heurístico · mejora local', garantia: 'Ninguna', tiempo: 'O(n²) por vuelta', memoria: 'O(n²)', simetria: 'No la necesita',
    idea: 'Parte de una ruta cualquiera y la <b>mejora con arreglos pequeños</b>: si dos tramos se cruzan, se deshacen y se recolocan, y casi siempre se ahorra distancia. Se repite hasta que no quedan cruces que arreglar. Es rapidísimo y muy bueno.',
    pseudo: ['ruta ← una ruta inicial (aquí, el vecino más cercano)', 'repetir:', '    para cada par de tramos (a→b) y (c→d):', '        calcular cuánto cambia el coste si se sustituyen por (a→c) y (b→d)',
      '    aplicar el mejor cambio si mejora  (invertir el tramo del medio)', 'hasta que ningún cambio mejore', 'devolver la ruta'],
  },
  christofides: {
    nombre: 'Christofides', familia: 'Heurísticos', color: '#008300', autor: 'Raimundo', limite: 75, soloNoDirigido: true,
    tipo: 'Aproximado con garantía', garantia: 'Nunca peor que 1,5 × el óptimo', tiempo: 'O(n³)', memoria: 'O(n²)', simetria: 'Necesita grafo no dirigido',
    idea: 'Promete que la ruta <b>no será más de un 50 % peor</b> que la mejor. Primero une todas las ciudades con la menor carretera posible (un árbol), empareja las que quedan con conexiones impares, recorre todas las carreteras una vez y <b>se salta las ciudades repetidas</b>.',
    pseudo: ['CHRISTOFIDES(grafo no dirigido):', 'T ← árbol de expansión mínimo', '    (añadir siempre la conexión más barata hacia una ciudad nueva)', 'I ← ciudades de grado impar en T',
      'M ← emparejamiento perfecto de coste mínimo entre las de I', 'G ← T + M ;  circuito ← circuito euleriano de G', 'ruta ← [ ]', 'para cada ciudad del circuito:  si no está en ruta, añadirla (atajo)', 'devolver la ruta'],
  },
  recocido_simulado: {
    nombre: 'Recocido simulado', familia: 'Metaheurísticas', color: '#e34948', autor: 'Juan', limite: 75,
    tipo: 'Metaheurística', garantia: 'Ninguna', tiempo: 'Niveles de T × iteraciones', memoria: 'O(n²)', simetria: 'No la necesita',
    idea: 'Como buscar el punto más bajo de un paisaje con los ojos tapados. Si solo bajas, te quedas en el primer valle. Este método <b>acepta también rutas peores</b> con cierta probabilidad, que va bajando con la «temperatura» (como el metal al forjarlo). Así sale de valles malos y acaba asentándose en uno bueno.',
    pseudo: ['RECOCIDO(T inicial, factor α):', 'ruta ← ruta al azar ;  T ← 15 % del coste', 'mientras T > T_min:', '    repetir n_iter veces:', '        proponer invertir un tramo al azar (cambio 2-opt)', '        Δ ← cambio de coste',
      '        si Δ ≤ 0:  aceptar', '        si no:  aceptar con probabilidad  e^(−Δ/T)', '        guardar la mejor ruta vista', '    T ← T × α                 (enfriar)', 'fin mientras', 'devolver la mejor ruta'],
  },
  genetico: {
    nombre: 'Genético', familia: 'Metaheurísticas', color: '#6250d6', autor: 'Raimundo', limite: 75,
    tipo: 'Metaheurística', garantia: 'Ninguna', tiempo: 'O(G·P·n·q)', memoria: 'O(P·n)', simetria: 'No la necesita',
    idea: 'Imita la evolución: empieza con muchas rutas <b>al azar</b>; las más cortas «tienen hijos» (se combinan trozos de dos rutas) y a veces hay pequeñas mutaciones. Tras muchas generaciones, la población mejora sola.',
    pseudo: ['GENÉTICO(población P, generaciones G):', 'población ← P rutas al azar', 'repetir hasta G generaciones o hasta no mejorar:', '    élite ← las 2 mejores rutas (pasan intactas)', '    mientras la nueva población no esté completa:',
      '        padres ← el mejor de 3 rutas al azar (torneo), dos veces', '        hijo ← CRUCE(padre 1, padre 2)', '        con probabilidad p:  MUTAR(hijo)   (invertir un tramo si mejora)', '    población ← nueva ; actualizar la mejor ruta', 'devolver la mejor ruta'],
  },
};

export const ORDEN = ['fuerza_bruta', 'held_karp', 'dfj', 'vecino_mas_cercano', 'dos_opt', 'christofides', 'recocido_simulado', 'genetico'];

// Colores de los circuitos sueltos de DFJ (8, en el mismo orden que la paleta)
export const COLORES_GRUPO = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6', '#e34948'];

// ── Qué puede ejecutarse con qué instancia (mismas reglas que el estudio del trabajo, con límites algo menores por la animación) ──
export const MIN_CIUDADES = 3;

function factorialTexto(m) {
  if (m <= 15) { let f = 1; for (let i = 2; i <= m; i++) f *= i; return f.toLocaleString('es-ES'); }
  let l = 0; for (let i = 2; i <= m; i++) l += Math.log10(i);
  return `≈ 10<sup>${Math.round(l)}</sup>`;
}

// Devuelve el motivo por el que `id` no se puede ejecutar con n ciudades (o null si sí se puede)
export function motivoNoAplicable(id, n, dirigido) {
  const a = ALGORITMOS[id];
  if (n < MIN_CIUDADES) return `Elige al menos ${MIN_CIUDADES} ciudades.`;
  if (id === 'fuerza_bruta' && n > a.limite) return `Con ${n} ciudades habría ${factorialTexto(n - 1)} rutas que probar (${n - 1}!): inviable. Aquí se anima con hasta ${a.limite} ciudades; el estudio del trabajo llegó a 11 (tarda más de 20 s) y con 13 serían unos 50 minutos.`;
  if (id === 'held_karp' && n > a.limite) return `La tabla de Held–Karp se duplica con cada ciudad (2<sup>${n - 1}</sup> subconjuntos). Aquí se anima con hasta ${a.limite} ciudades; el trabajo llegó a 20 (104 MB) y con 22 ya no cabría.`;
  if (a.soloNoDirigido && dirigido) return 'Christofides necesita distancias simétricas (que ir de A a B cueste lo mismo que de B a A). Elige «Sin sentidos únicos».';
  return null;
}

// Leyenda del mapa para cada algoritmo: [color (variable CSS), texto]
export const LEYENDA = {
  fuerza_bruta: [['var(--ciudad-sel)', 'Ruta que se prueba']],
  held_karp: [['var(--cand)', 'Caminos candidatos'], ['var(--ciudad-sel)', 'Mejor camino parcial']],
  dfj: [['var(--acento)', 'Cada color: un circuito suelto'], ['var(--ciudad-sel)', 'Ruta final']],
  vecino_mas_cercano: [['var(--cand)', 'Ciudades que se comparan'], ['var(--elegida)', 'La más cercana'], ['var(--ciudad-sel)', 'Ruta hasta ahora']],
  dos_opt: [['var(--quitar)', 'Tramos que se quitan'], ['var(--poner)', 'Tramos que se ponen'], ['var(--ciudad-sel)', 'Ruta']],
  christofides: [['var(--arbol)', 'Árbol mínimo'], ['var(--empar)', 'Emparejamiento'], ['var(--ciudad-sel)', 'Ruta final']],
  recocido_simulado: [['var(--ciudad-sel)', 'Mejor ruta'], ['var(--acento)', 'Ruta actual (tenue)'], ['var(--quitar)', 'Tramos que se cambian']],
  genetico: [['var(--ciudad-sel)', 'Mejor ruta'], ['var(--acento)', '8 rutas de la población (tenues)']],
};

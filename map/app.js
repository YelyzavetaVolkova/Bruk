// BRUK — веб-мапа для Android і комп'ютера.
// Повторює iOS-застосунок (bruk-app/Bruk/CityMapView.swift): ті самі дані,
// той самий стиль Mapbox, будинки з історією підсвічені теракотовим.
'use strict';

// MARK: - Налаштування

const CONFIG = {
  // Ключ Mapbox лежить окремо, у config.js (див. коментар там).
  token: (window.BRUK_CONFIG && window.BRUK_CONFIG.mapboxToken) || '',
  style: 'mapbox://styles/bizhymo-tsiluvatysia/cmqjg0si9005201sc4snphnsn',
  center: [30.516363999999985, 50.44522040000001],
  zoom: 17.7,
  bearing: 60.8,
  pitch: 60,
  // Колір будинків з картками, як у застосунку (colorBuildingHighlight).
  highlight: 'hsl(18, 55%, 80%)',
  email: 'bruk.kyiv@gmail.com',
  shortStoryWordLimit: 40,
};

const state = {
  buildings: [],
  byId: new Map(),
  filters: [],
  facts: [],
  haystacks: new Map(),
  activeFilters: new Set(),
  selectedId: null,
  buildingsTarget: null,   // featureset будинків у стилі Mapbox Standard
  highlighted: new Set(),  // osm way id з highlight: true
  selectedFeatureId: null,
  watchId: null,
  youMarker: null,
  installPrompt: null,
  resolved: loadResolved(), // id картки → ID будівлі Mapbox, знайдений за контуром
};

const $ = (id) => document.getElementById(id);
// /map/?embed=1 — мапа вбудована в головну сторінку bruk.city.
const EMBED = document.documentElement.classList.contains('embed');

// MARK: - Дані

const hasStory = (b) => !!(b.shortText || b.keyFacts);
const needsResearch = (b) => {
  if (!hasStory(b)) return true;
  const words = (b.shortText || b.keyFacts || '').split(/\s+/).filter(Boolean).length;
  return words < CONFIG.shortStoryWordLimit;
};
const wayId = (b) => (b.osmID && b.osmID.startsWith('way/') ? b.osmID.slice(4) : null);

// MARK: - ID будівель, знайдені на мапі (як resolveFeatureIDs у застосунку)
//
// ID будівель у Mapbox Standard — це ID ways з OSM. Але в частини карток osmID
// немає (координати з Visicom) або це relation, а буває, що Mapbox ріже будинок
// інакше, ніж OSM. Такі картки не підсвічувались. Тож коли мапа зупиняється,
// беремо будівлі на екрані й шукаємо ту, в контурі якої лежить точка картки
// (або край якої ближче ніж за 8 м — адреса часто стоїть на фасаді).
// Знайдене зберігаємо в браузері — наступного разу підсвітка є одразу.

const RESOLVE_KEY = 'bruk.resolvedFeatureIDs.v1';
const RESOLVE_TOLERANCE_M = 8;
const settledIds = new Set();

function loadResolved() {
  try { return JSON.parse(localStorage.getItem(RESOLVE_KEY)) || {}; } catch (_) { return {}; }
}
function saveResolved() {
  try { localStorage.setItem(RESOLVE_KEY, JSON.stringify(state.resolved)); } catch (_) { /* приватний режим */ }
}

/** ID будівлі Mapbox для картки: знайдений на мапі, інакше way з OSM. */
const featureIdFor = (b) => (b && state.resolved[b.id]) || wayId(b);

/** Відстань у метрах від точки до найближчого краю контуру. */
function distanceToGeometry(geometry, [lng, lat]) {
  let rings;
  if (geometry.type === 'Polygon') rings = geometry.coordinates;
  else if (geometry.type === 'MultiPolygon') rings = geometry.coordinates.flat();
  else return Infinity;
  const mLat = 111320;
  const mLng = mLat * Math.cos((lat * Math.PI) / 180);
  let best = Infinity;
  for (const ring of rings) {
    for (let i = 0; i + 1 < ring.length; i += 1) {
      const px = (ring[i][0] - lng) * mLng; const py = (ring[i][1] - lat) * mLat;
      const qx = (ring[i + 1][0] - lng) * mLng; const qy = (ring[i + 1][1] - lat) * mLat;
      const dx = qx - px; const dy = qy - py;
      const len2 = dx * dx + dy * dy;
      const t = len2 > 0 ? Math.max(0, Math.min(1, -(px * dx + py * dy) / len2)) : 0;
      const x = px + t * dx; const y = py + t * dy;
      best = Math.min(best, Math.hypot(x, y));
    }
  }
  return best;
}

function resolveFeatureIds() {
  if (!map || !state.buildingsTarget) return;
  // Нижче 15-го зуму Standard ще не малює окремих будинків.
  const zoom = map.getZoom();
  if (zoom < 15) return;
  const bounds = map.getBounds();
  const candidates = state.buildings.filter((b) => !settledIds.has(b.id) && !state.resolved[b.id]
    && bounds.contains([b.longitude, b.latitude]));
  if (!candidates.length) return;

  let features;
  try { features = map.queryRenderedFeatures({ target: state.buildingsTarget }); } catch (_) { return; }
  const footprints = features.filter((f) => f.id != null && f.geometry)
    .map((f) => ({ id: String(f.id), geometry: f.geometry }));
  const rendered = new Set(footprints.map((f) => f.id));
  // Будівлі, які вже належать карткам за osmID: їх не віддаємо сусідам.
  const claimed = new Set(state.buildings.map(wayId).filter(Boolean));

  let changed = false;
  for (const b of candidates) {
    const way = wayId(b);
    if (way && rendered.has(way)) { settledIds.add(b.id); continue; }
    const point = [b.longitude, b.latitude];
    const free = footprints.filter((f) => f.id === way || !claimed.has(f.id));
    let found = free.find((f) => geometryContains(f.geometry, point));
    if (!found) {
      let bestD = RESOLVE_TOLERANCE_M;
      for (const f of free) {
        const d = distanceToGeometry(f.geometry, point);
        if (d <= bestD) { bestD = d; found = f; }
      }
    }
    if (found) {
      state.resolved[b.id] = found.id;
      settledIds.add(b.id);
      changed = true;
    } else if (zoom >= 16.5) {
      // Зблизька будинок мав би бути на екрані: далі не шукаємо.
      settledIds.add(b.id);
    }
  }
  if (changed) {
    saveResolved();
    refreshHighlights();
  }
}

/** Усі тексти картки одним рядком у нижньому регістрі — по ньому шукають фільтри. */
function filterHaystack(b) {
  return [b.currentName, b.summary, b.shortText, b.extendedText, b.styleCurrent, b.styleOriginal,
    b.originalFunction, b.notablePeople, b.keyFacts].filter(Boolean).join(' ').toLowerCase();
}

function matchesFilters(b) {
  if (state.activeFilters.size === 0) return true;
  const text = state.haystacks.get(b.id) || '';
  return state.filters.some((f) => state.activeFilters.has(f.title) && f.words.some((w) => text.includes(w)));
}

async function loadData() {
  const get = (name) => fetch(`data/${name}.json`, { cache: 'no-cache' }).then((r) => {
    if (!r.ok) throw new Error(`${name}.json: ${r.status}`);
    return r.json();
  });
  const [buildings, facts, filters] = await Promise.all([get('buildings'), get('facts'), get('filters')]);
  state.buildings = buildings;
  state.facts = facts;
  state.filters = filters;
  for (const b of buildings) {
    state.byId.set(b.id, b);
    state.haystacks.set(b.id, filterHaystack(b));
  }
}

// MARK: - Пошук (як MapSearch.swift)

function normalize(s) {
  let out = (s || '').toLowerCase().replace(/[’ʼ`´]/g, "'").replace(/ё/g, 'е')
    .replace(/,/g, ' '); // «Хрещатик 15» і «Хрещатик, 15» — одне й те саме
  for (const p of ['вулиця ', 'вул. ', 'вул ', 'бульвар ', 'бульв. ', 'б-р ', 'провулок ', 'пров. ']) {
    out = out.split(p).join('');
  }
  return out.replace(/\s+/g, ' ').trim();
}

function search(query, limit = 8) {
  const q = normalize(query);
  if (q.length < 2) return [];
  const scored = [];
  for (const b of state.buildings) {
    const address = normalize(b.address);
    const name = normalize(b.currentName);
    const people = normalize([b.architectCurrent, b.architectOriginal, b.notablePeople].filter(Boolean).join(' '));
    let score;
    if (address.startsWith(q)) score = 0;
    else if (address.includes(q)) score = 1;
    else if (name.includes(q)) score = 2;
    else if (people.includes(q)) score = 3;
    else continue;
    scored.push({ b, score });
  }
  scored.sort((x, y) => (x.score - y.score)
    || (hasStory(y.b) - hasStory(x.b))
    || x.b.address.localeCompare(y.b.address, 'uk', { numeric: true }));
  return scored.slice(0, limit).map((s) => s.b);
}

function setupSearch() {
  const input = $('search');
  const list = $('results');
  const clear = $('search-clear');
  let items = [];
  let active = -1;

  const render = () => {
    const q = input.value;
    clear.hidden = !q;
    if (normalize(q).length < 2) { list.hidden = true; return; }
    items = search(q);
    active = -1;
    list.innerHTML = items.length
      ? items.map((b, i) => `<li role="option" data-i="${i}">
          <div class="addr">${esc(b.address)}</div>
          ${b.currentName ? `<div class="sub">${esc(b.currentName)}</div>` : ''}</li>`).join('')
      : '<li class="empty">Нічого не знайшли. Спробуй іншу адресу чи прізвище.</li>';
    list.hidden = false;
  };
  const choose = (b) => {
    input.value = '';
    clear.hidden = true;
    list.hidden = true;
    input.blur();
    showBuilding(b, { fly: true });
  };

  input.addEventListener('input', render);
  input.addEventListener('focus', render);
  input.addEventListener('keydown', (e) => {
    if (list.hidden || !items.length) return;
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      active = (active + (e.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length;
      [...list.children].forEach((li, i) => li.setAttribute('aria-selected', i === active));
    } else if (e.key === 'Enter') {
      choose(items[Math.max(active, 0)]);
    } else if (e.key === 'Escape') {
      list.hidden = true;
    }
  });
  list.addEventListener('click', (e) => {
    const li = e.target.closest('li[data-i]');
    if (li) choose(items[+li.dataset.i]);
  });
  clear.addEventListener('click', () => { input.value = ''; render(); input.focus(); });
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.top')) list.hidden = true;
  });
}

// MARK: - Мапа

let map;

function setupMap() {
  if (!mapboxgl.supported || (typeof mapboxgl.supported === 'function' && !mapboxgl.supported())) {
    showError('Цей браузер не показує 3D-мапу. Спробуй Chrome або Safari новішої версії.');
  }
  if (!CONFIG.token) {
    showError('Мапа ще не підключена: у map/config.js немає ключа Mapbox.');
    return;
  }
  mapboxgl.accessToken = CONFIG.token;
  const wide = window.matchMedia('(min-width: 900px)').matches;
  map = new mapboxgl.Map({
    container: 'map',
    style: CONFIG.style,
    center: CONFIG.center,
    zoom: wide ? 16.8 : CONFIG.zoom,
    bearing: CONFIG.bearing,
    pitch: CONFIG.pitch,
    attributionControl: true,
    language: 'uk',
    // У вбудованій мапі коліщатко гортає сторінку, а мапу масштабують з Ctrl/⌘.
    cooperativeGestures: EMBED,
  });
  map.on('error', (e) => {
    const status = e && e.error && e.error.status;
    if (status === 401 || status === 403) showError('Мапа не завантажилась: ключ Mapbox не дозволяє цей сайт.');
  });
  map.on('style.load', onStyleLoad);
}

function onStyleLoad() {
  state.buildingsTarget = findBuildingsFeatureset();
  if (state.buildingsTarget) {
    const { importId } = state.buildingsTarget;
    if (importId) {
      try { map.setConfigProperty(importId, 'colorBuildingHighlight', CONFIG.highlight); } catch (_) { /* стиль без цієї опції */ }
    }
    map.addInteraction('bruk-building-click', {
      type: 'click',
      target: state.buildingsTarget,
      handler: (e) => { onBuildingTap(e.feature, e.lngLat); return true; },
    });
    map.addInteraction('bruk-building-hover', {
      type: 'mouseenter', target: state.buildingsTarget,
      handler: () => { map.getCanvas().style.cursor = 'pointer'; },
    });
    map.addInteraction('bruk-building-leave', {
      type: 'mouseleave', target: state.buildingsTarget,
      handler: () => { map.getCanvas().style.cursor = ''; },
    });
  } else {
    addMarkerLayer();
  }
  fog.add(!!state.buildingsTarget);
  refreshHighlights();
  if (state.selectedId) markSelected(state.byId.get(state.selectedId));
  if (state.buildingsTarget) map.on('idle', resolveFeatureIds);
}

/** Featureset будинків Mapbox Standard: у корені стилю або в одному з імпортів. */
function findBuildingsFeatureset() {
  const candidates = [];
  try { candidates.push(...map.getFeaturesetDescriptors()); } catch (_) { /* старий стиль */ }
  for (const imp of (map.getStyle().imports || [])) {
    try { candidates.push(...map.getFeaturesetDescriptors(imp.id)); } catch (_) { /* пропускаємо */ }
  }
  return candidates.find((d) => d.featuresetId === 'buildings') || null;
}

function featureTarget(id) {
  return { id, target: state.buildingsTarget };
}

/** Усі будинки з картками (і під вибраний фільтр) — теракотові, як у застосунку. */
function refreshHighlights() {
  if (!map || !map.isStyleLoaded()) return;
  const wanted = new Set(state.buildings
    .filter((b) => matchesFilters(b))
    .map(featureIdFor).filter(Boolean));
  if (state.buildingsTarget) {
    for (const id of state.highlighted) {
      if (!wanted.has(id)) map.setFeatureState(featureTarget(id), { highlight: false });
    }
    for (const id of wanted) {
      if (!state.highlighted.has(id)) map.setFeatureState(featureTarget(id), { highlight: true });
    }
    state.highlighted = wanted;
  } else if (map.getSource('bruk-buildings')) {
    map.getSource('bruk-buildings').setData(markerData());
  }
}

function markSelected(b) {
  if (!state.buildingsTarget) return;
  if (state.selectedFeatureId) map.setFeatureState(featureTarget(state.selectedFeatureId), { select: false });
  state.selectedFeatureId = b ? featureIdFor(b) : null;
  if (state.selectedFeatureId) map.setFeatureState(featureTarget(state.selectedFeatureId), { select: true });
}

// Запасний варіант, якщо в стилі немає featureset будинків: точки на мапі.
function markerData() {
  return {
    type: 'FeatureCollection',
    features: state.buildings.filter((b) => matchesFilters(b)).map((b) => ({
      type: 'Feature', properties: { id: b.id },
      geometry: { type: 'Point', coordinates: [b.longitude, b.latitude] },
    })),
  };
}

function addMarkerLayer() {
  map.addSource('bruk-buildings', { type: 'geojson', data: markerData() });
  map.addLayer({
    id: 'bruk-buildings', type: 'circle', source: 'bruk-buildings',
    paint: {
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 12, 3, 17, 8],
      'circle-color': '#A20E00', 'circle-stroke-color': '#fff', 'circle-stroke-width': 2,
      'circle-pitch-alignment': 'map',
    },
  });
  map.on('click', 'bruk-buildings', (e) => {
    const b = state.byId.get(e.features[0].properties.id);
    if (b) showBuilding(b);
  });
  map.on('mouseenter', 'bruk-buildings', () => { map.getCanvas().style.cursor = 'pointer'; });
  map.on('mouseleave', 'bruk-buildings', () => { map.getCanvas().style.cursor = ''; });
}

// MARK: - Туман над неописаним Києвом (як у застосунку, Bruk/StoryFog.swift)
//
// Як у відеогрі: відкрито лише довкола будинків, що вже є в BRUK, решта міста
// під туманом. Нова вулиця в buildings.json сама розсіює туман над собою.
// Межу шукаємо по сітці відстаней до найближчого будинку (marching squares
// з інтерполяцією), тож край плавний. Туман лежить на землі під 3D-будинками,
// а легка вуаль поверх будинків — лише далеко від описаного.

const FOG_LEVELS = [[260, 0.2], [200, 0.2], [150, 0.3]];
const FOG_VEIL = [380, 0.35];
const FOG_OPEN_RADIUS = 200;
const M_PER_LAT = 111320;

const fog = (() => {
  let centers = null;
  let mPerLon = M_PER_LAT;
  const init = () => {
    if (centers) return;
    const pts = state.buildings.filter((b) => b.latitude && b.longitude);
    const lat0 = pts.length ? pts.reduce((s, b) => s + b.latitude, 0) / pts.length : 50.45;
    mPerLon = M_PER_LAT * Math.cos(lat0 * Math.PI / 180);
    centers = pts.map((b) => [b.longitude * mPerLon, b.latitude * M_PER_LAT]);
  };
  const nearest = (x, y) => centers.reduce((m, c) => Math.min(m, Math.hypot(c[0] - x, c[1] - y)), Infinity);

  function openRings(radius) {
    const step = 20, margin = radius + 3 * step;
    const xs = centers.map((c) => c[0]), ys = centers.map((c) => c[1]);
    const x0 = Math.min(...xs) - margin, x1 = Math.max(...xs) + margin;
    const y0 = Math.min(...ys) - margin, y1 = Math.max(...ys) + margin;
    const nx = Math.floor((x1 - x0) / step) + 1, ny = Math.floor((y1 - y0) / step) + 1;
    const field = new Float64Array(nx * ny).fill(Infinity);
    const reach = Math.floor(radius / step) + 3;
    for (const [cx, cy] of centers) {
      const ci = Math.floor((cx - x0) / step), cj = Math.floor((cy - y0) / step);
      for (let j = Math.max(0, cj - reach); j <= Math.min(ny - 1, cj + reach); j++) {
        for (let i = Math.max(0, ci - reach); i <= Math.min(nx - 1, ci + reach); i++) {
          const d = Math.hypot(x0 + i * step - cx, y0 + j * step - cy);
          if (d < field[j * nx + i]) field[j * nx + i] = d;
        }
      }
    }
    const value = (i, j) => field[j * nx + i];
    // Ключ ребра сітки: горизонтальне (h) чи вертикальне (v), що починається у вузлі i, j.
    const crossings = new Map();
    const crossing = (key) => {
      if (crossings.has(key)) return;
      const [kind, i, j] = key.split(':');
      const ai = +i, aj = +j, bi = kind === 'v' ? ai : ai + 1, bj = kind === 'v' ? aj + 1 : aj;
      const fa = value(ai, aj), fb = value(bi, bj);
      const t = isFinite(fa) && isFinite(fb) ? (radius - fa) / (fb - fa) : 0.5;
      crossings.set(key, [x0 + (ai + (bi - ai) * t) * step, y0 + (aj + (bj - aj) * t) * step]);
    };
    const segments = [];
    for (let j = 0; j < ny - 1; j++) {
      for (let i = 0; i < nx - 1; i++) {
        // Кути: низ-ліво, низ-право, верх-право, верх-ліво; ребро k — між кутами k і k+1.
        const v = [value(i, j), value(i + 1, j), value(i + 1, j + 1), value(i, j + 1)];
        const inside = v.map((x) => x < radius);
        const edges = [`h:${i}:${j}`, `v:${i + 1}:${j}`, `h:${i}:${j + 1}`, `v:${i}:${j}`];
        const crossed = [0, 1, 2, 3].filter((k) => inside[k] !== inside[(k + 1) % 4]);
        crossed.forEach((k) => crossing(edges[k]));
        if (crossed.length === 2) {
          segments.push([edges[crossed[0]], edges[crossed[1]]]);
        } else if (crossed.length === 4) {
          const finite = v.filter(isFinite);
          const centerInside = finite.length > 0 && finite.reduce((s, x) => s + x, 0) / finite.length < radius;
          if (centerInside === inside[0]) segments.push([edges[0], edges[1]], [edges[2], edges[3]]);
          else segments.push([edges[3], edges[0]], [edges[1], edges[2]]);
        }
      }
    }
    const byEdge = new Map();
    segments.forEach(([a, b], n) => {
      for (const k of [a, b]) { if (!byEdge.has(k)) byEdge.set(k, []); byEdge.get(k).push(n); }
    });
    const used = new Uint8Array(segments.length);
    const rings = [];
    for (let n = 0; n < segments.length; n++) {
      if (used[n]) continue;
      used[n] = 1;
      const start = segments[n][0];
      let current = segments[n][1];
      const keys = [start, current];
      while (current !== start) {
        const next = (byEdge.get(current) || []).find((s) => !used[s]);
        if (next === undefined) break;
        used[next] = 1;
        current = segments[next][0] === current ? segments[next][1] : segments[next][0];
        keys.push(current);
      }
      if (keys.length <= 3 || current !== start) continue;
      const ring = keys.map((k) => crossings.get(k));
      // Острівці туману всередині відкритої зони пропускаємо — там теж відкрито.
      const left = ring.reduce((a, b) => (b[0] < a[0] ? b : a));
      if (nearest(left[0] + step / 2, left[1]) < radius) rings.push(ring);
    }
    return rings;
  }

  function feature(radius, opacity) {
    const world = [[-180, -85], [180, -85], [180, 85], [-180, 85], [-180, -85]];
    const holes = openRings(radius).map((ring) => ring.map(([x, y]) => [x / mPerLon, y / M_PER_LAT]));
    return { type: 'Feature', properties: { opacity }, geometry: { type: 'Polygon', coordinates: [world, ...holes] } };
  }

  return {
    isOpen(lngLat) {
      init();
      return !centers.length || nearest(lngLat.lng * mPerLon, lngLat.lat * M_PER_LAT) < FOG_OPEN_RADIUS;
    },
    add(standard) {
      init();
      if (!centers.length || map.getSource('bruk-fog')) return;
      const layer = (id, slot) => ({
        id, type: 'fill', source: id, ...(standard ? { slot } : {}),
        paint: { 'fill-color': '#9C978F', 'fill-opacity': ['get', 'opacity'], 'fill-emissive-strength': 1 },
      });
      map.addSource('bruk-fog', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: FOG_LEVELS.map(([r, o]) => feature(r, o)) },
      });
      map.addLayer(layer('bruk-fog', 'middle'));
      if (standard) {
        map.addSource('bruk-fog-veil', { type: 'geojson', data: { type: 'FeatureCollection', features: [feature(...FOG_VEIL)] } });
        map.addLayer(layer('bruk-fog-veil', 'top'));
      }
    },
  };
})();

// MARK: - Тап по будинку (як Array.match у застосунку)

function onBuildingTap(feature, lngLat) {
  // Під туманом ще нічого не описано — тапи там нічого не відкривають.
  if (lngLat && !fog.isOpen(lngLat)) return;
  const featureId = feature.id != null ? String(feature.id) : null;
  let b = featureId
    ? (state.buildings.find((x) => state.resolved[x.id] === featureId)
      || state.buildings.find((x) => x.osmID === `way/${featureId}`))
    : null;
  // Запасний шлях для записів без osmID або з relation: чи лежить точка будинку
  // всередині тапнутого контуру. Сусіда за відстанню навмисно не беремо.
  if (!b && feature.geometry) {
    b = state.buildings.find((x) => geometryContains(feature.geometry, [x.longitude, x.latitude]));
  }
  if (b) {
    if (state.selectedId === b.id) closePanel();
    else showBuilding(b, { featureId });
  } else {
    showUnmapped(featureId, lngLat);
  }
}

function geometryContains(geometry, point) {
  const inRing = (ring) => {
    let inside = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [xi, yi] = ring[i];
      const [xj, yj] = ring[j];
      if ((yi > point[1]) !== (yj > point[1])
        && point[0] < ((xj - xi) * (point[1] - yi)) / (yj - yi) + xi) inside = !inside;
    }
    return inside;
  };
  const inPolygon = (rings) => inRing(rings[0]) && !rings.slice(1).some(inRing);
  if (geometry.type === 'Polygon') return inPolygon(geometry.coordinates);
  if (geometry.type === 'MultiPolygon') return geometry.coordinates.some(inPolygon);
  return false;
}

// MARK: - Картка

function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

/** Текст з екрануванням і клікабельними посиланнями (у джерелах бувають URL). */
function richText(s) {
  return esc(s).replace(/https?:\/\/[^\s<)»,;]+/g, (url) => `<a href="${url}" target="_blank" rel="noopener">${url}</a>`);
}

const SURVIVED = {
  yes: ['yes', '✦ Вижив 1941'],
  no: ['no', '✕ Знищений 1941'],
  partial: ['partial', '◑ Частково 1941'],
};

function displayDate(d) {
  const p = (d || '').split('-');
  return p.length === 3 ? `${p[2]}.${p[1]}.${p[0]}` : d;
}

// Форма «Розкажи історію будинку» на сайті (/story.html) з підставленою адресою.
function storyLink(place, lat, lng, kind = '') {
  const q = new URLSearchParams({ place, lat: lat.toFixed(6), lng: lng.toFixed(6) });
  if (kind) q.set('kind', kind);
  return `/story.html?${q}`;
}

// «Маєш краще фото?» під фото будинку — веде на ту саму форму в режимі фото.
function photoCta(b, hasPhotos) {
  const text = hasPhotos
    ? 'Маєш краще фото цього будинку? Поділися з нами, щоб усім було приємніше.'
    : 'У цього будинку ще немає фото. Маєш власне? Поділися з нами, щоб усім було приємніше.';
  return `<div class="photo-cta">
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 8h3l2-3h6l2 3h3a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1z" stroke="currentColor" stroke-width="1.75" stroke-linejoin="round"/><circle cx="12" cy="13.5" r="3.5" stroke="currentColor" stroke-width="1.75"/></svg>
    <p>${text}</p>
    <a class="btn ghost" href="${storyLink(b.address, b.latitude, b.longitude, 'photo')}">Надіслати фото</a>
  </div>`;
}

function researchBlock(place, lat, lng) {
  return `<div class="research">
    <h3>Ще досліджуємо</h3>
    <p>Знаєш щось про цей будинок? Хто його звів, хто тут жив, що тут було до війни? Розкажи нам! Найкращі історії з'являються саме так.</p>
    <a class="btn primary" href="${storyLink(place, lat, lng)}">Розповісти історію</a>
  </div>`;
}

function section(title, body, cls = '') {
  return `<div class="section ${cls}"><h3>${title}</h3><div class="text">${body}</div></div>`;
}

function renderBuilding(b) {
  const parts = [];
  const hasPhotos = !!(b.commonsCategory || (b.commonsFiles && b.commonsFiles.length));
  if (hasPhotos) parts.push('<div class="photo-skeleton" id="photos" aria-label="Завантажуємо фото"></div>', photoCta(b, true));

  const badges = [];
  const surv = SURVIVED[b.survived1941];
  if (surv) badges.push(`<span class="badge ${surv[0]}">${surv[1]}</span>`);
  if (b.warDamage && b.warDamage.length) badges.push('<span class="badge war">Пошкоджений війною</span>');
  if (b.heritageStatus) badges.push(`<span class="badge">${esc(b.heritageStatus)}</span>`);
  parts.push(`<div>
    <div class="eyebrow">${esc(b.address)}</div>
    ${b.currentName ? `<h1 class="title" id="panel-title">${esc(b.currentName)}</h1>` : `<h1 class="title" id="panel-title">${esc(b.address)}</h1>`}
    ${badges.length ? `<div class="badges">${badges.join('')}</div>` : ''}
  </div>`);
  parts.push('<hr class="div">');

  if (b.summary) {
    parts.push(`<div class="summary">${esc(b.summary)}</div>`);
  } else if (b.yearBuiltCurrent || b.yearBuiltOriginal || b.styleCurrent) {
    const rows = [];
    if (b.yearBuiltCurrent) rows.push(`<dt>Поточна будівля</dt><dd>${esc(b.yearBuiltCurrent)}${b.architectCurrent ? ` · ${esc(b.architectCurrent)}` : ''}</dd>`);
    if (b.yearBuiltOriginal) rows.push(`<dt>Попередня будівля</dt><dd>${esc(b.yearBuiltOriginal)}${b.architectOriginal ? ` · ${esc(b.architectOriginal)}` : ''}</dd>`);
    if (b.styleCurrent) rows.push(`<dt>Стиль</dt><dd>${esc(b.styleCurrent)}</dd>`);
    parts.push(`<div class="section"><h3>Хронологія</h3><dl class="facts-dl">${rows.join('')}</dl></div>`);
  }

  if (b.warDamage && b.warDamage.length) {
    const items = [...b.warDamage].sort((x, y) => x.date.localeCompare(y.date)).map((d) => `<div class="war-item">
      <div class="d">${esc(displayDate(d.date))}</div>
      <p>${esc(d.description)}</p>
      <div class="s">${d.url ? `<a href="${esc(d.url)}" target="_blank" rel="noopener">${esc(d.source)}</a>` : `<span class="small">${esc(d.source)}</span>`}</div>
    </div>`).join('');
    parts.push(`<div class="section war-block"><h3>Пошкодження війною</h3>${items}</div>`);
  }

  const story = b.shortText || b.keyFacts;
  if (story) parts.push(section('Історія', esc(story)));

  if (b.extendedText) {
    parts.push(b.shortText
      ? `<div class="section" id="extended"><button class="link-btn" id="more">Читати більше</button></div>`
      : `<div class="section"><div class="text">${esc(b.extendedText)}</div></div>`);
  }
  // Хто писав і редагував тексти (поле credits, tools/import_edits.py у bruk-app).
  if (b.credits && b.credits.length) {
    parts.push(`<div class="credits small">${b.credits.map((c) => `${esc(c.role)}: ${esc(c.name)}`).join(' · ')}</div>`);
  }
  if (b.notablePeople) parts.push(section('Відомі особистості', esc(b.notablePeople)));
  if (needsResearch(b)) parts.push(researchBlock(b.address, b.latitude, b.longitude));

  if (b.originalFunction || b.currentFunction) {
    const rows = [];
    if (b.originalFunction) rows.push(`<dt>Первісна функція</dt><dd>${esc(b.originalFunction)}</dd>`);
    if (b.currentFunction) rows.push(`<dt>Сьогодні</dt><dd>${esc(b.currentFunction)}</dd>`);
    parts.push(`<div class="section"><h3>Функції</h3><dl class="facts-dl">${rows.join('')}</dl></div>`);
  }
  if (!hasPhotos) parts.push(photoCta(b, false));
  if (b.sources) parts.push(section('Джерела', richText(b.sources), 'sources small'));

  return parts.join('');
}

function openPanel(html) {
  $('panel-body').innerHTML = html;
  $('panel-body').scrollTop = 0;
  $('panel').hidden = false;
  document.body.classList.add('panel-open');
  $('results').hidden = true;
}

function showBuilding(b, { fly = false, featureId = null } = {}) {
  state.selectedId = b.id;
  hideHint();
  openPanel(renderBuilding(b));
  const more = $('more');
  if (more) {
    more.addEventListener('click', () => {
      $('extended').innerHTML = `<div class="text">${esc(b.extendedText)}</div>`;
    });
  }
  if (map && map.isStyleLoaded()) markSelected(featureId ? { osmID: `way/${featureId}` } : b);
  if (fly) flyTo(b);
  loadPhotos(b);
  history.replaceState(null, '', `#b=${encodeURIComponent(b.id)}`);
}

function showUnmapped(featureId, lngLat) {
  state.selectedId = null;
  if (map && state.buildingsTarget) markSelected(featureId ? { osmID: `way/${featureId}` } : null);
  openPanel(`<div>
      <div class="eyebrow">Будинок без картки</div>
      <h1 class="title" id="panel-title">Його історію ще ніхто не розповів</h1>
    </div>
    ${researchBlock('', lngLat.lat, lngLat.lng)}`);
  history.replaceState(null, '', location.pathname);
}

function closePanel() {
  state.selectedId = null;
  $('panel').hidden = true;
  document.body.classList.remove('panel-open');
  if (map && map.isStyleLoaded()) markSelected(null);
  history.replaceState(null, '', location.pathname);
}

/** Камера трохи «позаду» будинку, щоб на екрані він був вище і картка його не закрила. */
function flyTo(b) {
  if (!map) return;
  const wide = window.matchMedia('(min-width: 900px)').matches;
  const metresBehind = wide ? 0 : 70;
  const rad = (CONFIG.bearing * Math.PI) / 180;
  const lat = b.latitude - (metresBehind * Math.cos(rad)) / 111320;
  const lng = b.longitude - (metresBehind * Math.sin(rad)) / (111320 * Math.cos((b.latitude * Math.PI) / 180));
  map.flyTo({
    center: [lng, lat], zoom: CONFIG.zoom, bearing: CONFIG.bearing, pitch: CONFIG.pitch,
    padding: wide ? { left: 450, top: 0, right: 0, bottom: 0 } : 0, essential: true,
  });
}

// MARK: - Фото з Wikimedia Commons (як fetchPhotos у застосунку)

const stripHTML = (s) => (s ? new DOMParser().parseFromString(s, 'text/html').body.textContent.trim() : '');

async function commonsQuery(source) {
  const params = new URLSearchParams({
    action: 'query', ...source, prop: 'imageinfo', iiprop: 'url|extmetadata',
    iiextmetadatafilter: 'Artist|LicenseShortName', iiurlwidth: '800', format: 'json', origin: '*',
  });
  try {
    const r = await fetch(`https://commons.wikimedia.org/w/api.php?${params}`);
    const json = await r.json();
    const pages = Object.values((json.query && json.query.pages) || {});
    return pages.map((p) => {
      const info = p.imageinfo && p.imageinfo[0];
      if (!info || !info.thumburl) return null;
      const meta = info.extmetadata || {};
      const credit = [stripHTML(meta.Artist && meta.Artist.value), stripHTML(meta.LicenseShortName && meta.LicenseShortName.value)]
        .filter(Boolean).join(' · ');
      return { url: info.thumburl, page: info.descriptionurl, title: p.title, credit };
    }).filter(Boolean).sort((a, b) => a.title.localeCompare(b.title));
  } catch (_) {
    return [];
  }
}

const categorySource = (category) => ({
  generator: 'categorymembers', gcmtitle: `Category:${category}`, gcmtype: 'file', gcmlimit: '6',
});

async function loadPhotos(b) {
  const slot = $('photos');
  if (!slot) return;
  let photos = [];
  if (b.commonsCategory) {
    photos = await commonsQuery(categorySource(b.commonsCategory));
    // Commons перейменовує «…, Kiev» на «…, Kyiv»; стара категорія після цього порожня.
    if (!photos.length && b.commonsCategory.endsWith('Kiev')) {
      photos = await commonsQuery(categorySource(`${b.commonsCategory.slice(0, -4)}Kyiv`));
    }
  } else if (b.commonsFiles && b.commonsFiles.length) {
    photos = await commonsQuery({ titles: b.commonsFiles.join('|') });
  }
  // Поки вантажилось, могли відкрити інший будинок.
  if (state.selectedId !== b.id || !document.body.contains(slot)) return;
  if (!photos.length) {
    slot.remove();
    // Фото не знайшлося — переносимо заклик униз, де він стоїть у будинків без фото.
    const cta = document.querySelector('.photo-cta');
    if (cta) {
      cta.querySelector('p').textContent = 'У цього будинку ще немає фото. Маєш власне? Поділися з нами, щоб усім було приємніше.';
      const sources = document.querySelector('#panel-body > .sources');
      if (sources) sources.before(cta); else $('panel-body').append(cta);
    }
    return;
  }
  const strip = document.createElement('div');
  strip.className = 'photos';
  // Автор і ліцензія обов'язкові за ліцензіями Commons.
  strip.innerHTML = photos.map((p) => `<figure>
      <img src="${esc(p.url)}" alt="${esc(b.address)}" loading="lazy">
      <figcaption><a href="${esc(p.page)}" target="_blank" rel="noopener">${esc(p.credit || 'Wikimedia Commons')}</a></figcaption>
    </figure>`).join('');
  slot.replaceWith(strip);
}

// MARK: - Бігучий рядок

function setupTicker() {
  const box = $('ticker');
  const facts = [...state.facts].sort(() => Math.random() - 0.5);
  if (!facts.length) { box.hidden = true; return; }

  const item = (f) => `<button class="ticker-item" data-address="${esc(f.address)}" aria-label="${esc(`${f.text} ${f.address}`)}">
      <span class="t">${esc(f.text)}</span><span class="a">${esc(f.address)}</span></button>`;
  box.addEventListener('click', (e) => {
    const btn = e.target.closest('.ticker-item');
    if (!btn) return;
    const b = state.buildings.find((x) => x.address === btn.dataset.address);
    if (b) showBuilding(b, { fly: true });
  });

  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    let i = 0;
    const show = () => { box.innerHTML = `<div class="ticker-track" style="padding:0 16px">${item(facts[i % facts.length])}</div>`; i += 1; };
    show();
    setInterval(show, 8000);
    return;
  }

  // Два однакові ряди поспіль: коли перший виїхав, другий стоїть на його місці.
  const row = facts.map((f) => `${item(f)}<span class="ticker-sep"></span>`).join('');
  box.innerHTML = `<div class="ticker-track">${row}${row}</div>`;
  const track = box.firstElementChild;
  const speed = 26; // px/с, як у застосунку
  let offset = 0;
  let last = performance.now();
  let paused = false;
  box.addEventListener('pointerenter', (e) => { if (e.pointerType === 'mouse') paused = true; });
  box.addEventListener('pointerleave', () => { paused = false; });
  const tick = (now) => {
    const dt = Math.min(now - last, 100) / 1000;
    last = now;
    const half = track.scrollWidth / 2;
    if (!paused && half > 0) {
      offset = (offset + speed * dt) % half;
      track.style.transform = `translateX(${-offset}px)`;
    }
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

// MARK: - Фільтри

const buildingsWord = (n) => {
  const m10 = n % 10;
  const m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return 'будинок';
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return 'будинки';
  return 'будинків';
};

function filterCounts() {
  const counts = new Map();
  for (const b of state.buildings) {
    if (!hasStory(b)) continue;
    const text = state.haystacks.get(b.id);
    for (const f of state.filters) {
      if (f.words.some((w) => text.includes(w))) counts.set(f.title, (counts.get(f.title) || 0) + 1);
    }
  }
  return counts;
}

function filteredCount() {
  return state.buildings.filter((b) => hasStory(b) && matchesFilters(b)).length;
}

function setupFilters() {
  const counts = filterCounts();
  const groups = [];
  for (const f of state.filters) {
    if (!counts.get(f.title)) continue;
    let g = groups.find((x) => x.name === f.group);
    if (!g) { g = { name: f.group, filters: [] }; groups.push(g); }
    g.filters.push(f);
  }
  const box = $('filter-groups');
  box.innerHTML = groups.map((g) => `<div class="group-title">${esc(g.name)}</div>
    <div class="chips">${g.filters.map((f) => `<button class="chip" data-title="${esc(f.title)}" aria-pressed="false">${esc(f.title)}<span class="n">${counts.get(f.title)}</span></button>`).join('')}</div>`).join('');

  const sync = () => {
    box.querySelectorAll('.chip').forEach((c) => c.setAttribute('aria-pressed', state.activeFilters.has(c.dataset.title)));
    const n = filteredCount();
    $('filters-done').textContent = state.activeFilters.size ? `Показати ${n} ${buildingsWord(n)}` : 'Показати всі';
    $('filter-dot').hidden = state.activeFilters.size === 0;
    $('btn-filters').setAttribute('aria-label', state.activeFilters.size ? 'Фільтри, увімкнено' : 'Фільтри');
    const pill = $('filter-pill');
    pill.hidden = state.activeFilters.size === 0;
    if (!pill.hidden) {
      const titles = state.filters.map((f) => f.title).filter((t) => state.activeFilters.has(t)).join(', ');
      $('filter-pill-open').textContent = `${titles} · ${n} ${buildingsWord(n)}`;
    }
    refreshHighlights();
  };
  box.addEventListener('click', (e) => {
    const chip = e.target.closest('.chip');
    if (!chip) return;
    const t = chip.dataset.title;
    if (state.activeFilters.has(t)) state.activeFilters.delete(t); else state.activeFilters.add(t);
    sync();
  });
  $('filters-reset').addEventListener('click', () => { state.activeFilters.clear(); sync(); });
  $('filters-done').addEventListener('click', () => closeSheet('sheet-filters'));
  $('btn-filters').addEventListener('click', () => openSheet('sheet-filters'));
  $('filter-pill-open').addEventListener('click', () => openSheet('sheet-filters'));
  $('filter-pill-clear').addEventListener('click', () => { state.activeFilters.clear(); sync(); });
  sync();
}

// MARK: - Шторки

function openSheet(id) {
  $(id).hidden = false;
}
function closeSheet(id) {
  $(id).hidden = true;
}
function setupSheets() {
  document.querySelectorAll('.sheet').forEach((sheet) => {
    sheet.addEventListener('click', (e) => {
      if (e.target === sheet || e.target.closest('[data-close]')) closeSheet(sheet.id);
    });
  });
  $('btn-about').addEventListener('click', () => openSheet('sheet-about'));
  $('panel-close').addEventListener('click', closePanel);
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    const open = [...document.querySelectorAll('.sheet')].find((s) => !s.hidden);
    if (open) closeSheet(open.id); else if (!$('panel').hidden) closePanel();
  });
}

// MARK: - «Ти тут»

function setupLocate() {
  const btn = $('btn-locate');
  btn.addEventListener('click', () => {
    if (state.watchId != null) {
      navigator.geolocation.clearWatch(state.watchId);
      state.watchId = null;
      if (state.youMarker) { state.youMarker.remove(); state.youMarker = null; }
      btn.classList.remove('on');
      return;
    }
    if (!navigator.geolocation) { showError('Цей браузер не вміє визначати, де ти.'); return; }
    btn.classList.add('on');
    let first = true;
    state.watchId = navigator.geolocation.watchPosition((pos) => {
      const lngLat = [pos.coords.longitude, pos.coords.latitude];
      if (!state.youMarker) {
        const el = document.createElement('div');
        el.className = 'you-dot';
        el.setAttribute('aria-label', 'Ти тут');
        state.youMarker = new mapboxgl.Marker({ element: el }).setLngLat(lngLat).addTo(map);
      } else {
        state.youMarker.setLngLat(lngLat);
      }
      if (first) {
        first = false;
        map.flyTo({ center: lngLat, zoom: CONFIG.zoom, bearing: CONFIG.bearing, pitch: CONFIG.pitch });
      }
    }, (err) => {
      navigator.geolocation.clearWatch(state.watchId);
      state.watchId = null;
      btn.classList.remove('on');
      showError(err.code === 1
        ? 'Не вдалося визначити, де ти: браузеру заборонено геолокацію. Дозволь її в налаштуваннях сайту.'
        : 'Не вдалося визначити, де ти. Спробуй ще раз на вулиці.');
    }, { enableHighAccuracy: true, maximumAge: 10000 });
  });
}

// MARK: - Підказка першого запуску

function storage(key, value) {
  try {
    if (value === undefined) return localStorage.getItem(key);
    localStorage.setItem(key, value);
  } catch (_) { /* приватний режим */ }
  return null;
}
function setupHint() {
  if (EMBED || storage('bruk.hasSeenTapHint')) return;
  $('hint').hidden = false;
  $('hint-close').addEventListener('click', hideHint);
}
function hideHint() {
  $('hint').hidden = true;
  storage('bruk.hasSeenTapHint', '1');
}

// MARK: - Плашка «нагороди й рівні — в застосунку»
// Акаунт і нагороди є лише в iOS-застосунку (рішення авторки 5.10.2026).

function setupAppPromo() {
  if (EMBED || storage('bruk.hasClosedAppPromo')) return;
  $('app-promo').hidden = false;
  $('app-promo-close').addEventListener('click', () => {
    $('app-promo').hidden = true;
    storage('bruk.hasClosedAppPromo', '1');
  });
}

// MARK: - Встановлення як застосунок

function setupInstall() {
  if ('serviceWorker' in navigator && location.protocol === 'https:') {
    navigator.serviceWorker.register('sw.js').catch(() => {});
  }
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    state.installPrompt = e;
    $('install-box').hidden = false;
  });
  $('install-btn').addEventListener('click', async () => {
    if (!state.installPrompt) return;
    state.installPrompt.prompt();
    await state.installPrompt.userChoice;
    state.installPrompt = null;
    $('install-box').hidden = true;
  });
}

// MARK: - Помилки

let errorTimer;
function showError(text) {
  const box = $('error');
  box.textContent = text;
  box.hidden = false;
  clearTimeout(errorTimer);
  errorTimer = setTimeout(() => { box.hidden = true; }, 6000);
}

// MARK: - Заставка

// Як у застосунку: літери складаються (4 × 110 мс), пауза 1100 мс — і заставка зникає.
const SPLASH_MIN_MS = 4 * 110 + 1100;
const splashStart = performance.now();

function hideSplash() {
  const sp = $('bruk-splash');
  if (!sp) return;
  const wait = Math.max(0, SPLASH_MIN_MS - (performance.now() - splashStart));
  setTimeout(() => {
    sp.classList.add('out');
    setTimeout(() => sp.remove(), 500);
  }, wait);
}

// MARK: - Старт

async function main() {
  setupSheets();
  setupInstall();
  try {
    await loadData();
  } catch (e) {
    hideSplash();
    showError('Не вдалося завантажити будинки. Перевір інтернет і онови сторінку.');
    return;
  }
  setupSearch();
  setupFilters();
  setupTicker();
  setupLocate();
  setupHint();
  setupAppPromo();
  try { setupMap(); } catch (e) { showError('Мапа не завантажилась. Онови сторінку.'); }

  // Посилання на будинок: bruk.city/map/#b=<id>
  const m = location.hash.match(/^#b=(.+)$/);
  const b = m && state.byId.get(decodeURIComponent(m[1]));
  if (b) showBuilding(b, { fly: true });
  hideSplash();
}

main();

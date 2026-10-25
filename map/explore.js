// BRUK — розділи веб-мапи: «Прогулянки» і «Біля мене» — чипи під пошуком.
// Логіка як у застосунку (bruk-app/Bruk/Walks.swift, BuildingLists.swift),
// вигляд — та сама біла картка, що й у будинку. Маршрути — data/walks.json: лише будинки
// з перевіреними текстами; адреса, якої немає в базі, просто пропускається.
// Підключається після app.js і користується його state, $, esc, showBuilding, map.
'use strict';

const NEARBY_RADIUS_M = 600;

const explore = {
  walks: [],
  stack: [],        // історія екранів у шторці: [{ view, arg }]
  walk: null,       // прогулянка на мапі: { walk, stops, index, markers }
};

// MARK: - Дрібниці

function plural(n, one, few, many) {
  const d = n % 10, h = n % 100;
  if (d === 1 && h !== 11) return one;
  if (d >= 2 && d <= 4 && (h < 12 || h > 14)) return few;
  return many;
}

function metres(a, b) {
  const k = 111320;
  const dy = (a.latitude - b.latitude) * k;
  const dx = (a.longitude - b.longitude) * k * Math.cos((a.latitude * Math.PI) / 180);
  return Math.hypot(dx, dy);
}

/** «350 м» або «1,4 км», як BrukDistance.label у застосунку. */
function distanceLabel(m) {
  if (m < 1000) return `${Math.round(m / 10) * 10} м`;
  return `${(Math.round(m / 100) / 10).toFixed(1).replace('.', ',')} км`;
}

/** Підпис у списках, як Building.listSubtitle. */
function listSubtitle(b) {
  const h = b.cardHeading || '';
  const i = h.indexOf(' — ');
  if (i >= 0) { const t = h.slice(i + 3); return t.charAt(0).toUpperCase() + t.slice(1); }
  return b.currentName || b.summary || (hasStory(b) ? 'Є історія' : 'Ще досліджуємо');
}

/** Перші речення тексту, не довше за limit символів (Building.teaser). */
function teaser(b, limit = 120) {
  const text = b.shortText || b.keyFacts;
  if (!text) return '';
  let out = '';
  for (const s of text.split('.')) {
    if (!s.trim()) continue;
    const next = `${out}${s.trim()}. `;
    if (next.length > limit) break;
    out = next;
  }
  return out ? out.trim() : `${text.slice(0, limit).trim()}…`;
}

// MARK: - Прогулянки: розрахунки (Walk у Walks.swift)

const byAddress = (address) => state.buildings.find((b) => b.address === address);
const walkStops = (w) => w.addresses.map(byAddress).filter(Boolean);
const walkLength = (stops) => stops.slice(1).reduce((sum, b, i) => sum + metres(stops[i], b), 0);
/** Пішки 4 км/год (вулиці не прямі — ×1,3) плюс по 5 хвилин біля кожного будинку. */
function walkMinutes(stops) {
  const walking = (walkLength(stops) * 1.3) / 4000 * 60;
  return (Math.floor((walking + stops.length * 5) / 5) + 1) * 5;
}
function walkMeta(stops) {
  const n = stops.length;
  return `${n} ${plural(n, 'адреса', 'адреси', 'адрес')} · ${distanceLabel(walkLength(stops))} · ${walkMinutes(stops)} хв`;
}

// MARK: - Шторка розділів

const ICONS = {
  walk: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="13" cy="4" r="2"/><path d="M10 21l2-6 3 3v4M8 12l2-4 4 1 2 4 3 1M10 8l-2 7"/></svg>',
  near: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 4 4 11l7 2 2 7z"/></svg>',
  back: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 5l-7 7 7 7"/></svg>',
  chevron: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 5l7 7-7 7"/></svg>',
};

const VIEWS = {
  walks: { title: 'Прогулянки', render: renderWalks },
  walk: { title: '', render: renderWalk },
  nearby: { title: 'Біля мене', render: renderNearby },
};

function openExplore(view, arg = null) {
  explore.stack = [];
  pushView(view, arg);
  openSheet('sheet-explore');
}

function closeExplore() {
  closeSheet('sheet-explore');
  syncChips();
}

/** Чип розділу, відкритого зараз, — червоний. */
function syncChips() {
  const open = !$('sheet-explore').hidden && explore.stack.length ? explore.stack[0].view : null;
  document.querySelectorAll('#explore-chips [data-chip]').forEach((c) => c.setAttribute('aria-pressed', String(c.dataset.chip === open)));
}

function pushView(view, arg = null) {
  explore.stack.push({ view, arg });
  drawView();
}

function popView() {
  explore.stack.pop();
  if (!explore.stack.length) { closeExplore(); return; }
  drawView();
}

function drawView() {
  const { view, arg } = explore.stack[explore.stack.length - 1];
  const v = VIEWS[view];
  const title = view === 'walk' ? arg.title : v.title;
  $('explore-title').textContent = title;
  $('explore-back').hidden = explore.stack.length < 2;
  $('sheet-explore').dataset.view = view;
  const body = $('explore-body');
  body.innerHTML = v.render(arg);
  $('explore-card').scrollTop = 0;
  if (view === 'nearby') locateForNearby();
  syncChips();
}

/** Маленька схема маршруту: зупинки в масштабі, з'єднані пунктиром. */
function miniRoute(stops, w = 72, h = 52, pad = 8) {
  const k = Math.cos((stops[0].latitude * Math.PI) / 180);
  const xs = stops.map((b) => b.longitude * k), ys = stops.map((b) => -b.latitude);
  const minX = Math.min(...xs), minY = Math.min(...ys);
  const span = Math.max(Math.max(...xs) - minX, Math.max(...ys) - minY) || 1;
  const sc = Math.min(w, h) - pad * 2;
  const offX = (w - ((Math.max(...xs) - minX) / span) * sc) / 2;
  const offY = (h - ((Math.max(...ys) - minY) / span) * sc) / 2;
  const pts = stops.map((_, i) => [offX + ((xs[i] - minX) / span) * sc, offY + ((ys[i] - minY) / span) * sc].map((v) => v.toFixed(1)));
  return `<svg class="mini-route" viewBox="0 0 ${w} ${h}" aria-hidden="true">
    <polyline points="${pts.map((p) => p.join(',')).join(' ')}"/>
    ${pts.map(([x, y]) => `<circle cx="${x}" cy="${y}" r="3"/>`).join('')}</svg>`;
}

function renderWalks() {
  const rows = explore.walks.map((w, i) => {
    const stops = walkStops(w);
    if (!stops.length) return '';
    return `<button class="walk-row" data-walk="${i}">
      ${miniRoute(stops)}
      <span class="row-main"><b>${esc(w.title)}</b><span class="sub">${walkMeta(stops)}</span>
      ${w.figures.length ? `<span class="walk-figures">${w.figures.map((f) => esc(f.name)).join(' · ')}</span>` : ''}</span>
    </button>`;
  }).join('');
  return `<p class="muted lead">Готові маршрути на годину пішки. Кожна зупинка: будинок з перевіреною історією.</p>
    <div class="walk-rows">${rows}</div>`;
}

function renderWalk(w) {
  const stops = walkStops(w);
  const figures = w.figures.filter((f) => byAddress(f.address)).map((f) => `<button class="row" data-open="${esc(byAddress(f.address).id)}">
      <span class="initial">${esc(f.name.charAt(0))}</span>
      <span class="row-main"><b>${esc(f.name)}</b><span class="sub">${esc(f.address)}</span></span>
      <span class="chev">${ICONS.chevron}</span>
    </button>`).join('');
  const rows = stops.map((b, i) => `<button class="row" data-open="${esc(b.id)}">
      <span class="stop-pin">${i + 1}</span>
      <span class="row-main"><b>${esc(b.address)}</b><span class="sub clamp">${esc(listSubtitle(b))}</span></span>
    </button>`).join('');
  return `<div class="walk-head">
      ${miniRoute(stops, 320, 120, 14)}
      <div class="walk-meta">${ICONS.walk}${walkMeta(stops)}</div>
      <p>${esc(w.intro)}</p>
    </div>
    ${figures ? `<h3 class="list-title">Постаті маршруту</h3><div class="rows">${figures}</div>
      <p class="muted small foot">Торкнися імені, і відкриється будинок, де ця людина жила, працювала чи бувала.</p>` : ''}
    <h3 class="list-title">Зупинки</h3><div class="rows">${rows}</div>
    <div class="sticky-cta"><button class="btn primary wide" data-start>Почати прогулянку</button></div>`;
}

// MARK: - Біля мене (NearbyView)

function renderNearby() {
  return `<div id="nearby-state" class="empty-state">
    <div class="spinner" aria-hidden="true"></div><p class="muted">Шукаємо, де ти…</p></div>`;
}

function locateForNearby() {
  const box = () => $('nearby-state');
  const fail = (title, text) => {
    if (!box()) return;
    box().innerHTML = `<div class="empty-icon">${ICONS.near}</div><b>${title}</b><p class="muted">${text}</p>
      <button class="btn ghost" data-retry>Спробувати ще раз</button>`;
  };
  if (!navigator.geolocation) {
    fail('Браузер не вміє визначати, де ти', 'Мапа й пошук працюють і так.');
    return;
  }
  navigator.geolocation.getCurrentPosition((pos) => {
    if (!box()) return;
    const here = { latitude: pos.coords.latitude, longitude: pos.coords.longitude };
    const near = state.buildings.filter(hasStory)
      .map((b) => ({ b, d: metres(here, b) }))
      .filter((x) => x.d <= NEARBY_RADIUS_M)
      .sort((x, y) => x.d - y.d)
      .slice(0, 30);
    if (!near.length) {
      box().outerHTML = `<div class="empty-state"><div class="empty-icon">${ICONS.near}</div><b>Поруч поки нічого</b>
        <p class="muted">У радіусі ${NEARBY_RADIUS_M} м немає будинків з історією. BRUK зараз описує центр Києва: від Подолу й Хрещатика до Золотих воріт, Липок і Великої Васильківської.</p></div>`;
      return;
    }
    box().outerHTML = `<h3 class="list-title">Будинки з історією в радіусі ${NEARBY_RADIUS_M} м</h3>
      <div class="rows">${near.map(({ b, d }) => buildingRow(b, distanceLabel(d))).join('')}</div>`;
  }, (err) => {
    if (err.code === 1) fail('Геолокацію вимкнено', 'Без неї ми не покажемо, що поруч. Дозволь її в налаштуваннях сайту, а мапа й пошук працюють і так.');
    else fail('Не вдалося визначити, де ти', 'Спробуй ще раз, краще на вулиці.');
  }, { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 });
}

function buildingRow(b, detail = '', cls = '') {
  return `<button class="row ${cls}" data-open="${esc(b.id)}">
    <span class="row-main"><b>${esc(b.address)}</b><span class="sub clamp">${esc(listSubtitle(b))}</span></span>
    ${detail ? `<span class="detail">${esc(detail)}</span>` : ''}
  </button>`;
}

// MARK: - Прогулянка на мапі (WalkPanel, WalkStopPin)

function startWalk(w) {
  const stops = walkStops(w);
  if (!stops.length || !map) return;
  stopWalk();
  closeExplore();
  closePanel();
  explore.walk = { walk: w, stops, index: 0, markers: [] };
  document.body.classList.add('walking');
  // Лінії між зупинками на мапі немає — лише номерні піни (рішення авторки 16.10.2026).
  explore.walk.markers = stops.map((b, i) => {
    const el = document.createElement('button');
    el.type = 'button';
    el.className = 'walk-pin';
    el.setAttribute('aria-label', `Зупинка ${i + 1}`);
    el.innerHTML = `<span class="head">${i + 1}</span><span class="stick"></span>`;
    el.addEventListener('click', (e) => { e.stopPropagation(); goToStop(i); });
    return new mapboxgl.Marker({ element: el, anchor: 'bottom' }).setLngLat([b.longitude, b.latitude]).addTo(map);
  });
  $('walk-ui').hidden = false;
  history.replaceState(null, '', `#walk=${encodeURIComponent(w.id)}`);
  goToStop(0);
}

function goToStop(i) {
  const wk = explore.walk;
  if (!wk) return;
  wk.index = Math.max(0, Math.min(i, wk.stops.length - 1));
  const b = wk.stops[wk.index];
  wk.markers.forEach((m, j) => m.getElement().classList.toggle('current', j === wk.index));
  let label = `Зупинка ${wk.index + 1}`;
  if (wk.index > 0) label += ` · ${distanceLabel(metres(wk.stops[wk.index - 1], b))}`;
  $('walk-progress-title').textContent = `${wk.walk.title} · зупинка ${wk.index + 1} з ${wk.stops.length}`;
  $('walk-progress-bar').style.width = `${((wk.index + 1) / wk.stops.length) * 100}%`;
  $('walk-stop-label').textContent = label;
  $('walk-stop-title').textContent = b.cardHeading || b.address;
  $('walk-stop-teaser').textContent = teaser(b);
  $('walk-prev').disabled = wk.index === 0;
  $('walk-next').disabled = wk.index === wk.stops.length - 1;
  if (!$('panel').hidden) showBuilding(b);
  flyTo(b);
  // Аудіогід (audio.js): у його режимі нова зупинка звучить сама.
  if (typeof onWalkStop === 'function') onWalkStop();
}

function overviewWalk() {
  const wk = explore.walk;
  if (!wk) return;
  const bounds = new mapboxgl.LngLatBounds();
  wk.stops.forEach((b) => bounds.extend([b.longitude, b.latitude]));
  const wide = window.matchMedia('(min-width: 900px)').matches;
  map.fitBounds(bounds, {
    padding: wide ? { top: 120, bottom: 240, left: 120, right: 120 } : { top: 110, bottom: 260, left: 40, right: 40 },
    pitch: 45, bearing: CONFIG.bearing, maxZoom: 17,
  });
}

function stopWalk() {
  const wk = explore.walk;
  if (!wk) return;
  wk.markers.forEach((m) => m.remove());
  explore.walk = null;
  document.body.classList.remove('walking');
  $('walk-ui').hidden = true;
  if (location.hash.startsWith('#walk=')) history.replaceState(null, '', location.pathname);
}

// MARK: - Старт

async function setupExplore() {
  try {
    const r = await fetch('data/walks.json', { cache: 'no-cache' });
    explore.walks = r.ok ? await r.json() : [];
  } catch (e) {
    console.warn(e);
  }
  $('explore-chips').addEventListener('click', (e) => {
    const chip = e.target.closest('[data-chip]');
    if (!chip) return;
    if (chip.getAttribute('aria-pressed') === 'true') closeExplore();
    else { closePanel(); openExplore(chip.dataset.chip); }
  });
  $('explore-close').addEventListener('click', closeExplore);
  // Шторку закривають і тап повз неї, і Esc (app.js) — тоді гасимо чип.
  // Тап по будинку на мапі відкриває його картку — шторка розділу ховається.
  new MutationObserver(() => { if (!$('panel').hidden && !$('sheet-explore').hidden) closeExplore(); })
    .observe($('panel'), { attributes: true, attributeFilter: ['hidden'] });
  new MutationObserver(syncChips).observe($('sheet-explore'), { attributes: true, attributeFilter: ['hidden'] });
  $('explore-back').addEventListener('click', popView);
  $('explore-body').addEventListener('click', (e) => {
    const el = e.target.closest('[data-walk],[data-open],[data-start],[data-retry]');
    if (!el) return;
    if (el.dataset.walk) pushView('walk', explore.walks[+el.dataset.walk]);
    else if (el.hasAttribute('data-start')) startWalk(explore.stack[explore.stack.length - 1].arg);
    else if (el.hasAttribute('data-retry')) drawView();
    else {
      const b = state.byId.get(el.dataset.open);
      if (!b) return;
      closeExplore();
      showBuilding(b, { fly: true });
    }
  });
  $('walk-close').addEventListener('click', stopWalk);
  $('walk-prev').addEventListener('click', () => goToStop(explore.walk.index - 1));
  $('walk-next').addEventListener('click', () => goToStop(explore.walk.index + 1));
  $('walk-overview').addEventListener('click', overviewWalk);
  const openCard = () => showBuilding(explore.walk.stops[explore.walk.index]);
  $('walk-card').addEventListener('click', openCard);
  $('walk-open').addEventListener('click', openCard);

  // Посилання: bruk.city/map/#walk=<id>, #walks, #nearby
  const h = location.hash;
  const m = h.match(/^#walk=(.+)$/);
  const w = m && explore.walks.find((x) => x.id === decodeURIComponent(m[1]));
  if (w) {
    const go = () => startWalk(w);
    if (map && map.isStyleLoaded()) go(); else if (map) map.once('load', go);
  } else if (['#walks', '#nearby'].includes(h)) {
    openExplore(h.slice(1));
  }
}

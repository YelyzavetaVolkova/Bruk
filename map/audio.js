// BRUK — аудіогід (спроба, 25.10.2026). Якщо будинок озвучено в ElevenLabs
// (tools/audio_elevenlabs.py → data/audio.json, audio/*.mp3), грає запис. Інакше картку читає
// голос самого пристрою (Web Speech API): український є на iPhone, Mac (Леся), в Android
// з Google TTS і в Edge; де його немає й запису теж, кнопки «Слухати» не видно.
// У прогулянці — режим аудіогіда: зупинка звучить сама, а коли ти підходиш
// до наступної (геолокація), гід переходить до неї.
// Підключається після app.js і explore.js, користується їхніми esc, state, explore, goToStop.
'use strict';

const ARRIVE_M = 35;        // ближче — вважаємо, що ти вже біля наступної зупинки
const CHARS_PER_MIN = 800;  // приблизна швидкість голосу, для «≈ 2 хв»

const guide = {
  voice: null,
  key: null,          // що звучить: 'b:<id>'
  parts: [],          // фрагменти: { url } — mp3, { text } — речення для голосу пристрою
  title: '',
  index: 0,
  state: 'idle',      // idle | playing | paused
  gen: 0,             // захист від onend скасованих фраз (Chrome кличе його й після cancel)
  onFinish: null,
};

// MARK: - Голос

function pickVoice() {
  if (!('speechSynthesis' in window)) return;
  const uk = speechSynthesis.getVoices().filter((v) => /^uk/i.test(v.lang));
  guide.voice = uk.find((v) => /natural|enhanced|premium/i.test(v.name)) || uk.find((v) => v.localService) || uk[0] || null;
  document.body.classList.toggle('can-listen', !!guide.voice);
}

// MARK: - Текст для читання вголос

const ROMAN = { I: 1, V: 5, X: 10, L: 50 };
const ORDINAL = ['', 'перш', 'друг', 'трет', 'четверт', "п'ят", 'шост', 'сьом', 'восьм', "дев'ят", 'десят',
  'одинадцят', 'дванадцят', 'тринадцят', 'чотирнадцят', "п'ятнадцят", 'шістнадцят', 'сімнадцят', 'вісімнадцят',
  "дев'ятнадцят", 'двадцят', 'двадцять перш'];

function romanValue(s) {
  const d = [...s.replace(/Х/g, 'X').replace(/І/g, 'I')].map((c) => ROMAN[c]);
  return d.reduce((sum, v, i) => sum + (v < (d[i + 1] || 0) ? -v : v), 0);
}

/** 19 → «дев'ятнадцятого», а перед «столітті» — «дев'ятнадцятому». */
function ordinal(n, locative) {
  const stem = ORDINAL[n];
  if (!stem) return null;
  const soft = n === 3; // третього / третьому
  return stem + (locative ? (soft ? 'ьому' : 'ому') : (soft ? 'ього' : 'ого'));
}

const AFTER_ROMAN = /^(\s*(?:[—–-]|і|й|та)\s*[IVXІХ]{1,5})?\s+(ст\.|століт|сторіч)/;

/** Римські цифри століть словами: X–XXI завжди, менші — лише перед «ст.»/«століття». */
function romanCenturies(text) {
  return text.replace(/(^|[\s(«—–-])([IVXІХ]{1,5})(?=$|[\s.,;:)»—–-])/g, (m, pre, r, offset, all) => {
    const rest = all.slice(offset + m.length);
    const n = romanValue(r);
    if (!AFTER_ROMAN.test(rest) && !(n >= 10 && n <= 21)) return m;
    const word = ordinal(n, /^(\s*(?:[—–-]|і|й|та)\s*[IVXІХ]{1,5})?\s+століт+і/.test(rest));
    return word ? pre + word : m;
  });
}

/** Скорочення: «наприкінці XIX ст. Тоді…» → «…століття. Тоді…», крапку речення не губимо. */
function expand(text, short, full) {
  const re = new RegExp(`(^|\\s)${short.replace('.', '\\.')}(?=(\\s+[А-ЯІЇЄҐ«])|$)`, 'g');
  return text.replace(re, `$1${full}.`).replace(new RegExp(`(^|\\s)${short.replace('.', '\\.')}`, 'g'), `$1${full}`);
}

/** Скорочення й римські цифри — так, як їх сказала б людина. */
function spoken(text) {
  let t = String(text || '')
    .replace(/(\d)\.(\d)/g, '$1\u2024$2') // дати 19.10.2026 не різати на речення
    .replace(/(\d)\s*рр\.(?=\s+[А-ЯІЇЄҐ«]|$)/g, '$1 роках.')
    .replace(/(\d)\s*рр\./g, '$1 роках')
    .replace(/(\d{4})\s*р\.(?=\s+[А-ЯІЇЄҐ«]|$)/g, '$1 року.')
    .replace(/(\d{4})\s*р\./g, '$1 року');
  t = romanCenturies(t);
  t = expand(t, 'ст.', 'століття');
  // Ці скорочення стоять перед назвою, кінцем речення вони не бувають.
  [['вул.', 'вулиця'], ['пл.', 'площа'], ['кв.', 'квартира'], ['арх.', 'архітектор'], ['інж.', 'інженер'], ['просп.', 'проспект'], ['буд.', 'будинок'], ['св.', 'святого'], ['тис.', 'тисяч']]
    .forEach(([short, full]) => { t = t.split(` ${short}`).join(` ${full}`); if (t.startsWith(short)) t = full + t.slice(short.length); });
  return t.replace(/№\s*/g, 'номер ').replace(/\s*[–—]\s*/g, ' — ');
}

const MAX_PART = 220;

/** Задовге речення ділимо по «;», « — » чи комі: голоси Google у Chrome уриваються секунд за 15. */
function shorten(s) {
  if (s.length <= MAX_PART) return [s];
  const out = [];
  let buf = '';
  const bits = s.split(/([;,:]\s+|\s+(?=— ))/); // без lookbehind: старий Safari його не знає
  for (let i = 0; i < bits.length; i += 2) {
    const piece = bits[i] + (bits[i + 1] || '').trim();
    if (buf && (buf + piece).length > MAX_PART) { out.push(buf.trim()); buf = ''; }
    buf += `${piece} `;
  }
  if (buf.trim()) out.push(buf.trim());
  return out;
}

/** Ріжемо на речення: Chrome обриває довгі фрази, а з реченнями легше ставити паузу. */
function sentences(text) {
  const pieces = text.match(/[^.!?…\n]+(?:[.!?…]+|\n+|$)/g) || [];
  const out = [];
  let buf = '';
  for (const piece of pieces) {
    buf += piece;
    const t = buf.trim();
    // «В. Гопкало», «А.-Ф. Краусс», «ім. Шевченка», «кв. 5» — це ще не кінець речення.
    if (/(^|[\s(«.-])([А-ЯІЇЄҐA-Z]|ім|о|т|див|кв|с)\.$/.test(t)) continue;
    buf = '';
    if (!t) continue;
    // «».», «)» — хвіст попереднього речення, а не нове.
    if (out.length && !/[A-Za-zА-ЯІЇЄҐа-яіїєґ0-9]/.test(t)) out[out.length - 1] += t;
    else out.push(t);
  }
  if (buf.trim()) out.push(buf.trim());
  return out.flatMap(shorten).map((x) => x.replace(/․/g, '.'));
}

// MARK: - Озвучка ElevenLabs (tools/audio_elevenlabs.py → data/audio.json, audio/*.mp3)

const files = { buildings: {}, walks: {} };

const buildingFile = (b) => files.buildings[b.id];
const canSpeak = () => !!guide.voice;

/** Фрагменти для програвання: { url } — готовий mp3, { text } — речення для голосу пристрою. */
const said = (text) => (canSpeak() ? sentences(spoken(text)).map((t) => ({ text: t })) : []);

function buildingScript(b, { before = '', after = null } = {}) {
  const file = buildingFile(b);
  // Є запис — тоді «Зупинка 2 з 5» не кажемо: інший голос посеред гарного запису звучить чужо.
  const main = file ? [{ url: file.file }] : said([before, b.currentName ? `${b.address}. ${b.currentName}.` : `${b.address}.`,
    [b.shortText || b.keyFacts, b.extendedText].filter(Boolean).join('\n')].filter(Boolean).join('\n'));
  if (!main.length) return [];
  return [...main, ...(after ? (after.url ? [after] : said(after.text)) : [])];
}

function listenMinutes(b) {
  const file = buildingFile(b);
  if (file && file.seconds) return Math.max(1, Math.round(file.seconds / 60));
  const len = (b.shortText || b.keyFacts || '').length + (b.extendedText || '').length;
  return Math.max(1, Math.round(len / CHARS_PER_MIN));
}

const canListen = (b) => !!(b.shortText || b.keyFacts) && (!!buildingFile(b) || canSpeak());

// MARK: - Програвання

const player = new Audio();
player.preload = 'auto';

function playCurrent() {
  const gen = ++guide.gen;
  const seg = guide.parts[guide.index];
  const next = () => {
    if (gen !== guide.gen) return;
    guide.index += 1;
    if (guide.index < guide.parts.length) playCurrent();
    else finish();
    syncListen();
  };
  if (seg.url) {
    const url = new URL(seg.url, location.href).href;
    if (player.src !== url) player.src = url; // той самий файл — продовжуємо з паузи
    player.onended = next;
    player.onerror = () => { if (gen === guide.gen) { console.warn('audio guide: файл не відкрився', url); next(); } };
    player.play().catch((e) => {
      if (gen !== guide.gen) return;
      console.warn('audio guide', e); // напр. iPhone не дав грати без дотику — чекаємо на кнопку
      guide.state = 'paused';
      syncListen();
    });
    setMediaSession();
    return;
  }
  const u = new SpeechSynthesisUtterance(seg.text);
  u.voice = guide.voice;
  u.lang = guide.voice.lang;
  u.rate = 0.95;
  u.onend = next;
  u.onerror = (e) => {
    if (gen !== guide.gen || e.error === 'interrupted' || e.error === 'canceled') return;
    console.warn('audio guide', e.error);
    stopListening();
  };
  speechSynthesis.speak(u);
}

function silence() {
  guide.gen += 1;
  if ('speechSynthesis' in window) speechSynthesis.cancel();
  player.pause();
}

function playParts(key, parts, onFinish = null, title = '') {
  if (!parts.length) return;
  silence();
  player.removeAttribute('src'); // новий запис — з початку
  Object.assign(guide, { key, parts, index: 0, state: 'playing', onFinish, title });
  // Safari іноді губить фразу, сказану одразу після cancel; mp3 запускаємо одразу — iPhone пускає звук лише в дотику.
  if (parts[0].url) playCurrent();
  else setTimeout(() => { if (guide.key === key && guide.state === 'playing') playCurrent(); }, 60);
  syncListen();
}

// Пауза голосу пристрою — через cancel: pause() в Android Chrome не працює, тож продовжимо з речення.
// mp3 ставимо на паузу як є й продовжуємо з того самого місця.
function pauseListening() {
  silence();
  guide.state = 'paused';
  syncListen();
}

function resumeListening() {
  guide.state = 'playing';
  playCurrent();
  syncListen();
}

function stopListening() {
  silence();
  Object.assign(guide, { key: null, parts: [], index: 0, state: 'idle', onFinish: null, title: '' });
  syncListen();
}

function finish() {
  const done = guide.onFinish;
  Object.assign(guide, { key: null, parts: [], index: 0, state: 'idle', onFinish: null, title: '' });
  if (done) done();
}

function toggleListening(key, makeParts, onFinish, title) {
  if (guide.key === key && guide.state === 'playing') pauseListening();
  else if (guide.key === key && guide.state === 'paused') resumeListening();
  else playParts(key, makeParts(), onFinish, title);
}

/** Назва й кнопки на заблокованому екрані телефона, поки грає запис. */
function setMediaSession() {
  if (!('mediaSession' in navigator) || !window.MediaMetadata) return;
  navigator.mediaSession.metadata = new MediaMetadata({ title: guide.title || 'BRUK', artist: 'BRUK · аудіогід' });
  navigator.mediaSession.setActionHandler('play', () => { if (guide.state === 'paused') resumeListening(); });
  navigator.mediaSession.setActionHandler('pause', () => { if (guide.state === 'playing') pauseListening(); });
}

// MARK: - Кнопки

const PLAY_SVG = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5.5v13l10.5-6.5z"/></svg>';
const PAUSE_SVG = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 5h3.5v14H7zM13.5 5H17v14h-3.5z"/></svg>';

/** Кнопка «Слухати» для картки (renderBuilding у app.js). Без запису її видно лише з українським голосом (.can-listen). */
function listenButton(b) {
  if (!(b.shortText || b.keyFacts)) return '';
  return `<button class="listen${buildingFile(b) ? ' has-file' : ''}" type="button" data-listen="b:${esc(b.id)}" data-minutes="${listenMinutes(b)}">
    <span class="listen-icon"></span><span class="listen-label"></span><span class="listen-bar"><i></i></span>
  </button>`;
}

/** Після showBuilding: оживляємо кнопку картки. */
function bindListen(b) {
  const btn = document.querySelector('#panel-body [data-listen]');
  // Інший будинок — історія попереднього замовкає (у прогулянці гід керує сам).
  if (guide.key && guide.key !== `b:${b.id}` && !walkAudioOn()) stopListening();
  if (!btn) return;
  btn.addEventListener('click', () => toggleListening(`b:${b.id}`, () => buildingScript(b), null, b.cardHeading || b.address));
  syncListen();
}

function progress() {
  if (!guide.parts.length) return 0;
  const seg = guide.parts[guide.index];
  const inside = seg && seg.url && player.duration ? player.currentTime / player.duration : 0;
  return Math.min(1, (guide.index + inside) / guide.parts.length);
}

function syncListen() {
  document.querySelectorAll('[data-listen]').forEach((btn) => {
    const mine = guide.key === btn.dataset.listen;
    const playing = mine && guide.state === 'playing';
    btn.classList.toggle('playing', playing);
    btn.classList.toggle('active', mine);
    btn.querySelector('.listen-icon').innerHTML = playing ? PAUSE_SVG : PLAY_SVG;
    const label = btn.querySelector('.listen-label');
    if (label) {
      label.textContent = playing ? 'Пауза' : mine ? 'Продовжити' : `Слухати історію · ${btn.dataset.minutes} хв`;
    }
    btn.setAttribute('aria-label', playing ? 'Пауза' : mine ? 'Продовжити слухати' : 'Слухати історію');
    const bar = btn.querySelector('.listen-bar i');
    if (bar) bar.style.width = mine ? `${progress() * 100}%` : '0';
  });
  syncWalkAudio();
}

// MARK: - Аудіогід у прогулянці

const walkAudio = { on: false, watch: null, here: null };

const walkAudioOn = () => !!(walkAudio.on && typeof explore !== 'undefined' && explore.walk);

/** «350 метрів», «1,4 кілометра» (кругляємо до десятків — тож завжди «метрів»). */
function spokenDistance(m) {
  if (m < 1000) return `${Math.max(10, Math.round(m / 10) * 10)} метрів`;
  return `${(Math.round(m / 100) / 10).toFixed(1).replace('.', ',')} кілометра`;
}

function stopScript(wk, i) {
  const b = wk.stops[i];
  const next = wk.stops[i + 1];
  // Хвіст «Далі — …» — той самий текст, що озвучує tools/audio_elevenlabs.py (next_text).
  const clip = (files.walks[wk.walk.id] || [])[i];
  const text = next
    ? `Далі — зупинка ${i + 2}: ${next.address}, приблизно ${spokenDistance(metres(b, next))}. Коли дійдеш, я продовжу.`
    : `Це остання зупинка прогулянки «${wk.walk.title}». Дякуємо, що гуляєш з BRUK.`;
  return buildingScript(b, { before: `Зупинка ${i + 1} з ${wk.stops.length}.`, after: clip ? { url: clip.file } : { text } });
}

function walkHasAudio(wk) {
  return wk.stops.some(canListen);
}

function playWalkStop() {
  const wk = explore.walk;
  if (!wk) return;
  const i = wk.index;
  const b = wk.stops[i];
  playParts(`b:${b.id}`, stopScript(wk, i), () => { syncListen(); checkArrival(); }, b.cardHeading || b.address);
}

function startWalkAudio() {
  walkAudio.on = true;
  playWalkStop();
  if (navigator.geolocation && walkAudio.watch == null) {
    walkAudio.watch = navigator.geolocation.watchPosition((pos) => {
      walkAudio.here = { latitude: pos.coords.latitude, longitude: pos.coords.longitude, accuracy: pos.coords.accuracy };
      checkArrival();
    }, () => { /* без геолокації гід усе одно працює: «далі» — стрілкою */ }, { enableHighAccuracy: true, maximumAge: 5000 });
  }
}

function stopWalkAudio() {
  walkAudio.on = false;
  if (walkAudio.watch != null) navigator.geolocation.clearWatch(walkAudio.watch);
  walkAudio.watch = null;
  walkAudio.here = null;
  stopListening();
}

/** Дійшла до наступної зупинки, а попередня вже дозвучала, — переходимо. */
function checkArrival() {
  const wk = walkAudioOn() && explore.walk;
  if (!wk || !walkAudio.here || guide.state !== 'idle') return;
  const next = wk.stops[wk.index + 1];
  if (!next) return;
  if (metres(walkAudio.here, next) <= ARRIVE_M + Math.min(walkAudio.here.accuracy || 0, 25)) goToStop(wk.index + 1);
}

/** Викликається з goToStop: у режимі гіда нова зупинка звучить сама. */
function onWalkStop() {
  if (walkAudioOn()) playWalkStop();
  else syncWalkAudio();
}

function syncWalkAudio() {
  const btn = document.getElementById('walk-audio');
  if (!btn) return;
  const wk = typeof explore !== 'undefined' && explore.walk;
  document.body.classList.toggle('walk-has-audio', !!(wk && walkHasAudio(wk)));
  const mine = wk && guide.key === `b:${wk.stops[wk.index].id}`;
  const playing = mine && guide.state === 'playing';
  btn.classList.toggle('on', walkAudio.on);
  btn.classList.toggle('playing', !!playing);
  btn.innerHTML = playing ? PAUSE_SVG : PLAY_SVG;
  btn.setAttribute('aria-label', playing ? 'Пауза' : walkAudio.on ? 'Слухати зупинку' : 'Увімкнути аудіогід');
  const hint = document.getElementById('walk-audio-hint');
  if (hint) hint.hidden = !walkAudio.on || !!playing || guide.state === 'paused';
}

// MARK: - Старт

async function loadAudioFiles() {
  try {
    const r = await fetch('data/audio.json', { cache: 'no-cache' });
    if (!r.ok) return;
    const data = await r.json();
    files.buildings = data.buildings || {};
    files.walks = data.walks || {};
  } catch (e) { /* записів ще немає — читає голос пристрою */ }
}

function setupAudio() {
  if ('speechSynthesis' in window) {
    pickVoice();
    speechSynthesis.addEventListener?.('voiceschanged', () => { pickVoice(); syncWalkAudio(); });
  }
  loadAudioFiles().then(syncWalkAudio);
  player.addEventListener('timeupdate', () => {
    const bar = guide.key && document.querySelector(`[data-listen="${CSS.escape(guide.key)}"] .listen-bar i`);
    if (bar) bar.style.width = `${progress() * 100}%`;
  });
  // Закрили картку — історія замовкає (крім прогулянки з гідом).
  new MutationObserver(() => { if ($('panel').hidden && !walkAudioOn() && guide.key) stopListening(); })
    .observe($('panel'), { attributes: true, attributeFilter: ['hidden'] });
  // Закрили прогулянку — гід теж.
  new MutationObserver(() => { if ($('walk-ui').hidden && walkAudio.on) stopWalkAudio(); })
    .observe($('walk-ui'), { attributes: true, attributeFilter: ['hidden'] });
  $('walk-audio').addEventListener('click', () => {
    const wk = explore.walk;
    if (!wk) return;
    const key = `b:${wk.stops[wk.index].id}`;
    if (!walkAudio.on) startWalkAudio();
    else if (guide.key === key && guide.state === 'playing') pauseListening();
    else if (guide.key === key && guide.state === 'paused') resumeListening();
    else playWalkStop();
  });
  // Сторінку закрили — замовкаємо. (mp3 на заблокованому екрані грає далі: pagehide тоді не настає.)
  window.addEventListener('pagehide', stopListening);
}

setupAudio();

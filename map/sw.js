// Сервіс-воркер BRUK: щоб мапу можна було встановити на телефон
// і щоб оболонка з даними відкривалась навіть зі слабким інтернетом.
// Дані будинків завжди беремо з мережі, кеш — лише запас без інтернету.
// Змінюючи app.js, app.css чи mapbox-gl, підніми номер версії.
const CACHE = 'bruk-map-v5';
const SHELL = [
  './', 'index.html', 'app.css', 'app.js', 'manifest.webmanifest',
  'config.js', 'vendor/mapbox-gl.js', 'vendor/mapbox-gl.css', 'icons/icon-192.png',
  'data/buildings.json', 'data/facts.json', 'data/filters.json',
];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(caches.keys()
    .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  // Тайли Mapbox і фото Commons не чіпаємо: їх кешує сам браузер.
  if (event.request.method !== 'GET' || url.origin !== location.origin) return;
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        const copy = response.clone();
        if (response.ok) caches.open(CACHE).then((c) => c.put(event.request, copy));
        return response;
      })
      .catch(() => caches.match(event.request, { ignoreSearch: true })),
  );
});

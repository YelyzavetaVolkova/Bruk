// Сторінки будинків (budynky/…, пише tools/site_seo.py): фото з Wikimedia Commons,
// «Поділитися» і «Випадковий будинок». Фото — як loadPhotos у map/app.js.
(function () {
  const esc = (s) => String(s || '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const strip = (s) => (s ? new DOMParser().parseFromString(s, 'text/html').body.textContent.trim() : '');

  async function commons(source) {
    const params = new URLSearchParams({
      action: 'query', ...source, prop: 'imageinfo', iiprop: 'url|extmetadata',
      iiextmetadatafilter: 'Artist|LicenseShortName', iiurlwidth: '800', format: 'json', origin: '*',
    });
    try {
      const json = await (await fetch(`https://commons.wikimedia.org/w/api.php?${params}`)).json();
      return Object.values((json.query && json.query.pages) || {}).map((p) => {
        const info = p.imageinfo && p.imageinfo[0];
        if (!info || !info.thumburl) return null;
        const meta = info.extmetadata || {};
        const credit = [strip(meta.Artist && meta.Artist.value), strip(meta.LicenseShortName && meta.LicenseShortName.value)]
          .filter(Boolean).join(' · ');
        return { url: info.thumburl, page: info.descriptionurl, title: p.title, credit };
      }).filter(Boolean).sort((a, b) => a.title.localeCompare(b.title));
    } catch (_) {
      return [];
    }
  }

  async function photos() {
    const box = document.querySelector('.photos[data-cat], .photos[data-files]');
    if (!box) return;
    const cat = box.dataset.cat;
    const files = box.dataset.files;
    const byCat = (c) => commons({ generator: 'categorymembers', gcmtitle: `Category:${c}`, gcmtype: 'file', gcmlimit: '6' });
    let list = [];
    if (cat) {
      list = await byCat(cat);
      // Commons перейменовує «…, Kiev» на «…, Kyiv»; стара категорія після цього порожня.
      if (!list.length && cat.endsWith('Kiev')) list = await byCat(`${cat.slice(0, -4)}Kyiv`);
    } else if (files) {
      list = await commons({ titles: files });
    }
    // Автор і ліцензія обов'язкові за ліцензіями Commons.
    box.innerHTML = list.map((p) => `<figure><img src="${esc(p.url)}" alt="${esc(box.dataset.alt)}" loading="lazy">
      <figcaption><a href="${esc(p.page)}" target="_blank" rel="noopener">${esc(p.credit || 'Wikimedia Commons')}</a></figcaption></figure>`).join('');
  }

  function share() {
    const btn = document.querySelector('[data-share]');
    if (!btn) return;
    btn.hidden = false;
    btn.addEventListener('click', async () => {
      const data = { title: document.title, url: location.href };
      if (navigator.share) {
        try { await navigator.share(data); } catch (_) { /* закрили меню */ }
        return;
      }
      try {
        await navigator.clipboard.writeText(location.href);
        btn.textContent = 'Посилання скопійовано';
        setTimeout(() => { btn.textContent = 'Поділитися'; }, 2000);
      } catch (_) { /* без доступу до буфера лишаємо як є */ }
    });
  }

  function random() {
    document.querySelectorAll('[data-random]').forEach((a) => a.addEventListener('click', async (e) => {
      e.preventDefault();
      try {
        const pages = Object.values(await (await fetch('/map/data/pages.json')).json()).filter((p) => p !== location.pathname);
        location.href = pages[Math.floor(Math.random() * pages.length)];
      } catch (_) {
        location.href = a.getAttribute('href');
      }
    }));
  }

  photos();
  share();
  random();
})();

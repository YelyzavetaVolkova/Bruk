#!/usr/bin/env python3
"""Бігучий рядок на головній — факти про будинки замість слів «фасади · тиньк · вікна».

Факти ті самі, що в застосунку (bruk-app/Bruk/facts.json), лише вже перевірені.
Сторінка бере їх з map/data/home-facts.json (його пише tools/sync_map_data.py):
українською на bruk.city, англійською на bruk.city/en. Натиснеш на факт —
відкривається мапа з цим будинком. Слова лишаються запасом, якщо факти не
завантажились.

Повторний запуск замінює попередню версію, нічого не дублює. Після нього: python3 tools/build_en.py
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "index.html"
MARK = "home-facts.json"

CSS = """
/* Facts strip (tools/site_facts_strip.py) */
.strip-track.facts { font-size: clamp(16px, 1.5vw, 22px); font-weight: 500; animation: none; will-change: transform; }
.strip-track .fact { color: inherit; text-decoration: none; }
.strip-track .fact b { color: #A20E00; font-weight: 700; margin-right: .5em; }
.strip-track .fact:hover { color: #A20E00; }
/* /Facts strip */
"""

# Без кирилиці: build_en.py вимагає, щоб в англійській сторінці її не лишалось.
# Рух — скриптом, а не CSS-анімацією: доріжка з 54 фактів завширшки ~170 000 px,
# і Safari таку не анімує. У доріжці тримаємо лише факти, що видно на екрані.
SCRIPT = """<script>/* facts-strip */
(function () {
  var track = document.querySelector('.strip .strip-track');
  if (!track || !window.fetch || !window.requestAnimationFrame) return;
  var en = location.pathname.indexOf('/en') === 0 || document.documentElement.lang === 'en';
  var esc = function (s) { var d = document.createElement('div'); d.textContent = s; return d.innerHTML; };
  fetch('/map/data/home-facts.json').then(function (r) { return r.json(); }).then(function (list) {
    if (!list.length) return;
    list.sort(function () { return Math.random() - 0.5; });
    var html = list.map(function (f) {
      var t = en ? f.en : f.uk;
      return '<a class="fact" href="/map/#b=' + encodeURIComponent(f.id) + '"><b>' + esc(t.address) +
        '</b>' + esc(t.text) + '</a><span class="dot"></span>';
    });
    var next = 0, offset = 0, last = 0, paused = false;
    track.classList.add('facts');
    track.innerHTML = '';
    var gap = function () { return parseFloat(getComputedStyle(track).columnGap) || 0; };
    var add = function () {
      var s = document.createElement('span');
      s.innerHTML = html[next % html.length];
      next += 1;
      track.appendChild(s);
    };
    var fill = function () {
      var w = track.parentNode.clientWidth;
      while (!track.lastChild || track.lastChild.getBoundingClientRect().right < w + 400) add();
    };
    var slow = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var speed = slow ? 20 : (window.innerWidth > 900 ? 70 : 45);
    track.parentNode.addEventListener('pointerenter', function (e) { if (e.pointerType === 'mouse') paused = true; });
    track.parentNode.addEventListener('pointerleave', function () { paused = false; });
    fill();
    var tick = function (now) {
      var dt = last ? Math.min(now - last, 100) / 1000 : 0;
      last = now;
      if (!paused) offset -= speed * dt;
      var first = track.firstChild;
      var w = first.getBoundingClientRect().width + gap();
      if (-offset > w) { track.removeChild(first); offset += w; }
      track.style.transform = 'translate3d(' + offset.toFixed(1) + 'px,0,0)';
      fill();
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }).catch(function () {});
})();
</script>
"""


def main():
    html = SRC.read_text(encoding="utf-8")
    m = re.search(r'(<script type="__bundler/template">)(.*?)(</script>)', html, re.S)
    if not m:
        raise SystemExit("нема блоку __bundler/template")
    tpl = json.loads(m.group(2))
    # Попередню версію прибираємо, щоб оновлення не дублювались.
    tpl = re.sub(r"\n/\* Facts strip \(tools/site_facts_strip\.py\) \*/\n.*?(?=</style>)", "", tpl, flags=re.S)
    tpl = re.sub(r"<script>(?:/\* facts-strip \*/)?\n\(function \(\) \{\n  var track = document\.querySelector\('\.strip \.strip-track'\).*?</script>\n", "", tpl, flags=re.S)
    if MARK in tpl:
        raise SystemExit("не вдалося прибрати попередню версію рядка")
    if '<div class="strip-track">' not in tpl:
        raise SystemExit("не знайшла бігучий рядок")
    i = tpl.rfind("</style>")
    tpl = tpl[:i] + CSS + tpl[i:]
    i = tpl.rfind("</body>")
    tpl = tpl[:i] + SCRIPT + tpl[i:]
    dumped = json.dumps(tpl, ensure_ascii=False).replace("</", "<\\/")
    SRC.write_text(html[:m.start(2)] + dumped + html[m.end(2):], encoding="utf-8")
    print("index.html: бігучий рядок тепер з фактами")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Бігучий рядок на головній — факти про будинки замість слів «фасади · тиньк · вікна».

Факти ті самі, що в застосунку (bruk-app/Bruk/facts.json), лише вже перевірені.
Сторінка бере їх з map/data/home-facts.json (його пише tools/sync_map_data.py):
українською на bruk.city, англійською на bruk.city/en. Натиснеш на факт —
відкривається мапа з цим будинком. Слова лишаються запасом, якщо факти не
завантажились.

Повторний запуск нічого не дублює. Після нього: python3 tools/build_en.py
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "index.html"
MARK = "home-facts.json"

CSS = """
/* Facts strip (tools/site_facts_strip.py) */
.strip-track.facts { font-size: clamp(16px, 1.5vw, 22px); font-weight: 500; }
.strip-track .fact { color: inherit; text-decoration: none; }
.strip-track .fact b { color: #A20E00; font-weight: 700; margin-right: .5em; }
.strip-track .fact:hover { color: #A20E00; }
.strip:hover .strip-track { animation-play-state: paused; }
@media (prefers-reduced-motion: reduce) {
  .strip { overflow-x: auto; }
  .strip-track { animation: none; }
}
"""

# Без кирилиці: build_en.py вимагає, щоб в англійській сторінці її не лишалось.
SCRIPT = """<script>
(function () {
  var track = document.querySelector('.strip .strip-track');
  if (!track || !window.fetch) return;
  var en = location.pathname.indexOf('/en') === 0 || document.documentElement.lang === 'en';
  var esc = function (s) { var d = document.createElement('div'); d.textContent = s; return d.innerHTML; };
  fetch('/map/data/home-facts.json').then(function (r) { return r.json(); }).then(function (list) {
    if (!list.length) return;
    list.sort(function () { return Math.random() - 0.5; });
    var row = list.map(function (f) {
      var t = en ? f.en : f.uk;
      return '<a class="fact" href="/map/#b=' + encodeURIComponent(f.id) + '"><b>' + esc(t.address) +
        '</b>' + esc(t.text) + '</a><span class="dot"></span>';
    }).join('');
    track.classList.add('facts');
    track.innerHTML = '<span>' + row + '</span><span>' + row + '</span>';
    // Same speed whatever the number of facts: half the track width / px per second.
    var speed = window.innerWidth > 900 ? 70 : 45;
    track.style.animationDuration = Math.round(track.scrollWidth / 2 / speed) + 's';
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
    if MARK in tpl:
        print("index.html: рядок з фактами вже є")
        return
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

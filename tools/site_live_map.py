#!/usr/bin/env python3
"""Жива мапа на головній сторінці замість прототипу телефона (на комп'ютері).

На комп'ютері (ширше 900 px) у розділі «03» замість намальованого телефона
показується справжня мапа bruk.city/map у вбудованому вікні. На телефоні
лишається телефон-прототип і кнопка «Відкрити мапу», бо маленьке вікно
мапи в довгій сторінці незручне.

Повторний запуск нічого не дублює. Після нього: python3 tools/build_en.py
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "index.html"

CSS = """
/* Live map (tools/site_live_map.py) */
.live-map { display: none; }
.live-map-open { margin-top: 32px; }
@media (min-width: 901px) {
  .phone-section .inner { grid-template-columns: minmax(0, .8fr) minmax(0, 1.2fr); }
  .live-map { display: block; position: relative; height: min(80vh, 720px); border-radius: 28px;
    overflow: hidden; background: #e9e6df; box-shadow: 0 30px 60px -24px rgba(0,0,0,.35); }
  .live-map iframe { display: block; width: 100%; height: 100%; border: 0; }
  .phone-section #phone { display: none; }
}
"""

MAP = ('<div class="live-map"><iframe src="/map/?embed=1" loading="lazy" '
       'title="Жива мапа BRUK" allow="geolocation"></iframe></div>\n      ')
BUTTON = '\n      <a class="btn btn-primary live-map-open" href="/map/">Відкрити мапу →</a>'


def block(html):
    m = re.search(r'(<script type="__bundler/template">)(.*?)(</script>)', html, re.S)
    if not m:
        raise SystemExit("нема блоку __bundler/template")
    return m


def main():
    html = SRC.read_text(encoding="utf-8")
    m = block(html)
    tpl = json.loads(m.group(2))
    if "live-map" in tpl:
        print("index.html: жива мапа вже є")
        return

    def swap(old, new):
        nonlocal tpl
        if old not in tpl:
            raise SystemExit(f"не знайшла в сторінці: {old[:80]}")
        tpl = tpl.replace(old, new, 1)

    swap("03 · Прототип додатку", "03 · Мапа")
    # Кнопка «Подивитись мапу» на першому екрані веде до живої мапи.
    swap('<a class="btn btn-ghost" href="#solution">Подивитись мапу</a>',
         '<a class="btn btn-ghost" href="#app">Подивитись мапу</a>')
    # Мапа — перед телефоном, у тій самій колонці.
    swap('<div class="phone" id="phone">', MAP + '<div class="phone" id="phone">')
    # Кнопка під кроками «Відкрий мапу / Натисни / Дізнайся».
    steps = tpl.index('<div class="steps-mini')
    end = tpl.index("\n    </div>\n\n    <div class=\"reveal d2\">", steps)
    tpl = tpl[:end] + BUTTON + tpl[end:]
    i = tpl.rfind("</style>")
    tpl = tpl[:i] + CSS + tpl[i:]

    dumped = json.dumps(tpl, ensure_ascii=False).replace("</", "<\\/")
    html = html[:m.start(2)] + dumped + html[m.end(2):]
    SRC.write_text(html, encoding="utf-8")
    print("index.html: живу мапу додано")


if __name__ == "__main__":
    main()

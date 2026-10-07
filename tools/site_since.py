#!/usr/bin/env python3
"""Рядок «з 2025 року» в розділі «02 · Рішення»: скільки існує проєкт.

Повторний запуск нічого не дублює. Після нього: python3 tools/site_typo.py && python3 tools/build_en.py
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
ANCHOR = "Живий архів, який прокидається від\xa0дотику.</p>\n"
LINE = ('      <p class="since reveal d3"><span class="since-year">Від 2025</span><span>'
        'BRUK почався з\xa0першого місця на\xa0<a href="https://hatathon.houseofeurope.org.ua/en-2025" target="_blank" rel="noopener noreferrer">Hatathon 6.0</a> від House of Europe.</span>'
        '</p>\n')
CSS = """/* bruk-since: tools/site_since.py */
.since { margin-top: 20px; display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap;
  font-size: 14px; color: var(--muted); max-width: 44ch; }
.since-year { color: #A20E00; font-weight: 600; font-size: 12px;
  letter-spacing: .08em; text-transform: uppercase; white-space: nowrap; }
.since a { color: inherit; text-decoration: underline; text-underline-offset: 3px; }
/* /bruk-since */
"""


def main():
    p = ROOT / "index.html"
    html = p.read_text()
    m = re.search(r'(<script type="__bundler/template">)(.*?)(</script>)', html, re.S)
    tpl = json.loads(m.group(2))
    if 'class="since ' not in tpl:
        assert ANCHOR in tpl, "не знайшла абзац «Живий архів…»"
        tpl = tpl.replace(ANCHOR, ANCHOR + LINE, 1)
    if "bruk-since" not in tpl:
        i = tpl.rfind("</style>")
        tpl = tpl[:i] + CSS + tpl[i:]
    data = json.dumps(tpl, ensure_ascii=False).replace("</", "<\\/")
    p.write_text(html[:m.start(2)] + data + html[m.end(2):])
    print("рядок «з 2025»: готово")


if __name__ == "__main__":
    main()

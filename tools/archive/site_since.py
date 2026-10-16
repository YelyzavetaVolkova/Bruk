#!/usr/bin/env python3
"""Перший екран: «Since 2025» замість «Est. 2026» — помітна червона плашка,
веде на результати Hatathon 6.0 (House of Europe), з якого почався BRUK.

Повторний запуск нічого не дублює. Після нього: python3 tools/site_typo.py && python3 tools/build_en.py
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = "https://hatathon.houseofeurope.org.ua/en-2025"
OLD = re.compile(r'<div class="eyebrow on-dark">BRUK ·\s*Cultural\s*Platform ·\s*Est\.\s*2026</div>')
NEW = ('<div class="eyebrow on-dark">BRUK ·\xa0Cultural Platform</div>'
       f'<a class="since-badge" href="{URL}" target="_blank" rel="noopener noreferrer" '
       'title="BRUK — 1 місце на Hatathon 6.0 (House of Europe), 2025">Since 2025</a>')
CSS = """/* bruk-since: tools/site_since.py */
.hero-topline { align-items: center; gap: 14px; flex-wrap: wrap; }
.since-badge { display: inline-flex; align-items: center; padding: 8px 14px; border-radius: 999px;
  background: #fff; color: #0e0e0e; font-size: 13px; font-weight: 600; letter-spacing: .1em;
  text-transform: uppercase; line-height: 1; white-space: nowrap; transition: background .2s; }
.since-badge:hover { background: rgba(255,255,255,.85); }
/* eyebrow next to the badge: more visible */
.hero-topline .eyebrow.on-dark { font-size: 13px !important; letter-spacing: .1em !important;
  color: #fff !important; opacity: 1 !important; font-weight: 600; text-shadow: 0 1px 8px rgba(0,0,0,.45); }
@media (max-width: 640px) { .hero-topline .eyebrow.on-dark { font-size: 11px !important; } }
@media (max-width: 640px) { .since-badge { font-size: 11.5px; padding: 7px 12px; } }
/* /bruk-since */
"""


def main():
    p = ROOT / "index.html"
    html = p.read_text()
    m = re.search(r'(<script type="__bundler/template">)(.*?)(</script>)', html, re.S)
    tpl = json.loads(m.group(2))
    if 'class="since-badge"' not in tpl:
        tpl, n = OLD.subn(NEW, tpl, 1)
        assert n, "не знайшла «Est. 2026» на першому екрані"
    if "bruk-since" not in tpl:
        i = tpl.rfind("</style>")
        tpl = tpl[:i] + CSS + tpl[i:]
    data = json.dumps(tpl, ensure_ascii=False).replace("</", "<\\/")
    p.write_text(html[:m.start(2)] + data + html[m.end(2):])
    print("Since 2025: готово")


if __name__ == "__main__":
    main()

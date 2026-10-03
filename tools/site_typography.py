#!/usr/bin/env python3
"""Типографіка сайту: без штучного курсиву й з ширшими інтервалами.

Poppins не має кирилиці, тож українські літери малює системний шрифт.
Через це:
  * <em> у заголовках ставав «штучним» курсивом (браузер просто нахиляв
    прямі літери) — тепер виділення лише кольором і тоншою вагою;
  * від'ємний трекінг (letter-spacing до −0.04em), підібраний під Poppins,
    зліплював кириличні слова — тепер 0, а між словами трохи більше місця;
  * міжрядковий інтервал великих заголовків 0.92–0.98 → 1.08, щоб «Ї», «Й»
    не налазили на рядок вище.

Повторний запуск нічого не дублює. Після нього: python3 tools/build_en.py
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "index.html"
MARK = "/* Typography (tools/site_typography.py) */"

CSS = MARK + """
em, i { font-style: normal !important; }
h1, h2, h3, .display-xl, .display-l, .display-m, .hero-headline, .waitlist h2,
.volunteer-title {
  letter-spacing: 0 !important; word-spacing: 0.08em; line-height: 1.08 !important;
}
.map-card-float h4, .sol-stats .stat .k, .phone-sheet h5, .phone-section .mini h4,
.orbit-caption, .value-row .name, .faq-item .q, .footer-brand p {
  letter-spacing: 0 !important; word-spacing: 0.05em;
}
body { word-spacing: 0.03em; }
"""


def main():
    html = SRC.read_text(encoding="utf-8")
    m = re.search(r'(<script type="__bundler/template">)(.*?)(</script>)', html, re.S)
    if not m:
        raise SystemExit("нема блоку __bundler/template")
    tpl = json.loads(m.group(2))
    if MARK in tpl:
        print("index.html: типографіка вже оновлена")
        return
    i = tpl.rfind("</style>")
    tpl = tpl[:i] + CSS + tpl[i:]
    dumped = json.dumps(tpl, ensure_ascii=False).replace("</", "<\\/")
    html = html[:m.start(2)] + dumped + html[m.end(2):]
    SRC.write_text(html, encoding="utf-8")
    print("index.html: типографіку оновлено")


if __name__ == "__main__":
    main()

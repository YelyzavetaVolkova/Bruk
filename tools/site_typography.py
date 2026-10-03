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
import base64
import json
import uuid
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "index.html"
MARK = "/* Typography (tools/site_typography.py) */"
FONT_MARK = "/* One font (tools/site_typography.py) */"
FONTS = ROOT / "tools" / "fonts"
SUBSETS = {
    "cyrillic-ext": "U+0460-052F, U+1C80-1C8A, U+20B4, U+2DE0-2DFF, U+A640-A69F, U+FE2E-FE2F",
    "cyrillic": "U+0301, U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116",
    "latin-ext": ("U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, "
                  "U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, "
                  "U+2113, U+2C60-2C7F, U+A720-A7FF"),
    "latin": ("U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, "
              "U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD"),
}
ONE_FONT_CSS = """
:root {
  --f-display: "Montserrat", -apple-system, sans-serif;
  --f-body: "Montserrat", -apple-system, sans-serif;
  --f-mono: "Montserrat", -apple-system, sans-serif;
}
body, body * { font-family: "Montserrat", -apple-system, sans-serif !important; }
em, i { font-weight: inherit !important; }
/* Montserrat is wider than the system font: light tracking, no extra word gap. */
h1, h2, h3, .display-xl, .display-l, .display-m, .hero-headline, .waitlist h2,
.volunteer-title { letter-spacing: -0.01em !important; word-spacing: normal; }
body, .map-card-float h4, .sol-stats .stat .k, .phone-sheet h5, .phone-section .mini h4,
.orbit-caption, .value-row .name, .faq-item .q, .footer-brand p { word-spacing: normal; }
"""

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


def font_id(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "bruk.city/fonts/montserrat-" + name))


def font_faces(html):
    out = []
    for name, rng in SUBSETS.items():
        out.append("@font-face { font-family: 'Montserrat'; font-style: normal; "
                   "font-weight: 100 900; font-display: swap; "
                   f'src: url("{font_id(name)}") format(\'woff2\'); unicode-range: {rng}; }}')
    return "\n".join(out) + "\n"


def add_fonts_to_manifest(html):
    m = re.search(r'(<script type="__bundler/manifest">)(.*?)(</script>)', html, re.S)
    if not m:
        raise SystemExit("нема блоку __bundler/manifest")
    man = json.loads(m.group(2))
    for name in SUBSETS:
        data = (FONTS / f"montserrat-{name}.woff2").read_bytes()
        man[font_id(name)] = {"mime": "font/woff2", "compressed": False,
                              "data": base64.b64encode(data).decode("ascii")}
    return html[:m.start(2)] + json.dumps(man) + html[m.end(2):]


def main():
    html = SRC.read_text(encoding="utf-8")
    m = re.search(r'(<script type="__bundler/template">)(.*?)(</script>)', html, re.S)
    if not m:
        raise SystemExit("нема блоку __bundler/template")
    tpl = json.loads(m.group(2))
    add = ""
    if MARK not in tpl:
        add += CSS
    if FONT_MARK not in tpl:
        add += FONT_MARK + "\n" + font_faces(html) + ONE_FONT_CSS
        html = add_fonts_to_manifest(html)
        m = re.search(r'(<script type="__bundler/template">)(.*?)(</script>)', html, re.S)
    if not add:
        print("index.html: типографіка вже оновлена")
        return
    i = tpl.rfind("</style>")
    tpl = tpl[:i] + add + tpl[i:]
    dumped = json.dumps(tpl, ensure_ascii=False).replace("</", "<\\/")
    html = html[:m.start(2)] + dumped + html[m.end(2):]
    SRC.write_text(html, encoding="utf-8")
    print("index.html: типографіку оновлено")


if __name__ == "__main__":
    main()

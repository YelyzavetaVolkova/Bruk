#!/usr/bin/env python3
"""Типографіка сайту: один український шрифт Fixel, без штучного курсиву.

Рішення авторки:
  * 3.10.2026 — без штучного курсиву (виділення в заголовках лише кольором),
    ширші інтервали, один шрифт на весь сайт;
  * 6.10.2026 — шрифт Fixel (MacPaw, Київ, OFL; файли в fonts/) замість
    Montserrat, чию кирилицю консультували московські дизайнери (Cyreal).
    Poppins і JetBrains Mono з бандла прибрано.

Fixel Text — для тексту, кнопок і підписів; Fixel Display — для великих
заголовків. Файли шрифту вшиваються в маніфест бандла, тож сайт не тягне
шрифти з Google.

Повторний запуск нічого не дублює. Після нього: python3 tools/build_en.py
"""
import base64
import json
import pathlib
import re
import uuid

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "index.html"
FONTS = ROOT / "fonts"
MARK = "/* Typography (tools/site_typography.py) */"
FONT_MARK = "/* One font (tools/site_typography.py) */"
FIXEL_MARK = "/* Fixel (tools/site_typography.py) */"
FIXEL_END = "/* /Fixel */"
BREAKS_MARK = "/* Headline breaks (tools/site_typography.py) */"
# «У кишені, / як компас.» — рівно два рядки: виділена частина завжди з нового
# рядка й не розривається, а на комп'ютері (колонка поруч із мапою) кегль
# підібрано під ширину колонки.
BREAKS_CSS = BREAKS_MARK + """
.phone-section h2.display-l em { display: block; white-space: nowrap; }
@media (min-width: 901px) {
  .phone-section h2.display-l { font-size: clamp(40px, 4.6vw, 84px) !important; white-space: nowrap; }
  html[lang="en"] .phone-section h2.display-l { font-size: clamp(32px, 3.6vw, 72px) !important; }
}
"""
DROP_FAMILIES = ("Poppins", "JetBrains Mono", "Montserrat")

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

# (сімейство, файл, вага)
FACES = [
    ("Fixel", "FixelText-Regular", 400),
    ("Fixel", "FixelText-Medium", 500),
    ("Fixel", "FixelText-SemiBold", 600),
    ("Fixel", "FixelText-Bold", 700),
    ("Fixel", "FixelText-ExtraBold", 800),
    ("Fixel Display", "FixelDisplay-Bold", 700),
    ("Fixel Display", "FixelDisplay-ExtraBold", 800),
]

HEADINGS = ("h1, h2, h3, .display-xl, .display-l, .display-m, .hero-headline, "
            ".waitlist h2, .volunteer-title")

FIXEL_CSS = """
:root {
  --f-display: "Fixel Display", "Fixel", -apple-system, sans-serif;
  --f-body: "Fixel", -apple-system, sans-serif;
  --f-mono: "Fixel", -apple-system, sans-serif;
}
body, body * { font-family: "Fixel", -apple-system, sans-serif !important; }
%s,
h1 *, h2 *, h3 *, .display-xl *, .display-l *, .display-m *, .hero-headline * {
  font-family: "Fixel Display", "Fixel", -apple-system, sans-serif !important;
  letter-spacing: -0.01em !important; word-spacing: normal;
}
em, i { font-weight: inherit !important; }
body, .map-card-float h4, .sol-stats .stat .k, .phone-sheet h5, .phone-section .mini h4,
.orbit-caption, .value-row .name, .faq-item .q, .footer-brand p { word-spacing: normal; }
""" % HEADINGS


def font_id(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "bruk.city/fonts/" + name))


def fixel_block():
    faces = "\n".join(
        f"@font-face {{ font-family: '{fam}'; font-style: normal; font-weight: {w}; "
        f'font-display: swap; src: url("{font_id(f)}") format(\'woff2\'); }}'
        for fam, f, w in FACES)
    return FIXEL_MARK + "\n" + faces + FIXEL_CSS + FIXEL_END + "\n"


def drop_old_fonts(tpl):
    """Прибирає @font-face Poppins, JetBrains Mono, Montserrat; повертає (tpl, uuid-и)."""
    ids = []

    def repl(m):
        face = m.group(0)
        if any(f"'{f}'" in face or f'"{f}"' in face for f in DROP_FAMILIES):
            ids.extend(re.findall(r'url\("([0-9a-f-]{36})"\)', face))
            return ""
        return face

    tpl = re.sub(r"(?:/\* [a-z-]+ \*/\s*)?@font-face\s*\{[^}]*\}\n?", repl, tpl)
    # Початкові змінні шрифтів шаблону (Poppins, JetBrains Mono) і preconnect до Google Fonts.
    tpl = re.sub(r'(--f-(?:display|body|mono)):[^;]*(Poppins|JetBrains)[^;]*;',
                 lambda m: m.group(1) + ': "Fixel", -apple-system, sans-serif;', tpl)
    tpl = re.sub(r'<link rel="preconnect" href="https://fonts\.(?:googleapis|gstatic)\.com"[^>]*>\n?', "", tpl)
    # Старий блок Montserrat (3.10.2026): лишаємо лише правила, без імені шрифту.
    if FONT_MARK in tpl:
        start = tpl.index(FONT_MARK)
        end = tpl.find("\n", tpl.find("no extra word gap", start))
        end = tpl.find(".footer-brand p { word-spacing: normal; }", end)
        end = tpl.find("\n", end) + 1
        tpl = tpl[:start] + tpl[end:]
    return tpl, ids


def main():
    html = SRC.read_text(encoding="utf-8")
    m = re.search(r'(<script type="__bundler/template">)(.*?)(</script>)', html, re.S)
    if not m:
        raise SystemExit("нема блоку __bundler/template")
    tpl = json.loads(m.group(2))
    if MARK in tpl and FIXEL_MARK in tpl and BREAKS_MARK in tpl:
        print("index.html: типографіка вже оновлена")
        return
    tpl, old_ids = drop_old_fonts(tpl)
    add = ("" if MARK in tpl else CSS) + ("" if FIXEL_MARK in tpl else fixel_block())
    add += "" if BREAKS_MARK in tpl else BREAKS_CSS
    i = tpl.rfind("</style>")
    tpl = tpl[:i] + add + tpl[i:]
    dumped = json.dumps(tpl, ensure_ascii=False).replace("</", "<\\/")
    html = html[:m.start(2)] + dumped + html[m.end(2):]

    mm = re.search(r'(<script type="__bundler/manifest">)(.*?)(</script>)', html, re.S)
    if not mm:
        raise SystemExit("нема блоку __bundler/manifest")
    man = json.loads(mm.group(2))
    for fid in set(old_ids):
        if fid not in tpl:
            man.pop(fid, None)
    for _, f, _ in (FACES if FIXEL_MARK not in json.loads(m.group(2)) else []):
        data = (FONTS / f"{f}.woff2").read_bytes()
        man[font_id(f)] = {"mime": "font/woff2", "compressed": False,
                           "data": base64.b64encode(data).decode("ascii")}
    html = html[:mm.start(2)] + json.dumps(man) + html[mm.end(2):]
    SRC.write_text(html, encoding="utf-8")
    print(f"index.html: типографіку оновлено (прибрано старих файлів шрифтів: {len(set(old_ids))})")


if __name__ == "__main__":
    main()

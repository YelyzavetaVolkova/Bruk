#!/usr/bin/env python3
"""Іконка бруківки (favicon) у вкладці браузера на всіх сторінках сайту.

Чому її не було: index.html — бандл, і посилання на іконку жили лише в шаблоні,
який розпаковується скриптом уже після завантаження. У справжньому <head>
іконки не було, а першою в шаблоні стояла емодзі-цеглина з SVG, тож браузер
показував стандартний глобус.

Скрипт:
  • вставляє /favicon.png, /favicon.ico і /apple-touch-icon.png у справжній
    <head> index.html, story.html, privacy.html;
  • у шаблоні index.html замінює емодзі й вбудовану картинку на ті самі файли;
  • на мапі /map ставить ту саму іконку у вкладку (іконка PWA лишається).
Повторний запуск нічого не дублює. Після нього: python3 tools/build_en.py
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
MARK = "<!-- bruk-favicon -->"
LINKS = (MARK + '\n<link rel="icon" type="image/png" sizes="256x256" href="/favicon.png">\n'
         '<link rel="icon" href="/favicon.ico" sizes="any">\n'
         '<link rel="apple-touch-icon" href="/apple-touch-icon.png">\n')


def add_head_links(html):
    if MARK in html:
        return html
    return html.replace("</head>", LINKS + "</head>", 1)


def fix_template(html):
    # Емодзі-цеглина з SVG — геть; вбудовані PNG за UUID — на файли з кореня.
    html = re.sub(r'<link rel=\\"icon\\" type=\\"image/svg\+xml\\" href=\\"data:image/svg\+xml,[^>]*?>\\n', "", html)
    html = re.sub(r'(<link rel=\\"icon\\" type=\\"image/png\\" href=\\")[0-9a-f-]{36}(\\")', r"\1/favicon.png\2", html)
    html = re.sub(r'(<link rel=\\"apple-touch-icon\\" href=\\")[0-9a-f-]{36}(\\")', r"\1/apple-touch-icon.png\2", html)
    return html


def main():
    p = ROOT / "index.html"
    p.write_text(fix_template(add_head_links(p.read_text())))
    for name in ("story.html", "privacy.html"):
        p = ROOT / name
        html = p.read_text().replace('<link rel="icon" href="/favicon.png">\n', "")
        p.write_text(add_head_links(html))
    p = ROOT / "map" / "index.html"
    html = p.read_text()
    html = html.replace('<link rel="icon" type="image/png" href="icons/icon-192.png">',
                        '<link rel="icon" type="image/png" href="/favicon.png">\n'
                        '<link rel="icon" href="/favicon.ico" sizes="any">')
    p.write_text(html)
    print("favicon: готово")


if __name__ == "__main__":
    main()

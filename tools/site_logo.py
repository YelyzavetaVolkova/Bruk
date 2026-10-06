#!/usr/bin/env python3
"""Нове лого BRUK (як у застосунку: bruk-app/Bruk/Assets.xcassets/BrukLogo) на сайті, біле.

Лого в index.html — вбудована картинка бандла (UUID нижче) у шапці й футері;
скрипт підміняє її вміст на нове лого з білою заливкою.
Запуск: python3 tools/site_logo.py [../bruk-app]; потім python3 tools/build_en.py
"""
import base64
import gzip
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOGO_UUID = "6bbe2045-4749-4bfc-8185-599653ff76ea"


def main():
    app = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ROOT.parent / "bruk-app")
    svg = (app / "Bruk/Assets.xcassets/BrukLogo.imageset/Logo.svg").read_text()
    svg = svg.replace('fill="#FFF5D9"', 'fill="#FFFFFF"')
    data = base64.b64encode(gzip.compress(svg.encode(), mtime=0)).decode()
    p = ROOT / "index.html"
    html = p.read_text()
    pat = re.compile(r'("' + LOGO_UUID + r'": \{"mime": "image/svg\+xml", "compressed": true, "data": ")[^"]*(")')
    html, n = pat.subn(lambda m: m.group(1) + data + m.group(2), html)
    if n != 1:
        sys.exit("лого в маніфесті не знайдено")
    p.write_text(html)
    print("лого: готово")


if __name__ == "__main__":
    main()

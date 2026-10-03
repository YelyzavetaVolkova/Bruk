#!/usr/bin/env python3
"""Фото в каруселі («галерея») і в колажі розділу «01 · Проблема».

Усі фото — з Unsplash (вільна ліцензія Unsplash), автор підписаний на кожному кадрі.
Стиснені копії лежать у tools/photos/ (довга сторона 1200 px, JPEG 74).
Скрипт вшиває їх у бандл index.html і переписує картки каруселі та колажу;
старі картинки, які більше ніде не використовуються, прибирає з маніфесту.
Повторний запуск нічого не дублює. Після нього: python3 tools/build_en.py

Додати нові фото: python3 tools/site_photos.py --import <файли *-unsplash.jpg>
(стисне їх у tools/photos/), потім допиши їх у PHOTOS нижче й запусти без аргументів.
"""
import base64
import json
import pathlib
import re
import sys
import uuid

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "index.html"
DIR = ROOT / "tools" / "photos"

# файл, автор, підпис у каруселі (uk), підпис (en)
PHOTOS = [
    ("kato-blackmore.jpg", "Kato Blackmore", "Готель «Салют»", "Hotel Salut"),
    ("anastasiya-chervinska.jpg", "Anastasiya Chervinska", "Київський двір", "A Kyiv courtyard"),
    ("maksym-tymchyk.jpg", "Maksym Tymchyk", "Погляд угору", "Looking up"),
    ("oksana-savinova.jpg", "Oksana Savinova", "Цегляний фасад", "Brick facade"),
    ("yanny-mishchuk.jpg", "Yanny Mishchuk", "Білий ріг", "White corner"),
    ("eugene-chystiakov.jpg", "Eugene Chystiakov", "Балкони", "Balconies"),
    ("ilona-purdes.jpg", "Ilona Purdes", "Дахи й балкони", "Roofs and balconies"),
    ("eugenia-pan-kiv.jpg", "Eugenia Pan'kiv", "Шпиль", "The spire"),
    ("nataliia-blazhko.jpg", "Nataliia Blazhko", "Кольорові фасади", "Colourful facades"),
    ("nataliia-kvitovska.jpg", "Nataliia Kvitovska", "Жовтий фасад", "Yellow facade"),
    ("yehor-litsov.jpg", "Yehor Litsov", "Округлий ріг", "Rounded corner"),
]
# колаж «Проблема»: клас плитки → фото
FRAGMENTS = [("a", "yehor-litsov.jpg"), ("b", "nataliia-kvitovska.jpg"), ("c", "anastasiya-chervinska.jpg"),
             ("d", "oksana-savinova.jpg"), ("e", "nataliia-blazhko.jpg"), ("f", "yanny-mishchuk.jpg"),
             ("g", "eugenia-pan-kiv.jpg")]


CSS_MARK = "/* Photo credits (tools/site_photos.py) */"
CSS = CSS_MARK + """
.orbit-item .cap { gap: 8px; }
.orbit-item .cap span:first-child { flex: none; }
.orbit-item .cap span:last-child { text-align: right; min-width: 0; }
@media (max-width: 640px) { .orbit-item .cap { letter-spacing: 0.04em; } }
"""


def photo_id(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "bruk.city/photos/" + name))


def import_photos(files):
    from PIL import Image, ImageOps
    DIR.mkdir(exist_ok=True)
    for f in files:
        f = pathlib.Path(f)
        name = re.sub(r"^[0-9a-f]{8}-", "", f.name)
        name = re.sub(r"-.{11}-unsplash\.jpg$", ".jpg", name)  # без id Unsplash (11 знаків)
        im = ImageOps.exif_transpose(Image.open(f)).convert("RGB")
        im.thumbnail((1200, 1200), Image.LANCZOS)
        im.save(DIR / name, "JPEG", quality=74, optimize=True, progressive=True)
        print(DIR / name, im.size, (DIR / name).stat().st_size // 1024, "KB")


def main():
    if sys.argv[1:2] == ["--import"]:
        return import_photos(sys.argv[2:])
    html = SRC.read_text()
    mm = re.search(r'(<script type="__bundler/manifest">)(.*?)(</script>)', html, re.S)
    tm = re.search(r'(<script type="__bundler/template">)(.*?)(</script>)', html, re.S)
    manifest = json.loads(mm.group(2))
    tpl = json.loads(tm.group(2))
    by_file = {p[0]: p for p in PHOTOS}

    old = set(re.findall(r'class="orbit-item"[^>]*><img src="([0-9a-f-]{36})"', tpl))
    old |= set(re.findall(r'class="frag \w"><img src="([0-9a-f-]{36})"', tpl))

    items = []
    for i, (f, author, uk, _) in enumerate(PHOTOS, 1):
        items.append(f'      <div class="orbit-item" data-title="{uk}"><img src="{photo_id(f)}" '
                     f'alt="Фото: {author} / Unsplash" loading="lazy"><div class="cap"><span>{i:02d}</span>'
                     f'<span>Фото: {author}</span></div></div>')
    tpl, n = re.subn(r'(?:[ \t]*<div class="orbit-item".*?</div></div>\n)+', "\n".join(items) + "\n", tpl, count=1)
    if n != 1:
        sys.exit("не знайшла карусель")
    frags = []
    for cls, f in FRAGMENTS:
        author = by_file[f][1]
        frags.append(f'    <div class="frag {cls}"><img src="{photo_id(f)}" alt="Фото: {author} / Unsplash">'
                     f'<span class="tag">Фото: {author}</span></div>')
    tpl, n = re.subn(r'(?:[ \t]*<div class="frag \w">.*?</div>\n)+', "\n".join(frags) + "\n", tpl, count=1)
    if n != 1:
        sys.exit("не знайшла колаж")

    if CSS_MARK not in tpl:
        i = tpl.rfind("</style>")
        tpl = tpl[:i] + CSS + tpl[i:]

    for f, *_ in PHOTOS:
        manifest[photo_id(f)] = {"mime": "image/jpeg", "compressed": False,
                                 "data": base64.b64encode((DIR / f).read_bytes()).decode("ascii")}
    for u in old:
        if u not in tpl and u in manifest and u not in {photo_id(p[0]) for p in PHOTOS}:
            del manifest[u]
            print("прибрано стару картинку", u)

    tpl_json = json.dumps(tpl, ensure_ascii=False).replace("</", "<\\/")
    html = (html[:mm.start(2)] + json.dumps(manifest) + html[mm.end(2):tm.start(2)]
            + tpl_json + html[tm.end(2):])
    SRC.write_text(html)
    print("index.html: фото оновлено")


if __name__ == "__main__":
    main()

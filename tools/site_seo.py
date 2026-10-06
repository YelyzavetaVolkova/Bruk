#!/usr/bin/env python3
"""Сторінки будинків для пошуковиків: bruk.city/budynky/…

Мапа на сайті малюється скриптом, і Google бачить її майже порожньою. Тому для кожного
будинку з BRUK-текстом робимо звичайну HTML-сторінку з тим самим текстом, що в застосунку,
плюс сторінку кожної вулиці й загальний список. Так людина, яка шукає «Хрещатик 12 історія»,
може знайти BRUK у Google, а звідти — відкрити будинок на мапі.

Що пише скрипт (усе перезаписується з нуля, руками не правити):
  budynky/index.html                    — усі вулиці й будинки
  budynky/<вулиця>/index.html           — будинки однієї вулиці
  budynky/<вулиця>/<номер>/index.html   — сторінка будинку
  sitemap.xml, robots.txt

Дані — map/data/buildings.json (його оновлює tools/sync_map_data.py і потім кличе цей скрипт).
Будинки без shortText пропускаємо: порожні сторінки шкодять сайту в пошуку.
Запуск з кореня репозиторію:  python3 tools/site_seo.py
"""
import html
import json
import pathlib
import re
import shutil
from collections import OrderedDict

from site_typo import typo_html

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "map" / "data" / "buildings.json"
OUT = ROOT / "budynky"
SITE = "https://bruk.city"

# Транслітерація за постановою КМУ № 55 (2010), як у назвах вулиць на сайті.
TR = {"а": "a", "б": "b", "в": "v", "г": "h", "ґ": "g", "д": "d", "е": "e", "є": "ie", "ж": "zh",
      "з": "z", "и": "y", "і": "i", "ї": "i", "й": "i", "к": "k", "л": "l", "м": "m", "н": "n",
      "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts",
      "ч": "ch", "ш": "sh", "щ": "shch", "ю": "iu", "я": "ia", "ь": "", "’": "", "'": ""}
TR_START = {"є": "ye", "ї": "yi", "й": "y", "ю": "yu", "я": "ya"}  # на початку слова


def slug(s):
    s = s.lower().replace("зг", "zgh")
    out = []
    for i, ch in enumerate(s):
        start = i == 0 or not s[i - 1].isalpha()
        out.append(TR_START.get(ch) if start and ch in TR_START else TR.get(ch, ch))
    return re.sub(r"[^a-z0-9]+", "-", "".join(out)).strip("-")


def esc(s):
    return html.escape(s or "", quote=True)


def txt(s):
    # у тексті не екрануємо лапки й апостроф, щоб site_typo зробив ’ і «»
    return html.escape(s or "", quote=False)


def ua_date(d):
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", d or "")
    return f"{m[3]}.{m[2]}.{m[1]}" if m else (d or "")


def paras(text):
    return "".join(f"<p>{txt(p.strip())}</p>\n" for p in re.split(r"\n\s*\n|\n", text or "") if p.strip())


def clip(text, n=155):
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= n:
        return text
    cut = text[:n].rsplit(" ", 1)[0].rstrip(",;:—–- ")
    return cut + "…"


ABC = "абвгґдеєжзиіїйклмнопрстуфхцчшщьюя"


def uk_key(s):
    s = s.lower().replace("бульвар ", "").replace(" площа", "")
    return [ABC.index(c) if c in ABC else 100 + ord(c) for c in s]


def street_of(address):
    return address.split(",")[0].strip()


def number_of(address):
    return address.split(",", 1)[1].strip() if "," in address else ""


CSS = """
:root { --bg:#fff; --soft:#f2f2f7; --ink:#0e0e0e; --muted:rgba(60,60,67,.6); --red:#A20E00;
        --f:"Fixel",-apple-system,BlinkMacSystemFont,sans-serif; }
* { box-sizing:border-box; margin:0; padding:0; }
body { background:var(--bg); color:var(--ink); font:400 17px/1.6 var(--f); -webkit-font-smoothing:antialiased; }
a { color:inherit; }
.top { display:flex; align-items:center; justify-content:space-between; gap:16px; padding:20px clamp(16px,4vw,56px); }
.brand { font-weight:700; letter-spacing:.18em; color:var(--red); text-decoration:none; font-size:18px; }
.top nav a { font-size:13px; font-weight:600; letter-spacing:.08em; text-transform:uppercase; text-decoration:none; margin-left:18px; }
main { max-width:760px; margin:0 auto; padding:16px clamp(16px,4vw,32px) 80px; }
.crumbs { font-size:14px; color:var(--muted); margin-bottom:20px; }
.crumbs a { text-decoration:none; } .crumbs a:hover { color:var(--red); }
h1 { font-family:"Fixel Display",var(--f); font-weight:700; font-size:clamp(30px,5vw,48px); line-height:1.08; }
h2 { font-family:"Fixel Display",var(--f); font-size:22px; margin:40px 0 12px; }
.meta { margin-top:14px; color:var(--muted); font-size:15px; }
.lead p { font-size:19px; margin-top:20px; }
.text p + p { margin-top:14px; }
.btn { display:inline-block; margin-top:28px; background:var(--red); color:#fff; text-decoration:none; font-weight:600;
       font-size:14px; letter-spacing:.08em; text-transform:uppercase; padding:14px 22px; border-radius:999px; }
.btn.ghost { background:var(--soft); color:var(--ink); }
.btns { display:flex; flex-wrap:wrap; gap:10px; margin-top:28px; } .btns .btn { margin-top:0; }
.war { margin-top:28px; background:var(--soft); border-left:4px solid var(--red); border-radius:12px; padding:16px 18px; }
.war b { color:var(--red); }
.war p + p { margin-top:8px; }
.src { font-size:14px; color:var(--muted); }
.list { list-style:none; margin-top:20px; }
.list li { padding:14px 0; border-top:1px solid rgba(14,14,14,.08); }
.list a { text-decoration:none; font-weight:600; } .list a:hover { color:var(--red); }
.list span { display:block; font-size:15px; color:var(--muted); font-weight:400; }
.streets { columns:2 220px; margin-top:20px; list-style:none; }
.streets li { padding:6px 0; break-inside:avoid; }
.near { display:flex; justify-content:space-between; gap:16px; margin-top:48px; font-size:15px; }
.near a { text-decoration:none; } .near a:hover { color:var(--red); }
footer { max-width:760px; margin:0 auto; padding:0 clamp(16px,4vw,32px) 48px; font-size:14px; color:var(--muted); }
"""


def page(path, title, description, body, jsonld=None):
    url = f"{SITE}/{path}/"
    ld = "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>\n'
                 for x in (jsonld or []))
    doc = f"""<!doctype html>
<html lang="uk">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="BRUK">
<meta property="og:locale" content="uk_UA">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{url}">
<meta name="theme-color" content="#A20E00">
<link rel="icon" type="image/png" href="/favicon.png">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="stylesheet" href="/fonts/fixel.css">
<style>{CSS}</style>
{ld}</head>
<body>
<header class="top"><a class="brand" href="/">BRUK</a><nav><a href="/budynky/">Будинки</a><a href="/map/">Мапа</a></nav></header>
<main>
{body}
</main>
<footer>BRUK — історії київських будинків: хто їх звів, хто в них жив і що з ними сталося. Кожен факт — з джерелом.</footer>
</body>
</html>
"""
    target = ROOT / path / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(typo_html(doc), encoding="utf-8")


def crumbs(*items):
    parts = []
    for name, href in items:
        parts.append(f'<a href="{href}">{esc(name)}</a>' if href else esc(name))
    return '<nav class="crumbs">' + " › ".join(parts) + "</nav>"


def breadcrumb_ld(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": SITE + h}
                                for i, (n, h) in enumerate(items)]}


def building_page(b, path, street, street_path, prev, nxt):
    title_main = b.get("cardHeading") or b["address"]
    title = f"{title_main} | BRUK" if "—" in title_main else f"{title_main} — історія будинку | BRUK"
    description = clip(b.get("shortText"))
    facts = [x for x in (b.get("yearBuiltCurrent") or b.get("yearBuiltOriginal"),
                         b.get("architectCurrent") or b.get("architectOriginal"),
                         b.get("styleCurrent") or b.get("styleOriginal"),
                         b.get("heritageStatus")) if x]
    body = [crumbs(("Будинки", "/budynky/"), (street, f"/{street_path}/"), (number_of(b["address"]) or b["address"], None)),
            f"<h1>{txt(title_main)}</h1>"]
    if facts:
        body.append(f'<p class="meta">{txt(" · ".join(facts))}</p>')
    body.append(f'<div class="lead">{paras(b.get("shortText"))}</div>')
    body.append(f'<div class="btns"><a class="btn" href="/map/#b={esc(b["id"])}">Відкрити на мапі</a>'
                f'<a class="btn ghost" href="/story.html">Розкажи історію будинку</a></div>')
    for w in b.get("warDamage") or []:
        body.append(f'<div class="war"><p><b>Пошкоджений війною · {ua_date(w.get("date"))}</b></p>'
                    f'<p>{txt(w.get("description"))}</p>'
                    f'<p class="src">Джерело: <a href="{esc(w.get("url"))}" rel="nofollow noopener" target="_blank">{esc(w.get("source"))}</a></p></div>')
    if (b.get("extendedText") or "").strip():
        body.append(f'<h2>Історія</h2><div class="text">{paras(b["extendedText"])}</div>')
    if (b.get("notablePeople") or "").strip():
        body.append(f'<h2>Відомі люди</h2><div class="text">{paras(b["notablePeople"])}</div>')
    if (b.get("sources") or "").strip():
        body.append(f'<h2>Джерела</h2><p class="src">{txt(b["sources"])}</p>')
    near = []
    near.append(f'<a href="/{prev[1]}/">← {esc(prev[0])}</a>' if prev else "<span></span>")
    near.append(f'<a href="/{nxt[1]}/">{esc(nxt[0])} →</a>' if nxt else "<span></span>")
    body.append('<div class="near">' + "".join(near) + "</div>")
    ld = {"@context": "https://schema.org", "@type": "LandmarksOrHistoricalBuildings",
          "name": title_main, "description": description, "url": f"{SITE}/{path}/",
          "address": {"@type": "PostalAddress", "streetAddress": b["address"],
                      "addressLocality": "Київ", "addressCountry": "UA"},
          "geo": {"@type": "GeoCoordinates", "latitude": b["latitude"], "longitude": b["longitude"]}}
    page(path, title, description, "\n".join(body),
         [ld, breadcrumb_ld([("Будинки", "/budynky/"), (street, f"/{street_path}/"), (b["address"], f"/{path}/")])])


HOME_TITLE = "<title>BRUK — Історія Києва, яка оживає</title>"
HOME_META = ('<meta name="description" content="BRUK — мапа центру Києва, де кожен будинок розповідає свою історію: '
             'хто його звів, хто в ньому жив і що з ним сталося. Коротко, тепло і з джерелами.">\n'
             '  <link rel="canonical" href="https://bruk.city/">\n'
             '  <meta property="og:title" content="BRUK — Історія Києва, яка оживає">\n'
             '  <meta property="og:description" content="Мапа центру Києва, де кожен будинок розповідає свою історію.">\n'
             '  <meta property="og:url" content="https://bruk.city/">\n'
             '  <meta property="og:type" content="website">\n')


def patch_home():
    """Опис і canonical у зовнішню оболонку index.html — їх бачить Google до розпакування бандла."""
    f = ROOT / "index.html"
    doc = f.read_text(encoding="utf-8")
    if 'rel="canonical"' in doc.split("<script", 1)[0]:
        return
    i = doc.index(HOME_TITLE) + len(HOME_TITLE)
    f.write_text(doc[:i] + "\n  " + HOME_META.rstrip("\n") + doc[i:], encoding="utf-8")
    print("site_seo: index.html — додано опис і canonical, тепер запусти python3 tools/build_en.py")


def main():
    patch_home()
    buildings = [b for b in json.loads(DATA.read_text(encoding="utf-8")) if (b.get("shortText") or "").strip()]
    if OUT.exists():
        shutil.rmtree(OUT)

    streets = OrderedDict()
    for b in buildings:
        streets.setdefault(street_of(b["address"]), []).append(b)
    num = lambda b: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", number_of(b["address"]))]
    used, urls = set(), []

    streets = OrderedDict((k, streets[k]) for k in sorted(streets, key=uk_key))
    for street in streets:
        items = sorted(streets[street], key=num)
        street_path = f"budynky/{slug(street)}"
        paths = []
        for b in items:
            p = f"{street_path}/{slug(number_of(b['address'])) or slug(b['id'])}"
            if p in used:
                p = f"{p}-{slug(b['id'])}"
            used.add(p)
            paths.append(p)
        for i, b in enumerate(items):
            prev = (items[i - 1]["address"], paths[i - 1]) if i else None
            nxt = (items[i + 1]["address"], paths[i + 1]) if i + 1 < len(items) else None
            building_page(b, paths[i], street, street_path, prev, nxt)
            urls.append((paths[i], b.get("factChecked")))
        rows = "".join(f'<li><a href="/{p}/">{txt(b.get("cardHeading") or b["address"])}</a>'
                       f'<span>{txt(clip(b.get("shortText"), 120))}</span></li>' for b, p in zip(items, paths))
        n = len(items)
        word = "будинок" if n % 10 == 1 and n % 100 != 11 else "будинки" if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else "будинків"
        page(street_path, f"{street}: історії будинків | BRUK",
             clip(f"{street}, Київ: {n} {word} з історіями — хто їх звів, хто в них жив і що з ними сталося. "
                  f"Тексти BRUK із джерелами."),
             crumbs(("Будинки", "/budynky/"), (street, None)) + f"<h1>{esc(street)}</h1>"
             f'<p class="meta">{n} {word} з історіями · <a href="/map/">відкрити мапу</a></p><ul class="list">{rows}</ul>',
             [breadcrumb_ld([("Будинки", "/budynky/"), (street, f"/{street_path}/")])])
        urls.append((street_path, None))
        streets[street] = (street_path, n)

    rows = "".join(f'<li><a href="/{p}/">{esc(s)}</a> <span style="display:inline">· {n}</span></li>'
                   for s, (p, n) in streets.items())
    page("budynky", "Історії будинків Києва за вулицями | BRUK",
         f"{len(buildings)} будинків центру Києва з історіями: архітектори, власники, мешканці й події. "
         f"Вулиці від Хрещатика до Рейтарської.",
         f"<h1>Історії будинків Києва</h1><p class=\"meta\">{len(buildings)} будинків з історіями · "
         f"<a href=\"/map/\">відкрити мапу</a></p><ul class=\"streets\">{rows}</ul>")
    urls.insert(0, ("budynky", None))

    head = [("", None), ("en", None), ("map", None), ("story.html", None)]
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for p, checked in head + urls:
        loc = f"{SITE}/{p}" + ("/" if p and not p.endswith(".html") else "")
        mod = f"<lastmod>{checked}</lastmod>" if checked else ""
        lines.append(f"  <url><loc>{loc}</loc>{mod}</url>")
    lines.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8")
    print(f"site_seo: {len(buildings)} будинків, {len(streets)} вулиць, sitemap — {len(head) + len(urls)} адрес")


if __name__ == "__main__":
    main()

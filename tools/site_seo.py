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
  prohulianky/, prohulianky/<id>/       — прогулянки з map/data/walks.json
  liudy/, liudy/<ім'я>/                 — люди з прогулянок і архітектори (2+ будинки)
  assets/budynok.js                     — фото з Commons на сторінці будинку (у браузері)
  sitemap.xml, robots.txt
  map/data/pages.json                   — id будинку → адреса сторінки (для «Поділитися» на мапі)

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
WALKS = ROOT / "map" / "data" / "walks.json"
# Код GoatCounter (bruk.goatcounter.com → "bruk"). Порожній — аналітики нема. Див. tools/site_analytics.py.
GOATCOUNTER = "bruk"
YEAR = __import__("datetime").date.today().year

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
.brand { font-weight:700; letter-spacing:.18em; color:var(--red); text-decoration:none; font-size:18px; } .brand img { display:block; height:20px; width:auto; }
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
.photos { display:flex; gap:10px; overflow-x:auto; margin:24px -4px 0; padding:0 4px 6px; scroll-snap-type:x mandatory; }
.photos:empty { display:none; }
.photos figure { flex:0 0 auto; width:min(82%,420px); scroll-snap-align:start; }
.photos img { display:block; width:100%; aspect-ratio:4/3; object-fit:cover; border-radius:14px; background:var(--soft); }
.photos figcaption { font-size:12px; color:var(--muted); margin-top:6px; }
.photos figcaption a { text-decoration:none; }
.cards { display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr)); gap:10px; margin-top:12px; }
.cards a { display:block; background:var(--soft); border-radius:14px; padding:14px 16px; text-decoration:none; font-weight:600; line-height:1.35; }
.cards a:hover { color:var(--red); }
.cards span { display:block; font-weight:400; font-size:14px; color:var(--muted); margin-top:6px; }
.chips { display:flex; flex-wrap:wrap; gap:8px; margin-top:12px; }
.chips a { background:var(--soft); border-radius:999px; padding:8px 14px; font-size:15px; text-decoration:none; font-weight:600; }
.chips a:hover { color:var(--red); }
.intro { margin-top:18px; }
button.btn { border:0; font:inherit; font-weight:600; font-size:14px; letter-spacing:.08em; text-transform:uppercase; cursor:pointer; }
.dyk { margin-top:40px; border-left:4px solid var(--red); padding:4px 0 4px 18px; }
.dyk b { font-family:"Fixel Display",var(--f); font-size:18px; }
.dyk p { margin:6px 0 8px; }
.dyk a { font-weight:600; text-decoration:none; font-size:15px; } .dyk a:hover { color:var(--red); }
.rand { margin-top:32px; } .rand a { font-weight:600; text-decoration:none; } .rand a:hover { color:var(--red); }
.intro p + p { margin-top:10px; }
@media (max-width:520px) { .top nav a { margin-left:12px; font-size:12px; letter-spacing:.04em; } }
footer { max-width:760px; margin:0 auto; padding:0 clamp(16px,4vw,32px) 48px; font-size:14px; color:var(--muted); }
"""


def analytics():
    if not GOATCOUNTER:
        return ""
    return (f'<script data-goatcounter="https://{GOATCOUNTER}.goatcounter.com/count" '
            'async src="//gc.zgo.at/count.js"></script>\n')


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
<meta property="og:image" content="https://bruk.city/assets/og.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#A20E00">
<link rel="icon" type="image/png" href="/favicon.png">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="stylesheet" href="/fonts/fixel.css">
<style>{CSS}</style>
{ld}{analytics()}</head>
<body>
<header class="top"><a class="brand" href="/"><img src="/assets/logo-red.svg" alt="BRUK" width="80" height="20"></a><nav><a href="/budynky/">Будинки</a><a href="/prohulianky/">Прогулянки</a><a href="/map/">Мапа</a></nav></header>
<main>
{body}
</main>
<footer>BRUK: історії київських будинків. Хто їх звів, хто в них жив і що з ними сталося. Кожен факт з джерелом.</footer>
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


def building_page(b, path, street, street_path, prev, nxt, links):
    title_main = b.get("cardHeading") or b["address"]
    title = f"{title_main} | BRUK" if ": " in title_main else f"{title_main}: історія будинку | BRUK"
    description = clip(b.get("shortText"))
    facts = [x for x in (b.get("yearBuiltCurrent") or b.get("yearBuiltOriginal"),
                         b.get("architectCurrent") or b.get("architectOriginal"),
                         b.get("styleCurrent") or b.get("styleOriginal"),
                         b.get("heritageStatus")) if x]
    body = [crumbs(("Будинки", "/budynky/"), (street, f"/{street_path}/"), (number_of(b["address"]) or b["address"], None)),
            f"<h1>{txt(title_main)}</h1>"]
    words = sum(len((b.get(f) or "").split()) for f in ("shortText", "extendedText", "notablePeople"))
    extra = [f"будинку {age} {plural(age, 'рік', 'роки', 'років')}"] if (y := exact_year(b)) and (age := YEAR - y) > 0 else []
    extra.append(f"читати {max(1, round(words / 180))} хв")
    body.append(f'<p class="meta">{txt(" · ".join(facts + extra))}</p>')
    if b.get("commonsCategory") or b.get("commonsFiles"):
        body.append(f'<div class="photos" data-cat="{esc(b.get("commonsCategory"))}" '
                    f'data-files="{esc("|".join(b.get("commonsFiles") or []))}" data-alt="{esc(b["address"])}"></div>')
    body.append(f'<div class="lead">{paras(b.get("shortText"))}</div>')
    body.append(f'<div class="btns"><a class="btn" href="/map/#b={esc(b["id"])}" data-goatcounter-click="budynok-mapa">Відкрити на мапі</a>'
                f'<a class="btn ghost" href="/story.html" data-goatcounter-click="budynok-story">Розкажи історію будинку</a>'
                f'<button class="btn ghost" type="button" data-share hidden>Поділитися</button></div>')
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
    if links.get("people"):
        body.append("<h2>Тут жили й працювали</h2><div class=\"chips\">"
                    + "".join(f'<a href="{h}">{esc(n)}</a>' for n, h in links["people"]) + "</div>")
    if links.get("walks"):
        body.append("<h2>У прогулянках</h2><div class=\"cards\">"
                    + "".join(f'<a href="{h}">{esc(t)}<span>{n} зупинок</span></a>' for t, h, n in links["walks"]) + "</div>")
    if links.get("fact"):
        f, h = links["fact"]
        body.append(f'<aside class="dyk"><b>Чи знали ви?</b><p>{txt(f["text"])}</p><a href="{h}">{esc(f["address"])} →</a></aside>')
    if links.get("nearby"):
        body.append("<h2>Поруч</h2><div class=\"cards\">"
                    + "".join(f'<a href="{h}">{txt(t)}<span>{esc(a)} · {d} м</span></a>' for t, a, h, d in links["nearby"]) + "</div>")
    body.append('<p class="rand"><a href="/budynky/" data-random data-goatcounter-click="budynok-random">Випадковий будинок →</a></p>')
    body.append('<script src="/assets/budynok.js" defer></script>')
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


def plural(n, one, few, many):
    if n % 10 == 1 and n % 100 != 11:
        return one
    return few if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else many


def dist(a, b):
    """Відстань між будинками в метрах (для кількох сотень метрів плоска формула точна)."""
    import math
    dy = (a["latitude"] - b["latitude"]) * 111320
    dx = (a["longitude"] - b["longitude"]) * 111320 * math.cos(math.radians(a["latitude"]))
    return math.hypot(dx, dy)


def exact_year(b):
    """Рік побудови, лише коли він точний: «1897» або «1897–1899» (береться перший)."""
    for f in ("yearBuiltCurrent", "yearBuiltOriginal"):
        m = re.fullmatch(r"\s*(1[6-9]\d\d|20\d\d)(\s*[–-]\s*\d{2,4})?\s*", b.get(f) or "")
        if m:
            return int(m[1])
    return None


ARCH = re.compile(r"(?:арх\.\s*|інж\.\s*)?((?:[А-ЯІЇЄҐ]\.\s*-?\s*){1,2}[А-ЯІЇЄҐ][а-яіїєґ’'-]+)")


def architects_of(b):
    names = set()
    for f in ("architectCurrent", "architectOriginal"):
        for m in ARCH.finditer(b.get(f) or ""):
            names.add(re.sub(r"\.\s+", ". ", re.sub(r"\.\s*-\s*", ".-", m[1])).strip())
    return names


def mention(name, b):
    """Речення з тексту картки, де згадано людину (за основою прізвища); інакше — початок shortText."""
    surname = re.sub(r"\(.*?\)", "", name).split()[-1]
    stem = surname[:-2] if re.search(r"(ий|ій)$", surname) else surname[:-1] if re.search(r"[аояьйе]$", surname) else surname
    for field in ("notablePeople", "shortText", "extendedText"):
        for sent in re.split(r"(?<=[.!?…])\s+", b.get(field) or ""):
            if stem in sent:
                return clip(sent, 220)
    return clip(b.get("shortText"), 160)


def people_index(walks, by_addr, buildings):
    people, seen = [], set()
    figs = OrderedDict()
    for w in walks:
        for f in w.get("figures") or []:
            if f["address"] in by_addr:
                figs.setdefault(f["name"], []).append(by_addr[f["address"]])
    for name, bs in figs.items():
        uniq = list({b["id"]: b for b in bs}.values())
        path = f"liudy/{slug(name)}"
        seen.add(path)
        people.append({"name": name, "path": path, "kind": "person", "buildings": uniq})
    arch = {}
    for b in buildings:
        for a in architects_of(b):
            arch.setdefault(a, []).append(b)
    # Одна людина буває записана по-різному: «А. Краусс» і «А.-Ф. Краусс», «С. Рикачов» і «(за участю) С. Рикачова».
    for name in sorted(arch, key=len):
        ini, sur = name.rsplit(" ", 1)
        for other in list(arch):
            o_ini, o_sur = other.rsplit(" ", 1)
            if other != name and name in arch and o_ini[:2] == ini[:2] and (
                    o_sur == sur and len(o_ini) > len(ini) or sur == o_sur + "а"):
                arch[other] = list({b["id"]: b for b in arch[other] + arch.pop(name)}.values())
    for name in sorted(arch, key=lambda n: uk_key(n.split()[-1])):
        path = f"liudy/{slug(name)}"
        if len(arch[name]) >= 2 and path not in seen:
            seen.add(path)
            people.append({"name": name, "path": path, "kind": "architect",
                           "buildings": sorted(arch[name], key=lambda b: exact_year(b) or 9999)})
    return people


def street_intro(street, items, people, walks, by_addr):
    """Вступ до сторінки вулиці — лише з даних карток, нічого не дописуємо."""
    out = []
    years = sorted(((y, b) for b in items if (y := exact_year(b))), key=lambda t: t[0])
    if len(years) >= 2:
        y0, b0 = years[0]
        out.append(f"<p>Серед описаних будинків, де відомий рік, найстаріший: "
                   f'<a href="#{esc(b0["id"])}">{esc(b0["address"])}</a> ({y0}), наймолодший зведено {years[-1][0]} року.</p>')
    ids = {b["id"] for b in items}
    arch = [x for x in people if x["kind"] == "architect" and any(b["id"] in ids for b in x["buildings"])]
    figs = [x for x in people if x["kind"] == "person" and any(b["id"] in ids for b in x["buildings"])]
    if arch:
        out.append("<p>Тут будували: " + ", ".join(f'<a href="/{x["path"]}/">{esc(x["name"])}</a>' for x in arch[:8]) + ".</p>")
    if figs:
        out.append("<p>Тут жили й працювали: " + ", ".join(f'<a href="/{x["path"]}/">{esc(x["name"])}</a>' for x in figs[:8]) + ".</p>")
    war = sum(1 for b in items if b.get("warDamage"))
    if war:
        out.append(f"<p>{war} {plural(war, 'будинок пошкоджено', 'будинки пошкоджено', 'будинків пошкоджено')} "
                   f"російськими атаками після 24 лютого 2022 року.</p>")
    ws = [w for w in walks if any(a in by_addr and by_addr[a]["id"] in ids for a in w["addresses"])]
    if ws:
        out.append('<div class="chips">' + "".join(f'<a href="/prohulianky/{slug(w["id"])}/">{esc(w["title"])}</a>' for w in ws) + "</div>")
    return f'<div class="intro">{"".join(out)}</div>' if out else ""


def walk_pages(walks, by_addr, path_of, people):
    urls, cards = [], []
    person_path = {x["name"]: x["path"] for x in people}
    for w in walks:
        path = f"prohulianky/{slug(w['id'])}"
        stops = [by_addr[a] for a in w["addresses"] if a in by_addr]
        km = sum(dist(a, b) for a, b in zip(stops, stops[1:])) / 1000
        figs = {}
        for f in w.get("figures") or []:
            figs.setdefault(f["address"], []).append(f["name"])
        rows = []
        for i, b in enumerate(stops, 1):
            who = ", ".join(f'<a href="/{person_path[n]}/">{esc(n)}</a>' for n in figs.get(b["address"], []) if n in person_path)
            rows.append(f'<li><a href="/{path_of[b["id"]]}/">{i}. {txt(b.get("cardHeading") or b["address"])}</a>'
                        f'<span>{esc(b["address"])}{" · " + who if who else ""}</span></li>')
        n = len(stops)
        meta = f"{n} {plural(n, 'зупинка', 'зупинки', 'зупинок')} · близько {km:.1f} км по прямій".replace(".", ",")
        page(path, f"{w['title']}: прогулянка Києвом | BRUK", clip(f"{w['title']}. {w.get('intro', '')}"),
             crumbs(("Прогулянки", "/prohulianky/"), (w["title"], None)) + f"<h1>{esc(w['title'])}</h1>"
             f'<p class="meta">{meta}</p><div class="lead"><p>{txt(w.get("intro"))}</p></div>'
             f'<div class="btns"><a class="btn" href="/map/#walk={esc(w["id"])}" data-goatcounter-click="walk-mapa">Пройти на мапі</a></div>'
             f'<h2>Маршрут</h2><ul class="list">{"".join(rows)}</ul>',
             [breadcrumb_ld([("Прогулянки", "/prohulianky/"), (w["title"], f"/{path}/")])])
        urls.append((path, None))
        cards.append(f'<a href="/{path}/">{esc(w["title"])}<span>{txt(clip(w.get("intro"), 110))}</span></a>')
    page("prohulianky", "Прогулянки Києвом за історіями будинків | BRUK",
         f"{len(walks)} пішохідних маршрутів центром Києва: будинки, люди й історії з джерелами.",
         f'<h1>Прогулянки</h1><p class="meta">{len(walks)} маршрутів · кожна зупинка з перевіреною історією</p>'
         f'<div class="cards">{"".join(cards)}</div>')
    return [("prohulianky", None)] + urls


def people_pages(people, walks, path_of):
    urls = []
    for x in people:
        bs = x["buildings"]
        n = len(bs)
        if x["kind"] == "architect":
            h1 = f"Архітектор {x['name']}"
            meta = f"{n} {plural(n, 'будинок', 'будинки', 'будинків')} у Києві з історіями BRUK"
            desc = f"Будинки архітектора {x['name']} у Києві: адреси, роки й історії з джерелами."
            rows = "".join(f'<li><a href="/{path_of[b["id"]]}/">{txt(b.get("cardHeading") or b["address"])}</a>'
                           f'<span>{esc(b["address"])}{" · " + str(exact_year(b)) if exact_year(b) else ""}</span></li>' for b in bs)
        else:
            h1 = x["name"]
            meta = f"{n} {plural(n, 'адреса', 'адреси', 'адрес')} у Києві"
            desc = f"{x['name']} у Києві: адреси й історії будинків, пов’язаних з цією людиною, з джерелами."
            rows = "".join(f'<li><a href="/{path_of[b["id"]]}/">{esc(b["address"])}</a>'
                           f'<span>{txt(mention(x["name"], b))}</span></li>' for b in bs)
        ws = [w for w in walks if any(f["name"] == x["name"] for f in w.get("figures") or [])]
        chips = ('<h2>У прогулянках</h2><div class="chips">'
                 + "".join(f'<a href="/prohulianky/{slug(w["id"])}/">{esc(w["title"])}</a>' for w in ws) + "</div>") if ws else ""
        page(x["path"], f"{h1}: адреси в Києві | BRUK", desc,
             crumbs(("Люди", "/liudy/"), (x["name"], None)) + f"<h1>{esc(h1)}</h1><p class=\"meta\">{meta}</p>"
             f'<ul class="list">{rows}</ul>{chips}',
             [breadcrumb_ld([("Люди", "/liudy/"), (x["name"], f"/{x['path']}/")])])
        urls.append((x["path"], None))
    figs = "".join(f'<a href="/{x["path"]}/">{esc(x["name"])}</a>' for x in people if x["kind"] == "person")
    arch = "".join(f'<a href="/{x["path"]}/">{esc(x["name"])}</a>' for x in people if x["kind"] == "architect")
    page("liudy", "Люди й архітектори Києва: адреси | BRUK",
         "Де в Києві жили письменники, науковці й митці і що збудували київські архітектори: адреси з історіями BRUK.",
         f'<h1>Люди й архітектори</h1><h2>Люди</h2><div class="chips">{figs}</div>'
         f'<h2>Архітектори</h2><div class="chips">{arch}</div>')
    return [("liudy", None)] + urls


HOME_TITLE = "<title>BRUK. Історія Києва, яка оживає</title>"
HOME_META = ('<meta name="description" content="BRUK: мапа центру Києва, де кожен будинок розповідає свою історію: '
             'хто його звів, хто в ньому жив і що з ним сталося. Коротко, тепло і з джерелами.">\n'
             '  <link rel="canonical" href="https://bruk.city/">\n'
             '  <meta property="og:title" content="BRUK. Історія Києва, яка оживає">\n'
             '  <meta property="og:description" content="Мапа центру Києва, де кожен будинок розповідає свою історію.">\n'
             '  <meta property="og:url" content="https://bruk.city/">\n'
             '  <meta property="og:type" content="website">\n')


def patch_home():
    """Опис і canonical у <head> головної (index.html), якщо їх там нема."""
    f = ROOT / "index.html"
    doc = f.read_text(encoding="utf-8")
    if 'rel="canonical"' in doc.split("</head>", 1)[0]:
        return
    i = doc.index(HOME_TITLE) + len(HOME_TITLE)
    f.write_text(doc[:i] + "\n  " + HOME_META.rstrip("\n") + doc[i:], encoding="utf-8")
    print("site_seo: index.html — додано опис і canonical, тепер запусти python3 tools/build_en.py")


def main():
    patch_home()
    buildings = [b for b in json.loads(DATA.read_text(encoding="utf-8")) if (b.get("shortText") or "").strip()]
    # Без довгих тире в заголовках (прохання авторки 20.10.2026): «Адреса — назва» → «Адреса: назва».
    for b in buildings:
        if b.get("cardHeading"):
            b["cardHeading"] = re.sub(r"\s+—\s+", ": ", b["cardHeading"], count=1).replace(" — ", ", ")
    for d in (OUT, ROOT / "prohulianky", ROOT / "liudy"):
        if d.exists():
            shutil.rmtree(d)

    streets = OrderedDict()
    for b in buildings:
        streets.setdefault(street_of(b["address"]), []).append(b)
    num = lambda b: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", number_of(b["address"]))]
    used, urls, pages = set(), [], {}

    # Перший прохід: адреса сторінки кожного будинку (потрібна для посилань «Поруч», людей і прогулянок).
    streets = OrderedDict((k, sorted(streets[k], key=num)) for k in sorted(streets, key=uk_key))
    path_of = {}
    for street, items in streets.items():
        for b in items:
            p = f"budynky/{slug(street)}/{slug(number_of(b['address'])) or slug(b['id'])}"
            if p in used:
                p = f"{p}-{slug(b['id'])}"
            used.add(p)
            path_of[b["id"]] = p
    by_addr = {b["address"]: b for b in buildings}
    walks = [w for w in json.loads(WALKS.read_text(encoding="utf-8"))
             if sum(a in by_addr for a in w["addresses"]) >= 2]
    people = people_index(walks, by_addr, buildings)
    facts = [f for f in json.loads((ROOT / "map" / "data" / "facts.json").read_text(encoding="utf-8")) if f["address"] in by_addr]
    walks_of, people_of = {}, {}
    for w in walks:
        for a in w["addresses"]:
            if a in by_addr:
                walks_of.setdefault(by_addr[a]["id"], []).append(
                    (w["title"], f"/prohulianky/{slug(w['id'])}/", sum(x in by_addr for x in w["addresses"])))
    for person in people:
        for b in person["buildings"]:
            people_of.setdefault(b["id"], []).append((person["name"], f"/{person['path']}/"))

    for street, items in streets.items():
        street_path = f"budynky/{slug(street)}"
        paths = [path_of[b["id"]] for b in items]
        for i, b in enumerate(items):
            prev = (items[i - 1]["address"], paths[i - 1]) if i else None
            nxt = (items[i + 1]["address"], paths[i + 1]) if i + 1 < len(items) else None
            close = sorted(((dist(b, o), o) for o in buildings if o["id"] != b["id"]), key=lambda t: t[0])[:3]
            links = {"people": people_of.get(b["id"]), "walks": walks_of.get(b["id"]),
                     "nearby": [(o.get("cardHeading") or o["address"], o["address"], f"/{path_of[o['id']]}/", round(d / 10) * 10)
                                for d, o in close if d < 600]}
            # «Чи знали ви?» — факт бігучого рядка про найближчий інший будинок (до 800 м)
            near_facts = sorted(((dist(b, by_addr[f["address"]]), f) for f in facts if f["address"] != b["address"]), key=lambda t: t[0])
            if near_facts and near_facts[0][0] < 800:
                f = near_facts[0][1]
                links["fact"] = (f, f"/{path_of[by_addr[f['address']]['id']]}/")
            building_page(b, paths[i], street, street_path, prev, nxt, links)
            urls.append((paths[i], b.get("factChecked")))
            pages[b["id"]] = f"/{paths[i]}/"
        rows = "".join(f'<li id="{esc(b["id"])}"><a href="/{p}/">{txt(b.get("cardHeading") or b["address"])}</a>'
                       f'<span>{txt(clip(b.get("shortText"), 120))}</span></li>' for b, p in zip(items, paths))
        n = len(items)
        word = plural(n, "будинок", "будинки", "будинків")
        page(street_path, f"{street}: історії будинків | BRUK",
             clip(f"{street}, Київ: {n} {word} з історіями: хто їх звів, хто в них жив і що з ними сталося. "
                  f"Тексти BRUK із джерелами."),
             crumbs(("Будинки", "/budynky/"), (street, None)) + f"<h1>{esc(street)}</h1>"
             f'<p class="meta">{n} {word} з історіями · <a href="/map/">відкрити мапу</a></p>'
             + street_intro(street, items, people, walks, by_addr) + f'<ul class="list">{rows}</ul>',
             [breadcrumb_ld([("Будинки", "/budynky/"), (street, f"/{street_path}/")])])
        urls.append((street_path, None))
        streets[street] = (street_path, n)

    urls += walk_pages(walks, by_addr, path_of, people)
    urls += people_pages(people, walks, path_of)

    rows = "".join(f'<li><a href="/{p}/">{esc(s)}</a> <span style="display:inline">· {n}</span></li>'
                   for s, (p, n) in streets.items())
    page("budynky", "Історії будинків Києва за вулицями | BRUK",
         f"{len(buildings)} будинків центру Києва з історіями: архітектори, власники, мешканці й події. "
         f"Вулиці від Хрещатика до Рейтарської.",
         f"<h1>Історії будинків Києва</h1><p class=\"meta\">{len(buildings)} будинків з історіями · "
         f"<a href=\"/map/\">відкрити мапу</a></p>"
         f'<div class="chips"><a href="/prohulianky/">{len(walks)} прогулянок</a><a href="/liudy/">Люди й архітектори</a></div>'
         f"<h2>Вулиці</h2><ul class=\"streets\">{rows}</ul>")
    urls.insert(0, ("budynky", None))

    head = [("", None), ("en", None), ("map", None), ("story.html", None)]
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for p, checked in head + urls:
        loc = f"{SITE}/{p}" + ("/" if p and not p.endswith(".html") else "")
        mod = f"<lastmod>{checked}</lastmod>" if checked else ""
        lines.append(f"  <url><loc>{loc}</loc>{mod}</url>")
    lines.append("</urlset>")
    # Адреси сторінок для кнопки «Поділитися» в картці на мапі (map/app.js).
    (ROOT / "map" / "data" / "pages.json").write_text(json.dumps(pages, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (ROOT / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8")
    print(f"site_seo: {len(buildings)} будинків, {len(streets)} вулиць, sitemap — {len(head) + len(urls)} адрес")


if __name__ == "__main__":
    main()

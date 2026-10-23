#!/usr/bin/env python3
"""Збирає англомовну версію сайту: index.html → en/index.html.

index.html — звичайна HTML-сторінка; картинки — в assets/, шрифти — у fonts/,
скрипт сторінки — assets/home.js (англійський — assets/home.en.js, його пише цей скрипт).
До 16.10.2026 сторінка була «бандлом» з усім вшитим усередину (8 МБ), її розпакували.
Скрипт:
  1. додає в українську сторінку перемикач мови «EN» і hreflang (якщо їх ще нема);
  2. робить копію з англійськими текстами в en/index.html і assets/home.en.js.

Запуск після БУДЬ-ЯКОЇ зміни index.html:  python3 tools/build_en.py
Якщо український текст змінився, скрипт зупиниться й покаже, якого рядка не знайшов —
тоді онови переклад у TRANSLATIONS нижче.
"""
import pathlib
import re
import sys

from site_photos import PHOTOS  # підписи фото в каруселі
from site_seo import STATS  # підписи цифр на головній
from site_typo import typo_html, uk_apos, untypo  # типографіка (tools/site_typo.py)

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "index.html"
DST = ROOT / "en" / "index.html"
JS_UK = ROOT / "assets" / "home.js"
JS_EN = ROOT / "assets" / "home.en.js"

CYRILLIC = re.compile(r"[Ѐ-ӿ]")

# ---------- перемикач мови ----------
SWITCH_CSS = """
/* Language switch (tools/build_en.py) */
.nav-right { display: flex; align-items: center; gap: 14px; }
.nav-lang { font-size: 13px; font-weight: 500; letter-spacing: 0.08em; opacity: 0.75; transition: opacity .2s; }
.nav-lang:hover { opacity: 1; }
@media (max-width: 640px) { .nav-right { gap: 10px; } .nav-lang { font-size: 12px; } }
"""
CTA = '<a href="https://www.instagram.com/bruk.kyiv/" target="_blank" rel="noopener noreferrer" class="nav-cta">Instagram →</a>'
LANG_UK = '<a class="nav-lang" href="/en/" hreflang="en" lang="en" aria-label="English version">EN</a>'
LANG_EN = '<a class="nav-lang" href="/" hreflang="uk" lang="uk" aria-label="Українська версія">UA</a>'
HREFLANG = ('<link rel="alternate" hreflang="uk" href="https://bruk.city/">\n'
            '<link rel="alternate" hreflang="en" href="https://bruk.city/en/">\n'
            '<link rel="alternate" hreflang="x-default" href="https://bruk.city/">\n')

# ---------- переклад ----------
# Опис і canonical для пошуковиків (tools/site_seo.py) і прев'ю в соцмережах.
META = [
    ('content="BRUK: мапа центру Києва, де кожен будинок розповідає свою історію: хто його звів, хто в ньому жив і що з ним сталося. Коротко, тепло і з джерелами."',
     'content="BRUK is a map of central Kyiv where every building tells its story: who built it, who lived there and what happened to it. Short, warm and with sources."'),
    ('<link rel="canonical" href="https://bruk.city/">', '<link rel="canonical" href="https://bruk.city/en/">'),
    ('content="BRUK. Історія Києва, яка оживає"', 'content="BRUK. Kyiv\'s history, coming alive"'),
    ('content="Мапа центру Києва, де кожен будинок розповідає свою історію."', 'content="A map of central Kyiv where every building tells its story."'),
    ('<meta property="og:url" content="https://bruk.city/">', '<meta property="og:url" content="https://bruk.city/en/">'),
]

# Сама сторінка. Вулиці — за українським стандартом транслітерації.
PAGE = [
    ('<li><a href="/budynky/">Усі будинки</a></li>', '<li><a href="/budynky/">All buildings</a></li>'),
    ('<html lang="uk">', '<html lang="en">'),
    ("<title>BRUK. Історія Києва, яка оживає</title>", "<title>BRUK. Kyiv's history, coming alive</title>"),
    ('aria-label="Головна навігація"', 'aria-label="Main navigation"'),
    ('href="#about">Про проєкт<', 'href="#about">About<'),
    ('href="#solution">Мапа<', 'href="#solution">Map<'),
    ('href="#app">Додаток<', 'href="#app">App<'),
    ('href="#values">Цінності<', 'href="#values">Values<'),
    # hero
    ("Історія Києва,<br>яка оживає.", "Kyiv's history,<br>coming alive."),
    (">Долучитись до запуску<", ">Join the launch<"),
    (">Подивитись мапу<", ">See the map<"),
    ("<div>Живий архів Києва</div>", "<div>A living archive of Kyiv</div>"),
    ("<div>Київ · 2026</div>", "<div>Kyiv · 2026</div>"),
    # marquee
    ("<span>фасади<span", "<span>facades<span"),
    ("</span>балкони<span", "</span>balconies<span"),
    ("</span>сходи<span", "</span>staircases<span"),
    ("</span>дахи<span", "</span>roofs<span"),
    ("</span>двори<span", "</span>courtyards<span"),
    ("</span>камінь<span", "</span>stone<span"),
    ("</span>тиньк<span", "</span>plaster<span"),
    ("</span>вікна<span", "</span>windows<span"),
    ("</span>арки<span", "</span>arches<span"),
    ("</span>пам’ять<span", "</span>memory<span"),
    # 01 problem
    ("01 · Проблема", "01 · The problem"),
    ("Київ, про який <em>мовчали</em><br>поколіннями.", "The Kyiv that was <em>kept silent</em><br>for generations."),
    ("Десятиліттями історія Києва була спотвореною, згладженою або зведеною до кількох відомих назв. Архіви горіли, кам'яниці зносили, а про двори, у яких жили поколіннями, ніхто так і не розповів.",
     "For decades, Kyiv's history was distorted, smoothed over or reduced to a handful of famous names. Archives burned, old townhouses were torn down, and nobody ever told the story of the courtyards where families lived for generations."),
    # 02 solution
    ("02 · Рішення", "02 · The solution"),
    ("Місто стає <em>інтерфейсом.</em>", "The city becomes <em>the interface.</em>"),
    ("BRUK: інтерактивна мапа Києва, де кожна підсвічена будівля відкриває свою історію: коли була зведена, хто в ній жив, що пам'ятає і чому досі стоїть.",
     "BRUK is an interactive map of Kyiv where every highlighted building opens up its story: when it was built, who lived there, what it remembers and why it is still standing."),
    ("Не енциклопедія. Не путівник. Живий архів, який прокидається від дотику.",
     "Not an encyclopedia. Not a guidebook. A living archive that wakes up at your touch."),
    ('title="BRUK: 1 місце на Hatathon 6.0 (House of Europe), 2025"',
     'title="BRUK: 1st place at Hatathon 6.0 (House of Europe), 2025"'),
    (">1 місце · Hatathon House of Europe<", ">1st place · Hatathon House of Europe<"),
    (">Подивитись у додатку<", ">See it in the app<"),
    (">Стежити в Instagram<", ">Follow on Instagram<"),
    ('<div class="map-chip tl">Київ · Центр</div>', '<div class="map-chip tl">Kyiv · City centre</div>'),
    ("№ 001 · Хрещатик", "No. 001 · Khreshchatyk"),
    ("Колись Хрещатик був долиною з річкою, а не вулицею.", "Khreshchatyk was once a valley with a river, not a street."),
    ("На місці сучасної головної вулиці колись текла річка, а довкола були луки й сади заможних київських родин.",
     "Where the city's main street runs today, a river once flowed, surrounded by meadows and the gardens of wealthy Kyiv families."),
    ('<div class="volunteer-eyebrow">Долучайся</div>', '<div class="volunteer-eyebrow">Join us</div>'),
    ("Шукаємо <em>волонтерів,</em><br>щоб збудувати це разом.", "We're looking for <em>volunteers</em><br>to build this together."),
    ("Розробники, дослідники історії, копірайтери, фотографи, архітектори: якщо Київ важливий для тебе, у нас знайдеться, над чим попрацювати разом.",
     "Developers, history researchers, copywriters, photographers, architects: if Kyiv matters to you, we'll find something to work on together."),
    (">Написати нам в Instagram →<", ">Message us on Instagram →<"),
    # 03 app
    ("03 · Мапа", "03 · The map"),
    (">Відкрити мапу →<", ">Open the map →<"),
    ('title="Жива мапа BRUK"', 'title="BRUK live map"'),
    ('aria-label="Відкрити мапу на весь екран"', 'aria-label="Open the full-screen map"'),
    (">На весь екран ↗<", ">Full screen ↗<"),
    ("У кишені, <em>як компас.</em>", "In your pocket, <em>like a compass.</em>"),
    ("<h4>Відкрий мапу</h4>", "<h4>Open the map</h4>"),
    ("3D-мапа центру Києва завантажується за секунди.", "A 3D map of central Kyiv loads in seconds."),
    ("<h4>Натисни на будівлю</h4>", "<h4>Tap a building</h4>"),
    ("Підсвічуються тільки будинки з перевіреними історіями.", "Only buildings with verified stories are highlighted."),
    ("<h4>Дізнайся історію</h4>", "<h4>Discover its story</h4>"),
    ("Маєток Онуфрія Головинського", "Onufrii Holovynskyi's estate"),
    ("1797 · ранній класицизм / ампір", "1797 · early Classicism / Empire"),
    ("Одна з перших знакових споруд на Хрещатику і фактичний початок забудови майбутньої головної вулиці Києва. У той час Хрещатик ще не був міським бульваром. Це була напівпорожня долина між історичними частинами міста. Головинський звів тут двоповерховий палацовий будинок у стилі раннього класицизму / ампіру.",
     "One of the first landmark buildings on Khreshchatyk and, in effect, the beginning of what would become Kyiv's main street. Back then Khreshchatyk was not yet a city boulevard but a half-empty valley between the historic parts of town. Holovynskyi built a two-storey palace-like house here in the early Classicist / Empire style."),
    ("<span>Класицизм</span><span>Ампір</span>", "<span>Classicism</span><span>Empire</span>"),
    ('<div class="cta">Читати історію →</div>', '<div class="cta">Read the story →</div>'),
    # 04 gallery
    ("04 · Архів", "04 · The archive"),
    ("Сотні <em>фасадів</em>,<br>одне місто.", "Hundreds of <em>facades</em>,<br>one city."),
    # 04 archive: carousel captions come from tools/site_photos.py
    *[(f'data-title="{uk}"', f'data-title="{en}"') for _, _, uk, en in PHOTOS],
    ('alt="Фото: ', 'alt="Photo: '),
    ('>Фото: ', '>Photo: '),
    ('aria-label="Попереднє"', 'aria-label="Previous"'),
    ('aria-label="Пауза"', 'aria-label="Pause"'),
    ('aria-label="Наступне"', 'aria-label="Next"'),
    # 05 values
    ("05 · Цінності", "05 · Values"),
    ("Ми стоїмо на <em>бруківці.</em>", "We stand on <em>cobblestones.</em>"),
    ('<div class="name">Відкритість</div>', '<div class="name">Openness</div>'),
    ('<div class="name">Повага до пам\'яті</div>', '<div class="name">Respect for memory</div>'),
    ('<div class="name">Ненудна освіта</div>', '<div class="name">Learning that isn’t boring</div>'),
    ('<div class="name">Малі історії мають значення</div>', '<div class="name">Small stories matter</div>'),
    ('<div class="name">Нове українське бачення</div>', '<div class="name">A new Ukrainian vision</div>'),
    # Посилання на форму історії (story.html — українською)
    ('href="/story.html">Розповісти історію<', 'href="/story.html" hreflang="uk">Share a story<'),
    # footer
    ("<p>Місто, що говорить через будинки.</p>", "<p>A city that speaks through its buildings.</p>"),
    ("<h5>Проєкт</h5>", "<h5>Project</h5>"),
    ('href="#about">Про BRUK<', 'href="#about">About BRUK<'),
    ('<li><a href="/metodolohiia.html">Як ми працюємо</a></li>', '<li><a href="/metodolohiia.html#en">How we work</a></li>'),
    ('<div class="k">Співпраця та партнерство</div>', '<div class="k">Collaboration and partnerships</div>'),
    (">Написати листа →<", ">Email us →<"),
    ('<div>Тексти: <a href="/metodolohiia.html#license"', '<div>Texts: <a href="/metodolohiia.html#en"'),
    ('<a href="/privacy.html" style="text-decoration:underline;">Політика конфіденційності</a>',
     '<a href="/privacy.html#en" style="text-decoration:underline;">Privacy policy</a>'),
    ("<div>Зроблено в Києві, для Києва</div>", "<div>Made in Kyiv, for Kyiv</div>"),
]

# Скрипт сторінки (історія в анімованому телефоні).
SCRIPT = [
    ('k: "№ 001 · Хрещатик"', 'k: "No. 001 · Khreshchatyk"'),
    ('t: "Маєток Онуфрія Головинського"', 't: "Onufrii Holovynskyi\'s estate"'),
    ('a: "1797 · ранній класицизм / ампір"', 'a: "1797 · early Classicism / Empire"'),
    ('txt: "Одна з перших знакових споруд на Хрещатику і фактичний початок забудови майбутньої головної вулиці Києва. У той час Хрещатик ще не був міським бульваром. Це була напівпорожня долина між історичними частинами міста. Головинський звів тут двоповерховий палацовий будинок у стилі раннього класицизму / ампіру."',
     'txt: "One of the first landmark buildings on Khreshchatyk and, in effect, the beginning of what would become Kyiv\'s main street. Back then Khreshchatyk was not yet a city boulevard but a half-empty valley between the historic parts of town. Holovynskyi built a two-storey palace-like house here in the early Classicist / Empire style."'),
    ('chips: ["Класицизм", "Ампір", "1797"]', 'chips: ["Classicism", "Empire", "1797"]'),
    ('"Вас додано ✓"', '"You’re on the list ✓"'),
    ('"Приєднатися"', '"Join"'),
]


STAT_TILE = re.compile(r'(<a class="stat" href="([^"]+)"><div class="k">(\d+)</div><div class="l">)([^<]*)(</div>)')


def translate_stats(text):
    """Цифри пише tools/site_seo.py, і форма слова залежить від числа, тому перекладаємо за STATS."""
    tiles = STAT_TILE.findall(text)
    if len(tiles) != len(STATS):
        fail(f"на головній {len(tiles)} цифр замість {len(STATS)} (запусти python3 tools/site_seo.py)")
    for (head, href, n, uk, tail), (s_href, s_uk, (one, many)) in zip(tiles, STATS):
        if href != s_href or uk not in s_uk:
            fail(f"цифра «{n} {uk}» не збігається з STATS у tools/site_seo.py")
        text = text.replace(head + uk + tail, head + (one if n == "1" else many) + tail, 1)
    return text


def fail(msg):
    sys.exit("build_en: " + msg)


def translate(text, pairs, where):
    for uk, en in pairs:
        if uk not in text and uk_apos(uk) in text:
            uk = uk_apos(uk)  # site_typo.py міняє ' на ’
        if uk not in text:
            fail(f"у {where} не знайдено рядка (змінився український текст?):\n  {uk[:120]}")
        text = text.replace(uk, en)
    return text


def add_switch(tpl, lang_link):
    if 'class="nav-lang"' not in tpl:
        if CTA not in tpl:
            fail("не знайшла кнопку Instagram у навігації")
        tpl = tpl.replace(CTA, f'<div class="nav-right">\n    {lang_link}\n    {CTA}\n  </div>', 1)
        i = tpl.rfind("</style>")
        tpl = tpl[:i] + SWITCH_CSS + tpl[i:]
    if 'hreflang="x-default"' not in tpl:
        tpl = tpl.replace("</head>", HREFLANG + "</head>", 1)
    return tpl


def main():
    page = SRC.read_text(encoding="utf-8")
    if "__bundler/" in page:
        fail("index.html знову бандл — його треба розпакувати (див. README, «Головна сторінка»)")

    # 1. Перемикач в українській версії.
    page_uk = add_switch(page, LANG_UK)
    if page_uk != page:
        SRC.write_text(page_uk, encoding="utf-8")
        print("index.html: додано перемикач EN")

    # 2. Англійська версія.
    en = untypo(page_uk).replace(LANG_UK, LANG_EN)
    en = translate(en, META, "описі для пошуковиків")
    en = translate(en, PAGE, "сторінці")
    en = translate_stats(en)
    if en.count('src="/assets/home.js"') != 1:
        fail("не знайшла <script src=\"/assets/home.js\">")
    en = en.replace('src="/assets/home.js"', 'src="/assets/home.en.js"')
    i = en.find("<body")
    en = en[:i] + typo_html(en[i:])
    rest = CYRILLIC.search(en.replace(LANG_EN, ""))
    if rest:
        i = rest.start()
        fail("у сторінці лишився неперекладений текст: …" + en.replace(LANG_EN, "")[max(0, i - 60):i + 60])

    js = translate(JS_UK.read_text(encoding="utf-8"), SCRIPT, "скрипті")
    if CYRILLIC.search(js):
        fail("у скрипті лишився неперекладений текст")
    JS_EN.write_text(js, encoding="utf-8")

    DST.parent.mkdir(exist_ok=True)
    DST.write_text(en, encoding="utf-8")
    print(f"{DST.relative_to(ROOT)}: готово ({len(en.encode()) // 1024} КБ)")


if __name__ == "__main__":
    main()

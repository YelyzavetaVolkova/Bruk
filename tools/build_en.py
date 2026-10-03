#!/usr/bin/env python3
"""Збирає англомовну версію сайту: index.html → en/index.html.

index.html — це «бандл»: зовнішня оболонка + сторінка в <script type="__bundler/template">
+ картинки, шрифти й скрипт у <script type="__bundler/manifest">.
Скрипт:
  1. додає в українську сторінку перемикач мови «EN» і hreflang (якщо їх ще нема);
  2. робить копію з англійськими текстами в en/index.html.

Запуск після БУДЬ-ЯКОЇ зміни index.html:  python3 tools/build_en.py
Якщо український текст змінився, скрипт зупиниться й покаже, якого рядка не знайшов —
тоді онови переклад у TRANSLATIONS нижче.
"""
import base64
import gzip
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "index.html"
DST = ROOT / "en" / "index.html"
SCRIPT_UUID = "1e4d953e-ce13-424c-9286-e2a251a7a89f"  # JS сторінки в маніфесті

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
# Оболонка бандла (екран завантаження).
SHELL = [
    ("<!DOCTYPE html>\n<html>", '<!DOCTYPE html>\n<html lang="en">'),
    ("<title>BRUK — Історія Києва, яка оживає</title>", "<title>BRUK — Kyiv's history, coming alive</title>"),
    ("'помилка: бракує даних'", "'error: missing data'"),
    ("'розпаковуємо ' + uuids.length + ' артефактів'", "'unpacking ' + uuids.length + ' assets'"),
    ("'монтуємо сцену'", "'building the page'"),
    ("'помилка: ' + err.message", "'error: ' + err.message"),
]

# Сама сторінка. Вулиці — за українським стандартом транслітерації.
PAGE = [
    ('<html lang="uk">', '<html lang="en">'),
    ("<title>BRUK — Історія Києва, яка оживає</title>", "<title>BRUK — Kyiv's history, coming alive</title>"),
    ('aria-label="Головна навігація"', 'aria-label="Main navigation"'),
    ('href="#about">Про проєкт<', 'href="#about">About<'),
    ('href="#solution">Мапа<', 'href="#solution">Map<'),
    ('href="#app">Додаток<', 'href="#app">App<'),
    ('href="#values">Цінності<', 'href="#values">Values<'),
    # hero
    ("Історія Києва,<br>яка оживає.", "Kyiv's history,<br>coming alive."),
    ("Інтерактивна мапа міста, де кожен будинок — початок історії. Без підручників. Без туристичних кліше.",
     "An interactive map of the city where every building is the start of a story. No textbooks. No tourist clichés."),
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
    ("Десятиліттями історія Києва була спотвореною, згладженою або зведеною до кількох відомих назв. Архіви горіли, кам'яниці зносили, а про двори, у яких жили поколіннями — ніхто так і не розповів.",
     "For decades, Kyiv's history was distorted, smoothed over or reduced to a handful of famous names. Archives burned, old townhouses were torn down, and nobody ever told the story of the courtyards where families lived for generations."),
    ('<span class="tag">Поділ</span>', '<span class="tag">Podil</span>'),
    ('<span class="tag">Хрещатик</span>', '<span class="tag">Khreshchatyk</span>'),
    ('<span class="tag">Андріївський узвіз</span>', '<span class="tag">Andriivskyi Descent</span>'),
    ('<span class="tag">Ярославів Вал · 1902</span>', '<span class="tag">Yaroslaviv Val · 1902</span>'),
    ('<span class="tag">Прорізна</span>', '<span class="tag">Prorizna</span>'),
    ('<span class="tag">Саксаганського</span>', '<span class="tag">Saksahanskoho</span>'),
    # 02 solution
    ("02 · Рішення", "02 · The solution"),
    ("Місто стає <em>інтерфейсом.</em>", "The city becomes <em>the interface.</em>"),
    ("BRUK — це інтерактивна мапа Києва, де кожна підсвічена будівля відкриває свою історію: коли була зведена, хто в ній жив, що пам'ятає і чому досі стоїть.",
     "BRUK is an interactive map of Kyiv where every highlighted building opens up its story: when it was built, who lived there, what it remembers and why it is still standing."),
    ("Не енциклопедія. Не путівник. Живий архів, який прокидається від дотику.",
     "Not an encyclopedia. Not a guidebook. A living archive that wakes up at your touch."),
    (">Подивитись у додатку<", ">See it in the app<"),
    (">Стежити в Instagram<", ">Follow on Instagram<"),
    ('<div class="map-chip tl">Київ · Центр</div>', '<div class="map-chip tl">Kyiv · City centre</div>'),
    ("№ 001 · Хрещатик", "No. 001 · Khreshchatyk"),
    ("Колись Хрещатик був долиною з річкою, а не вулицею.", "Khreshchatyk was once a valley with a river, not a street."),
    ("На місці сучасної головної вулиці колись текла річка, а довкола — луки й сади заможних київських родин.",
     "Where the city's main street runs today, a river once flowed, surrounded by meadows and the gardens of wealthy Kyiv families."),
    ('<div class="volunteer-eyebrow">Долучайся</div>', '<div class="volunteer-eyebrow">Join us</div>'),
    ("Шукаємо <em>волонтерів,</em><br>щоб збудувати це разом.", "We're looking for <em>volunteers</em><br>to build this together."),
    ("Розробники, дослідники історії, копірайтери, фотографи, архітектори — якщо Київ важливий для тебе, у нас знайдеться, над чим попрацювати разом.",
     "Developers, history researchers, copywriters, photographers, architects: if Kyiv matters to you, we'll find something to work on together."),
    (">Написати нам в Instagram →<", ">Message us on Instagram →<"),
    # 03 app
    ("03 · Мапа", "03 · The map"),
    (">Відкрити мапу →<", ">Open the map →<"),
    ('title="Жива мапа BRUK"', 'title="BRUK live map"'),
    ("У кишені, <em>як компас.</em>", "In your pocket, <em>like a compass.</em>"),
    ("Відкрий мапу — і місто стане інтерактивним. Натисни на підсвічений будинок, щоб прочитати його історію. Усе на одному екрані, без реєстрації.",
     "Open the map and the city becomes interactive. Tap a highlighted building to read its story. All on one screen, no sign-up."),
    ("<h4>Відкрий мапу</h4>", "<h4>Open the map</h4>"),
    ("3D-мапа центру Києва завантажується за секунди. Жодних акаунтів.", "A 3D map of central Kyiv loads in seconds. No accounts."),
    ("<h4>Натисни на будівлю</h4>", "<h4>Tap a building</h4>"),
    ("Підсвічуються тільки будинки з готовими історіями.", "Only buildings with finished stories are highlighted."),
    ("<h4>Дізнайся історію</h4>", "<h4>Discover its story</h4>"),
    ("Короткий текст із фото, аудіо або архівним документом.", "A short text with a photo, audio or an archival document."),
    ("Маєток Онуфрія Головинського", "Onufrii Holovynskyi's estate"),
    ("1797 · ранній класицизм / ампір", "1797 · early Classicism / Empire"),
    ("Одна з перших знакових споруд на Хрещатику і фактичний початок забудови майбутньої головної вулиці Києва. У той час Хрещатик ще не був міським бульваром — це була напівпорожня долина між історичними частинами міста. Головинський звів тут двоповерховий палацовий будинок у стилі раннього класицизму / ампіру.",
     "One of the first landmark buildings on Khreshchatyk and, in effect, the beginning of what would become Kyiv's main street. Back then Khreshchatyk was not yet a city boulevard but a half-empty valley between the historic parts of town. Holovynskyi built a two-storey palace-like house here in the early Classicist / Empire style."),
    ("<span>Класицизм</span><span>Ампір</span>", "<span>Classicism</span><span>Empire</span>"),
    ('<div class="cta">Читати історію →</div>', '<div class="cta">Read the story →</div>'),
    # 04 gallery
    ("04 · Архів", "04 · The archive"),
    ("Сотні <em>фасадів</em><br>— одне місто.", "Hundreds of <em>facades</em><br>— one city."),
    ('data-title="Ярославів Вал"', 'data-title="Yaroslaviv Val"'),
    ('data-title="Хрещатик"', 'data-title="Khreshchatyk"'),
    ('data-title="Андріївський"', 'data-title="Andriivskyi"'),
    ('data-title="Прорізна"', 'data-title="Prorizna"'),
    ('data-title="Саксаганського"', 'data-title="Saksahanskoho"'),
    ('data-title="Центр"', 'data-title="City centre"'),
    ('data-title="Старе місто"', 'data-title="Old Town"'),
    ('data-title="Поділ"', 'data-title="Podil"'),
    ('data-title="Прибутковий дім"', 'data-title="Apartment house"'),
    ('data-title="Готель Салют"', 'data-title="Hotel Salut"'),
    ('data-title="Палацовий будинок"', 'data-title="Palace house"'),
    ("<span>Ярославів Вал</span>", "<span>Yaroslaviv Val</span>"),
    ("<span>Хрещатик</span>", "<span>Khreshchatyk</span>"),
    ("<span>Андріївський</span>", "<span>Andriivskyi</span>"),
    ("<span>Прорізна</span>", "<span>Prorizna</span>"),
    ("<span>Саксаганського</span>", "<span>Saksahanskoho</span>"),
    ("<span>Центр</span>", "<span>City centre</span>"),
    ("<span>Старе місто</span>", "<span>Old Town</span>"),
    ("<span>Поділ</span>", "<span>Podil</span>"),
    ("<span>Печерськ</span>", "<span>Pechersk</span>"),
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
    # 06 FAQ
    ("Що люди <em>питають.</em>", "What people <em>ask.</em>"),
    ("Якщо ваше питання тут не знайшло себе — напишіть нам у ", "If you can’t find your question here, message us on "),
    ("Що таке BRUK?", "What is BRUK?"),
    ("Інтерактивна мапа Києва, у якій кожен підсвічений будинок — початок короткої історії. Платформа, створена для того, щоб повернути місту власний голос і зробити його архів живим та доступним.",
     "An interactive map of Kyiv where every highlighted building is the start of a short story. A platform made to give the city back its own voice and to make its archive alive and accessible."),
    ("Це для туристів чи для киян?", "Is it for tourists or for Kyivans?"),
    ("І для тих, і для інших. BRUK розроблений для киян, яким бракує відчуття коренів, і для гостей, яким бракує глибини.",
     "Both. BRUK is made for Kyivans who miss a sense of their roots, and for visitors who want more depth."),
    ("Чи буде англомовна версія?", "Is there an English version?"),
    ("Так. Від запуску — двомовна платформа: українська як основна, англійська як повноцінний паралельний шар.",
     "Yes. BRUK is bilingual from launch: Ukrainian is the primary language, and English is a full parallel layer."),
    ("Чи можна додавати власні історії?", "Can I add my own stories?"),
    ("Так. Після фази запуску ми відкриваємо модерований канал community curation — для істориків, краєзнавців і просто сусідів, які хочуть розказати про свій двір.",
     "Yes. After the launch phase we will open a moderated community curation channel for historians, local history enthusiasts and neighbours who simply want to tell the story of their courtyard."),
    ("Як долучитися як партнер?", "How can I become a partner?"),
    ("Напишіть нам у <a", "Message us on <a"),
    (" — ми відповідаємо протягом тижня.", " and we’ll reply within a week."),
    # footer
    ("<p>Місто, що говорить через будинки.</p>", "<p>A city that speaks through its buildings.</p>"),
    ("<h5>Проєкт</h5>", "<h5>Project</h5>"),
    ('href="#about">Про BRUK<', 'href="#about">About BRUK<'),
    ('<div class="k">Співпраця та партнерство</div>', '<div class="k">Collaboration and partnerships</div>'),
    (">Написати в Instagram →<", ">Message us on Instagram →<"),
    ('<a href="/privacy.html" style="text-decoration:underline;">Політика конфіденційності</a>',
     '<a href="/privacy.html#en" style="text-decoration:underline;">Privacy policy</a>'),
    ("<div>Зроблено в Києві, для Києва</div>", "<div>Made in Kyiv, for Kyiv</div>"),
]

# Скрипт сторінки (історія в анімованому телефоні).
SCRIPT = [
    ('k: "№ 001 · Хрещатик"', 'k: "No. 001 · Khreshchatyk"'),
    ('t: "Маєток Онуфрія Головинського"', 't: "Onufrii Holovynskyi\'s estate"'),
    ('a: "1797 · ранній класицизм / ампір"', 'a: "1797 · early Classicism / Empire"'),
    ('txt: "Одна з перших знакових споруд на Хрещатику і фактичний початок забудови майбутньої головної вулиці Києва. У той час Хрещатик ще не був міським бульваром — це була напівпорожня долина між історичними частинами міста. Головинський звів тут двоповерховий палацовий будинок у стилі раннього класицизму / ампіру."',
     'txt: "One of the first landmark buildings on Khreshchatyk and, in effect, the beginning of what would become Kyiv\'s main street. Back then Khreshchatyk was not yet a city boulevard but a half-empty valley between the historic parts of town. Holovynskyi built a two-storey palace-like house here in the early Classicist / Empire style."'),
    ('chips: ["Класицизм", "Ампір", "1797"]', 'chips: ["Classicism", "Empire", "1797"]'),
    ('"Вас додано ✓"', '"You’re on the list ✓"'),
    ('"Приєднатися"', '"Join"'),
]


def fail(msg):
    sys.exit("build_en: " + msg)


def translate(text, pairs, where):
    for uk, en in pairs:
        if uk not in text:
            fail(f"у {where} не знайдено рядка (змінився український текст?):\n  {uk[:120]}")
        text = text.replace(uk, en)
    return text


def block(html, kind):
    m = re.search(r'(<script type="__bundler/%s">)(.*?)(</script>)' % kind, html, re.S)
    if not m:
        fail(f"нема блоку __bundler/{kind}")
    return m


def put_block(html, kind, content):
    m = block(html, kind)
    return html[:m.start(2)] + content + html[m.end(2):]


def dump_template(tpl):
    return json.dumps(tpl, ensure_ascii=False).replace("</", "<\\/")


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
    html = SRC.read_text(encoding="utf-8")

    # 1. Перемикач в українській версії.
    tpl = json.loads(block(html, "template").group(2))
    tpl_uk = add_switch(tpl, LANG_UK)
    if tpl_uk != tpl:
        html = put_block(html, "template", dump_template(tpl_uk))
        SRC.write_text(html, encoding="utf-8")
        print("index.html: додано перемикач EN")

    # 2. Англійська версія.
    tpl_en = tpl_uk.replace(LANG_UK, LANG_EN)
    tpl_en = translate(tpl_en, PAGE, "сторінці")
    rest = CYRILLIC.findall(tpl_en.replace(LANG_EN, ""))
    if rest:
        i = CYRILLIC.search(tpl_en.replace(LANG_EN, "")).start()
        fail("у сторінці лишився неперекладений текст: …" + tpl_en.replace(LANG_EN, "")[max(0, i - 60):i + 60])

    manifest = json.loads(block(html, "manifest").group(2))
    entry = manifest[SCRIPT_UUID]
    js = base64.b64decode(entry["data"])
    if entry.get("compressed"):
        js = gzip.decompress(js)
    js = translate(js.decode("utf-8"), SCRIPT, "скрипті")
    if CYRILLIC.search(js):
        fail("у скрипті лишився неперекладений текст")
    data = js.encode("utf-8")
    if entry.get("compressed"):
        data = gzip.compress(data, mtime=0)
    manifest[SCRIPT_UUID] = dict(entry, data=base64.b64encode(data).decode("ascii"))

    m = block(html, "template")
    shell_head = translate(html[:block(html, "manifest").start()], SHELL, "оболонці")
    out = shell_head + html[block(html, "manifest").start():]
    out = put_block(out, "manifest", json.dumps(manifest))
    out = put_block(out, "template", dump_template(tpl_en))
    if CYRILLIC.search(out.replace(json.dumps(LANG_EN, ensure_ascii=False)[1:-1].replace("</", "<\\/"), "")):
        fail("у en/index.html лишилася кирилиця")

    DST.parent.mkdir(exist_ok=True)
    DST.write_text(out, encoding="utf-8")
    print(f"{DST.relative_to(ROOT)}: готово ({len(out) // 1024} КБ)")


if __name__ == "__main__":
    main()

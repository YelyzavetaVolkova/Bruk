#!/usr/bin/env python3
"""Лічильник відвідувань GoatCounter на всіх сторінках bruk.city.

GoatCounter — безкоштовна аналітика без cookie і без банера згоди: рахує перегляди,
звідки прийшли люди й на які кнопки тиснули (атрибут data-goatcounter-click).
Код — це назва сайту в GoatCounter: https://<код>.goatcounter.com.

Запуск з кореня репозиторію:  python3 tools/site_analytics.py <код>
Скрипт вписує код у tools/site_seo.py (сторінки будинків, прогулянок, людей),
додає лічильник у головну, мапу, форму, політику й 404 і дописує абзац у політику.
Повторний запуск нічого не дублює. Після нього: python3 tools/site_seo.py і python3 tools/build_en.py
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGES = ["index.html", "map/index.html", "story.html", "privacy.html", "404.html"]
MARK = "<!-- goatcounter -->"
# У політиці після прийменників стоять нерозривні пробіли (site_typo), тож шукаємо з будь-яким пробілом.
OLD_PRIVACY = r"Сайт\s+не\s+використовує\s+файлів\s+cookie,\s+аналітики\s+чи\s+рекламних\s+трекерів\."
OLD_PRIVACY_EN = r"The\s+website\s+uses\s+no\s+cookies,\s+analytics\s+or\s+advertising\s+trackers;"
NEW_PRIVACY = ("Сайт не використовує файлів cookie чи рекламних трекерів. Щоб розуміти, які сторінки читають, "
               "ми рахуємо перегляди через GoatCounter: без cookie, без профілів відвідувачів і без збереження IP-адреси. "
               "Видно лише загальні числа: скільки разів відкрили сторінку, з якого сайту прийшли, тип пристрою й країну.")
NEW_PRIVACY_EN = ("The website uses no cookies or advertising trackers. To see which pages people read, we count visits "
                  "with GoatCounter: no cookies, no visitor profiles and no stored IP addresses, only totals such as "
                  "page views, referring sites, device type and country;")


def main(code):
    if not re.fullmatch(r"[a-z0-9-]+", code):
        sys.exit("код — латиницею, як у адресі <код>.goatcounter.com")
    snippet = f'{MARK}<script data-goatcounter="https://{code}.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>\n'
    seo = ROOT / "tools" / "site_seo.py"
    seo.write_text(re.sub(r'^GOATCOUNTER = ".*"$', f'GOATCOUNTER = "{code}"', seo.read_text(encoding="utf-8"), flags=re.M), encoding="utf-8")
    for name in PAGES:
        f = ROOT / name
        doc = f.read_text(encoding="utf-8")
        doc = re.sub(re.escape(MARK) + r".*\n", "", doc)
        doc = doc.replace("</head>", snippet + "</head>", 1)
        if name == "privacy.html":
            doc = re.sub(OLD_PRIVACY, NEW_PRIVACY, doc)
            doc = re.sub(OLD_PRIVACY_EN, NEW_PRIVACY_EN, doc)
        f.write_text(doc, encoding="utf-8")
    print(f"site_analytics: {code}.goatcounter.com — тепер python3 tools/site_seo.py і python3 tools/build_en.py")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])

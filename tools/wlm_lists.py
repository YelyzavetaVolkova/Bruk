#!/usr/bin/env python3
"""Фільтр «Вікі любить пам'ятки» на веб-мапі: які картки BRUK є у списках WLM.

Запуск з кореня репозиторію (після sync_map_data.py, бо зіставляє з map/data/buildings.json):
    python3 tools/wlm_lists.py            # завантажити списки з uk.wikipedia і зіставити
    python3 tools/wlm_lists.py <тека>     # взяти вже завантажені списки (JSON з API) з теки

Пише map/data/wlm.json: адреса картки → записи зі списків (ID пам'ятки, назва).
Зіставлення за вулицею й номером будинку (як фото з WLM у bruk-app), плюс картки,
чия commonsCategory — це «галерея» запису у списку. Таблички, пам'ятники, надгробки
й археологію пропускаємо: фільтр про будинки.
"""
import json
import math
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PREFIX = "Вікіпедія:Вікі_любить_пам'ятки/Київ/"
LISTS = [
    "Печерський_район_(А–В)", "Печерський_район_(Г–Л)", "Печерський_район_(М)", "Печерський_район_(Н–Я)",
    "Подільський_район_(А–В)", "Подільський_район_(Г–П)", "Подільський_район_(Р–Я)",
]
API = "https://uk.wikipedia.org/w/api.php?action=query&prop=revisions&rvprop=content&rvslots=main&format=json&formatversion=2&titles="
SKIP = re.compile(r"Меморіальна дошка|Пам'ятн|Пам'ятник|Скульптур|Надгроб|Могил|Культурний шар|Погруддя|Городище|Поселення", re.I)
STREET_TYPES = r"(вулиця|вул\.|провулок|пров\.|бульвар|бул\.|бульв\.|площа|пл\.|узвіз|узв\.|проспект|просп\.|шосе|набережна|тупик|алея|майдан)"
LATIN = str.maketrans("ABCEHIKMOPTXaceiopx", "АВСЕНІКМОРТХасеіорх")


def load_page(title: str, cache: Path | None) -> str:
    if cache:
        data = json.loads((cache / f"{title}.json").read_text(encoding="utf-8"))
    else:
        url = API + urllib.parse.quote(PREFIX + title)
        req = urllib.request.Request(url, headers={"User-Agent": "BRUK-map/1.0 (https://bruk.city)"})
        for attempt in range(6):
            try:
                with urllib.request.urlopen(req) as r:
                    data = json.load(r)
                break
            except urllib.error.HTTPError as e:
                if e.code != 429 or attempt == 5:
                    raise
                # Вікіпедія обмежує частоту запитів: чекаємо, скільки просить, або дедалі довше
                time.sleep(int(e.headers.get("Retry-After") or 0) or 10 * 2 ** attempt)
        time.sleep(5)
    return data["query"]["pages"][0]["revisions"][0]["slots"]["main"]["content"]


def parse_rows(text: str) -> list[dict]:
    rows = []
    for m in re.finditer(r"\{\{ВЛП-рядок(.*?)\n\}\}", text, re.S):
        row, key = {}, None
        for line in m.group(1).split("\n"):
            kv = re.match(r"\s*\|\s*([^=|]+?)\s*=\s*(.*)$", line)
            if kv:
                key = kv.group(1)
                row[key] = kv.group(2).strip()
            elif key and line.strip():
                row[key] += " " + line.strip()
        rows.append(row)
    return rows


def unlink(s: str) -> str:
    return re.sub(r"\[\[([^\]|]*\|)?([^\]]*)\]\]", r"\2", s)


def street_key(s: str) -> str:
    s = unlink(s).replace("&nbsp;", " ").replace("’", "'").replace("ʼ", "'")
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(STREET_TYPES, " ", s, flags=re.I)
    return re.sub(r"\s+", " ", s).strip().lower()


def num_key(n: str) -> str:
    n = n.translate(LATIN).lower().replace(" ", "").replace("—", "-").replace("–", "-")
    return re.sub(r"(\d)-?([а-яієї])\b", r"\1\2", n)


def same_street(card: str, wlm: str, raw: str) -> bool:
    # «Городецького» = «Архітектора Городецького»; стара назва в дужках теж рахується.
    old = re.findall(r"\(([^()]*)\)", re.sub(r"\[\[[^\]]*\]\]", "", raw).lower())
    return card == wlm or wlm.endswith(" " + card) or card.endswith(" " + wlm) or card in old


def distance_m(lat1, lon1, lat2, lon2) -> float:
    return math.hypot((lat1 - lat2) * 111000, (lon1 - lon2) * 111000 * math.cos(math.radians(50.45)))


def main(cache: Path | None = None) -> None:
    buildings = json.loads((ROOT / "map/data/buildings.json").read_text(encoding="utf-8"))
    cards = []  # (картка, ключ вулиці, номер)
    for b in buildings:
        if "," not in b["address"]:
            continue
        street, number = b["address"].rsplit(",", 1)
        for s in re.split(r"\s+—\s+", street):
            cards.append((b, street_key(s), num_key(number.strip())))

    found: dict[str, list] = {}
    for title in LISTS:
        for row in parse_rows(load_page(title, cache)):
            name = unlink(row.get("назва", ""))
            if SKIP.search(name):
                continue
            hits = set()
            address = row.get("адреса", "")
            # Головна адреса і кутові в дужках: «вул. А, 5 (вул. Б, 2)»
            for part in [re.sub(r"\([^()]*\)", "", address)] + re.findall(r"\(([^()]*,\s*\d[^()]*)\)", address):
                m = re.match(r"(.*?),\s*(\d[\d\-–—/А-Яа-яІіЄєЇї ]*)", part)
                if not m:
                    continue
                skey, number = street_key(m.group(1)), num_key(m.group(2).strip())
                for b, ckey, cnum in cards:
                    if not same_street(ckey, skey, address):
                        continue
                    if cnum != number and cnum.split("/")[0] != number and number.split("/")[0] != cnum:
                        continue
                    try:
                        if distance_m(float(row["широта"]), float(row["довгота"]), b["latitude"], b["longitude"]) > 300:
                            continue
                    except (KeyError, ValueError):
                        pass
                    hits.add(b["address"])
            gallery = row.get("галерея", "").strip()
            if gallery:
                hits |= {b["address"] for b in buildings if b.get("commonsCategory") == gallery}
            for a in hits:
                entry = {"id": row.get("ID", ""), "name": name}
                if entry not in found.setdefault(a, []):
                    found[a].append(entry)

    out = {
        "lists": [{"title": t.replace("_", " "), "url": "https://uk.wikipedia.org/wiki/" + urllib.parse.quote(PREFIX + t)} for t in LISTS],
        "buildings": dict(sorted(found.items())),
    }
    path = ROOT / "map/data/wlm.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wlm.json: {len(found)} карток у списках «Вікі любить пам'ятки»")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else None)

#!/usr/bin/env python3
"""Копіює дані застосунку BRUK у веб-мапу bruk.city/map.

Запуск з кореня цього репозиторію, коли поруч лежить bruk-app:
    python3 tools/sync_map_data.py ../bruk-app

Береться buildings.json, facts.json і filters.json з bruk-app/Bruk.
Заодно пишеться home-facts.json — факти для бігучого рядка на головній
(українською й англійською, з id будинку для посилання на мапу).
Наприкінці перегенеровуються сторінки будинків budynky/… і sitemap.xml (tools/site_seo.py).
Дані сайт завжди бере з мережі, кеш — лише запас на випадок без інтернету.
"""
import json
import shutil
import sys
from pathlib import Path

FILES = ["buildings.json", "facts.json", "filters.json"]

def main() -> None:
    app = Path(sys.argv[1] if len(sys.argv) > 1 else "../bruk-app") / "Bruk"
    target = Path(__file__).resolve().parent.parent / "map" / "data"
    target.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        src = app / name
        data = json.loads(src.read_text(encoding="utf-8"))  # заодно перевіряємо, що JSON цілий
        shutil.copyfile(src, target / name)
        print(f"{name}: {len(data)} записів")
    write_home_facts(app, target)
    import site_seo  # сторінки будинків для пошуковиків і sitemap — з тих самих даних
    site_seo.main()


def write_home_facts(app: Path, target: Path) -> None:
    read = lambda name: json.loads((app / name).read_text(encoding="utf-8"))
    ids = {b["address"]: b["id"] for b in read("buildings.json")}
    en = read("buildings_en.json")
    out = []
    for f in read("facts.json"):
        bid = ids.get(f["address"])
        if not bid:
            print(f"home-facts: нема будинку «{f['address']}», пропускаю")
            continue
        out.append({
            "id": bid,
            "uk": {"address": f["address"], "text": f["text"]},
            "en": {"address": en.get(bid, {}).get("address") or f["address"],
                   "text": f.get("textEn") or f["text"]},
        })
    (target / "home-facts.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"home-facts.json: {len(out)} фактів")

if __name__ == "__main__":
    main()

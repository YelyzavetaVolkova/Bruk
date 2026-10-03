#!/usr/bin/env python3
"""Копіює дані застосунку BRUK у веб-мапу bruk.city/map.

Запуск з кореня цього репозиторію, коли поруч лежить bruk-app:
    python3 tools/sync_map_data.py ../bruk-app

Береться buildings.json, facts.json і filters.json з bruk-app/Bruk.
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

if __name__ == "__main__":
    main()

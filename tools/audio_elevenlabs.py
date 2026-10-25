#!/usr/bin/env python3
"""Озвучка аудіогіда через ElevenLabs: mp3 для карток будинків і підказки «Далі — …» прогулянок.

Ключ — у змінній середовища (у репозиторій його не класти):
    export ELEVENLABS_API_KEY=sk_...

    python3 tools/audio_elevenlabs.py --voices                  # голоси з твого акаунта: ім'я та id
    python3 tools/audio_elevenlabs.py --walk lesia --voice ID    # план: що озвучимо і скільки символів
    python3 tools/audio_elevenlabs.py --walk lesia --voice ID --go
    python3 tools/audio_elevenlabs.py --all-walks --go           # голос береться з map/data/audio.json
    python3 tools/audio_elevenlabs.py --id 147322969 --go        # один будинок

Файли: map/audio/b/<id>.mp3, map/audio/walks/<walk>/<n>-next.mp3 і список map/data/audio.json,
з якого їх бере мапа (map/audio.js). Без --go нічого не надсилається: лише план і кількість символів
(≈ кредитів ElevenLabs). Вже озвучене з тим самим текстом і голосом пропускається; змінився текст
картки — запусти ще раз, і перепишеться лише він. --force — переозвучити все вибране.

Текст для озвучки — той самий, що читає голос браузера: spoken() тут — копія spoken() з map/audio.js
(римські століття, «р.», «ст.», «вул.» словами). Правиш одне — поправ і друге.
"""
import argparse
import hashlib
import json
import math
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAP = ROOT / 'map'
MANIFEST = MAP / 'data' / 'audio.json'
API = 'https://api.elevenlabs.io/v1'
MODEL = 'eleven_multilingual_v2'   # українську знає; ліміт 10 000 символів на запит, найдовша картка ~7 000
FORMAT = 'mp3_44100_64'            # для голосу досить: ~0,5 МБ на хвилину
KBPS = 64

# MARK: - Текст (як spoken() у map/audio.js)

ROMAN = {'I': 1, 'V': 5, 'X': 10, 'L': 50}
ORDINAL = ['', 'перш', 'друг', 'трет', 'четверт', "п'ят", 'шост', 'сьом', 'восьм', "дев'ят", 'десят',
           'одинадцят', 'дванадцят', 'тринадцят', 'чотирнадцят', "п'ятнадцят", 'шістнадцят', 'сімнадцят',
           'вісімнадцят', "дев'ятнадцят", 'двадцят', 'двадцять перш']
AFTER_ROMAN = re.compile(r'^(\s*(?:[—–-]|і|й|та)\s*[IVXІХ]{1,5})?\s+(ст\.|століт|сторіч)')
LOCATIVE = re.compile(r'^(\s*(?:[—–-]|і|й|та)\s*[IVXІХ]{1,5})?\s+століт+і')
CAPITAL_NEXT = r'(?=\s+[А-ЯІЇЄҐ«]|$)'
BEFORE_NAME = [('вул.', 'вулиця'), ('пл.', 'площа'), ('кв.', 'квартира'), ('арх.', 'архітектор'), ('інж.', 'інженер'),
               ('просп.', 'проспект'), ('буд.', 'будинок'), ('св.', 'святого'), ('тис.', 'тисяч')]


def roman_value(s):
    d = [ROMAN[c] for c in s.replace('Х', 'X').replace('І', 'I')]
    return sum(-v if v < (d[i + 1] if i + 1 < len(d) else 0) else v for i, v in enumerate(d))


def ordinal(n, locative):
    if not 0 < n < len(ORDINAL):
        return None
    soft = n == 3  # третього / третьому
    return ORDINAL[n] + (('ьому' if soft else 'ому') if locative else ('ього' if soft else 'ого'))


def roman_centuries(text):
    def rep(m):
        rest = text[m.end():]
        n = roman_value(m.group(2))
        if not AFTER_ROMAN.match(rest) and not 10 <= n <= 21:
            return m.group(0)
        word = ordinal(n, bool(LOCATIVE.match(rest)))
        return m.group(1) + word if word else m.group(0)
    return re.sub(r'(^|[\s(«—–-])([IVXІХ]{1,5})(?=$|[\s.,;:)»—–-])', rep, text)


def spoken(text):
    t = text or ''
    t = re.sub(r'(\d)\s*рр\.' + CAPITAL_NEXT, r'\1 роках.', t)
    t = re.sub(r'(\d)\s*рр\.', r'\1 роках', t)
    t = re.sub(r'(\d{4})\s*р\.' + CAPITAL_NEXT, r'\1 року.', t)
    t = re.sub(r'(\d{4})\s*р\.', r'\1 року', t)
    t = roman_centuries(t)
    t = re.sub(r'(^|\s)ст\.' + CAPITAL_NEXT, r'\1століття.', t)
    t = re.sub(r'(^|\s)ст\.', r'\1століття', t)
    for short, full in BEFORE_NAME:
        t = t.replace(f' {short}', f' {full}')
        if t.startswith(short):
            t = full + t[len(short):]
    t = re.sub(r'№\s*', 'номер ', t)
    return re.sub(r'\s*[–—]\s*', ' — ', t)


def building_text(b):
    head = f"{b['address']}. {b['currentName']}." if b.get('currentName') else f"{b['address']}."
    body = '\n'.join(x for x in (b.get('shortText') or b.get('keyFacts'), b.get('extendedText')) if x)
    return '\n'.join(spoken(x) for x in (head, body) if x)


def metres(a, b):
    k = 111320
    dy = (a['latitude'] - b['latitude']) * k
    dx = (a['longitude'] - b['longitude']) * k * math.cos(math.radians(a['latitude']))
    return math.hypot(dx, dy)


def spoken_distance(m):
    """Як spokenDistance() у map/audio.js."""
    if m < 1000:
        return f'{max(10, round(m / 10) * 10)} метрів'
    return f'{round(m / 100) / 10:.1f}'.replace('.', ',') + ' кілометра'


def next_text(walk, stops, i):
    """Хвіст зупинки — як after у stopScript() у map/audio.js."""
    if i + 1 < len(stops):
        nxt = stops[i + 1]
        return (f"Далі — зупинка {i + 2}: {nxt['address']}, приблизно {spoken_distance(metres(stops[i], nxt))}. "
                'Коли дійдеш, я продовжу.')
    return f"Це остання зупинка прогулянки «{walk['title']}». Дякуємо, що гуляєш з BRUK."

# MARK: - ElevenLabs


def api(path, key, body=None):
    req = urllib.request.Request(f'{API}{path}', headers={'xi-api-key': key, 'Content-Type': 'application/json'},
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        sys.exit(f'ElevenLabs відповів {e.code}: {e.read().decode(errors="replace")[:500]}')


def list_voices(key):
    data = json.loads(api('/voices', key))
    for v in sorted(data.get('voices', []), key=lambda v: v.get('name', '')):
        labels = ', '.join(f'{k}: {val}' for k, val in (v.get('labels') or {}).items())
        print(f"{v['voice_id']}  {v.get('name', '')}  {labels}")


def tts(key, voice, text):
    return api(f'/text-to-speech/{voice}?output_format={FORMAT}', key,
               {'text': text, 'model_id': MODEL, 'language_code': 'uk'})

# MARK: - Що озвучувати


def text_hash(voice, text):
    return hashlib.sha1(f'{MODEL}|{FORMAT}|{voice}|{text}'.encode()).hexdigest()[:12]


def plan(args, buildings, walks):
    """Список завдань: (ключ у маніфесті, шлях mp3, текст)."""
    by_id = {b['id']: b for b in buildings}
    by_address = {b['address']: b for b in buildings}
    jobs = []
    seen = set()

    def add_building(b):
        if b['id'] in seen or not (b.get('shortText') or b.get('keyFacts')):
            return
        seen.add(b['id'])
        safe = re.sub(r'[^A-Za-z0-9_-]+', '-', b['id'])  # «osm:way/123» → «osm-way-123»
        jobs.append((('b', b['id']), f'audio/b/{safe}.mp3', building_text(b)))

    chosen = walks if args.all_walks else [w for w in walks if w['id'] in (args.walk or [])]
    for w in chosen:
        stops = [by_address[a] for a in w['addresses'] if a in by_address]
        for i, b in enumerate(stops):
            add_building(b)
            jobs.append((('w', w['id'], i), f"audio/walks/{w['id']}/{i + 1}-next.mp3", next_text(w, stops, i)))
    for bid in args.id or []:
        if bid not in by_id:
            sys.exit(f'Немає будинку з id {bid}')
        add_building(by_id[bid])
    if args.all_buildings:
        for b in buildings:
            add_building(b)
    return jobs


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--voices', action='store_true', help='показати голоси з акаунта')
    p.add_argument('--voice', help='voice_id з ElevenLabs (запам’ятовується в map/data/audio.json)')
    p.add_argument('--walk', action='append', help='id прогулянки з map/data/walks.json (можна кілька)')
    p.add_argument('--all-walks', action='store_true', help='усі прогулянки')
    p.add_argument('--id', action='append', help='id будинку (можна кілька)')
    p.add_argument('--all-buildings', action='store_true', help='усі будинки з текстом (~1,5 млн символів!)')
    p.add_argument('--go', action='store_true', help='справді озвучити (витрачає кредити)')
    p.add_argument('--force', action='store_true', help='переозвучити навіть те, що вже є')
    args = p.parse_args()

    key = os.environ.get('ELEVENLABS_API_KEY', '').strip()
    if args.voices:
        if not key:
            sys.exit('Немає ключа: export ELEVENLABS_API_KEY=...')
        list_voices(key)
        return

    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    manifest.setdefault('buildings', {})
    manifest.setdefault('walks', {})
    voice = args.voice or manifest.get('voice')
    if not voice:
        sys.exit('Вибери голос: --voices покаже список, далі --voice <id>')

    buildings = json.loads((MAP / 'data' / 'buildings.json').read_text())
    walks = json.loads((MAP / 'data' / 'walks.json').read_text())
    jobs = plan(args, buildings, walks)
    if not jobs:
        sys.exit('Нічого не вибрано: --walk <id>, --all-walks, --id <id> або --all-buildings')

    def entry(k):
        if k[0] == 'b':
            return manifest['buildings'].get(k[1])
        clips = manifest['walks'].get(k[1], [])
        return clips[k[2]] if k[2] < len(clips) else None

    todo = [(k, path, text) for k, path, text in jobs
            if args.force or not entry(k) or entry(k).get('hash') != text_hash(voice, text)
            or not (MAP / path).exists()]
    chars = sum(len(t) for _, _, t in todo)
    print(f'Голос {voice}, модель {MODEL}. Вибрано {len(jobs)} фрагментів, озвучити треба {len(todo)}: '
          f'{chars:,} символів (≈ стільки ж кредитів).'.replace(f'{chars:,}', f'{chars:,}'.replace(',', ' ')))
    if not args.go:
        print('Це лише план. Щоб озвучити, додай --go.')
        return
    if not key:
        sys.exit('Немає ключа: export ELEVENLABS_API_KEY=...')

    manifest['voice'] = voice
    manifest['model'] = MODEL
    for n, (k, path, text) in enumerate(todo, 1):
        print(f'[{n}/{len(todo)}] {path} ({len(text)} симв.)', flush=True)
        audio = tts(key, voice, text)
        out = MAP / path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(audio)
        item = {'file': path, 'hash': text_hash(voice, text), 'seconds': round(len(audio) * 8 / (KBPS * 1000))}
        if k[0] == 'b':
            manifest['buildings'][k[1]] = item
        else:
            clips = manifest['walks'].setdefault(k[1], [])
            clips.extend([None] * (k[2] + 1 - len(clips)))
            clips[k[2]] = item
        # Зберігаємо після кожного файла: якщо обірветься, вже озвучене не пропаде.
        MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + '\n')
    print('Готово. Тепер закоміть map/audio/ і map/data/audio.json — мапа візьме їх сама.')


if __name__ == '__main__':
    main()

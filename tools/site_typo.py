#!/usr/bin/env python3
"""Типографіка текстів сайту: нерозривні пробіли, апостроф, лапки, тире.

Правила (лише в тексті, не в тегах, скриптах і стилях):
  • українське: прийменники, сполучники й частки (і, в, на, до, від, не, що… — UK_WORDS)
    і № не лишаються в кінці рядка — після них нерозривний пробіл; апостроф ' → ’; "лапки" → «лапки»;
  • англійське: a, an, the, of, to… (EN_WORDS) так само тримаються наступного слова;
    апостроф ' → ’; "quotes" → “quotes”;
  • тире — й стрілка → не починають рядок (нерозривний пробіл перед ними); ... → …;
  • останнє слово абзацу, заголовка чи пункту списку не лишається на рядку саме.
Мова визначається для кожного шматка тексту: є кирилиця — українські правила.

Обробляє index.html (шаблон бандла), story.html, privacy.html; en/index.html —
build_en.py викликає typo_html() сам. Повторний запуск нічого не змінює.
Після запуску: python3 tools/build_en.py
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
NBSP = " "
CYR = "А-Яа-яЇїІіЄєҐґ"
SKIP = re.compile(r"(<(script|style|svg|textarea|title)\b.*?</\2>)|(<!--.*?-->)|(<[^>]+>)", re.S | re.I)

UK_WORDS = "а в у і й з о до за на по від для без над під про при між із зі та чи не ні що як".split()
EN_WORDS = "a an the of to in on at by for and or I".split()
UK_SHORT = re.compile(r"(?<![\w’'-])(%s|№)[ \t]+(?=[\w«(\d]|\Z)" % "|".join(UK_WORDS), re.I)
EN_SHORT = re.compile(r"(?<![\w’'-])(%s)[ \t]+(?=[\w“(\d]|\Z)" % "|".join(EN_WORDS), re.I)
UK_APOS = re.compile(r"(?<=[%s])'(?=[%s])" % (CYR, CYR))
EN_APOS = re.compile(r"(?<=[A-Za-z])'(?=[A-Za-z])")
DASH = re.compile(r"[ \t]+(—|→|↗)")
END_TAG = re.compile(r"</(p|h[1-6]|li)>", re.I)
LAST_SPACE = re.compile(r"[ \t]+(?=\S+\s*\Z)")


def typo_text(s):
    if not s.strip():
        return s
    if re.search("[%s]" % CYR, s):
        s = UK_APOS.sub("’", s)
        s = re.sub(r'"([^"<>]+)"', r"«\1»", s)
        s = UK_SHORT.sub(r"\1" + NBSP, s)
    else:
        s = EN_APOS.sub("’", s)
        s = re.sub(r'"([^"<>]+)"', r"“\1”", s)
        s = EN_SHORT.sub(r"\1" + NBSP, s)
    s = DASH.sub(NBSP + r"\1", s)
    return s.replace("...", "…")


def typo_html(html):
    out, pos = [], 0
    for m in SKIP.finditer(html):
        seg = typo_text(html[pos:m.start()])
        if END_TAG.match(m.group(0)) and len(seg.split()) >= 3:
            seg = LAST_SPACE.sub(NBSP, seg)  # останнє слово абзацу не висить саме
        out.append(seg)
        out.append(m.group(0))
        pos = m.end()
    out.append(typo_text(html[pos:]))
    return "".join(out)


def untypo(html):
    """Для build_en: повертає українські рядки до вигляду ключів у перекладі."""
    return html.replace(NBSP, " ")


def uk_apos(s):
    return UK_APOS.sub("’", s)


def bundle_body(html, fn):
    m = re.search(r'(<script type="__bundler/template">)(.*?)(</script>)', html, re.S)
    tpl = json.loads(m.group(2))
    i = tpl.find("<body")
    tpl = tpl[:i] + fn(tpl[i:])
    data = json.dumps(tpl, ensure_ascii=False).replace("</", "<\\/")
    return html[:m.start(2)] + data + html[m.end(2):]


def main():
    p = ROOT / "index.html"
    p.write_text(bundle_body(p.read_text(), typo_html))
    for name in ("story.html", "privacy.html"):
        p = ROOT / name
        html = p.read_text()
        i = html.find("<body")
        p.write_text(html[:i] + typo_html(html[i:]))
    print("типографіка: готово")


if __name__ == "__main__":
    main()

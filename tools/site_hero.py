#!/usr/bin/env python3
"""Виразніший хедер (перший екран) і кнопки капсом на головній.

  • прибирає підзаголовок «Інтерактивна мапа міста…» з першого екрана;
  • заголовок звичного розміру, кнопки під ним, низ фото темніший, навігація щільніша;
  • усі кнопки сайту — капсом, з розрядкою й однаковими відступами;
  • переноси в заголовках: тире не починає рядок.
Повторний запуск нічого не дублює. Після нього: python3 tools/site_typo.py && python3 tools/build_en.py
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
MARK = "/* bruk-hero: tools/site_hero.py */"
END = "/* /bruk-hero */\n"

TEXT = [
    ("          <p>Інтерактивна мапа міста, де кожен будинок — початок історії. Без підручників. Без туристичних кліше.</p>\n", ""),
    ("Сотні <em>фасадів</em><br>— одне місто.", "Сотні <em>фасадів</em> —<br>одне місто."),
    ("у яких жили поколіннями — ніхто", "у яких жили поколіннями, — ніхто"),
]

CSS = MARK + """
/* Hero: buttons below the headline */
.nav.on-dark { background: rgba(14,14,14,0.72); border-color: rgba(255,255,255,0.18); }
.hero-media::after {
  background: linear-gradient(180deg, rgba(0,0,0,0.5) 0%, rgba(0,0,0,0.12) 24%, rgba(0,0,0,0.18) 42%,
    rgba(0,0,0,0.62) 64%, rgba(0,0,0,0.9) 86%, rgba(0,0,0,0.95) 100%);
}
.hero-topline { padding-top: 72px; }
.hero-headline-wrap { grid-template-columns: 1fr; gap: 36px; }
.hero-side { padding-bottom: 0; }
@media (max-width: 860px) {
  .hero-topline { padding-top: 0; }
  .hero-headline-wrap { gap: 28px; }
}

/* Buttons: caps, tracking, consistent padding */
.btn, .volunteer-cta, .waitlist button[type=submit], .nav-cta {
  text-transform: uppercase;
  letter-spacing: 0.08em !important;
  font-weight: 600;
  line-height: 1;
  white-space: nowrap;
}
.btn, .volunteer-cta, .waitlist button[type=submit] {
  display: inline-flex; align-items: center; justify-content: center; gap: 10px;
  min-height: 52px;
  padding: 0 30px !important;
  font-size: 12.5px !important;
}
.nav-cta { padding: 11px 18px !important; font-size: 11.5px !important; }
@media (max-width: 640px) {
  .btn, .volunteer-cta, .waitlist button[type=submit] { min-height: 52px; padding: 0 24px !important; }
  .nav-cta { padding: 9px 13px !important; font-size: 10.5px !important; letter-spacing: 0.06em !important; }
}
/* Centered paragraphs: even lines, centered */
.volunteer-desc, .waitlist p, .orbit-caption { text-align: center; text-wrap: balance; margin-inline: auto; }
/* /bruk-hero */
"""

STORY_CSS = """  /* bruk-hero: кнопки капсом (tools/site_hero.py) */
  .btn { text-transform: uppercase; letter-spacing: .08em; font-size: 13px; font-weight: 600; }
"""


def main():
    p = ROOT / "index.html"
    html = p.read_text()
    m = re.search(r'(<script type="__bundler/template">)(.*?)(</script>)', html, re.S)
    tpl = json.loads(m.group(2))
    for old, new in TEXT:
        tpl = tpl.replace(old, new)
    if MARK in tpl:  # старий блок — геть, щоб правки CSS застосувались
        i = tpl.index(MARK)
        tpl = tpl[:i] + tpl[tpl.index(END, i) + len(END):] if END in tpl[i:] else tpl[:i] + tpl[tpl.index("</style>", i):]
    i = tpl.rfind("</style>")
    tpl = tpl[:i] + CSS + tpl[i:]
    data = json.dumps(tpl, ensure_ascii=False).replace("</", "<\\/")
    p.write_text(html[:m.start(2)] + data + html[m.end(2):])

    p = ROOT / "story.html"
    html = p.read_text()
    if "bruk-hero" not in html:
        i = html.find("</style>")
        p.write_text(html[:i] + STORY_CSS + html[i:])
    print("хедер і кнопки: готово")


if __name__ == "__main__":
    main()

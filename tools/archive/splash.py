#!/usr/bin/env python3
"""Заставка BRUK, як у застосунку: літери B-R-U-K по черзі на червоному тлі.

Літери — з bruk-app (Assets.xcassets/splashLetter*), позиції — з Figma
(логотип 295×74), анімація — як SplashView в OnboardingView.swift.

Скрипт вставляє заставку в:
  • index.html — замість кільця-спінера, поки розпаковується сторінка;
  • map/index.html — поки вантажаться дані мапи.
Повторний запуск нічого не дублює. Після нього: python3 tools/build_en.py
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent

LETTERS = [  # (svg, x, y) — як у SplashView
    ("<svg width=\"70\" height=\"70\" viewBox=\"0 0 70 70\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\"><path d=\"M9.53623 69C9.94203 63.6667 10.1449 58.3333 10.1449 53V1.4C8.657 1.4 5.41063 2.06667 0.405797 3.4L0 2.8L2.33333 0H33.1739C39.599 0 45.2126 0.733334 50.0145 2.2C54.8164 3.66667 58.5362 5.76667 61.1739 8.50001C63.8116 11.1667 65.1304 14.2667 65.1304 17.8C65.1304 21.8 63.4396 25.3333 60.058 28.4C56.6763 31.4667 52.5845 33.4333 47.7826 34.3V34.4C54.2077 34.9333 59.5169 36.7667 63.7101 39.9C67.9034 42.9667 70 46.8 70 51.4C70 57.4667 67.058 62.1 61.1739 65.3C55.2898 68.4333 46.7681 70 35.6087 70H9.53623V69ZM32.4638 34C35.3043 34 37.8744 33.3 40.1739 31.9C42.4734 30.5 44.2657 28.5667 45.5507 26.1C46.9034 23.5667 47.5797 20.7667 47.5797 17.7C47.5797 14.6333 46.9034 11.9 45.5507 9.5C44.2657 7.03334 42.4734 5.1 40.1739 3.7C37.8744 2.3 35.3043 1.6 32.4638 1.6H31.4493V34H32.4638ZM32.5652 68.7C37.7729 68.7 42 67.2 45.2464 64.2C48.5604 61.1333 50.2174 57.1667 50.2174 52.3C50.2174 47.3667 48.5604 43.3667 45.2464 40.3C41.9324 37.2333 37.6039 35.7 32.2609 35.7H31.4493V68.7H32.5652Z\" fill=\"#FFF5D9\"/></svg>", 0, 1),
    ("<svg width=\"74\" height=\"70\" viewBox=\"0 0 74 70\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\"><path d=\"M9.31584 68.9986C9.77909 64.2644 10.0139 58.9344 10.0139 52.9959V7.09823C9.1445 7.09823 7.71032 7.31372 5.705 7.75102C3.69968 8.18832 1.93551 8.60027 0.399792 8.99955L0 8.39746L2.30357 0H32.1422C38.7483 0 44.4406 0.798551 49.2128 2.40199C53.9849 3.99909 57.6592 6.35038 60.2293 9.44952C62.7994 12.5487 64.0876 16.1358 64.0876 20.1983C64.0876 23.665 63.0025 26.8022 60.8322 29.5971C58.6619 32.3984 55.6412 34.699 51.7702 36.4989L61.2827 50.9995C63.085 53.7311 65.103 56.6655 67.3431 59.8026C69.5769 62.9398 71.798 65.9375 74 68.8022V70H41.7563L39.0529 62.699L39.5542 62.0969C40.2206 62.1666 40.8742 62.2807 41.5088 62.4455C42.1434 62.6102 42.8922 62.7306 43.7616 62.794C45.9636 63.3961 47.7659 63.694 49.1683 63.694L35.1502 40.1938C34.6806 40.2635 34.2173 40.2952 33.7477 40.2952H27.8396V52.9959C27.8396 58.6618 28.0046 63.9982 28.341 68.9986V70H9.31584V68.9986ZM32.7514 33.4948C37.1555 33.4948 40.6267 32.297 43.1651 29.895C45.7035 27.493 46.9726 24.3622 46.9726 20.4961C46.9726 16.6301 45.6844 13.531 43.1143 11.1987C40.5442 8.86646 37.092 7.70032 32.7514 7.70032H27.846V33.5011H32.7514V33.4948Z\" fill=\"#FFF5D9\"/></svg>", 68, 1),
    ("<svg width=\"73\" height=\"73\" viewBox=\"0 0 73 73\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\"><path d=\"M39.7418 73C33.7314 73 28.5374 71.7967 24.1243 69.3783C19.723 66.9599 16.3274 63.5388 13.9374 59.1149C11.5475 54.691 10.3525 49.5239 10.3525 43.6018L10.246 7.26697C9.48882 7.26697 8.1282 7.46752 6.15235 7.88041C4.1765 8.29331 2.25981 8.7298 0.414101 9.21348L0 8.60003L2.37812 0.011797H36.9851L38.4167 8.69441L38.0026 9.30786C36.3699 8.76519 34.607 8.28151 32.7258 7.88041C30.8446 7.46752 29.5313 7.26697 28.7859 7.26697V42.3867C28.7859 47.3533 29.3775 51.3996 30.5724 54.5377C31.7674 57.6639 33.5185 59.9643 35.8493 61.4271C38.1682 62.89 40.9959 63.6214 44.3442 63.6214C47.6925 63.6214 50.4374 62.8192 52.7919 61.2266C55.1464 59.6222 56.9684 57.31 58.2699 54.2899C59.5713 51.2581 60.2102 47.7072 60.2102 43.6254V7.25517C59.595 7.25517 58.4355 7.44392 56.7318 7.82143C55.028 8.19893 53.2178 8.69441 51.3011 9.29606L50.887 8.68261L52.1175 0H73V1.02634C71.9707 4.97835 71.0833 10.1926 70.3379 16.6928C69.5807 23.193 69.2139 29.7049 69.2139 36.2405V41.962C69.2139 48.356 68.019 53.877 65.629 58.5015C63.2391 63.1259 59.8316 66.7004 55.3948 69.225C50.958 71.7377 45.7404 73 39.73 73H39.7418Z\" fill=\"#FFF5D9\"/></svg>", 135, 1),
    ("<svg width=\"83\" height=\"71\" viewBox=\"0 0 83 71\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\"><path d=\"M0 0H35.9745V71H4.92776V69.0255C5.58563 69.0255 5.99679 68.6964 6.16126 68.0382C6.32573 67.3801 6.40798 66.8232 6.40798 66.3612V9.66369C6.34472 9.27132 6.21188 8.85997 6.01578 8.42963C5.81968 8.00561 5.49075 7.60692 5.02897 7.24619C4.56719 6.88546 3.92829 6.57536 3.10594 6.30956C2.28359 6.05009 1.24617 5.91719 0 5.91719V0ZM49.2838 51.97L38.9349 56.2102C38.9349 48.1919 39.1816 41.2242 39.675 35.307C40.1684 29.3898 40.8706 24.3586 41.7942 20.2197C42.7114 16.0808 43.8627 12.6951 45.2417 10.0624C46.6207 7.43605 48.1832 5.37927 49.9227 3.89839C51.6623 2.41751 53.6043 1.39861 55.7361 0.841697C57.8678 0.284785 60.1894 0.00632869 62.6817 0.00632869C65.7054 0.00632869 68.2484 0.449326 70.3232 1.33532C72.3918 2.22132 74.0491 3.40476 75.3016 4.88564C76.5478 6.36652 77.4523 8.05624 78.0153 9.96114C78.572 11.866 78.8567 13.8089 78.8567 15.7771C78.8567 18.4097 78.4771 20.9412 77.7243 23.3713C76.9716 25.8015 76.0354 27.8773 74.9157 29.586L67.5209 21.5993C68.3749 19.4286 68.805 17.1947 68.805 14.8911C68.805 11.9356 68.0649 9.45485 66.5847 7.4487C65.1045 5.44255 62.9854 4.44264 60.2273 4.44264C58.4561 4.44264 56.9759 5.1641 55.793 6.61333C54.6101 8.06257 53.6739 9.86621 52.9844 12.0369C52.2949 14.2076 51.8015 16.5555 51.5042 19.0869C51.2069 21.6183 51.0614 24.0042 51.0614 26.2382C51.0614 28.276 51.074 29.9847 51.112 31.3643C51.1436 32.7439 51.2258 34.0413 51.3587 35.2563C51.4915 36.4714 51.7382 37.7371 52.0988 39.0535C52.4593 40.3698 52.9338 41.9773 53.5284 43.8822L69.4945 37.4713L83 71H56.9759L49.2902 51.97H49.2838Z\" fill=\"#FFF5D9\"/></svg>", 212, 0),
]

# Мінімальний час заставки: 4 літери × 110 мс + пауза 1100 мс, як у застосунку.
MIN_MS = 4 * 110 + 1100

CSS = """
/* bruk-splash: tools/splash.py */
.bruk-splash { position: fixed; inset: 0; z-index: 99990; background: #A20E00;
  display: flex; align-items: center; justify-content: center; transition: opacity .35s ease-out; }
.bruk-splash.out { opacity: 0; pointer-events: none; }
.bruk-splash-logo { position: relative; width: 295px; height: 74px; }
@media (min-width: 900px) { .bruk-splash-logo { transform: scale(1.25); } }
.bruk-splash-logo svg { position: absolute; opacity: 0; transform-origin: 50% 100%;
  transform: translateY(18px) scale(.92); filter: blur(6px);
  animation: bruk-letter .5s cubic-bezier(.3,1.35,.6,1) forwards; }
.bruk-splash.shown .bruk-splash-logo svg { animation: none; opacity: 1; transform: none; filter: none; }
@keyframes bruk-letter { to { opacity: 1; transform: none; filter: blur(0); } }
@media (prefers-reduced-motion: reduce) {
  .bruk-splash-logo svg { transform: none; filter: none; animation: bruk-fade .3s ease-out forwards; }
  @keyframes bruk-fade { to { opacity: 1; } }
}
/* /bruk-splash */
"""


def html(cls="bruk-splash", el_id="bruk-splash"):
    parts = []
    for i, (svg, x, y) in enumerate(LETTERS):
        svg = svg.replace("<svg ", f'<svg style="left:{x}px;top:{y}px;animation-delay:{i * 110}ms" aria-hidden="true" ', 1)
        parts.append(svg)
    return (f'<div id="{el_id}" class="{cls}" role="img" aria-label="BRUK">'
            f'<div class="bruk-splash-logo">{"".join(parts)}</div></div>')


def replace_between(text, start, end, new):
    i = text.index(start)
    j = text.index(end, i) + len(end)
    return text[:i] + new + text[j:]


def patch_site():
    path = ROOT / "index.html"
    s = path.read_text(encoding="utf-8")
    if "bruk-splash" not in s:
        # 1) стилі: замість кільця-спінера
        s = replace_between(s, "    .load-spinner {", "    #__bundler_loading { display: none; }",
                            CSS.strip() + "\n    #__bundler_loading { display: none; }")
        s = s.replace("#__bundler_thumbnail {\n      position: fixed; inset: 0;\n      display: flex; align-items: center; justify-content: center;\n      background: #faf9f5;",
                      "#__bundler_thumbnail {\n      position: fixed; inset: 0;\n      display: flex; align-items: center; justify-content: center;\n      background: #A20E00;")
        # 2) розмітка: літери замість спінера
        s = replace_between(s, '    <div class="load-spinner"', "      <div class=\"mark\">BRUK</div>\n    </div>",
                            "    " + html())
        # 3) сторінку показуємо не раніше, ніж літери складуться, а потім
        #    така сама заставка плавно зникає вже поверх готової сторінки.
        s = s.replace("document.addEventListener('DOMContentLoaded', async function() {",
                      "var __brukSplashStart = Date.now();\n"
                      "document.addEventListener('DOMContentLoaded', async function() {", 1)
        swap = "    document.documentElement.replaceWith(doc.documentElement);\n"
        assert swap in s, "не знайшла місце, де підміняється сторінка"
        s = s.replace(swap,
            f"    var __brukWait = {MIN_MS} - (Date.now() - __brukSplashStart);\n"
            "    if (__brukWait > 0) await new Promise(function(r) { setTimeout(r, __brukWait); });\n"
            + swap +
            "    (function() {\n"
            "      var st = document.createElement('style');\n"
            f"      st.textContent = {CSS.strip()!r};\n"
            "      document.head.appendChild(st);\n"
            "      var wrap = document.createElement('div');\n"
            f"      wrap.innerHTML = {html('bruk-splash shown', 'bruk-splash-after')!r};\n"
            "      var sp = wrap.firstChild;\n"
            "      document.body.appendChild(sp);\n"
            "    })();\n", 1)
        # Ховаємо заставку, коли скрипти сторінки вже відпрацювали й вона намалювалась.
        babel = "      window.Babel.transformScriptTags();\n    }\n"
        assert babel in s, "не знайшла кінець запуску скриптів"
        s = s.replace(babel, babel +
            "    setTimeout(function() {\n"
            "      var sp = document.getElementById('bruk-splash-after');\n"
            "      if (!sp) return;\n"
            "      sp.classList.add('out');\n"
            "      setTimeout(function() { sp.remove(); }, 500);\n"
            "    }, 150);\n", 1)
        path.write_text(s, encoding="utf-8")
        print("index.html: заставку додано")
    else:
        print("index.html: заставка вже є")


def patch_map():
    path = ROOT / "map" / "index.html"
    s = path.read_text(encoding="utf-8")
    if "bruk-splash" in s:
        print("map/index.html: заставка вже є")
        return
    s = s.replace("</head>", f"  <style>{CSS}</style>\n</head>", 1)
    s = s.replace("<body>\n", f"<body>\n  {html()}\n", 1)
    path.write_text(s, encoding="utf-8")
    print("map/index.html: заставку додано")


if __name__ == "__main__":
    patch_site()
    patch_map()

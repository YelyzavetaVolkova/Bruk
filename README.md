# Bruk
## Англійська версія

`en/index.html` збирається з `index.html` скриптом `tools/build_en.py` (переклад — у самому скрипті).
Після кожної зміни `index.html` запусти `python3 tools/build_en.py`: він додасть перемикач мови й перебудує англійську сторінку, а якщо український текст змінився — покаже, який рядок перекласти.

## Шрифт і типографіка

Увесь сайт набраний українським шрифтом Fixel (MacPaw, OFL; файли в `fonts/`, для story.html і privacy.html — `fonts/fixel.css`). Шрифт і інтервали вшиває `python3 tools/site_typography.py`; після чужих змін `index.html` запусти його, а потім `python3 tools/build_en.py`.

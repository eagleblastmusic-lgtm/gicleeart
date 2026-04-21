"""Generator pliku HTML z podgladem posta we wszystkich 7 jezykach.

Wyjscie: pojedynczy plik `data/preview.html` zawierajacy:
- Zakladki (tabs) dla kazdej wersji jezykowej (PL/EN/DE/FR/ES/NL/IT),
- Dla kazdej: tytul, summary, body_html (rzeczywiscie wyrenderowany), SEO title/description, tagi,
- Prosty CSS w stylu bloga (Bodoni Moda + Cormorant - jak motyw Horizon),
- Vanilla JS do przelaczania zakladek.
"""

from __future__ import annotations

import html
import webbrowser
from pathlib import Path
from typing import Any

_COMPONENT_DIR = Path(__file__).resolve().parent
_PREVIEW_FILE = _COMPONENT_DIR / "data" / "preview.html"

_LANG_LABELS = [
    ("pl", "Polski", "🇵🇱"),
    ("en", "Angielski", "🇬🇧"),
    ("de", "Niemiecki", "🇩🇪"),
    ("fr", "Francuski", "🇫🇷"),
    ("es", "Hiszpanski", "🇪🇸"),
    ("nl", "Holenderski", "🇳🇱"),
    ("it", "Wloski", "🇮🇹"),
]

_CSS = """\
:root {
  --bg: #fafaf7;
  --fg: #1a1a1a;
  --muted: #666;
  --accent: #6d4c41;
  --tab-bg: #efeae3;
  --tab-active-bg: #fff;
  --border: #d8d2c7;
  --chip-bg: #e9e3d7;
  --chip-fg: #3e2723;
  --seo-bg: #fff8e1;
  --seo-border: #f9e3b6;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  padding: 0;
  background: var(--bg);
  color: var(--fg);
  font-family: 'Cormorant Garamond', Georgia, serif;
  font-size: 17px;
  line-height: 1.7;
}

header {
  padding: 24px 40px 16px;
  border-bottom: 1px solid var(--border);
  background: #fff;
  position: sticky;
  top: 0;
  z-index: 10;
}

header .brand {
  font-family: 'Bodoni Moda', 'Playfair Display', serif;
  font-size: 26px;
  font-weight: 700;
  letter-spacing: 0.02em;
}

header .meta {
  color: var(--muted);
  font-family: 'Segoe UI', sans-serif;
  font-size: 13px;
  margin-top: 4px;
}

.tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 12px 40px 0;
  background: #fff;
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 78px;
  z-index: 9;
}

.tab {
  padding: 10px 18px;
  background: var(--tab-bg);
  border: 1px solid var(--border);
  border-bottom: none;
  border-radius: 8px 8px 0 0;
  cursor: pointer;
  font-family: 'Segoe UI', sans-serif;
  font-size: 13px;
  font-weight: 600;
  color: var(--muted);
  transition: background 0.15s;
}

.tab:hover { background: #fff; }

.tab.active {
  background: var(--tab-active-bg);
  color: var(--fg);
  position: relative;
  top: 1px;
}

.tab .flag { margin-right: 6px; }

.tab.missing {
  opacity: 0.4;
  text-decoration: line-through;
  cursor: not-allowed;
}

.panel {
  display: none;
  max-width: 820px;
  margin: 0 auto;
  padding: 32px 40px 64px;
}

.panel.active { display: block; }

.panel h1 {
  font-family: 'Bodoni Moda', serif;
  font-size: 38px;
  font-weight: 700;
  line-height: 1.2;
  margin: 0 0 8px;
}

.panel .summary {
  font-style: italic;
  color: #444;
  font-size: 18px;
  margin: 16px 0 24px;
  padding: 16px 20px;
  background: #fff;
  border-left: 4px solid var(--accent);
  border-radius: 0 6px 6px 0;
}

.panel .body {
  font-size: 17px;
}

.panel .body p { margin: 1em 0; }
.panel .body h2 {
  font-family: 'Bodoni Moda', serif;
  font-size: 26px;
  margin: 1.4em 0 0.6em;
  font-weight: 700;
}
.panel .body h3 {
  font-family: 'Bodoni Moda', serif;
  font-size: 21px;
  margin: 1.2em 0 0.5em;
  font-weight: 700;
}
.panel .body blockquote {
  border-left: 3px solid var(--accent);
  margin: 1em 0;
  padding: 0.3em 1em;
  color: #555;
  font-style: italic;
}
.panel .body ul, .panel .body ol { padding-left: 1.6em; }
.panel .body a { color: var(--accent); }

.seo {
  margin: 40px 0 24px;
  padding: 18px 20px;
  background: var(--seo-bg);
  border: 1px dashed var(--seo-border);
  border-radius: 8px;
  font-family: 'Segoe UI', sans-serif;
}

.seo h3 {
  font-family: 'Segoe UI', sans-serif;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin: 0 0 10px;
  color: #8b6b2f;
}

.seo-row {
  display: grid;
  grid-template-columns: 140px 1fr;
  gap: 10px;
  font-size: 13px;
  padding: 4px 0;
}

.seo-row .key { color: var(--muted); }
.seo-row .val { word-break: break-word; }
.seo-row .chars { color: #888; font-size: 11px; margin-left: 6px; }

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 12px;
}

.chip {
  background: var(--chip-bg);
  color: var(--chip-fg);
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-family: 'Segoe UI', sans-serif;
}

.empty {
  padding: 60px 40px;
  text-align: center;
  color: var(--muted);
  font-style: italic;
}

.missing-note {
  background: #ffebee;
  border: 1px solid #f8bbd0;
  padding: 14px 18px;
  border-radius: 8px;
  color: #b71c1c;
  margin: 16px 40px;
  font-family: 'Segoe UI', sans-serif;
  font-size: 13px;
}
"""

_JS = """\
document.addEventListener('DOMContentLoaded', function () {
  var tabs = document.querySelectorAll('.tab:not(.missing)');
  var panels = document.querySelectorAll('.panel');
  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      var target = tab.dataset.lang;
      tabs.forEach(function (t) { t.classList.remove('active'); });
      panels.forEach(function (p) { p.classList.remove('active'); });
      tab.classList.add('active');
      var panel = document.getElementById('panel-' + target);
      if (panel) panel.classList.add('active');
    });
  });
});
"""


def _escape(s: str) -> str:
    return html.escape(str(s or ""), quote=True)


def _render_panel(code: str, lang_label: str, data: dict[str, Any]) -> str:
    title = data.get("title") or ""
    body_html = data.get("body_html") or ""
    summary_html = data.get("summary_html") or ""
    seo_title = data.get("seo_title") or ""
    seo_description = data.get("seo_description") or ""
    tags = data.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    chips = "".join(f'<span class="chip">{_escape(t)}</span>' for t in tags)
    summary_block = f'<div class="summary">{summary_html}</div>' if summary_html else ""

    return f"""\
<section class="panel" id="panel-{code}">
  <h1>{_escape(title)}</h1>
  {summary_block}
  <div class="body">{body_html}</div>
  <div class="seo">
    <h3>SEO - {lang_label}</h3>
    <div class="seo-row">
      <span class="key">SEO title</span>
      <span class="val">{_escape(seo_title)} <span class="chars">({len(seo_title)} znakow)</span></span>
    </div>
    <div class="seo-row">
      <span class="key">SEO description</span>
      <span class="val">{_escape(seo_description)} <span class="chars">({len(seo_description)} znakow)</span></span>
    </div>
    <div class="seo-row">
      <span class="key">Tagi ({len(tags)})</span>
      <span class="val"><div class="chips">{chips}</div></span>
    </div>
  </div>
</section>
"""


def _render_missing_panel(code: str, lang_label: str) -> str:
    return f"""\
<section class="panel" id="panel-{code}">
  <div class="empty">
    Brak tlumaczenia dla jezyka: <strong>{lang_label}</strong>.<br/>
    Wroc do okna generatora i sprawdz odpowiedz LLM lub odznacz ten jezyk przed wysylka.
  </div>
</section>
"""


def build_preview_html(parsed: dict[str, Any]) -> Path:
    """Generuje plik HTML z podgladem wszystkich wersji jezykowych.

    Zwraca sciezke do wygenerowanego pliku.
    """
    _PREVIEW_FILE.parent.mkdir(parents=True, exist_ok=True)

    langs = parsed.get("languages") or {}
    topic = parsed.get("topic") or ""
    category = parsed.get("category") or ""
    image_hint = parsed.get("image_hint") or ""

    # Pierwszy istniejacy jezyk = domyslnie aktywny
    default_active = next(
        (code for code, _, _ in _LANG_LABELS if code in langs and (langs.get(code) or {}).get("title")),
        "pl",
    )

    tabs_html = []
    panels_html = []
    for code, label, flag in _LANG_LABELS:
        data = langs.get(code)
        has_content = isinstance(data, dict) and data.get("title") and data.get("body_html")
        active_class = " active" if code == default_active and has_content else ""
        missing_class = "" if has_content else " missing"
        tabs_html.append(
            f'<button class="tab{active_class}{missing_class}" data-lang="{code}">'
            f'<span class="flag">{flag}</span>{label}</button>'
        )
        if has_content:
            panels_html.append(_render_panel(code, label, data))
        else:
            panels_html.append(_render_missing_panel(code, label))

    # Ustawi 'active' na panelu default
    panels_html_str = "\n".join(panels_html).replace(
        f'id="panel-{default_active}"',
        f'id="panel-{default_active}" class="panel active"',
        1,
    )
    # Hack: poprzednie replace moglo byc duplikat jesli panel mial juz class. Lepiej:
    # Zastapmy bezposrednio w panel wygenerowanym:
    panels_html_fixed = []
    for html_chunk in panels_html:
        if f'id="panel-{default_active}"' in html_chunk and 'class="panel active"' not in html_chunk:
            html_chunk = html_chunk.replace(
                f'<section class="panel" id="panel-{default_active}">',
                f'<section class="panel active" id="panel-{default_active}">',
            )
        panels_html_fixed.append(html_chunk)

    missing_langs = [label for code, label, _ in _LANG_LABELS if code not in langs or not (langs.get(code) or {}).get("title")]
    missing_note = ""
    if missing_langs:
        missing_note = (
            f'<div class="missing-note">⚠ Brak tlumaczen dla: {", ".join(missing_langs)}. '
            "Odznacz te jezyki przed wyslaniem lub wroc do LLM po uzupelnienie.</div>"
        )

    full = f"""\
<!doctype html>
<html lang="pl">
<head>
  <meta charset="utf-8"/>
  <title>Podglad posta - {_escape(topic or "blog")}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Bodoni+Moda:wght@700&family=Cormorant+Garamond:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
  <style>{_CSS}</style>
</head>
<body>
  <header>
    <div class="brand">GicleeArt - podglad posta</div>
    <div class="meta">
      Temat: <strong>{_escape(topic)}</strong>
      {f' &middot; Kategoria: <strong>{_escape(category)}</strong>' if category else ''}
      {f' &middot; Sugestia obrazka: <em>{_escape(image_hint)}</em>' if image_hint else ''}
    </div>
  </header>
  <div class="tabs">
    {''.join(tabs_html)}
  </div>
  {missing_note}
  {''.join(panels_html_fixed)}
  <script>{_JS}</script>
</body>
</html>
"""

    _PREVIEW_FILE.write_text(full, encoding="utf-8")
    return _PREVIEW_FILE


def open_preview_in_browser(parsed: dict[str, Any]) -> Path:
    path = build_preview_html(parsed)
    webbrowser.open(path.as_uri())
    return path

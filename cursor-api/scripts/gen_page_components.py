#!/usr/bin/env python3
"""Generator plików komponentów stron menu."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "Komponenty"

STANDARD_INIT = '"""Komponent: {title}."""\n'
STANDARD_MAIN = '''"""Uruchomienie: python -m Komponenty.{id}"""

from .gui import main

if __name__ == "__main__":
    main()
'''
STANDARD_VIEW = '''"""Widok inline — {title} w launcherze GicleeApp."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from Komponenty._shared.inline_view_shell import mount_inline_view

from .gui import APP_TITLE, _build_ui


def build_view(parent: tk.Widget, on_back: Callable[[], None]) -> tk.Widget:
    return mount_inline_view(
        parent,
        on_back,
        title=APP_TITLE,
        build_content=lambda frame: _build_ui(frame, inline=True),
    )
'''
STANDARD_GUI = '''"""GUI: {title}."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from Komponenty._shared.theme_page_editor.bootstrap import build_editor_config, build_page_ui
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .registry import PAGE_ZONES
{extra_imports}

APP_TITLE = "{app_title}"
_COMPONENT_ID = "{id}"


def _config():
    return build_editor_config(
        module_file=__file__,
        component_id=_COMPONENT_ID,
        app_title=APP_TITLE,
        intro_title="{intro_title}",
        intro_body="{intro_body}",
        template_rel="{template}",
        preview_path="{preview}",
        variant_id_prefix="{prefix}",
        zones=PAGE_ZONES,{extra_config}
    )


def main() -> None:
    root = tk.Tk()
    root.title(APP_TITLE)
    position_toplevel_screen_center(root, {width}, {height})
    root.minsize({min_w}, {min_h})
    build_page_ui(root, _config())
    root.mainloop()


def _build_ui(host: tk.Misc, *, inline: bool = False) -> None:
    build_page_ui(host, _config(), inline=inline)
{extra_funcs}
'''
STANDARD_REGISTRY_HEADER = '''"""Mapowanie stref → {template}."""

from __future__ import annotations

from Komponenty._shared.theme_page_editor.types import TemplateField, TemplateZone, _s

'''


def write_component(meta: dict) -> None:
    cid = meta["id"]
    folder = ROOT / cid
    folder.mkdir(parents=True, exist_ok=True)

    (folder / "__init__.py").write_text(STANDARD_INIT.format(title=meta["name"]), encoding="utf-8")
    (folder / "__main__.py").write_text(STANDARD_MAIN.format(id=cid), encoding="utf-8")
    (folder / "view.py").write_text(STANDARD_VIEW.format(title=meta["name"]), encoding="utf-8")
    (folder / "registry.py").write_text(
        STANDARD_REGISTRY_HEADER.format(template=meta["template"]) + meta["registry"] + "\n",
        encoding="utf-8",
    )
    (folder / "component.json").write_text(
        json.dumps(
            {
                "name": meta["name"],
                "description": meta["description"],
                "icon": meta["icon"],
                "color": meta["color"],
                "order": meta["order"],
                "mode": "inline",
                "inline_width": meta.get("width", 1100),
                "inline_height": meta.get("height", 720),
                "inline_min_width": meta.get("min_w", 880),
                "inline_min_height": meta.get("min_h", 560),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (folder / "gui.py").write_text(
        STANDARD_GUI.format(
            title=meta["name"],
            id=cid,
            app_title=meta["app_title"],
            intro_title=meta["intro_title"],
            intro_body=meta["intro_body"],
            template=meta["template"],
            preview=meta["preview"],
            prefix=meta["prefix"],
            width=meta.get("width", 1100),
            height=meta.get("height", 720),
            min_w=meta.get("min_w", 880),
            min_h=meta.get("min_h", 560),
            extra_imports=meta.get("extra_imports", ""),
            extra_config=meta.get("extra_config", ""),
            extra_funcs=meta.get("extra_funcs", ""),
        ),
        encoding="utf-8",
    )


def _media_zone(sid: str, label: str, jumbo_id: str, text_id: str, jumbo_field: str, body_field: str) -> str:
    return f"""    TemplateZone(
        zone_id="{sid}",
        label="{label}",
        description="Grafika i treść sekcji media-with-content.",
        section_key="{sid}",
        fields=(
            TemplateField("{jumbo_field}", "Nagłówek jumbo", "text", _s("{sid}", "blocks", "content", "blocks", "{jumbo_id}", "settings", "text")),
            TemplateField("{body_field}", "Treść", "body", _s("{sid}", "blocks", "content", "blocks", "{text_id}", "settings", "text")),
            TemplateField("{jumbo_field}_img", "Grafika", "shopify_image", _s("{sid}", "blocks", "media", "settings", "image")),
        ),
    ),"""


GF_SECTIONS = [
    ("media_with_content_xdDQna", "Intro — Giclée Frame™", "jumbo_text_pnNRiB", "text_GifUG3", "gf_intro_jumbo", "gf_intro_body"),
    ("media_with_content_bJdEUY", "Materiały archiwalne", "jumbo_text_8YqY9Y", "text_8YqY9Y", "gf_mat_jumbo", "gf_mat_body"),
    ("media_with_content_mEjyEw", "Konstrukcja ramy", "jumbo_text_mEjyEw", "text_mEjyEw", "gf_konstr_jumbo", "gf_konstr_body"),
    ("media_with_content_TpnJQ4", "Montaż i stabilność", "jumbo_text_TpnJQ4", "text_TpnJQ4", "gf_montaz_jumbo", "gf_montaz_body"),
    ("media_with_content_wDiVPB", "Wykończenie", "jumbo_text_wDiVPB", "text_wDiVPB", "gf_wyko_jumbo", "gf_wyko_body"),
    ("media_with_content_8yinAT", "Ekspozycja", "jumbo_text_8yinAT", "text_8yinAT", "gf_eksp_jumbo", "gf_eksp_body"),
    ("media_with_content_tyUaLL", "Podsumowanie", "jumbo_text_tyUaLL", "text_tyUaLL", "gf_podsum_jumbo", "gf_podsum_body"),
]

# Read actual jumbo/text ids from giclee-frame - use grep results from first section only for others we guess - need to verify

COMPONENTS: list[dict] = []  # filled below

COMPONENTS.extend([
    {
        "id": "wspolpraca",
        "name": "Współpraca",
        "app_title": "Współpraca — wygląd strony",
        "description": "Wygląd strony Współpraca — templates/page.wspolpraca.json.",
        "icon": "🤝", "color": "#1565c0", "order": 41,
        "template": "templates/page.wspolpraca.json", "preview": "/pages/wspolpraca", "prefix": "ws",
        "intro_title": "Strona Współpraca",
        "intro_body": "Edytujesz szablon strony współpracy. Treść artykułu pochodzi z Shopify Pages (page-content).",
        "registry": """PAGE_ZONES: tuple[TemplateZone, ...] = (
    TemplateZone(
        zone_id="main",
        label="Treść strony",
        description="Nagłówek strony (treść z Shopify Pages w bloku page-content).",
        section_key="main",
        fields=(
            TemplateField("heading", "Nagłówek", "heading", _s("main", "blocks", "heading", "settings", "text")),
        ),
    ),
)""",
    },
    {
        "id": "kontakt",
        "name": "Kontakt",
        "app_title": "Kontakt — wygląd strony",
        "description": "Wygląd strony Kontakt — hero, formularz (templates/page.contact.json).",
        "icon": "✉️", "color": "#6a1b9a", "order": 43,
        "template": "templates/page.contact.json", "preview": "/pages/contact", "prefix": "ko",
        "intro_title": "Strona Kontakt",
        "intro_body": "Edytujesz hero i formularz kontaktowy w templates/page.contact.json.",
        "registry": """PAGE_ZONES: tuple[TemplateZone, ...] = (
    TemplateZone(
        zone_id="hero",
        label="Hero — Kontakt",
        description="Nagłówek i tło sekcji hero.",
        section_key="hero_VWALbr",
        fields=(
            TemplateField("hero_heading", "Nagłówek", "heading", _s("hero_VWALbr", "blocks", "text_XJxnAG", "settings", "text")),
            TemplateField("hero_image", "Tło — grafika", "shopify_image", _s("hero_VWALbr", "settings", "image_1")),
        ),
    ),
    TemplateZone(
        zone_id="form",
        label="Formularz kontaktowy",
        description="Przycisk wysyłki formularza.",
        section_key="form",
        fields=(
            TemplateField(
                "submit_label",
                "Etykieta przycisku",
                "text",
                _s("form", "blocks", "contact_form_UwiCkQ", "blocks", "submit-button", "settings", "label"),
            ),
        ),
    ),
)""",
    },
    {
        "id": "stronablogu",
        "name": "Strona blogu",
        "app_title": "Strona blogu — wygląd listy",
        "description": "Wygląd listy bloga — hero i layout (templates/blog.json). Osobno od komponentu treści postów.",
        "icon": "📰", "color": "#0277bd", "order": 44,
        "template": "templates/blog.json", "preview": "/blogs/news", "prefix": "sb",
        "intro_title": "Wygląd strony bloga",
        "intro_body": "Edytujesz hero i ustawienia listy artykułów. Treści postów — komponent Blog w Marketing.",
        "registry": """PAGE_ZONES: tuple[TemplateZone, ...] = (
    TemplateZone(
        zone_id="hero",
        label="Hero bloga",
        description="Nagłówek i wprowadzenie nad listą artykułów.",
        section_key="hero_BMCrdL",
        fields=(
            TemplateField("hero_title", "Nagłówek", "heading", _s("hero_BMCrdL", "blocks", "text_4crMR9", "settings", "text")),
            TemplateField("hero_intro", "Wprowadzenie", "body", _s("hero_BMCrdL", "blocks", "text_PDh9dG", "settings", "text")),
            TemplateField("hero_image", "Tło — grafika", "shopify_image", _s("hero_BMCrdL", "settings", "image_1")),
        ),
    ),
    TemplateZone(
        zone_id="main",
        label="Lista artykułów",
        description="Odstępy sekcji main-blog.",
        section_key="main",
        fields=(
            TemplateField("padding_top", "Padding góra", "int", _s("main", "settings", "padding-block-start")),
            TemplateField("padding_bottom", "Padding dół", "int", _s("main", "settings", "padding-block-end")),
        ),
    ),
)""",
    },
    {
        "id": "faq",
        "name": "FAQ",
        "app_title": "FAQ — wygląd strony",
        "description": "Wygląd strony FAQ — hero i accordion (templates/page.faq.json).",
        "icon": "❓", "color": "#455a64", "order": 45,
        "template": "templates/page.faq.json", "preview": "/pages/faq", "prefix": "fq",
        "intro_title": "Strona FAQ",
        "intro_body": "Edytujesz hero i pytania w accordion na stronie FAQ.",
        "registry": """PAGE_ZONES: tuple[TemplateZone, ...] = (
    TemplateZone(
        zone_id="hero",
        label="Hero FAQ",
        description="Nagłówek i tło strony FAQ.",
        section_key="hero_NaxrxE",
        fields=(
            TemplateField("hero_title", "Nagłówek", "heading", _s("hero_NaxrxE", "blocks", "text_HJGb9e", "settings", "text")),
            TemplateField("hero_image", "Tło — grafika", "shopify_image", _s("hero_NaxrxE", "settings", "image_1")),
        ),
    ),
    TemplateZone(
        zone_id="faq_accordion",
        label="Pytania i odpowiedzi",
        description="Accordion z najczęstszymi pytaniami.",
        section_key="section_9YgpHf",
        fields=(
            TemplateField("q1_heading", "Pytanie 1", "text", _s("section_9YgpHf", "blocks", "accordion_3BVjAx", "blocks", "accordion_row_mUQFCU", "settings", "heading")),
            TemplateField("q1_answer", "Odpowiedź 1", "body", _s("section_9YgpHf", "blocks", "accordion_3BVjAx", "blocks", "accordion_row_mUQFCU", "blocks", "text_Q8RMTC", "settings", "text")),
            TemplateField("q2_heading", "Pytanie 2", "text", _s("section_9YgpHf", "blocks", "accordion_3BVjAx", "blocks", "accordion_row_gq7xgd", "settings", "heading")),
            TemplateField("q2_answer", "Odpowiedź 2", "body", _s("section_9YgpHf", "blocks", "accordion_3BVjAx", "blocks", "accordion_row_gq7xgd", "blocks", "text_dbKFYM", "settings", "text")),
            TemplateField("q3_heading", "Pytanie 3", "text", _s("section_9YgpHf", "blocks", "accordion_3BVjAx", "blocks", "accordion_row_fxrNFP", "settings", "heading")),
            TemplateField("q3_answer", "Odpowiedź 3", "body", _s("section_9YgpHf", "blocks", "accordion_3BVjAx", "blocks", "accordion_row_fxrNFP", "blocks", "text_KT9gtp", "settings", "text")),
            TemplateField("q4_heading", "Pytanie 4", "text", _s("section_9YgpHf", "blocks", "accordion_3BVjAx", "blocks", "accordion_row_VwgmXW", "settings", "heading")),
            TemplateField("q4_answer", "Odpowiedź 4", "body", _s("section_9YgpHf", "blocks", "accordion_3BVjAx", "blocks", "accordion_row_VwgmXW", "blocks", "text_kCYhHF", "settings", "text")),
            TemplateField("q5_heading", "Pytanie 5", "text", _s("section_9YgpHf", "blocks", "accordion_3BVjAx", "blocks", "accordion_row_7nCpLH", "settings", "heading")),
            TemplateField("q5_answer", "Odpowiedź 5", "body", _s("section_9YgpHf", "blocks", "accordion_3BVjAx", "blocks", "accordion_row_7nCpLH", "blocks", "text_BnRprG", "settings", "text")),
        ),
    ),
)""",
    },
    {
        "id": "filozofiamarki",
        "name": "Filozofia marki",
        "app_title": "Filozofia marki — wygląd strony",
        "description": "Wygląd strony Filozofia marki — templates/page.filozofia-marki.json.",
        "icon": "✨", "color": "#4e342e", "order": 42,
        "template": "templates/page.filozofia-marki.json", "preview": "/pages/filozofia-marki", "prefix": "fm",
        "width": 1180, "height": 780,
        "intro_title": "Strona Filozofia marki",
        "intro_body": "Edytujesz sekcje manifestu marki i treści filozofii w szablonie motywu.",
        "registry": """PAGE_ZONES: tuple[TemplateZone, ...] = (
    TemplateZone(
        zone_id="hero_manifest",
        label="Hero — manifest",
        description="Główna sekcja filozofii marki z grafiką.",
        section_key="media_with_content_D7REjd",
        fields=(
            TemplateField("hero_title", "Nagłówek", "heading", _s("media_with_content_D7REjd", "blocks", "content", "blocks", "text_UerD4k", "settings", "text")),
            TemplateField("hero_body", "Treść", "body", _s("media_with_content_D7REjd", "blocks", "content", "blocks", "text_kdAGGw", "settings", "text")),
            TemplateField("hero_image", "Grafika", "shopify_image", _s("media_with_content_D7REjd", "blocks", "media", "settings", "image")),
        ),
    ),
    TemplateZone(
        zone_id="section_story",
        label="Sekcja — opowieść",
        description="Druga sekcja media-with-content.",
        section_key="media_with_content_LgNBmd",
        fields=(
            TemplateField("story_title", "Nagłówek", "heading", _s("media_with_content_LgNBmd", "blocks", "content", "blocks", "group_dimbtz", "blocks", "text_nMfgYW", "settings", "text")),
            TemplateField("story_body", "Treść", "body", _s("media_with_content_LgNBmd", "blocks", "content", "blocks", "group_dimbtz", "blocks", "text_9ftdzW", "settings", "text")),
            TemplateField("story_image", "Grafika", "shopify_image", _s("media_with_content_LgNBmd", "blocks", "media", "settings", "image")),
        ),
    ),
    TemplateZone(
        zone_id="section_quote",
        label="Sekcja — cytat",
        description="Sekcja tekstowa pod manifestem.",
        section_key="section_tAj94h",
        fields=(
            TemplateField("quote_text", "Tekst", "body", _s("section_tAj94h", "blocks", "text_RDX6ft", "settings", "text")),
        ),
    ),
)""",
    },
    {
        "id": "gicleeframe",
        "name": "Giclée Frame",
        "app_title": "Giclée Frame — wygląd strony",
        "description": "Wygląd strony Giclée Frame™ — templates/page.giclee-frame.json.",
        "icon": "🖼️", "color": "#bf360c", "order": 40,
        "template": "templates/page.giclee-frame.json", "preview": "/pages/giclee-frame", "prefix": "gf",
        "width": 1240, "height": 820,
        "intro_title": "Strona Giclée Frame™",
        "intro_body": "Edytujesz sekcje produktu Giclée Frame — grafiki i treści w szablonie motywu.",
        "registry": "PAGE_ZONES: tuple[TemplateZone, ...] = (\n" + _media_zone("media_with_content_xdDQna", "Intro — Giclée Frame™", "jumbo_text_pnNRiB", "text_GifUG3", "gf_intro_jumbo", "gf_intro_body") + "\n)\n",
    },
    {
        "id": "wlasnafotografia",
        "name": "Własna fotografia",
        "app_title": "Własna fotografia — szablon PDP",
        "description": "Szablon produktu własnej fotografii — templates/product.szablon-wlasna-fotografia.json.",
        "icon": "📷", "color": "#2e7d32", "order": 39,
        "template": "templates/product.szablon-wlasna-fotografia.json",
        "preview": "/products/twoje-zdjecie-jako-wydruk-giclee-na-papierze-fine-art-w-drewnianej-ramie",
        "prefix": "wf",
        "intro_title": "Własna fotografia — PDP",
        "intro_body": "Edytujesz szablon produktu (mockup w motywie + Worker). Menu kieruje na PDP, nie na page.fotografia-obraz.",
        "registry": """PAGE_ZONES: tuple[TemplateZone, ...] = (
    TemplateZone(
        zone_id="product_main",
        label="Nagłówek produktu",
        description="Tytuł produktu na stronie PDP własnej fotografii.",
        section_key="main",
        fields=(
            TemplateField(
                "product_title",
                "Tytuł",
                "heading",
                _s("main", "blocks", "product-details", "blocks", "group_icgrde", "blocks", "text_xrnftG", "settings", "text"),
            ),
        ),
    ),
    TemplateZone(
        zone_id="recommendations",
        label="Rekomendacje",
        description="Nagłówek sekcji «Może Ci się spodobać».",
        section_key="product_recommendations_qggXJq",
        fields=(
            TemplateField(
                "rec_heading",
                "Nagłówek",
                "heading",
                _s("product_recommendations_qggXJq", "blocks", "text_cbcgyb", "settings", "text"),
            ),
        ),
    ),
)""",
    },
    {
        "id": "katalog",
        "name": "Katalog",
        "app_title": "Katalog — wygląd kolekcji",
        "description": "Wygląd stron kolekcji artystów — templates/collection.json. Artyści: komponent Dodaj obraz.",
        "icon": "📚", "color": "#5d4037", "order": 38,
        "template": "templates/collection.json",
        "preview": "/collections",
        "prefix": "ka",
        "intro_title": "Katalog — strony kolekcji",
        "intro_body": "Edytujesz layout stron artystów (collection.json). Listę artystów w menu zarządzasz w Dodaj obraz.",
        "extra_imports": "\nimport subprocess\nimport sys\nfrom pathlib import Path\n",
        "extra_config": '\n        extra_toolbar=(("Zarządzaj artystami →", _open_dodajobraz),),',
        "extra_funcs": '''

def _open_dodajobraz() -> None:
    root = Path(__file__).resolve().parents[2]
    subprocess.Popen([sys.executable, "-m", "Komponenty.dodajobraz"], cwd=str(root))
''',
        "registry": """PAGE_ZONES: tuple[TemplateZone, ...] = (
    TemplateZone(
        zone_id="biography",
        label="Biografia autora",
        description="Tło i ustawienia sekcji biografii na stronie kolekcji.",
        section_key="section",
        fields=(
            TemplateField("bio_bg", "Tło — grafika", "shopify_image", _s("section", "settings", "background_image")),
            TemplateField("bio_pad_top", "Padding góra", "int", _s("section", "settings", "padding_top")),
            TemplateField("bio_pad_bottom", "Padding dół", "int", _s("section", "settings", "padding_bottom")),
        ),
    ),
    TemplateZone(
        zone_id="showcase",
        label="Galeria kolekcji",
        description="Nagłówki sekcji giclee-artist-collection-showcase.",
        section_key="giclee_artist_collection_showcase_7djLQQ",
        fields=(
            TemplateField("eyebrow", "Nadtytuł", "text", _s("giclee_artist_collection_showcase_7djLQQ", "settings", "eyebrow")),
            TemplateField("heading", "Nagłówek", "text", _s("giclee_artist_collection_showcase_7djLQQ", "settings", "heading")),
            TemplateField("lead", "Lead", "body", _s("giclee_artist_collection_showcase_7djLQQ", "settings", "lead")),
            TemplateField("cta_label", "Etykieta CTA", "text", _s("giclee_artist_collection_showcase_7djLQQ", "settings", "cta_label")),
        ),
    ),
    TemplateZone(
        zone_id="works",
        label="Sekcja Dzieła",
        description="Nagłówek nad siatką produktów.",
        section_key="section_ANxq96",
        fields=(
            TemplateField("works_heading", "Nagłówek", "heading", _s("section_ANxq96", "blocks", "text_FNbyeV", "settings", "text")),
        ),
    ),
)""",
    },
])

if __name__ == "__main__":
    for meta in COMPONENTS:
        write_component(meta)
        print(f"OK {meta['id']}")

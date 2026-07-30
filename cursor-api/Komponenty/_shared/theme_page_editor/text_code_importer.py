"""Bezpieczna adaptacja wklejonego HTML/CSS/JS do warstwy tekstowej."""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlparse


_ALLOWED_TAGS = {
    "a",
    "article",
    "aside",
    "audio",
    "b",
    "blockquote",
    "br",
    "button",
    "cite",
    "circle",
    "code",
    "dd",
    "defs",
    "dl",
    "dt",
    "ellipse",
    "div",
    "em",
    "figcaption",
    "figure",
    "footer",
    "g",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "i",
    "img",
    "li",
    "line",
    "lineargradient",
    "main",
    "mark",
    "mask",
    "ol",
    "p",
    "path",
    "picture",
    "polygon",
    "polyline",
    "pre",
    "radialgradient",
    "rect",
    "section",
    "small",
    "source",
    "span",
    "stop",
    "strong",
    "sub",
    "sup",
    "svg",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "time",
    "tr",
    "u",
    "ul",
    "video",
}
_VOID_TAGS = {"br", "hr", "img", "source"}
_DROP_WITH_CONTENT = {"script", "iframe", "object", "embed", "form", "canvas"}
_ALLOWED_ATTRS = {
    "alt",
    "class",
    "colspan",
    "controls",
    "decoding",
    "height",
    "loading",
    "loop",
    "muted",
    "playsinline",
    "poster",
    "role",
    "rowspan",
    "title",
    "type",
    "viewbox",
    "width",
}
_URL_ATTRS = {"href", "poster", "src"}
_SVG_REFERENCE_ATTRS = {
    "clip-path",
    "fill",
    "filter",
    "marker-end",
    "marker-mid",
    "marker-start",
    "mask",
    "stroke",
}
_SVG_ATTRS = {
    "clip-path",
    "cx",
    "cy",
    "d",
    "fill",
    "fill-opacity",
    "filter",
    "gradienttransform",
    "gradientunits",
    "height",
    "marker-end",
    "marker-mid",
    "marker-start",
    "mask",
    "offset",
    "points",
    "preserveaspectratio",
    "r",
    "rx",
    "ry",
    "spreadmethod",
    "stop-color",
    "stop-opacity",
    "stroke",
    "stroke-dasharray",
    "stroke-linecap",
    "stroke-linejoin",
    "stroke-opacity",
    "stroke-width",
    "transform",
    "viewbox",
    "width",
    "x",
    "x1",
    "x2",
    "y",
    "y1",
    "y2",
}
_UNSAFE_CSS = re.compile(
    r"(?:expression\s*\(|javascript\s*:|vbscript\s*:|-moz-binding\s*:|behavior\s*:)",
    re.IGNORECASE,
)
_CSS_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_STYLE_BLOCK = re.compile(r"<style\b[^>]*>(.*?)</style\s*>", re.IGNORECASE | re.DOTALL)
_SCRIPT_BLOCK = re.compile(r"<script\b[^>]*>.*?</script\s*>", re.IGNORECASE | re.DOTALL)
_FONT_LINK = re.compile(
    r"<link\b[^>]*href=[\"'](https://fonts\.googleapis\.com/[^\"']+)[\"'][^>]*>",
    re.IGNORECASE,
)


def _safe_href(value: str) -> str | None:
    cleaned = html.unescape(value or "").strip()
    if cleaned.startswith(("#", "mailto:", "tel:")):
        return cleaned
    if cleaned.startswith("/") and not cleaned.startswith("//"):
        return cleaned
    parsed = urlparse(cleaned)
    if parsed.scheme == "https":
        return cleaned
    return None


class _Sanitizer(HTMLParser):
    def __init__(self, *, layer_id: str) -> None:
        super().__init__(convert_charrefs=True)
        self.layer_id = layer_id
        self.output: list[str] = []
        self.drop_depth = 0
        self.removed_tags: set[str] = set()
        self.removed_attributes: set[str] = set()
        self.open_tags: list[str] = []
        self.plain: list[str] = []
        self.id_map: dict[str, str] = {}
        self.inline_style_report: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if self.drop_depth:
            if tag in _DROP_WITH_CONTENT:
                self.drop_depth += 1
            return
        if tag in _DROP_WITH_CONTENT:
            self.drop_depth = 1
            self.removed_tags.add(tag)
            return
        if tag not in _ALLOWED_TAGS:
            self.removed_tags.add(tag)
            return

        safe_attrs: list[str] = []
        for key, raw_value in attrs:
            name = key.lower()
            value = str(raw_value or "")
            if name.startswith("on"):
                self.removed_attributes.add(name)
                continue
            if name == "id":
                clean_id = re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-")
                if clean_id:
                    namespaced = f"{self.layer_id}--{clean_id}"
                    self.id_map[clean_id] = namespaced
                    safe_attrs.append(
                        f'id="{html.escape(namespaced, quote=True)}"'
                    )
                else:
                    self.removed_attributes.add(name)
                continue
            if name == "style":
                safe_style = _safe_declarations(
                    value,
                    self.inline_style_report,
                )
                if safe_style:
                    safe_attrs.append(
                        f'style="{html.escape(safe_style, quote=True)}"'
                    )
                else:
                    self.removed_attributes.add(name)
                continue
            if name in _SVG_REFERENCE_ATTRS:
                local_reference = re.fullmatch(
                    r"\s*url\(\s*#([A-Za-z_][\w:.-]*)\s*\)\s*",
                    value,
                    re.IGNORECASE,
                )
                if local_reference:
                    clean_reference = re.sub(
                        r"[^a-zA-Z0-9_-]+",
                        "-",
                        local_reference.group(1),
                    ).strip("-")
                    safe_attrs.append(
                        f'{name}="url(#{html.escape(self.layer_id, quote=True)}--'
                        f'{html.escape(clean_reference, quote=True)})"'
                    )
                    continue
                if "url(" in value.lower() or _UNSAFE_CSS.search(value):
                    self.removed_attributes.add(name)
                    continue
            if name in _URL_ATTRS:
                safe_url = _safe_href(value)
                if safe_url:
                    if safe_url.startswith("#"):
                        fragment = re.sub(
                            r"[^a-zA-Z0-9_-]+",
                            "-",
                            safe_url[1:],
                        ).strip("-")
                        safe_url = f"#{self.layer_id}--{fragment}"
                    safe_attrs.append(
                        f'{name}="{html.escape(safe_url, quote=True)}"'
                    )
                    if tag == "a" and name == "href":
                        safe_attrs.append('rel="noopener noreferrer"')
                else:
                    self.removed_attributes.add(name)
                continue
            if name.startswith("data-"):
                safe_attrs.append(
                    f'{name}="{html.escape(value[:2000], quote=True)}"'
                )
                continue
            if name in _SVG_ATTRS and tag in {
                "svg",
                "g",
                "path",
                "circle",
                "ellipse",
                "line",
                "polyline",
                "polygon",
                "rect",
                "defs",
                "lineargradient",
                "radialgradient",
                "stop",
                "mask",
            }:
                safe_attrs.append(
                    f'{name}="{html.escape(value, quote=True)}"'
                )
                continue
            if name in _ALLOWED_ATTRS or name.startswith("aria-"):
                if name in {"aria-controls", "aria-labelledby", "aria-describedby"}:
                    refs = [
                        f"{self.layer_id}--{re.sub(r'[^a-zA-Z0-9_-]+', '-', ref)}"
                        for ref in value.split()
                        if ref
                    ]
                    value = " ".join(refs)
                safe_attrs.append(
                    f'{name}="{html.escape(value, quote=True)}"'
                )
            else:
                self.removed_attributes.add(name)
        suffix = (" " + " ".join(dict.fromkeys(safe_attrs))) if safe_attrs else ""
        self.output.append(f"<{tag}{suffix}>")
        if tag not in _VOID_TAGS:
            self.open_tags.append(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self.drop_depth:
            if tag in _DROP_WITH_CONTENT:
                self.drop_depth -= 1
            return
        if tag not in _ALLOWED_TAGS or tag in _VOID_TAGS:
            return
        if tag not in self.open_tags:
            return
        while self.open_tags:
            current = self.open_tags.pop()
            self.output.append(f"</{current}>")
            if current == tag:
                break

    def handle_data(self, data: str) -> None:
        if self.drop_depth:
            return
        self.output.append(html.escape(data))
        self.plain.append(data)

    def close(self) -> None:
        super().close()
        while self.open_tags:
            self.output.append(f"</{self.open_tags.pop()}>")


def _balanced_blocks(css: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    pos = 0
    length = len(css)
    while pos < length:
        open_pos = css.find("{", pos)
        if open_pos < 0:
            break
        prelude = css[pos:open_pos].strip()
        depth = 1
        cursor = open_pos + 1
        quote = ""
        while cursor < length and depth:
            char = css[cursor]
            if quote:
                if char == quote and css[cursor - 1] != "\\":
                    quote = ""
            elif char in ("'", '"'):
                quote = char
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
            cursor += 1
        if depth:
            break
        body = css[open_pos + 1 : cursor - 1]
        if prelude:
            blocks.append((prelude, body))
        pos = cursor
    return blocks


def _safe_declarations(
    body: str,
    report: list[str],
    *,
    keyframe_map: dict[str, str] | None = None,
) -> str:
    declarations: list[str] = []
    for chunk in body.split(";"):
        if ":" not in chunk:
            continue
        prop, value = chunk.split(":", 1)
        prop = prop.strip()
        value = value.strip()
        if not re.fullmatch(r"--[\w-]+|[a-zA-Z-]+", prop):
            continue
        if (
            _UNSAFE_CSS.search(f"{prop}:{value}")
            or "url(" in value.lower()
            or prop.lower() in {"all", "content-visibility"}
            or (
                prop.lower() == "position"
                and value.strip().lower() == "fixed"
            )
        ):
            report.append(f"Usunięto niebezpieczną deklarację CSS: {prop}.")
            continue
        if keyframe_map and prop.lower() in {
            "animation",
            "animation-name",
            "-webkit-animation",
            "-webkit-animation-name",
        }:
            for old_name, new_name in keyframe_map.items():
                value = re.sub(
                    rf"(?<![\w-]){re.escape(old_name)}(?![\w-])",
                    new_name,
                    value,
                )
        declarations.append(f"{prop}: {value}")
    return ";\n".join(declarations) + (";" if declarations else "")


def _split_css_selectors(prelude: str) -> list[str]:
    selectors: list[str] = []
    start = 0
    depth = 0
    quote = ""
    for index, char in enumerate(prelude):
        if quote:
            if char == quote and (index == 0 or prelude[index - 1] != "\\"):
                quote = ""
            continue
        if char in {"'", '"'}:
            quote = char
        elif char in {"(", "["}:
            depth += 1
        elif char in {")", "]"}:
            depth = max(0, depth - 1)
        elif char == "," and depth == 0:
            selectors.append(prelude[start:index].strip())
            start = index + 1
    selectors.append(prelude[start:].strip())
    return [selector for selector in selectors if selector]


def scope_css(
    css: str,
    layer_id: str,
    *,
    id_map: dict[str, str] | None = None,
) -> tuple[str, list[str]]:
    report: list[str] = []
    cleaned = _CSS_COMMENT.sub("", css or "")
    cleaned = re.sub(r"@import\b[^;]*;", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"@charset\b[^;]*;", "", cleaned, flags=re.IGNORECASE)
    scope = f'[data-giclee-text-layer-id="{layer_id}"]'
    adapted_visibility = False
    keyframe_map = {
        match.group(1): f"{layer_id}--kf--{match.group(1)}"
        for match in re.finditer(
            r"@(?:-webkit-)?keyframes\s+([a-zA-Z_][\w-]*)",
            cleaned,
            re.IGNORECASE,
        )
    }

    def convert(source: str, *, keyframe_body: bool = False) -> str:
        nonlocal adapted_visibility
        output: list[str] = []
        for prelude, body in _balanced_blocks(source):
            low = prelude.lower()
            if low.startswith(("@media", "@supports", "@container", "@layer")):
                nested = convert(body)
                if nested:
                    output.append(f"{prelude} {{\n{nested}\n}}")
                continue
            if low.startswith(("@keyframes", "@-webkit-keyframes")):
                match = re.match(
                    r"(@(?:-webkit-)?keyframes)\s+([a-zA-Z_][\w-]*)",
                    prelude,
                    re.IGNORECASE,
                )
                if match:
                    name = keyframe_map.get(match.group(2), match.group(2))
                    nested = convert(body, keyframe_body=True)
                    if nested:
                        output.append(f"{match.group(1)} {name} {{\n{nested}\n}}")
                continue
            if low.startswith(("@font-face", "@page")):
                report.append(f"Usunięto regułę CSS: {prelude.split()[0]}.")
                continue
            if low.startswith("@"):
                report.append(f"Usunięto nieobsługiwaną regułę CSS: {prelude.split()[0]}.")
                continue
            declarations = _safe_declarations(
                body,
                report,
                keyframe_map=keyframe_map,
            )
            if not declarations:
                continue
            if keyframe_body:
                output.append(f"{prelude} {{\n{declarations}\n}}")
                continue
            selectors: list[str] = []
            for selector in _split_css_selectors(prelude):
                selector = selector.strip()
                if not selector:
                    continue
                for old_id, new_id in (id_map or {}).items():
                    selector = re.sub(
                        rf"#{re.escape(old_id)}(?![\w-])",
                        f"#{new_id}",
                        selector,
                    )
                if ".is-visible" in selector:
                    selector = selector.replace(".is-visible", "")
                    selector = f"{scope}.is-entered {selector}".strip()
                    adapted_visibility = True
                elif re.match(r"^(?::root|html|body)(?![\w-])", selector):
                    selector = re.sub(
                        r"^(?::root|html|body)(?![\w-])",
                        scope,
                        selector,
                        count=1,
                    )
                elif selector.startswith(scope):
                    pass
                else:
                    selector = f"{scope} {selector}"
                selectors.append(selector)
            if selectors:
                output.append(",\n".join(selectors) + " {\n" + declarations + "\n}")
        return "\n".join(output)

    scoped = convert(cleaned)
    if adapted_visibility:
        report.append(
            "Zaadaptowano klasę .is-visible do stanu animacji GicleeApp."
        )
    return scoped, report


def _adapt_observer_behavior(source: str) -> dict[str, Any]:
    if "IntersectionObserver" not in source:
        return {
            "trigger": "section-progress",
            "threshold": 0.08,
            "rootMargin": "0px",
            "once": False,
        }
    threshold_match = re.search(
        r"\bthreshold\s*:\s*(0(?:\.\d+)?|1(?:\.0+)?)",
        source,
    )
    margin_match = re.search(
        r"\brootMargin\s*:\s*[\"']([^\"']+)[\"']",
        source,
    )
    threshold = float(threshold_match.group(1)) if threshold_match else 0.2
    return {
        "trigger": "intersection",
        "threshold": max(0.0, min(1.0, threshold)),
        "rootMargin": (
            margin_match.group(1)[:100]
            if margin_match
            else "0px"
        ),
        "once": bool(re.search(r"\.(?:unobserve|disconnect)\s*\(", source)),
    }


def adapt_code(source: str, *, layer_id: str) -> dict[str, Any]:
    text = str(source or "")
    styles = _STYLE_BLOCK.findall(text)
    fonts = list(dict.fromkeys(_FONT_LINK.findall(text)))[:8]
    had_script = bool(_SCRIPT_BLOCK.search(text))
    stripped = _STYLE_BLOCK.sub("", text)
    stripped = _SCRIPT_BLOCK.sub("", stripped)
    stripped = re.sub(r"<link\b[^>]*>", "", stripped, flags=re.IGNORECASE)

    parser = _Sanitizer(layer_id=layer_id)
    parser.feed(stripped)
    parser.close()
    scoped_css, css_report = scope_css(
        "\n".join(styles),
        layer_id,
        id_map=parser.id_map,
    )
    report = [
        (
            "Tryb pełnego komponentu: zachowano bezpieczną strukturę HTML, "
            "obiekty dekoracyjne i układ CSS w przestrzeni wybranej sekcji."
        )
    ]
    report.extend(css_report)
    report.extend(parser.inline_style_report)
    if had_script:
        report.append(
            "Usunięto JavaScript. IntersectionObserver i klasy widoczności obsługuje runtime GicleeApp."
        )
    if parser.removed_tags:
        report.append(
            "Usunięto tagi: " + ", ".join(sorted(parser.removed_tags)) + "."
        )
    if parser.removed_attributes:
        report.append(
            "Usunięto atrybuty: "
            + ", ".join(sorted(parser.removed_attributes))
            + "."
        )
    if fonts:
        report.append(f"Zaadaptowano {len(fonts)} arkusz(e) Google Fonts.")
    preset = (
        "soft-blur-reveal"
        if re.search(
            r"\bblur\s*\(|opacity\s*:\s*0",
            "\n".join(styles),
            re.I,
        )
        else "fade-up"
    )
    behavior = _adapt_observer_behavior(text)
    owns_motion = ".is-visible" in "\n".join(styles) and had_script
    if owns_motion:
        preset = "none"
        report.append(
            "Zachowano własną animację komponentu; runtime steruje jej bezpiecznym stanem widoczności."
        )
    plain = " ".join("".join(parser.plain).split())
    return {
        "html": "".join(parser.output).strip(),
        "plainText": plain,
        "scopedCss": scoped_css,
        "fontUrls": fonts,
        "suggestedEnterPreset": preset,
        "componentMode": True,
        "ownsMotion": owns_motion,
        "behavior": behavior,
        "report": report,
    }


__all__ = ["adapt_code", "scope_css"]

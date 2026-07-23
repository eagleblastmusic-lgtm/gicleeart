"""Gemini + lokalne kadrowanie grafik mini-stron PDP v3.

Gemini analizuje tekst wszystkich stron i wskazuje obszary obrazu. GicleeApp
wycina wyłącznie oryginalne piksele przez Pillow; model nie generuje ani nie
retuszuje reprodukcji.
"""

from __future__ import annotations

import json
import math
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Iterable

TARGET_ASPECT_RATIO = 4 / 3.4  # zgodne z .giclee-story__frame w PDP v3
SOURCE_MAX_WIDTH = 4096
ANALYSIS_MAX_WIDTH = 1600
MIN_CROP_WIDTH_PX = 1200
MAX_VARIANTS_PER_PAGE = 3

StatusCallback = Callable[[str], None] | None
ShouldAbort = Callable[[], bool] | None


class SmartCropError(RuntimeError):
    """Błąd przygotowania inteligentnych kadrów."""


@dataclass(frozen=True)
class NormalizedBox:
    """Ramka [0..1] w układzie xmin, ymin, xmax, ymax."""

    xmin: float
    ymin: float
    xmax: float
    ymax: float

    @property
    def width(self) -> float:
        return max(0.0, self.xmax - self.xmin)

    @property
    def height(self) -> float:
        return max(0.0, self.ymax - self.ymin)

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center(self) -> tuple[float, float]:
        return ((self.xmin + self.xmax) / 2.0, (self.ymin + self.ymax) / 2.0)

    def clamped(self) -> "NormalizedBox":
        x1 = max(0.0, min(1.0, float(self.xmin)))
        y1 = max(0.0, min(1.0, float(self.ymin)))
        x2 = max(x1, min(1.0, float(self.xmax)))
        y2 = max(y1, min(1.0, float(self.ymax)))
        return NormalizedBox(x1, y1, x2, y2)


FULL_BOX = NormalizedBox(0.0, 0.0, 1.0, 1.0)


@dataclass(frozen=True)
class CropCandidate:
    box: NormalizedBox
    crop_type: str
    matched_subject: str
    reason: str
    confidence: float


@dataclass(frozen=True)
class RenderedVariant:
    box: NormalizedBox
    crop_type: str
    matched_subject: str
    reason: str
    confidence: float
    local_path: Path | None
    is_full_view: bool = False


@dataclass
class PageCropProposal:
    page_index: int
    page_text: str
    existing_image: str
    variants: list[RenderedVariant] = field(default_factory=list)
    selected_variant: int = 0


@dataclass
class CropSession:
    product_id: int
    title: str
    handle: str
    image_url: str
    paragraph_counts: list[int]
    page_texts: list[str]
    existing_config: dict[str, Any]
    proposals: list[PageCropProposal]
    source_size: tuple[int, int]
    model_used: str
    temp_dir: Path


@dataclass(frozen=True)
class ProductStoryContext:
    product_id: int
    title: str
    handle: str
    image_url: str
    paragraphs: list[str]
    config: dict[str, Any]


def build_page_texts(paragraphs: Iterable[str], paragraph_counts: Iterable[int]) -> list[str]:
    """Dzieli akapity według bieżącego układu mini-stron."""

    source = [str(p).strip() for p in paragraphs]
    out: list[str] = []
    cursor = 0
    for raw_count in paragraph_counts:
        try:
            count = max(1, int(raw_count))
        except (TypeError, ValueError):
            count = 1
        chunk = [p for p in source[cursor : cursor + count] if p]
        out.append("\n\n".join(chunk).strip())
        cursor += count
    return out


def extract_product_image_url(product: dict[str, Any]) -> str:
    """Zwraca główny URL obrazu z odpowiedzi Shopify REST."""

    image = product.get("image") or {}
    if isinstance(image, dict):
        src = str(image.get("src") or "").strip()
        if src:
            return src
    for item in product.get("images") or []:
        if not isinstance(item, dict):
            continue
        src = str(item.get("src") or "").strip()
        if src:
            return src
    return ""


def resolve_product_story_context(handle: str) -> ProductStoryContext:
    """Pobiera produkt, akapity, konfigurację stron i główny obraz."""

    from Komponenty.dodajobraz import shopify_client as sc
    from .service import load_product_story, normalize_story_config

    target = (handle or "").strip()
    if not target:
        raise SmartCropError("Brak handle wybranego produktu.")

    shop, token = sc.load_session()
    data = sc.rest_get(shop, token, "products.json", handle=target, limit=10)
    products = (data or {}).get("products") or []
    product = next(
        (p for p in products if str((p or {}).get("handle") or "").strip() == target),
        None,
    )
    if not product:
        raise SmartCropError(f"Nie znaleziono produktu o handle: {target}")

    try:
        product_id = int(product.get("id") or 0)
    except (TypeError, ValueError) as exc:
        raise SmartCropError("Produkt nie ma poprawnego ID.") from exc
    if not product_id:
        raise SmartCropError("Produkt nie ma poprawnego ID.")

    detail = load_product_story(product_id)
    if not detail.get("ok"):
        raise SmartCropError(str(detail.get("error") or "Nie udało się wczytać opisu produktu."))

    image_url = extract_product_image_url(product)
    if not image_url:
        image_url = extract_product_image_url(sc.get_product(shop, token, product_id))
    if not image_url:
        raise SmartCropError("Produkt nie ma głównego obrazu.")

    config = normalize_story_config(detail.get("config") or {})
    return ProductStoryContext(
        product_id=product_id,
        title=str(detail.get("title") or product.get("title") or "").strip(),
        handle=target,
        image_url=image_url,
        paragraphs=list(detail.get("paragraphs") or []),
        config=config,
    )


def _strip_json_wrapper(raw: str) -> str:
    text = (raw or "").strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        return fenced.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]
    return text


def _parse_box(raw: Any) -> NormalizedBox | None:
    if not isinstance(raw, (list, tuple)) or len(raw) != 4:
        return None
    try:
        ymin, xmin, ymax, xmax = [float(v) for v in raw]
    except (TypeError, ValueError):
        return None
    scale = 1000.0 if max(abs(ymin), abs(xmin), abs(ymax), abs(xmax)) > 1.5 else 1.0
    box = NormalizedBox(xmin / scale, ymin / scale, xmax / scale, ymax / scale).clamped()
    if box.width < 0.01 or box.height < 0.01:
        return None
    return box


def parse_crop_plan(raw: str, *, page_count: int) -> dict[int, list[CropCandidate]]:
    """Parsuje odpowiedź Gemini; pomija wadliwe wpisy bez wywracania sesji."""

    try:
        payload = json.loads(_strip_json_wrapper(raw))
    except json.JSONDecodeError as exc:
        raise SmartCropError(f"Gemini nie zwrócił poprawnego JSON: {exc}") from exc
    pages = payload.get("pages") if isinstance(payload, dict) else None
    if not isinstance(pages, list):
        raise SmartCropError("Odpowiedź Gemini nie zawiera tablicy pages.")

    out: dict[int, list[CropCandidate]] = {}
    for item in pages:
        if not isinstance(item, dict):
            continue
        try:
            page_index = int(item.get("page_index"))
        except (TypeError, ValueError):
            continue
        if page_index < 0 or page_index >= page_count or page_index == 0:
            continue
        raw_candidates = item.get("candidates")
        if not isinstance(raw_candidates, list):
            raw_candidates = [item]
        candidates: list[CropCandidate] = []
        for candidate in raw_candidates[:8]:
            if not isinstance(candidate, dict):
                continue
            box = _parse_box(candidate.get("box_2d"))
            if box is None:
                continue
            try:
                confidence = float(candidate.get("confidence", 0.5))
            except (TypeError, ValueError):
                confidence = 0.5
            candidates.append(
                CropCandidate(
                    box=box,
                    crop_type=str(candidate.get("crop_type") or "detail").strip()[:80],
                    matched_subject=str(candidate.get("matched_subject") or "fragment dzieła").strip()[:160],
                    reason=str(candidate.get("reason") or "Dopasowanie do tekstu strony.").strip()[:500],
                    confidence=max(0.0, min(1.0, confidence)),
                )
            )
        if candidates:
            out[page_index] = candidates
    return out


def _fit_interval(center: float, length: float) -> tuple[float, float]:
    length = max(0.0, min(1.0, length))
    start = center - length / 2.0
    end = center + length / 2.0
    if start < 0.0:
        end -= start
        start = 0.0
    if end > 1.0:
        start -= end - 1.0
        end = 1.0
    return max(0.0, start), min(1.0, end)


def fit_box_to_aspect(
    box: NormalizedBox,
    *,
    source_size: tuple[int, int],
    target_aspect: float = TARGET_ASPECT_RATIO,
    min_width_px: int = MIN_CROP_WIDTH_PX,
    padding: float = 0.08,
) -> NormalizedBox:
    """Rozszerza ramkę do ratio pola PDP bez wyjścia poza obraz."""

    source_w, source_h = source_size
    if source_w <= 0 or source_h <= 0:
        raise ValueError("Niepoprawny rozmiar obrazu źródłowego.")
    b = box.clamped()
    cx, cy = b.center
    width = min(1.0, max(b.width * (1.0 + 2.0 * padding), min_width_px / source_w))
    height = min(1.0, b.height * (1.0 + 2.0 * padding))

    current_aspect = (width * source_w) / max(1e-9, height * source_h)
    if current_aspect < target_aspect:
        width = min(1.0, target_aspect * height * source_h / source_w)
    else:
        height = min(1.0, width * source_w / (target_aspect * source_h))

    if width >= 1.0:
        height = min(1.0, source_w / (target_aspect * source_h))
    if height >= 1.0:
        width = min(1.0, target_aspect * source_h / source_w)

    x1, x2 = _fit_interval(cx, width)
    y1, y2 = _fit_interval(cy, height)
    return NormalizedBox(x1, y1, x2, y2).clamped()


def box_iou(a: NormalizedBox, b: NormalizedBox) -> float:
    ix1 = max(a.xmin, b.xmin)
    iy1 = max(a.ymin, b.ymin)
    ix2 = min(a.xmax, b.xmax)
    iy2 = min(a.ymax, b.ymax)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    union = a.area + b.area - inter
    return inter / union if union > 0 else 0.0


def rank_page_candidates(
    plan: dict[int, list[CropCandidate]],
    *,
    page_count: int,
    source_size: tuple[int, int],
) -> dict[int, list[CropCandidate]]:
    """Wybiera z kandydatów różnorodne, poprawne kompozycyjnie warianty."""

    selected_boxes: list[NormalizedBox] = [FULL_BOX]
    result: dict[int, list[CropCandidate]] = {}
    for page_index in range(1, page_count):
        raw = plan.get(page_index) or []
        scored: list[tuple[float, CropCandidate]] = []
        for candidate in raw:
            adjusted = fit_box_to_aspect(candidate.box, source_size=source_size)
            max_overlap = max((box_iou(adjusted, prev) for prev in selected_boxes[1:]), default=0.0)
            tiny_penalty = max(0.0, 0.12 - adjusted.area) * 1.8
            edge_penalty = 0.03 if adjusted.xmin == 0 and adjusted.xmax == 1 else 0.0
            score = candidate.confidence - 0.42 * max_overlap - tiny_penalty - edge_penalty
            scored.append(
                (
                    score,
                    CropCandidate(
                        box=adjusted,
                        crop_type=candidate.crop_type,
                        matched_subject=candidate.matched_subject,
                        reason=candidate.reason,
                        confidence=candidate.confidence,
                    ),
                )
            )
        scored.sort(key=lambda item: item[0], reverse=True)
        unique: list[CropCandidate] = []
        for _, candidate in scored:
            if any(box_iou(candidate.box, old.box) > 0.92 for old in unique):
                continue
            unique.append(candidate)
            if len(unique) >= MAX_VARIANTS_PER_PAGE:
                break
        if not unique:
            unique = [
                CropCandidate(
                    box=fit_box_to_aspect(FULL_BOX, source_size=source_size, padding=0.0),
                    crop_type="safe_wide",
                    matched_subject="szerszy widok dzieła",
                    reason="Model nie wskazał pewnego detalu; użyto bezpiecznego szerokiego kadru.",
                    confidence=0.25,
                )
            ]
        result[page_index] = unique
        selected_boxes.append(unique[0].box)
    return result


def build_gemini_prompt(*, title: str, page_texts: list[str]) -> str:
    pages_json = json.dumps(
        [{"page_index": i, "text": text} for i, text in enumerate(page_texts)],
        ensure_ascii=False,
        indent=2,
    )
    return f"""
Jesteś kuratorem sztuki i analitykiem kompozycji obrazu. Analizujesz reprodukcję
oraz teksty kolejnych mini-stron produktu „{title}”. Masz wskazać wyłącznie
kadry z ORYGINALNEGO obrazu; niczego nie generuj, nie retuszuj i nie dopowiadaj.

Zasady:
1. Strona 0 zawsze pokaże pełny obraz — NIE zwracaj dla niej kandydatów.
2. Dla każdej kolejnej strony znajdź 2–3 różne kadry pasujące do treści.
3. Szukaj konkretnych postaci, gestów, architektury, nieba, światła, tkanin,
   przedmiotów, fragmentów pejzażu lub innych elementów faktycznie widocznych.
4. Przy tekście abstrakcyjnym wybierz szerszy kadr atmosferyczny.
5. Unikaj niemal identycznych kadrów między stronami i przypadkowego ucinania
   twarzy, dłoni oraz głównych obiektów.
6. box_2d ma format [ymin, xmin, ymax, xmax], współrzędne całkowite 0–1000.
7. confidence ma być liczbą 0–1.
8. Zwróć WYŁĄCZNIE poprawny JSON, bez markdownu i komentarzy.

Wymagany format:
{{
  "pages": [
    {{
      "page_index": 1,
      "candidates": [
        {{
          "box_2d": [100, 200, 800, 750],
          "crop_type": "subject_detail",
          "matched_subject": "krótka nazwa widocznego motywu",
          "reason": "krótkie uzasadnienie po polsku",
          "confidence": 0.86
        }}
      ]
    }}
  ]
}}

Teksty mini-stron:
{pages_json}
""".strip()


def _require_pillow() -> tuple[Any, Any]:
    try:
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise SmartCropError("Funkcja AI wymaga Pillow. Zainstaluj: pip install Pillow") from exc
    return Image, ImageOps


def _prepare_images(source_bytes: bytes) -> tuple[Any, bytes, str, tuple[int, int], dict[str, Any]]:
    Image, ImageOps = _require_pillow()
    try:
        with Image.open(BytesIO(source_bytes)) as opened:
            source = ImageOps.exif_transpose(opened).copy()
            metadata = {"icc_profile": opened.info.get("icc_profile")}
    except Exception as exc:
        raise SmartCropError(f"Nie udało się otworzyć obrazu produktu: {exc}") from exc

    if source.mode not in ("RGB", "L"):
        background = Image.new("RGB", source.size, "white")
        if "A" in source.getbands():
            background.paste(source, mask=source.getchannel("A"))
        else:
            background.paste(source.convert("RGB"))
        source = background
    elif source.mode == "L":
        source = source.convert("RGB")

    analysis = source.copy()
    if analysis.width > ANALYSIS_MAX_WIDTH:
        height = max(1, round(analysis.height * ANALYSIS_MAX_WIDTH / analysis.width))
        analysis = analysis.resize((ANALYSIS_MAX_WIDTH, height), Image.Resampling.LANCZOS)
    buf = BytesIO()
    analysis.save(buf, "JPEG", quality=90, optimize=True)
    return source, buf.getvalue(), "image/jpeg", source.size, metadata


def _pixel_box(box: NormalizedBox, size: tuple[int, int]) -> tuple[int, int, int, int]:
    width, height = size
    left = max(0, min(width - 1, int(math.floor(box.xmin * width))))
    top = max(0, min(height - 1, int(math.floor(box.ymin * height))))
    right = max(left + 1, min(width, int(math.ceil(box.xmax * width))))
    bottom = max(top + 1, min(height, int(math.ceil(box.ymax * height))))
    return left, top, right, bottom


def _save_crop(source: Any, box: NormalizedBox, path: Path, metadata: dict[str, Any]) -> None:
    crop = source.crop(_pixel_box(box, source.size)).convert("RGB")
    path.parent.mkdir(parents=True, exist_ok=True)
    kwargs: dict[str, Any] = {"quality": 95, "subsampling": 0, "optimize": True}
    if metadata.get("icc_profile"):
        kwargs["icc_profile"] = metadata["icc_profile"]
    crop.save(path, "JPEG", **kwargs)


def _slug(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip()).strip("-").lower()
    return text[:80] or "produkt"


def generate_crop_session(
    *,
    handle: str,
    paragraph_counts: list[int],
    model: str | None = None,
    on_status: StatusCallback = None,
    should_abort: ShouldAbort = None,
) -> CropSession:
    """Pełny etap: Shopify → Gemini → lokalne warianty cropów do podglądu."""

    from Komponenty._shared.clipboard_image import fetch_image_bytes, shopify_sized_image_url
    from Komponenty._shared.gemini_client import DEFAULT_MODEL, generate_from_image_bytes

    def status(message: str) -> None:
        if on_status:
            on_status(message)

    if should_abort and should_abort():
        raise SmartCropError("Przerwano.")
    status("Pobieram produkt i tekst mini-stron...")
    context = resolve_product_story_context(handle)
    counts = [max(1, int(v)) for v in paragraph_counts]
    texts = build_page_texts(context.paragraphs, counts)
    if not texts:
        raise SmartCropError("Brak mini-stron do analizy.")

    status("Pobieram główny obraz w wysokiej jakości...")
    source_url = shopify_sized_image_url(context.image_url, width=SOURCE_MAX_WIDTH)
    source_bytes = fetch_image_bytes(source_url, timeout=60.0)
    source, analysis_bytes, analysis_mime, source_size, metadata = _prepare_images(source_bytes)

    model_used = "bez wywołania Gemini"
    ranked: dict[int, list[CropCandidate]] = {}
    if len(texts) > 1:
        prompt = build_gemini_prompt(title=context.title, page_texts=texts)
        raw, model_used = generate_from_image_bytes(
            image_bytes=analysis_bytes,
            mime_type=analysis_mime,
            prompt=prompt,
            model=(model or DEFAULT_MODEL),
            on_status=on_status,
            should_abort=should_abort,
        )
        plan = parse_crop_plan(raw, page_count=len(texts))
        ranked = rank_page_candidates(plan, page_count=len(texts), source_size=source_size)

    temp_dir = Path(tempfile.mkdtemp(prefix=f"giclee-story-crops-{context.product_id}-"))
    full_preview_path = temp_dir / f"{_slug(context.handle)}-story-full-preview.jpg"
    _save_crop(source, FULL_BOX, full_preview_path, metadata)
    proposals: list[PageCropProposal] = []
    existing_pages = list((context.config or {}).get("pages") or [])
    full_variant = RenderedVariant(
        box=FULL_BOX,
        crop_type="full_view",
        matched_subject="pełny obraz",
        reason="Pełny obraz produktu — bez tworzenia kopii w Shopify Files.",
        confidence=1.0,
        local_path=full_preview_path,
        is_full_view=True,
    )
    for page_index, page_text in enumerate(texts):
        existing = ""
        if page_index < len(existing_pages):
            existing = str((existing_pages[page_index] or {}).get("image") or "").strip()
        variants: list[RenderedVariant] = []
        if page_index == 0:
            variants = [full_variant]
        else:
            for variant_index, candidate in enumerate(ranked.get(page_index) or []):
                path = temp_dir / f"{_slug(context.handle)}-story-{page_index + 1}-v{variant_index + 1}.jpg"
                _save_crop(source, candidate.box, path, metadata)
                variants.append(
                    RenderedVariant(
                        box=candidate.box,
                        crop_type=candidate.crop_type,
                        matched_subject=candidate.matched_subject,
                        reason=candidate.reason,
                        confidence=candidate.confidence,
                        local_path=path,
                    )
                )
            variants.append(full_variant)
        proposals.append(
            PageCropProposal(
                page_index=page_index,
                page_text=page_text,
                existing_image=existing,
                variants=variants,
            )
        )
    try:
        source.close()
    except Exception:
        pass
    status("Kadry są gotowe do podglądu.")
    return CropSession(
        product_id=context.product_id,
        title=context.title,
        handle=context.handle,
        image_url=context.image_url,
        paragraph_counts=counts,
        page_texts=texts,
        existing_config=context.config,
        proposals=proposals,
        source_size=source_size,
        model_used=model_used,
        temp_dir=temp_dir,
    )


def save_selected_crops(
    session: CropSession,
    selections: dict[int, int],
    *,
    on_status: StatusCallback = None,
) -> dict[str, Any]:
    """Uploaduje zatwierdzone kadry i zapisuje custom.story_pages w Shopify."""

    from .service import save_story_config, upload_story_image

    existing_pages = list((session.existing_config or {}).get("pages") or [])
    pages: list[dict[str, Any]] = []
    for index, count in enumerate(session.paragraph_counts):
        old_image = ""
        if index < len(existing_pages):
            old_image = str((existing_pages[index] or {}).get("image") or "").strip()
        pages.append({"paragraphs": max(1, int(count)), "image": old_image})

    uploaded: dict[int, str] = {}
    for page_index in sorted(selections):
        if page_index < 0 or page_index >= len(session.proposals):
            continue
        proposal = session.proposals[page_index]
        variant_index = int(selections[page_index])
        if variant_index < 0 or variant_index >= len(proposal.variants):
            continue
        variant = proposal.variants[variant_index]
        if variant.is_full_view:
            pages[page_index]["image"] = ""
            continue
        if not variant.local_path or not variant.local_path.is_file():
            raise SmartCropError(f"Brak lokalnego kadru dla strony {page_index + 1}.")
        if on_status:
            on_status(f"Wgrywam kadr strony {page_index + 1}/{len(session.proposals)}...")
        alt = f"{session.title} — fragment do strony {page_index + 1}"
        url = upload_story_image(variant.local_path, alt=alt)
        pages[page_index]["image"] = url
        uploaded[page_index] = url

    config: dict[str, Any] = {"pages": pages}
    details_image = str((session.existing_config or {}).get("details_image") or "").strip()
    if details_image:
        config["details_image"] = details_image
    if on_status:
        on_status("Zapisuję konfigurację mini-stron w Shopify...")
    result = save_story_config(session.product_id, config)
    result["uploaded"] = uploaded
    return result


def cleanup_crop_session(session: CropSession | None) -> None:
    if not session:
        return
    try:
        shutil.rmtree(session.temp_dir, ignore_errors=True)
    except OSError:
        pass

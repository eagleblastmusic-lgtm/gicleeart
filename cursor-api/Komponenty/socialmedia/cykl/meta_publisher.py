"""Publikacja postow do Meta Graph API v19 (Facebook + Instagram).

## Wymagane credentiale (plik data/cykl/meta_credentials.json)

```json
{
  "fb_pl": {"page_id": "...",      "access_token": "..."},
  "fb_en": {"page_id": "...",      "access_token": "..."},
  "ig_pl": {"ig_user_id": "...",   "access_token": "..."},
  "ig_en": {"ig_user_id": "...",   "access_token": "..."}
}
```

- FB `page_id`: numeryczny ID strony FB (z Meta Business Suite -> Settings -> Page Info).
- FB `access_token`: najlepiej **Page Access Token**. Mozesz tez wkleic **long-lived User token**
  (pages_manage_posts, pages_show_list) — przed publikacja kod zamieni go na token strony
  (`GET /{page-id}?fields=access_token`), zeby uniknac bledu o deprecated `publish_actions`.
- IG `ig_user_id`: Instagram Business Account ID (z GET /me/accounts?fields=instagram_business_account).
- IG `access_token`: ten sam Page Access Token co dla powiazanej strony FB
  (Instagram Content Publishing wymaga scope instagram_basic, instagram_content_publish,
  pages_read_engagement).

## Flow publikacji

- **FB single photo**: POST /{page_id}/photos url=<cdn> message=<caption> access_token=...
- **FB sam tekst**: POST /{page_id}/feed message=<tresc> access_token=... (bez zdjecia)
- **IG single**: POST /{ig_user_id}/media image_url=... caption=... -> creation_id.
  Potem POST /{ig_user_id}/media_publish creation_id=... -> media_id.
- **IG carousel (2-10 obrazow)**:
    1. Dla kazdego obrazu: POST /{ig_user_id}/media image_url=... is_carousel_item=true -> child_id.
    2. POST /{ig_user_id}/media media_type=CAROUSEL children=id1,id2,... caption=...
    3. POST /{ig_user_id}/media_publish creation_id=...

## Problem: IG wymaga publicznych URL-i zdjec

Uzywamy Shopify Files API do hostingu zoomow i mockupa (main image ma juz CDN URL
z product.image.src). `upload_to_shopify_files()` korzysta z GraphQL `stagedUploadsCreate`
+ upload na GCS + `fileCreate` -> `File.url`. URL-e cache'ujemy w CykleItem.cdn_*.
"""

from __future__ import annotations

import base64
import json
import mimetypes
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

# Reuse klienta Shopify (graphql + rest + load_session)
from Komponenty.dodajobraz import shopify_client as sc  # type: ignore

from . import images, storage
from . import platforms_cykl as _cp

GRAPH_API_VERSION = "v19.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


class MetaError(RuntimeError):
    """Blad publikacji Meta API."""


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _post(url: str, payload) -> dict:
    """POST form-urlencoded. `payload` moze byc dict lub list of tuples
    (dla parametrow z powtorzonymi kluczami typu attached_media[0/1/2])."""
    if isinstance(payload, dict):
        data = urllib.parse.urlencode(payload).encode("utf-8")
    else:
        data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=30) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        msg = f"HTTP {e.code} POST {url}\n{detail}"
        if "publish_actions" in detail:
            msg += (
                "\n\nFacebook wymaga **Page Access Token** (nie profilu uzytkownika). "
                "W konfiguracji Meta wklej token strony albo long-lived user token "
                "z scope pages_manage_posts — aplikacja probuje zamienic go na token strony."
            )
        raise MetaError(msg) from e
    except urllib.error.URLError as e:
        raise MetaError(f"Network error POST {url}: {e}") from e
    try:
        return json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        raise MetaError(f"Invalid JSON from {url}: {raw[:200]}")


def _get(url: str, params: dict[str, str]) -> dict:
    qs = urllib.parse.urlencode(params)
    full = f"{url}?{qs}"
    req = urllib.request.Request(full, method="GET")
    try:
        with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=30) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise MetaError(f"HTTP {e.code} GET {full}\n{detail}") from e
    except urllib.error.URLError as e:
        raise MetaError(f"Network error GET {full}: {e}") from e
    return json.loads(raw) if raw else {}


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------

def check_credentials(channel_code: str) -> tuple[bool, str]:
    """Sprawdza czy credentiale dla kanalu sa skonfigurowane. Zwraca (ok, msg)."""
    creds = storage.load_meta_credentials().get(channel_code) or {}
    ch = _cp.get(channel_code)
    if ch is None:
        return False, f"Nieznany kanal: {channel_code}"
    token = creds.get("access_token", "")
    if not token:
        return False, f"Brak access_token dla {ch.label}"
    if ch.platform == "fb":
        if not creds.get("page_id"):
            return False, f"Brak page_id dla {ch.label}"
    else:
        if not creds.get("ig_user_id"):
            return False, f"Brak ig_user_id dla {ch.label}"
    return True, "OK"


# Cache Page tokena w sesji procesu (ten sam user token + page_id -> token strony).
_fb_page_token_cache: dict[tuple[str, str], str] = {}


def resolve_fb_page_access_token(page_id: str, access_token: str) -> str:
    """Zwraca Page Access Token do publikacji na stronie FB.

    POST /{page_id}/photos z **User** tokenem bez zamiany konczy sie bledem o
    `publish_actions` (deprecated). Poprawny flow: user token z
    `pages_manage_posts` -> GET `/{page_id}?fields=access_token` -> page token.
    """
    pid = str(page_id).strip()
    tok = (access_token or "").strip()
    if not pid or not tok:
        return tok
    cache_key = (pid, tok)
    if cache_key in _fb_page_token_cache:
        return _fb_page_token_cache[cache_key]

    resolved: str | None = None
    try:
        r = _get(f"{GRAPH_BASE}/{pid}", {"fields": "access_token", "access_token": tok})
        at = r.get("access_token")
        if isinstance(at, str) and len(at) > 12:
            resolved = at
    except MetaError:
        pass

    if resolved is None:
        try:
            r = _get(
                f"{GRAPH_BASE}/me/accounts",
                {"fields": "id,access_token", "access_token": tok},
            )
        except MetaError:
            _fb_page_token_cache[cache_key] = tok
            return tok
        accounts = r.get("data") or []
        for acc in accounts:
            if str(acc.get("id")) == pid:
                at = acc.get("access_token")
                if isinstance(at, str) and len(at) > 12:
                    resolved = at
                break
        if resolved is None and accounts:
            raise MetaError(
                f"Token OAuth nie obejmuje strony Facebook o id={pid} "
                "(brak jej na liscie /me/accounts). Sprawdz page_id w "
                "Meta Business Suite albo wygeneruj token na tej stronie."
            )

    out = resolved if resolved is not None else tok
    _fb_page_token_cache[cache_key] = out
    return out


# ---------------------------------------------------------------------------
# Shopify Files upload (dla zoomow / mockup - zeby mialy public CDN URL)
# ---------------------------------------------------------------------------

def _http_put_raw(url: str, body: bytes, content_type: str,
                   extra_headers: dict[str, str] | None = None) -> None:
    """PUT surowych bajtow (dla Google Cloud Storage upload URL)."""
    headers = {"Content-Type": content_type}
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, data=body, headers=headers, method="PUT")
    try:
        with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=60) as _:
            pass
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise MetaError(f"HTTP {e.code} PUT staged upload\n{detail}") from e


def _http_post_multipart(url: str, body: bytes, content_type: str) -> str:
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": content_type},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=120) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise MetaError(f"HTTP {e.code} POST multipart\n{detail}") from e


def upload_to_shopify_files_with_id(local_path: Path) -> tuple[str, str]:
    """Upload do Shopify Files; zwraca (publiczny CDN URL, id pliku do fileDelete).

    Kroki jak w `upload_to_shopify_files`.
    """
    local_path = Path(local_path)
    if not local_path.is_file():
        raise MetaError(f"Plik nie istnieje: {local_path}")
    shop, token = sc.load_session()
    raw = local_path.read_bytes()
    size = len(raw)
    mime = mimetypes.guess_type(local_path.name)[0] or "image/jpeg"
    filename = local_path.name

    # 1) stagedUploadsCreate
    mutation = """
    mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
      stagedUploadsCreate(input: $input) {
        stagedTargets {
          url
          resourceUrl
          parameters { name value }
        }
        userErrors { field message }
      }
    }
    """
    variables = {
        "input": [{
            "resource": "FILE",
            "filename": filename,
            "mimeType": mime,
            "httpMethod": "POST",
            "fileSize": str(size),
        }],
    }
    data = sc.graphql(shop, token, mutation, variables)
    res = (data or {}).get("stagedUploadsCreate") or {}
    errs = res.get("userErrors") or []
    if errs:
        raise MetaError(f"stagedUploadsCreate errors: {errs}")
    targets = res.get("stagedTargets") or []
    if not targets:
        raise MetaError("stagedUploadsCreate: brak targets w odpowiedzi")
    t = targets[0]
    upload_url = t.get("url")
    resource_url = t.get("resourceUrl")
    params = {p["name"]: p["value"] for p in (t.get("parameters") or [])}

    # 2) POST multipart
    boundary = "----gicleeart-" + uuid.uuid4().hex
    lines: list[bytes] = []
    for name, value in params.items():
        lines.append(f"--{boundary}\r\n".encode("utf-8"))
        lines.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        lines.append(f"{value}\r\n".encode("utf-8"))
    lines.append(f"--{boundary}\r\n".encode("utf-8"))
    lines.append(
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode("utf-8")
    )
    lines.append(f"Content-Type: {mime}\r\n\r\n".encode("utf-8"))
    lines.append(raw)
    lines.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(lines)
    _http_post_multipart(upload_url, body, f"multipart/form-data; boundary={boundary}")

    # 3) fileCreate
    file_create = """
    mutation fileCreate($files: [FileCreateInput!]!) {
      fileCreate(files: $files) {
        files { id fileStatus ... on MediaImage { image { url } } ... on GenericFile { url } }
        userErrors { field message }
      }
    }
    """
    fc_vars = {"files": [{"alt": filename, "originalSource": resource_url}]}
    fc_data = sc.graphql(shop, token, file_create, fc_vars)
    fc_res = (fc_data or {}).get("fileCreate") or {}
    fc_errs = fc_res.get("userErrors") or []
    if fc_errs:
        raise MetaError(f"fileCreate errors: {fc_errs}")
    files = fc_res.get("files") or []
    if not files:
        raise MetaError("fileCreate: brak files w odpowiedzi")
    file_id = files[0].get("id")

    # 4) Polling az bedzie READY + url
    for _attempt in range(30):  # max 30s
        cdn_url = _poll_file_url(shop, token, file_id)
        if cdn_url:
            return cdn_url, str(file_id)
        time.sleep(1)
    raise MetaError(f"Shopify File {file_id} nie bylo gotowe po 30s.")


def upload_to_shopify_files(local_path: Path) -> str:
    """Uploaduje lokalny plik do Shopify Files i zwraca publiczny CDN URL.

    Kroki (Shopify GraphQL Admin 2026-04):
    1. stagedUploadsCreate(input) - zwraca target: url (upload POST), resourceUrl (do fileCreate).
    2. POST multipart na target.url (z parameters jako hidden fields) z plikiem.
    3. fileCreate(files: [{alt, originalSource: <resourceUrl>}]) - zwraca File.url (CDN).

    WAZNE: Shopify przetwarza plik asynchronicznie. Po fileCreate file.url moze byc puste
    przez kilka sekund - robimy polling po fileStatus.
    """
    url, _fid = upload_to_shopify_files_with_id(Path(local_path))
    return url


def delete_shopify_file_ids(file_ids: list[str]) -> None:
    """Usuwa pliki z Shopify Files (`fileDelete`). Best-effort — nie rzuca przy bledzie.

    Wymaga scope `write_files`. Uzywaj po udanym pobraniu obrazka przez Meta (URL juz nie
    jest potrzebny w sklepie).
    """
    ids = [str(i).strip() for i in file_ids if i and str(i).strip()]
    if not ids:
        return
    shop, token = sc.load_session()
    mutation = """
    mutation fileDelete($fileIds: [ID!]!) {
      fileDelete(fileIds: $fileIds) {
        deletedFileIds
        userErrors { field message code }
      }
    }
    """
    try:
        data = sc.graphql(shop, token, mutation, {"fileIds": ids})
        res = (data or {}).get("fileDelete") or {}
        errs = res.get("userErrors") or []
        if errs:
            pass  # cleanup nie blokuje aplikacji
    except Exception:
        pass


def _poll_file_url(shop: str, token: str, file_id: str) -> str:
    query = """
    query($id: ID!) {
      node(id: $id) {
        ... on MediaImage { fileStatus image { url } }
        ... on GenericFile { fileStatus url }
      }
    }
    """
    data = sc.graphql(shop, token, query, {"id": file_id})
    node = (data or {}).get("node") or {}
    status = str(node.get("fileStatus") or "")
    if status != "READY":
        return ""
    img = node.get("image") or {}
    return str(img.get("url") or node.get("url") or "")


# ---------------------------------------------------------------------------
# Preparacja CDN URL-i dla postu (z cache w CykleItem)
# ---------------------------------------------------------------------------

def _ensure_cdn_triplet(
    main_rel: str,
    zooms_rel: list[str],
    mockup_rel: str,
    cdn_main_current: str,
    cdn_zooms_current: list[str],
    cdn_mockup_current: str,
    *,
    product_image_fallback: str = "",
    logger=None,
) -> tuple[str, list[str], str]:
    """Generalizowana wersja - upload do Shopify Files dla triplet-u (main, zooms, mockup).

    Idempotentne: jesli cache `cdn_*_current` pasuje rozmiarem/obecnoscia,
    uzywamy go; w przeciwnym razie uploadujemy. Zwraca nowe (main_url,
    zooms_urls, mockup_url) - caller zapisuje je w odpowiednich polach item.
    """
    # MAIN
    if main_rel:
        if cdn_main_current:
            main_url = cdn_main_current
        else:
            local = images.resolve_abs(main_rel)
            if logger:
                logger(f"  upload main -> Shopify Files: {local.name}")
            main_url = upload_to_shopify_files(local)
    else:
        main_url = product_image_fallback

    # ZOOMY
    if len(cdn_zooms_current) == len(zooms_rel) and all(cdn_zooms_current):
        zoom_urls = list(cdn_zooms_current)
    else:
        zoom_urls = []
        for rel in zooms_rel:
            local = images.resolve_abs(rel)
            if logger:
                logger(f"  upload zoom -> Shopify Files: {local.name}")
            zoom_urls.append(upload_to_shopify_files(local))

    # MOCKUP
    if mockup_rel:
        if cdn_mockup_current:
            mockup_url = cdn_mockup_current
        else:
            local = images.resolve_abs(mockup_rel)
            if logger:
                logger(f"  upload mockup -> Shopify Files: {local.name}")
            mockup_url = upload_to_shopify_files(local)
    else:
        mockup_url = ""

    return main_url, zoom_urls, mockup_url


def ensure_cdn_urls_for_platform(
    item: storage.CykleItem,
    platform: str,                # "fb" | "ig"
    *,
    logger=None,
) -> tuple[str, list[str], str]:
    """Uploaduje/czyta z cache CDN URL-e dla danej platformy.

    Modyfikuje pola item.cdn_{platform}_main/zooms/mockup (caller zapisuje).
    Dla FB: jesli folder nie ma niczego - fallback do product_image_url.
    """
    if platform == "fb":
        main_rel = item.image_fb_main
        zooms_rel = list(item.image_fb_zooms or [])
        mockup_rel = item.image_fb_mockup
        fallback = item.product_image_url
        main_url, zoom_urls, mockup_url = _ensure_cdn_triplet(
            main_rel, zooms_rel, mockup_rel,
            item.cdn_fb_main, list(item.cdn_fb_zooms or []), item.cdn_fb_mockup,
            product_image_fallback=fallback, logger=logger,
        )
        item.cdn_fb_main = main_url
        item.cdn_fb_zooms = zoom_urls
        item.cdn_fb_mockup = mockup_url
        return main_url, zoom_urls, mockup_url

    # IG
    main_rel = item.image_ig_main
    zooms_rel = list(item.image_ig_zooms or [])
    mockup_rel = item.image_ig_mockup
    fallback = item.product_image_url
    main_url, zoom_urls, mockup_url = _ensure_cdn_triplet(
        main_rel, zooms_rel, mockup_rel,
        item.cdn_ig_main, list(item.cdn_ig_zooms or []), item.cdn_ig_mockup,
        product_image_fallback=fallback, logger=logger,
    )
    item.cdn_ig_main = main_url
    item.cdn_ig_zooms = zoom_urls
    item.cdn_ig_mockup = mockup_url
    return main_url, zoom_urls, mockup_url


# ---------------------------------------------------------------------------
# Publikacja Facebook
# ---------------------------------------------------------------------------

def publish_fb_photo(
    *,
    page_id: str,
    access_token: str,
    image_url: str,
    caption: str,
) -> str:
    """POST /{page_id}/photos - pojedyncze zdjecie. Zwraca id postu."""
    token = resolve_fb_page_access_token(page_id, access_token)
    url = f"{GRAPH_BASE}/{page_id}/photos"
    res = _post(url, {
        "url": image_url,
        "message": caption,
        "access_token": token,
    })
    post_id = str(res.get("post_id") or res.get("id") or "")
    if not post_id:
        raise MetaError(f"FB publish: brak id w odpowiedzi {res}")
    return post_id


def publish_fb_feed_text(
    *,
    page_id: str,
    access_token: str,
    message: str,
) -> str:
    """POST /{page_id}/feed — post ze samym tekstem (bez grafiki). Zwraca id postu."""
    token = resolve_fb_page_access_token(page_id, access_token)
    feed_url = f"{GRAPH_BASE}/{page_id}/feed"
    res = _post(feed_url, {
        "message": message,
        "access_token": token,
    })
    post_id = str(res.get("id") or "")
    if not post_id:
        raise MetaError(f"FB feed (tekst): brak id w odpowiedzi {res}")
    return post_id


def _fb_upload_unpublished(
    page_id: str,
    access_token: str,
    image_url: str,
) -> str:
    """Uploaduje 1 zdjecie do strony jako UNPUBLISHED - zwraca photo_id do uzycia
    w attached_media przy publikacji feed postu."""
    url = f"{GRAPH_BASE}/{page_id}/photos"
    res = _post(url, {
        "url": image_url,
        "published": "false",
        "access_token": access_token,
    })
    pid = str(res.get("id") or "")
    if not pid:
        raise MetaError(f"FB upload unpublished: brak id w odpowiedzi {res}")
    return pid


def publish_fb_multi(
    *,
    page_id: str,
    access_token: str,
    image_urls: list[str],
    caption: str,
) -> str:
    """Publikuje post FB z wieloma zdjeciami (attached_media).

    Flow:
    1. Dla kazdego URL: POST /photos published=false -> photo_id.
    2. POST /feed message=caption attached_media[0..N]={"media_fbid": photo_id}.

    Zwraca id postu.
    """
    if not image_urls:
        raise MetaError("FB multi-photo: brak zdjec do publikacji")

    if len(image_urls) == 1:
        return publish_fb_photo(
            page_id=page_id, access_token=access_token,
            image_url=image_urls[0], caption=caption,
        )

    token = resolve_fb_page_access_token(page_id, access_token)

    # 1) Upload wszystkich jako unpublished
    photo_ids: list[str] = []
    for url in image_urls:
        pid = _fb_upload_unpublished(page_id, token, url)
        photo_ids.append(pid)

    # 2) Feed post z attached_media
    feed_url = f"{GRAPH_BASE}/{page_id}/feed"
    payload: list[tuple[str, str]] = [
        ("message", caption),
        ("access_token", token),
    ]
    for i, pid in enumerate(photo_ids):
        payload.append((f"attached_media[{i}]", json.dumps({"media_fbid": pid})))
    res = _post(feed_url, payload)
    post_id = str(res.get("id") or "")
    if not post_id:
        raise MetaError(f"FB feed publish: brak id w odpowiedzi {res}")
    return post_id


# ---------------------------------------------------------------------------
# Publikacja Instagram (single + carousel)
# ---------------------------------------------------------------------------

def _ig_create_media_container(
    ig_user_id: str,
    access_token: str,
    *,
    image_url: str,
    caption: str | None = None,
    is_carousel_item: bool = False,
    media_type: str | None = None,
    children: list[str] | None = None,
) -> str:
    url = f"{GRAPH_BASE}/{ig_user_id}/media"
    payload: dict[str, str] = {"access_token": access_token}
    if media_type:
        payload["media_type"] = media_type
    if image_url:
        payload["image_url"] = image_url
    if caption is not None:
        payload["caption"] = caption
    if is_carousel_item:
        payload["is_carousel_item"] = "true"
    if children:
        payload["children"] = ",".join(children)
    res = _post(url, payload)
    cid = str(res.get("id") or "")
    if not cid:
        raise MetaError(f"IG create media container: brak id {res}")
    return cid


def _ig_wait_container_ready(ig_user_id: str, access_token: str, container_id: str,
                             *, max_wait: int = 30) -> None:
    """Po utworzeniu container trzeba poczekac az status_code=FINISHED."""
    url = f"{GRAPH_BASE}/{container_id}"
    for _ in range(max_wait):
        try:
            res = _get(url, {"fields": "status_code", "access_token": access_token})
        except MetaError:
            time.sleep(1)
            continue
        status = str(res.get("status_code") or "")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            raise MetaError(f"IG container {container_id} status={status}")
        time.sleep(1)
    raise MetaError(f"IG container {container_id}: timeout (status_code nie = FINISHED)")


def _ig_publish_container(ig_user_id: str, access_token: str, creation_id: str) -> str:
    url = f"{GRAPH_BASE}/{ig_user_id}/media_publish"
    res = _post(url, {"creation_id": creation_id, "access_token": access_token})
    mid = str(res.get("id") or "")
    if not mid:
        raise MetaError(f"IG publish: brak media id {res}")
    return mid


def publish_ig_single(
    *,
    ig_user_id: str,
    access_token: str,
    image_url: str,
    caption: str,
) -> str:
    cid = _ig_create_media_container(
        ig_user_id, access_token,
        image_url=image_url, caption=caption,
    )
    _ig_wait_container_ready(ig_user_id, access_token, cid)
    return _ig_publish_container(ig_user_id, access_token, cid)


def publish_ig_carousel(
    *,
    ig_user_id: str,
    access_token: str,
    image_urls: list[str],
    caption: str,
) -> str:
    if len(image_urls) < 2:
        raise MetaError(f"IG carousel wymaga min 2 obrazow, otrzymano {len(image_urls)}")
    if len(image_urls) > 10:
        image_urls = image_urls[:10]

    # 1) Child containers
    children: list[str] = []
    for url in image_urls:
        cid = _ig_create_media_container(
            ig_user_id, access_token,
            image_url=url, is_carousel_item=True,
        )
        children.append(cid)
    # 2) Carousel container
    parent = _ig_create_media_container(
        ig_user_id, access_token,
        image_url="", media_type="CAROUSEL",
        children=children, caption=caption,
    )
    _ig_wait_container_ready(ig_user_id, access_token, parent)
    return _ig_publish_container(ig_user_id, access_token, parent)


# ---------------------------------------------------------------------------
# Orchestrator - publikacja pojedynczej pozycji kolejki
# ---------------------------------------------------------------------------

def publish_item(
    item: storage.CykleItem,
    channels: list[str] | None = None,
    *,
    logger=None,
    skip_preflight: bool = False,
) -> dict[str, str]:
    """Publikuje pozycje na wybranych kanalach. Zwraca dict {channel: status_msg}.

    Per-kanal try/except: blad w jednym kanale nie blokuje pozostalych.
    Aktualizuje pola item.published_<channel> + item.media_ids + zapisuje w meta_state.
    Caller odpowiada za save_queue().

    Domyslnie uruchamia pre-flight check (credentiale, caption, obrazy) i nie
    wysyla do kanalow, ktore go nie przejdza. `skip_preflight=True` pomija check.
    """
    if channels is None:
        channels = list(item.channels_enabled) or list(_cp.CHANNEL_ORDER)

    if not skip_preflight:
        try:
            from . import preflight as _pf
        except ImportError:
            _pf = None  # type: ignore[assignment]
        if _pf is not None:
            skipped_channels: list[str] = []
            for ch in list(channels):
                rep = _pf.preflight_for_channel(item, ch)
                if not rep.ok:
                    msg = _pf.summarize_result(rep)
                    err_msg = f"error: preflight ({msg})"
                    setattr(item, f"published_{ch}", err_msg)
                    storage.append_meta_log({
                        "item_id": item.id, "channel": ch, "status": "error",
                        "message": msg, "phase": "preflight",
                    })
                    skipped_channels.append(ch)
            if skipped_channels:
                channels = [c for c in channels if c not in skipped_channels]
            if not channels:
                item.status = "error"
                return {ch: getattr(item, f"published_{ch}", "error") for ch in skipped_channels}

    # Przygotuj CDN URL-e (raz per platforma - FB i IG osobno)
    fb_main_url = ""
    fb_zoom_urls: list[str] = []
    fb_mockup_url = ""
    ig_main_url = ""
    ig_zoom_urls: list[str] = []
    ig_mockup_url = ""

    need_fb = any(ch.startswith("fb_") for ch in channels)
    need_ig = any(ch.startswith("ig_") for ch in channels)

    try:
        if need_fb:
            fb_main_url, fb_zoom_urls, fb_mockup_url = ensure_cdn_urls_for_platform(
                item, "fb", logger=logger,
            )
        if need_ig:
            ig_main_url, ig_zoom_urls, ig_mockup_url = ensure_cdn_urls_for_platform(
                item, "ig", logger=logger,
            )
    except Exception as e:  # noqa: BLE001
        err_msg = f"error: {e}"
        for ch in channels:
            setattr(item, f"published_{ch}", err_msg)
            storage.append_meta_log({
                "item_id": item.id, "channel": ch, "status": "error",
                "message": str(e), "phase": "cdn_prep",
            })
        return {ch: err_msg for ch in channels}

    fb_all_urls = [u for u in (
        [fb_main_url] + list(fb_zoom_urls) + ([fb_mockup_url] if fb_mockup_url else [])
    ) if u]
    ig_carousel_urls = [u for u in (
        [ig_main_url] + list(ig_zoom_urls) + ([ig_mockup_url] if ig_mockup_url else [])
    ) if u]
    creds_all = storage.load_meta_credentials()

    results: dict[str, str] = {}
    for ch_code in channels:
        ch = _cp.get(ch_code)
        if ch is None:
            results[ch_code] = "error: nieznany kanal"
            continue
        # Skip jesli juz opublikowany z sukcesem
        current = getattr(item, f"published_{ch_code}", "")
        if current.startswith("done@"):
            results[ch_code] = current
            continue

        ok, msg = check_credentials(ch_code)
        if not ok:
            err_msg = f"error: {msg}"
            setattr(item, f"published_{ch_code}", err_msg)
            storage.append_meta_log({
                "item_id": item.id, "channel": ch_code, "status": "error",
                "message": msg, "phase": "credentials",
            })
            results[ch_code] = err_msg
            continue

        creds = creds_all.get(ch_code) or {}
        # Wybor captiona
        caption = _caption_for_channel(item, ch_code)

        try:
            if ch.platform == "fb":
                if len(fb_all_urls) >= 2:
                    post_id = publish_fb_multi(
                        page_id=creds["page_id"],
                        access_token=creds["access_token"],
                        image_urls=fb_all_urls,
                        caption=caption,
                    )
                elif fb_all_urls:
                    post_id = publish_fb_photo(
                        page_id=creds["page_id"],
                        access_token=creds["access_token"],
                        image_url=fb_all_urls[0],
                        caption=caption,
                    )
                else:
                    raise MetaError("FB: brak obrazow do publikacji")
                item.media_ids[ch_code] = post_id
            else:
                if len(ig_carousel_urls) >= 2:
                    media_id = publish_ig_carousel(
                        ig_user_id=creds["ig_user_id"],
                        access_token=creds["access_token"],
                        image_urls=ig_carousel_urls,
                        caption=caption,
                    )
                elif ig_carousel_urls:
                    media_id = publish_ig_single(
                        ig_user_id=creds["ig_user_id"],
                        access_token=creds["access_token"],
                        image_url=ig_carousel_urls[0],
                        caption=caption,
                    )
                else:
                    raise MetaError("IG: brak obrazow do publikacji")
                item.media_ids[ch_code] = media_id
            from datetime import datetime as _dt
            ts = _dt.now().isoformat(timespec="seconds")
            msg = f"done@{ts}"
            setattr(item, f"published_{ch_code}", msg)
            storage.append_meta_log({
                "item_id": item.id, "channel": ch_code, "status": "done",
                "media_id": item.media_ids[ch_code], "phase": "publish",
            })
            results[ch_code] = msg
        except Exception as e:  # noqa: BLE001
            err_msg = f"error: {e}"
            setattr(item, f"published_{ch_code}", err_msg)
            storage.append_meta_log({
                "item_id": item.id, "channel": ch_code, "status": "error",
                "message": str(e), "phase": "publish",
            })
            results[ch_code] = err_msg

    # Update status item:
    succeeded = sum(1 for v in results.values() if v.startswith("done@"))
    failed = sum(1 for v in results.values() if v.startswith("error"))
    if succeeded == len(channels) and failed == 0:
        item.status = "done"
    elif succeeded > 0 and failed > 0:
        item.status = "error"  # czesciowy sukces - uzytkownik decyduje co dalej
    elif failed == len(channels):
        item.status = "error"
    return results


def _caption_for_channel(item: storage.CykleItem, ch_code: str) -> str:
    """Wybiera caption dla danego kanalu (nadpisanie edycji > caption_platform > caption_lang)."""
    # Priorytet: caption_{platform}_{lang} > caption_{lang}
    lang = "pl" if ch_code.endswith("_pl") else "en"
    platform = "fb" if ch_code.startswith("fb") else "ig"
    specific = getattr(item, f"caption_{platform}_{lang}", "") or ""
    if specific:
        return _append_hashtags_for_ig(specific, item, lang) if platform == "ig" else specific
    fallback = item.caption_pl if lang == "pl" else item.caption_en
    return _append_hashtags_for_ig(fallback, item, lang) if platform == "ig" else fallback


def _append_hashtags_for_ig(caption: str, item: storage.CykleItem, lang: str) -> str:
    """Jesli caption nie zawiera juz bloku hashtagow na koncu - dokleja z item.hashtags_{lang}."""
    tags = item.hashtags_pl if lang == "pl" else item.hashtags_en
    if not tags:
        return caption
    if "#" in caption[-500:]:
        return caption
    block = " ".join(tags)
    return f"{caption.rstrip()}\n\n{block}"


# ---------------------------------------------------------------------------
# Publikacja zbiorcza (dla publisher daemon w launcherze)
# ---------------------------------------------------------------------------

def publish_due_items(*, logger=None) -> list[tuple[str, dict[str, str]]]:
    """Publikuje pozycje ktorych scheduled_at <= now i ktore sa gotowe (content + obrazy).

    Zwraca liste (item_id, results_dict). NIE publikuje jesli auto_publish=False
    w config.json (bezpieczny default).
    """
    from datetime import datetime as _dt

    cfg = storage.load_config()
    if not cfg.get("auto_publish"):
        return []

    items = storage.load_queue()
    now = _dt.now()
    out: list[tuple[str, dict[str, str]]] = []
    dirty = False

    for it in items:
        if it.status in ("done", "skipped"):
            continue
        if not it.scheduled_at:
            continue
        try:
            sched = _dt.fromisoformat(it.scheduled_at)
        except ValueError:
            continue
        if sched > now:
            continue
        # Potrzebujemy conajmniej caption w obu jezykach
        if not ((it.caption_pl or it.caption_fb_pl) and (it.caption_en or it.caption_fb_en)):
            continue
        # Potrzebujemy conajmniej main image (product CDN lub lokalne)
        has_any_image = (
            it.product_image_url
            or it.image_main
            or it.image_fb_main or it.image_ig_main
        )
        if not has_any_image:
            continue

        it.status = "publishing"
        if logger:
            logger(f"Publikuje: {it.artist} - {it.painting_title_pl} ({it.id})")
        results = publish_item(it, logger=logger)
        out.append((it.id, results))
        dirty = True

    if dirty:
        storage.save_queue(items)
    return out

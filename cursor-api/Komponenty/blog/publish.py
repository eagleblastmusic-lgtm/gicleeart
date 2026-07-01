"""Wspolna logika publikacji posta na Shopify (PL + tlumaczenia)."""

from __future__ import annotations

from typing import Any

from . import shopify_blog, storage


def publish_parsed_article(
    parsed: dict[str, Any],
    *,
    image_url: str = "",
    author: str = "GicleeArt",
    selected_locales: list[str] | None = None,
    topic_id: str = "",
) -> dict[str, Any]:
    """Publikuje zwalidowany slownik `parsed` (jak z JSON LLM lub html_import).

    Zwraca: {article_id, article, blog_id, admin_url, translation_errors, selected_locales}.
    """
    langs = parsed.get("languages") or {}
    pl = langs.get("pl") or {}
    if not (pl.get("title") and pl.get("body_html")):
        raise ValueError("Wersja PL (bazowa) jest wymagana - brak title/body_html.")

    if selected_locales is None:
        selected_locales = [
            code for code in langs
            if code != "pl" and (langs.get(code) or {}).get("title")
        ]

    shop, token = shopify_blog.load_session()
    blogs = shopify_blog.list_blogs(shop, token)
    if not blogs:
        raise shopify_blog.ShopifyError(
            "Brak blogow w sklepie Shopify. Utworz bloga w Shopify Admin -> Sklep internetowy -> Blog."
        )
    blog_id = int(blogs[0].get("id") or 0)

    tags = pl.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    article = shopify_blog.create_article(
        shop, token, blog_id,
        title=str(pl.get("title") or ""),
        body_html=str(pl.get("body_html") or ""),
        summary_html=str(pl.get("summary_html") or ""),
        tags=list(tags),
        author=author,
        image_src=image_url,
        image_alt=str(pl.get("title") or ""),
        seo_title=str(pl.get("seo_title") or ""),
        seo_description=str(pl.get("seo_description") or ""),
        published=True,
    )
    article_id = int(article.get("id") or 0)
    if not article_id:
        raise shopify_blog.ShopifyError(f"Shopify nie zwrocil id artykulu: {article}")

    translation_errors: list[str] = []
    for locale in selected_locales:
        if locale == "pl":
            continue
        loc = langs.get(locale) or {}
        if not loc.get("title"):
            continue
        try:
            shopify_blog.register_article_translations(
                shop, token,
                article_id=article_id,
                locale=locale,
                title=str(loc.get("title") or ""),
                body_html=str(loc.get("body_html") or ""),
                summary_html=str(loc.get("summary_html") or ""),
                seo_title=str(loc.get("seo_title") or ""),
                seo_description=str(loc.get("seo_description") or ""),
            )
        except shopify_blog.ShopifyError as e:
            translation_errors.append(f"{locale}: {e}")

    if topic_id:
        storage.mark_topic_used(topic_id, True)

    try:
        all_articles = shopify_blog.list_all_articles(shop, token)
        storage.save_articles_cache(all_articles)
    except shopify_blog.ShopifyError:
        pass

    admin_url = shopify_blog.article_admin_url(shop, blog_id, article_id)
    return {
        "article_id": article_id,
        "article": article,
        "blog_id": blog_id,
        "admin_url": admin_url,
        "translation_errors": translation_errors,
        "selected_locales": selected_locales,
    }

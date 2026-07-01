# Komponent: blog



**Cel:** Generowanie i publikacja postów na blog Shopify (7 języków) — tematy, treść, podgląd, import HTML.



| Plik | Rola |

|------|------|

| `view.py` | Inline: 5 kafelków |

| `shopify_blog.py` | REST blogs/articles |

| `generator_tresci.py`, `generator_tematow.py` | Prompty LLM |

| `html_import.py` | Parser pliku HTML podglądu → struktura posta |

| `import_html.py` | Dialog: wybierz HTML → publikuj |

| `publish.py` | Wspólna wysyłka na Shopify (PL + tłumaczenia) |



Tryb: `inline`. SHOP_KNOWLEDGE: §9a



→ [`README.md`](README.md)


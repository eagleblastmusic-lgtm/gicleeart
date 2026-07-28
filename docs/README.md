# GicleeArt — dokumentacja projektu (START TUTAJ)



> **Wklejka na start rozmowy:** [`MATKA.md`](../MATKA.md) (korzeń `pusty/`)  

> Ten plik = hub integracji: scenariusze, ID, „problem → gdzie”. Potem hub **warstwy** → **jeden** plik modułowy.



---



## Polityka dokumentacji



| Typ | Pliki | AI: czytaj | AI: pisz po zmianie |

|-----|-------|------------|---------------------|

| **Prawda (modułowa)** | `docs/motyw/`, `cursor-api/docs/komponenty/`, `giclee_app/docs/` | Tak | **Tak** |

| **Integracja** | `docs/zaleznosci.md`, ten README | Tak | Tak (scenariusze, problem→gdzie) |

| **Skrót startowy** | `MATKA.md` | Tak | Tylko ID/trasy/linki |

| **Konta zewnętrzne** | `USLUGI.md` | Tak | Tak |

| **Archiwum** | `THEME_KNOWLEDGE.md`, `SHOP_KNOWLEDGE.md` | Sekcja po sekcji | **Nie** |



Jeden fakt w jednym pliku modułowym. Nie duplikuj treści między `MATKA` a tym README.



---



## Trzy warstwy



| Warstwa | Folder kodu | Hub dokumentacji |

|---------|-------------|------------------|

| **Sklep (motyw)** | korzeń `pusty/` | [`motyw/README.md`](motyw/README.md) |

| **Mechanika API** | `cursor-api/` | [`../cursor-api/docs/README.md`](../cursor-api/docs/README.md) |

| **GicleeApp** | `cursor-api/giclee_app/` | [`../cursor-api/giclee_app/docs/README.md`](../cursor-api/giclee_app/docs/README.md) |



**Mapa zależności:** [`zaleznosci.md`](zaleznosci.md)



---



## Problem → gdzie



| Problem | Plik |

|---------|------|

| Brak maila po zakupie (upload klienta) | [`zaleznosci.md`](zaleznosci.md) + [`../cursor-api/docs/worker/mockup-order-worker.md`](../cursor-api/docs/worker/mockup-order-worker.md) |

| Mockup / layout / upload na stronie | [`motyw/troubleshooting.md`](motyw/troubleshooting.md) |

| OAuth, R2, Worker, Python ogólnie | [`../cursor-api/docs/troubleshooting.md`](../cursor-api/docs/troubleshooting.md) |

| OVH / Cloudflare / Resend / plany | [`USLUGI.md`](../USLUGI.md) |

| Brak kafelka GicleeApp | [`../cursor-api/giclee_app/docs/troubleshooting.md`](../cursor-api/giclee_app/docs/troubleshooting.md) |

| Zoom HD pusty | [`motyw/produkt-i-zoom.md`](motyw/produkt-i-zoom.md) |

| PDP v3 / scroll-over: pusty scroll, wjazd, prześwit | [`motyw/pdp-v3-pusty-scroll.md`](motyw/pdp-v3-pusty-scroll.md) (wzór uniwersalny) |
| Film lub klatki sterowane scrollem | [`Film-scroll.md`](Film-scroll.md) (źródło prawdy) + [`Film-scroll-AI-Integration-Guide.md`](Film-scroll-AI-Integration-Guide.md) (kanoniczna instrukcja rozszerzania) |

| Księgowość, DNR, KPiR, faktury | [`../cursor-api/docs/komponenty/finanse.md`](../cursor-api/docs/komponenty/finanse.md) |

| Limity: Resend 403 / 401 | [`../cursor-api/docs/komponenty/limity.md`](../cursor-api/docs/komponenty/limity.md) + `USLUGI.md` |

| Poczta: IMAP login failed | [`../cursor-api/docs/komponenty/poczta.md`](../cursor-api/docs/komponenty/poczta.md) |

| Meta tokeny wygasłe | [`../cursor-api/docs/komponenty/meta-tokeny.md`](../cursor-api/docs/komponenty/meta-tokeny.md) |



---



## Identyfikatory



| Element | Wartość |

|---------|---------|

| Domena | `gicleeart.eu` |

| Shopify CLI | `giclee-art-3.myshopify.com` |

| OAuth (kanoniczny shop) | `19v3bj-n0.myshopify.com` |

| Motyw live | `#197314249052` („Kopia Giclee Art Br”) |

| Worker upload | `giclee-mockup-orders.eagleblastmusic.workers.dev` |

| R2 bucket | `giclee-zoom` |

| R2 public | `https://pub-c9a1bd43074c459d98d4cc0292b1210e.r2.dev` |

| Cart property | `_Upload ID` |

| Zoom metafield | `custom.zoom_manifest` |

| Gmail IMAP (Poczta) | `.env`: `GMAIL_IMAP_USER`, `GMAIL_IMAP_APP_PASSWORD` |

| Resend | Limity: `.env` Full access · Worker: send-only OK |



---



## Scenariusze end-to-end



### Klient wgrał zdjęcie, kupił — nie ma maila



1. [`zaleznosci.md`](zaleznosci.md) → *Brak maila po zamówieniu*

2. [`../cursor-api/docs/worker/mockup-order-worker.md`](../cursor-api/docs/worker/mockup-order-worker.md)

3. Shopify Admin → linia zamówienia → `_Upload ID`



### Mockup na stronie wygląda źle / nie uploaduje



1. [`motyw/mockup-wlasna-fotografia.md`](motyw/mockup-wlasna-fotografia.md)

2. [`motyw/troubleshooting.md`](motyw/troubleshooting.md)



### Księgowość — faktura, DNR, KPiR



1. GicleeApp → **Księgowość** (hub `finanse`)

2. [`../cursor-api/docs/komponenty/finanse.md`](../cursor-api/docs/komponenty/finanse.md)

3. Moduły: [`dokumentysprzedazy.md`](../cursor-api/docs/komponenty/dokumentysprzedazy.md) · [`dnr.md`](../cursor-api/docs/komponenty/dnr.md) · [`kpir.md`](../cursor-api/docs/komponenty/kpir.md)



### Chcę dodać reprodukcję klasyka do katalogu



1. [`../cursor-api/giclee_app/docs/README.md`](../cursor-api/giclee_app/docs/README.md)

2. [`../cursor-api/docs/komponenty/dodajobraz.md`](../cursor-api/docs/komponenty/dodajobraz.md)



### Zoom HD na karcie produktu nie działa



1. [`motyw/produkt-i-zoom.md`](motyw/produkt-i-zoom.md)

2. [`../cursor-api/docs/komponenty/dodajobraz.md`](../cursor-api/docs/komponenty/dodajobraz.md)



### Limity usług / Meta tokeny / Poczta



- Limity: [`../cursor-api/docs/komponenty/limity.md`](../cursor-api/docs/komponenty/limity.md) + [`USLUGI.md`](../USLUGI.md)

- Poczta: [`../cursor-api/docs/komponenty/poczta.md`](../cursor-api/docs/komponenty/poczta.md)

- Meta: [`../cursor-api/docs/komponenty/meta-tokeny.md`](../cursor-api/docs/komponenty/meta-tokeny.md)



---



## Archiwum (tylko czytanie)



| Plik | Użycie |

|------|--------|

| [`THEME_KNOWLEDGE.md`](../THEME_KNOWLEDGE.md) | Historia motywu Horizon, struktura — jeśli brak w `docs/motyw/` |

| [`../cursor-api/SHOP_KNOWLEDGE.md`](../cursor-api/SHOP_KNOWLEDGE.md) | Rynki, tagi, prompty LLM — jeśli brak w `docs/komponenty/` |

| [`../cursor-api/CHECKLIST_SETUP.md`](../cursor-api/CHECKLIST_SETUP.md) | Pierwsza konfiguracja środowiska |



---



## Drzewo



```

docs/README.md          ← ten plik

docs/zaleznosci.md

docs/motyw/

cursor-api/docs/komponenty/

cursor-api/giclee_app/docs/

MATKA.md                ← wklejka (linki, nie duplikat tabel)

```



---



## Ostatnia aktualizacja hubu



2026-07-27 — Film-scroll: centralny scheduler, profile ruchu, MP4/WebP,
60 FPS, alfa oraz kanoniczna instrukcja integracji dla kolejnych AI.


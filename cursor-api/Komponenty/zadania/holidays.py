"""Kalendarz swiat i wydarzen marketingowych per rynek.

Wydarzenia pogrupowane w 3 kategorie:
- 'global' - wazne dla WSZYSTKICH rynkow (Boze Narodzenie, BF, Nowy Rok, Walentynki, Dzien Matki ...)
- 'pl' - tylko rynek PL (Dzien Babci, Dzien Kobiet, Mikolajki, Boze Cialo)
- 'market-specific' - konkretne rynki (Dzien Ojca - DE inny niz PL, Sinterklaas NL, Ferragosto IT, itd.)

Daty sa ruchome (Wielkanoc) - tu wpisuje konkrente lata recznie zeby nie robic pelnego algo.
Wsparcie dla lat 2026-2028. Po tym okresie trzeba dopisac.

Kazde wydarzenie ma:
- date: YYYY-MM-DD
- name (pl): nazwa do wyswietlenia
- markets: ktore rynki w {pl, eu, fr, de, es, nl, it}
- marketing_value: 'prezent' | 'dekoracja' | 'sezon' | 'inspiracja' - jak wykorzystac w contencie
- suggested_topic_pl / _en: gotowy temat do wpisania w Generator tresci
- lead_time_days: ile dni WCZESNIEJ trzeba zaczac kampanie
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any


@dataclass(frozen=True)
class HolidayEvent:
    date: str            # YYYY-MM-DD
    name: str            # po polsku (display)
    markets: tuple[str, ...]
    marketing_value: str  # 'prezent' | 'dekoracja' | 'sezon' | 'inspiracja'
    suggested_topic_pl: str
    suggested_topic_en: str
    lead_time_days: int = 14


ALL_MARKETS = ("pl", "eu", "fr", "de", "es", "nl", "it")


_RAW: list[tuple[str, str, tuple[str, ...], str, str, str, int]] = [
    # Nowy Rok
    ("2026-01-01", "Nowy Rok", ALL_MARKETS, "sezon",
     "Nowe wnetrze na Nowy Rok - jak zaaranzowac przestrzen na swiezy start",
     "New Year new walls - how to refresh your space for 2026", 10),
    ("2027-01-01", "Nowy Rok", ALL_MARKETS, "sezon",
     "Nowe wnetrze na Nowy Rok - jak zaaranzowac przestrzen na swiezy start",
     "New Year new walls - how to refresh your space for 2027", 10),

    # Dzien Babci / Dziadka (PL)
    ("2026-01-21", "Dzien Babci (PL)", ("pl",), "prezent",
     "Prezent dla Babci - spersonalizowane zdjecie wnuczek na plotnie",
     "", 14),
    ("2026-01-22", "Dzien Dziadka (PL)", ("pl",), "prezent",
     "Prezent dla Dziadka - sentymentalne zdjecie rodzinne na plotnie",
     "", 14),
    ("2027-01-21", "Dzien Babci (PL)", ("pl",), "prezent",
     "Prezent dla Babci - spersonalizowane zdjecie wnuczek na plotnie",
     "", 14),
    ("2027-01-22", "Dzien Dziadka (PL)", ("pl",), "prezent",
     "Prezent dla Dziadka - sentymentalne zdjecie rodzinne na plotnie",
     "", 14),

    # Walentynki
    ("2026-02-14", "Walentynki", ALL_MARKETS, "prezent",
     "Walentynki - Twoje zdjecie we dwoje jako trwala pamiatka milosci (wydruk giclee)",
     "Valentine's Day - your photo together as a lasting canvas memory (giclée print)", 21),
    ("2027-02-14", "Walentynki", ALL_MARKETS, "prezent",
     "Walentynki - obrazy i reprodukcje o milosci (Klimt 'Pocalunek', Chagall, romantycy)",
     "Valentine's Day - art about love (Klimt 'The Kiss', Chagall, Romantics)", 21),

    # Dzien Kobiet
    ("2026-03-08", "Dzien Kobiet", ("pl", "it", "es"), "prezent",
     "Dzien Kobiet - reprodukcje kobiecosci: Klimt, Mucha, portret jako prezent",
     "International Women's Day - celebrating feminine art (Klimt, Mucha, portraits)", 14),
    ("2027-03-08", "Dzien Kobiet", ("pl", "it", "es"), "prezent",
     "Dzien Kobiet - reprodukcje kobiecosci: Klimt, Mucha, portret jako prezent",
     "International Women's Day - celebrating feminine art", 14),

    # Wielkanoc - ruchome (PL, CE, DE)
    ("2026-04-05", "Wielkanoc", ALL_MARKETS, "sezon",
     "Wielkanocne wnetrza - pastelowe obrazy i reprodukcje na wiosenny reset domu",
     "Easter interiors - pastel art and reproductions for a spring home refresh", 14),
    ("2027-03-28", "Wielkanoc", ALL_MARKETS, "sezon",
     "Wielkanocne wnetrza - pastelowe obrazy i reprodukcje na wiosenny reset domu",
     "Easter interiors - pastel art for a spring home refresh", 14),

    # Dzien Matki - PL (26.05), DE/FR (drugi niedziel maja), ES (pierwszy niedziel maja), IT (druga niedziela maja)
    ("2026-05-03", "Dia de la Madre (ES)", ("es",), "prezent",
     "", "Dia de la Madre - regalo personalizado en lienzo giclée", 21),
    ("2026-05-10", "Mother's Day (EU/DE/FR/NL/IT)", ("eu", "de", "fr", "nl", "it"), "prezent",
     "", "Mother's Day - a personal photo canvas for the most important person", 21),
    ("2026-05-26", "Dzien Matki (PL)", ("pl",), "prezent",
     "Dzien Matki - zdjecie rodzinne Mamy na plotnie (albo portret Klimt/Mucha)",
     "", 21),
    ("2027-05-02", "Dia de la Madre (ES)", ("es",), "prezent",
     "", "Dia de la Madre - regalo personalizado", 21),
    ("2027-05-09", "Mother's Day (EU/DE/FR/NL/IT)", ("eu", "de", "fr", "nl", "it"), "prezent",
     "", "Mother's Day - personal photo canvas", 21),
    ("2027-05-26", "Dzien Matki (PL)", ("pl",), "prezent",
     "Dzien Matki - zdjecie rodzinne Mamy na plotnie",
     "", 21),

    # Dzien Ojca
    ("2026-06-19", "Dzien Ojca (DE)", ("de",), "prezent", "",
     "Vatertag - Fotoleinwand als persönliches Geschenk", 14),   # DE: Wniebowstapienie (ruchome)
    ("2026-06-21", "Dzien Ojca (FR, Father's Day EU)", ("fr", "eu"), "prezent", "",
     "Father's Day - a memorable photo canvas for Dad", 14),
    ("2026-06-23", "Dzien Ojca (PL)", ("pl",), "prezent",
     "Dzien Ojca - zdjecie z Ojcem na plotnie (sport, podroz, najlepsza wspomnienia)",
     "", 14),

    # Lato / wakacje - inspiracja
    ("2026-07-01", "Poczatek lata / wakacje", ALL_MARKETS, "sezon",
     "Wakacyjne zdjecia na plotnie - jak wybrac najlepszy kadr z wyjazdu",
     "Summer memories on canvas - choosing the best holiday shot for print", 0),
    ("2026-08-15", "Ferragosto (IT)", ("it",), "sezon",
     "", "", 0),

    # Powrot do szkoly / jesien
    ("2026-09-01", "Pierwszy dzien szkoly / jesien", ALL_MARKETS, "sezon",
     "Jesienne wnetrze - ciemne ramy, cieple kolory, powroty do domu po lecie",
     "Autumn interiors - dark frames, warm palettes, cozy home after summer", 0),

    # Halloween
    ("2026-10-31", "Halloween", ("eu", "de", "fr", "nl", "it"), "sezon",
     "", "Halloween gallery wall - dark, dramatic art from the masters (Caravaggio, Bosch)", 21),

    # Wszystkich Swietych / Zaduszki (PL, IT, ES, FR)
    ("2026-11-01", "Wszystkich Swietych", ("pl", "it", "es", "fr"), "sezon",
     "", "", 0),

    # Sinterklaas NL
    ("2026-12-05", "Sinterklaas (NL)", ("nl",), "prezent",
     "", "Sinterklaas - personalized photo canvas as a surprise gift", 28),

    # Mikolajki (PL)
    ("2026-12-06", "Mikolajki (PL)", ("pl",), "prezent",
     "Mikolajki - maly duzy prezent - zdjecie najwazniejszej osoby na plotnie",
     "", 21),

    # Black Friday / Cyber Monday
    ("2026-11-27", "Black Friday", ALL_MARKETS, "sezon",
     "Black Friday w GicleeArt - sztuka w promocyjnej cenie; jak wybrac najlepsze obrazy na swoje wnetrze",
     "Black Friday at GicleeArt - masterpieces at special prices; how to pick the best for your home", 14),
    ("2026-11-30", "Cyber Monday", ALL_MARKETS, "sezon",
     "Cyber Monday - ostatni dzien na zakup prezentow na plotnie przed Boze Narodzenie",
     "Cyber Monday - last chance to order personal canvas gifts before Christmas", 7),

    # Boze Narodzenie / Christmas
    ("2026-12-24", "Wigilia Boze Narodzenie", ALL_MARKETS, "prezent",
     "Boze Narodzenie - jaki obraz wisi nad kominkiem u Ciebie?",
     "Christmas - what painting hangs above your fireplace?", 45),
    ("2026-12-25", "Boze Narodzenie", ALL_MARKETS, "sezon",
     "Swiateczne wnetrze - klasyczne reprodukcje jako akcent nad choinka",
     "Christmas interiors - classic reproductions as the fireplace accent", 45),

    # Sylwester
    ("2026-12-31", "Sylwester", ALL_MARKETS, "sezon",
     "Podsumowanie roku w zdjeciach - wybierz 1 kadr roku i zawies na scianie",
     "Year in photos - pick the one shot of 2026 and put it on your wall", 0),
]


EVENTS: list[HolidayEvent] = [
    HolidayEvent(
        date=d, name=n, markets=m, marketing_value=v,
        suggested_topic_pl=pl, suggested_topic_en=en,
        lead_time_days=lt,
    )
    for d, n, m, v, pl, en, lt in _RAW
]


def events_between(start: date, end: date, *, markets: tuple[str, ...] | None = None) -> list[HolidayEvent]:
    """Zwraca wydarzenia w zakresie [start, end] (inclusive) ewentualnie dla konkretnych rynkow."""
    out: list[HolidayEvent] = []
    for ev in EVENTS:
        try:
            d = date.fromisoformat(ev.date)
        except ValueError:
            continue
        if d < start or d > end:
            continue
        if markets is not None:
            if not any(m in ev.markets for m in markets):
                continue
        out.append(ev)
    out.sort(key=lambda e: e.date)
    return out


def events_upcoming(days_ahead: int = 60, *, markets: tuple[str, ...] | None = None) -> list[HolidayEvent]:
    """Wydarzenia w ciagu najblizszych `days_ahead` dni (od dzisiaj)."""
    today = date.today()
    end = today + timedelta(days=days_ahead)
    return events_between(today, end, markets=markets)


def format_events_for_prompt(events: list[HolidayEvent]) -> str:
    """Formatuje liste wydarzen do wklejenia do prompta LLM."""
    if not events:
        return "(brak wydarzen w zakresie)"
    lines: list[str] = []
    for ev in events:
        topic = ev.suggested_topic_pl or ev.suggested_topic_en or "(brak propozycji)"
        markets_str = ",".join(ev.markets) if ev.markets else "all"
        lines.append(
            f"- {ev.date} | {ev.name} | rynki: {markets_str} | "
            f"lead: {ev.lead_time_days}d | value: {ev.marketing_value} | temat: {topic}"
        )
    return "\n".join(lines)


def serialize(events: list[HolidayEvent]) -> list[dict[str, Any]]:
    """JSON-serializable forma (do cache'a sygnalow)."""
    return [
        {
            "date": e.date,
            "name": e.name,
            "markets": list(e.markets),
            "marketing_value": e.marketing_value,
            "suggested_topic_pl": e.suggested_topic_pl,
            "suggested_topic_en": e.suggested_topic_en,
            "lead_time_days": e.lead_time_days,
        }
        for e in events
    ]

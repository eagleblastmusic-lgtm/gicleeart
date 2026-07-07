"""App profiles for Performance Agent."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

from tools.performance_agent.models import ScenarioDefinition

_REPO_ROOT = Path(__file__).resolve().parents[2]

STUDIO_ENV: dict[str, str] = {
    "GICLEE_STUDIO_PERF": "1",
    "GICLEE_STUDIO_IDLE_PREWARM": "0",
}


@dataclass(frozen=True)
class LaunchConfig:
    command: tuple[str, ...]
    working_dir: Path
    env: dict[str, str]
    env_unset: tuple[str, ...] = ("GICLEE_ASSET_LAB_AUTO_FULL_CARDS",)

    @classmethod
    def studio_preview(cls, repo_root: Path | None = None) -> LaunchConfig:
        root = repo_root or _REPO_ROOT
        return cls(
            command=(sys.executable, "-m", "giclee_app.studio_preview"),
            working_dir=root,
            env=dict(STUDIO_ENV),
        )


MANUAL_SCENARIOS: tuple[ScenarioDefinition, ...] = (
    ScenarioDefinition(
        id="dashboard_cold",
        display_title="Dashboard — start aplikacji",
        click_path=(
            "Nic nie klikaj.",
            "To scenariusz obserwacyjny po starcie Studio.",
            "Poczekaj, aż główny ekran aplikacji będzie gotowy.",
        ),
        goal="Sprawdzenie pierwszego widoku po uruchomieniu Studio.",
        observe=(
            "Czy ekran startowy pokazuje się płynnie?",
            "Czy widać puste placeholdery albo skeletony?",
            "Czy elementy doskakują po kolei?",
            "Czy aplikacja wygląda na zamrożoną?",
        ),
        success_hint=(
            "Naciśnij Enter, gdy dashboard jest widoczny i przez 2–3 sekundy nic już się wyraźnie nie zmienia. "
            "Jeśli dashboard był już gotowy zanim rozpocząłeś scenariusz, oceń to, co widziałeś zaraz po starcie aplikacji."
        ),
        expected_event_patterns=("studio.dashboard",),
    ),
    ScenarioDefinition(
        id="hub_theme",
        display_title="Hub motywu — kafelki Strony / Motywu",
        click_path=(
            "Z dashboardu przejdź do obszaru Strona / Motyw.",
            "Otwórz hub z kafelkami komponentów motywu.",
            "Jeśli jesteś już w hubie, odśwież ocenę po wejściu / powrocie do tego widoku.",
        ),
        goal="Sprawdzenie, czy kafelki motywu pojawiają się płynnie.",
        observe=(
            "Czy pierwsze kafelki pojawiają się szybko?",
            "Czy reszta kafelków doskakuje partiami?",
            "Czy układ skacze?",
        ),
        success_hint="Naciśnij Enter, gdy kafelki hubu są widoczne i przestaną się wyraźnie dorysowywać.",
        expected_event_patterns=("studio.hub", "studio.show_view"),
    ),
    ScenarioDefinition(
        id="hub_products",
        display_title="Katalog / Produkty — wejście do widoku",
        click_path=(
            "Przejdź do Katalogu albo obszaru Produkty.",
            "Poczekaj na listy / karty / dane katalogowe.",
            "Nie klikaj dalej przez 2–3 sekundy.",
        ),
        goal="Sprawdzenie wejścia do Katalogu / Produktów.",
        observe=(
            "Czy widok pojawia się od razu?",
            "Czy lista buduje się partiami?",
            "Czy jest freeze albo zauważalne opóźnienie?",
        ),
        success_hint="Naciśnij Enter, gdy widok Katalogu / Produktów jest widoczny i stabilny.",
        expected_event_patterns=("studio.katalog", "studio.hub"),
    ),
    ScenarioDefinition(
        id="gf_open",
        display_title="GICLÉE FRAME — pierwsze otwarcie",
        click_path=(
            "Wróć do hubu motywu / komponentów.",
            'Znajdź kafelek „GICLÉE FRAME".',
            'Kliknij „GICLÉE FRAME".',
            "Poczekaj, aż widok się odsłoni.",
            "Odczekaj jeszcze 2–3 sekundy.",
        ),
        goal="Sprawdzenie pierwszego wejścia do edytora GICLÉE FRAME.",
        observe=(
            "Czy overlay trwa za długo?",
            "Czy po odsłonięciu elementy jeszcze doskakują?",
            "Czy prawa kolumna albo lista sekcji zmienia układ?",
        ),
        success_hint="Naciśnij Enter dopiero wtedy, gdy GICLÉE FRAME jest widoczny i stabilny.",
        expected_event_patterns=("studio.gicleeframe",),
    ),
    ScenarioDefinition(
        id="section_click_normal",
        display_title="GICLÉE FRAME — normalne klikanie sekcji",
        click_path=(
            "Zostań w widoku GICLÉE FRAME.",
            "Kliknij 5–10 różnych sekcji na liście po lewej.",
            "Klikaj normalnym tempem, mniej więcej co pół sekundy.",
            "Po ostatnim kliknięciu poczekaj 2 sekundy.",
        ),
        goal="Sprawdzenie reakcji edytora przy zwykłym klikaniu sekcji.",
        observe=(
            "Czy klik od razu zaznacza sekcję?",
            "Czy prawy panel reaguje natychmiast?",
            "Czy pojawia się skeleton albo pusty stan?",
            "Czy panel zmienia wysokość / układ?",
        ),
        success_hint="Naciśnij Enter po kilku kliknięciach, gdy ostatni wybrany panel jest stabilny.",
        expected_event_patterns=(
            "studio.gicleeframe.selection",
            "studio.gicleeframe.editor",
        ),
    ),
    ScenarioDefinition(
        id="section_click_fast",
        display_title="GICLÉE FRAME — szybkie klikanie sekcji",
        click_path=(
            "Zostań w GICLÉE FRAME.",
            "Kliknij szybko kilka / kilkanaście sekcji na liście.",
            "Nie czekaj aż każdy panel się dorysuje.",
            "Po serii kliknięć poczekaj 2–3 sekundy.",
        ),
        goal="Sprawdzenie, czy UI gubi się przy szybkich kliknięciach.",
        observe=(
            "Czy zaznaczenie nadąża za kliknięciami?",
            "Czy prawy panel pokazuje właściwą sekcję?",
            "Czy UI się zawiesza albo pokazuje stale stary panel?",
        ),
        success_hint="Naciśnij Enter po szybkiej serii kliknięć i krótkim odczekaniu.",
        expected_event_patterns=("studio.gicleeframe.selection",),
    ),
    ScenarioDefinition(
        id="aba_cache",
        display_title="GICLÉE FRAME — powrót A → B → A",
        click_path=(
            "Wybierz jedną sekcję A.",
            "Poczekaj około 1 sekundy.",
            "Wybierz inną sekcję B.",
            "Poczekaj około 1 sekundy.",
            "Wróć do sekcji A.",
            "Obserwuj, czy A wraca szybciej niż za pierwszym razem.",
        ),
        goal="Sprawdzenie, czy cache wizualny sekcji jest odczuwalny.",
        observe=(
            "Czy powrót do A jest szybszy?",
            "Czy panel A wraca bez skeletona?",
            "Czy layout pozostaje stabilny?",
        ),
        success_hint="Naciśnij Enter po powrocie do A i krótkiej obserwacji.",
        expected_event_patterns=(
            "minimal_cache_hit",
            "cache_hit",
            "studio.gicleeframe.selection",
        ),
    ),
    ScenarioDefinition(
        id="media_section",
        display_title="GICLÉE FRAME — sekcja media_section",
        click_path=(
            'W GICLÉE FRAME znajdź sekcję typu „media_section" albo sekcję z mediami.',
            "Kliknij tę sekcję.",
            "Jeśli są dzieci / elementy zagnieżdżone, kliknij jeden child.",
            "Poczekaj 2–3 sekundy.",
        ),
        goal="Sprawdzenie, czy specjalna sekcja mediów ładuje się płynnie.",
        observe=(
            "Czy prawy panel pokazuje minimalny edytor?",
            'Czy pojawia się CTA „Pokaż szczegóły" / „Pokaż szczegóły mediów"?',
            "Czy media / children doskakują po kolei?",
        ),
        success_hint="Naciśnij Enter, gdy media_section jest widoczna i stabilna.",
        expected_event_patterns=("media_section", "studio.gicleeframe.selection"),
    ),
    ScenarioDefinition(
        id="details_cta",
        display_title="GICLÉE FRAME — Pokaż szczegóły",
        click_path=(
            'W GICLÉE FRAME wybierz sekcję, która ma przycisk „Pokaż szczegóły" albo „Pokaż szczegóły mediów".',
            "Kliknij ten przycisk.",
            "Jeśli pojawią się moduły, kliknij jeden moduł, np. podgląd / warstwy / elementy.",
            "Poczekaj 2–3 sekundy.",
            "Jeśli chcesz sprawdzić cache, kliknij ten sam szczegół drugi raz.",
        ),
        goal="Sprawdzenie szybkości szczegółów ładowanych na żądanie.",
        observe=(
            "Czy sam panel szczegółów pojawia się szybko?",
            "Czy moduł szczegółów ładuje się długo?",
            "Czy drugie kliknięcie jest szybsze?",
            "Czy coś ładuje się automatycznie bez kliknięcia?",
        ),
        success_hint="Naciśnij Enter po kliknięciu szczegółów / modułu i krótkiej obserwacji.",
        expected_event_patterns=(
            "details_shell",
            "details_on_demand",
            "details_module",
            "studio.gicleeframe.details",
        ),
    ),
)


@dataclass(frozen=True)
class Budgets:
    slow_event_warning_ms: float = 80.0
    slow_event_major_ms: float = 200.0
    details_cta_warning_ms: float = 300.0
    details_cta_major_ms: float = 700.0


@dataclass(frozen=True)
class AppProfile:
    id: str
    display_name: str
    default_log_path: Path
    output_root: Path
    budgets: Budgets
    launch_config: LaunchConfig
    manual_scenarios: tuple[ScenarioDefinition, ...] = MANUAL_SCENARIOS

    @property
    def studio_env_hints(self) -> dict[str, str]:
        return dict(self.launch_config.env)

    def scenario_by_id(self) -> dict[str, ScenarioDefinition]:
        return {scenario.id: scenario for scenario in self.manual_scenarios}

    def resolve_log_path(self, override: Path | None) -> Path:
        if override is not None:
            path = override
            if not path.is_absolute():
                path = _REPO_ROOT / path
            return path
        return _REPO_ROOT / self.default_log_path

    def resolve_output_root(self) -> Path:
        return _REPO_ROOT / self.output_root


_PROFILES: dict[str, AppProfile] = {
    "giclee_studio": AppProfile(
        id="giclee_studio",
        display_name="GicleeApp Studio Preview",
        default_log_path=Path("giclee_app/logs/studio_perf.log"),
        output_root=Path("reports/performance"),
        budgets=Budgets(),
        launch_config=LaunchConfig.studio_preview(),
    ),
}


def get_profile(profile_id: str) -> AppProfile:
    try:
        return _PROFILES[profile_id]
    except KeyError as exc:
        known = ", ".join(sorted(_PROFILES))
        raise ValueError(f"Unknown profile {profile_id!r}. Known: {known}") from exc


def list_profiles() -> list[str]:
    return sorted(_PROFILES)

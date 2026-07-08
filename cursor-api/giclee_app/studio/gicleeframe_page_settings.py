"""Specyfikacja pól settings sekcji strony (read + edycja RAM w Studio F2.1)."""

from __future__ import annotations

from dataclasses import dataclass, replace


def _float_range_options(min_val: float, max_val: float, step: float) -> tuple[str, ...]:
    values: list[str] = []
    current = min_val
    while current <= max_val + 1e-9:
        text = str(int(current)) if current == int(current) else str(current)
        values.append(text)
        current += step
    return tuple(values)


def _int_range_options(min_val: int, max_val: int, step: int = 1) -> tuple[str, ...]:
    return tuple(str(v) for v in range(min_val, max_val + 1, step))


@dataclass(frozen=True)
class PageSettingSpec:
    label: str
    key: str
    control: str
    options: tuple[str, ...] = ()


@dataclass(frozen=True)
class PageSettingField:
    label: str
    key: str
    value: str
    control: str
    options: tuple[str, ...] = ()


_COLOR_SCHEME_OPTIONS = tuple(f"scheme-{n}" for n in range(1, 7))

_DIVIDER_SETTING_SPECS: tuple[PageSettingSpec, ...] = (
    PageSettingSpec("Grubość linii", "thickness", "select", _float_range_options(0.5, 5, 0.5)),
    PageSettingSpec(
        "Szerokość sekcji",
        "section_width",
        "select",
        ("page-width", "full-width"),
    ),
    PageSettingSpec(
        "Szerokość linii %",
        "width_percent",
        "select",
        _int_range_options(5, 100, 5),
    ),
    PageSettingSpec(
        "Wyrównanie",
        "alignment_horizontal",
        "select",
        ("flex-start", "center", "flex-end"),
    ),
    PageSettingSpec("Schemat kolorów", "color_scheme", "select", _COLOR_SCHEME_OPTIONS),
    PageSettingSpec("Zaokrąglenie", "corner_radius", "select", ("square", "rounded")),
    PageSettingSpec("Odstęp góra", "padding-block-start", "select", _int_range_options(0, 100, 4)),
    PageSettingSpec("Odstęp dół", "padding-block-end", "select", _int_range_options(0, 100, 4)),
)

_MEDIA_SECTION_SETTING_SPECS: tuple[PageSettingSpec, ...] = (
    PageSettingSpec(
        "Układ treści",
        "content_direction",
        "select",
        ("column", "row"),
    ),
    PageSettingSpec("Odstęp między blokami", "gap", "select", _int_range_options(0, 48, 4)),
    PageSettingSpec("Schemat kolorów", "color_scheme", "select", _COLOR_SCHEME_OPTIONS),
    PageSettingSpec("Odstęp góra", "padding-block-start", "select", _int_range_options(0, 100, 4)),
    PageSettingSpec("Odstęp dół", "padding-block-end", "select", _int_range_options(0, 100, 4)),
)


_DIVIDER_SETTING_GROUP_ORDER: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Linia", ("thickness", "width_percent", "alignment_horizontal")),
    ("Układ", ("section_width", "padding-block-start", "padding-block-end")),
    ("Styl", ("color_scheme", "corner_radius")),
)


def divider_setting_groups() -> tuple[tuple[str, tuple[str, ...]], ...]:
    return _DIVIDER_SETTING_GROUP_ORDER


def _specs_for_section(section_type: str) -> tuple[PageSettingSpec, ...]:
    if section_type == "divider":
        return _DIVIDER_SETTING_SPECS
    if section_type in ("media_section", "section"):
        return _MEDIA_SECTION_SETTING_SPECS
    return ()


def page_settings_from_section(section: dict) -> tuple[PageSettingField, ...]:
    section_type = str(section.get("type", ""))
    specs = _specs_for_section(section_type)
    if not specs:
        return ()
    settings = section.get("settings")
    if not isinstance(settings, dict):
        return ()
    fields: list[PageSettingField] = []
    for spec in specs:
        if spec.key not in settings:
            continue
        value = str(settings[spec.key])
        options = spec.options
        if spec.control == "select" and value not in options and options:
            options = (value, *options)
        fields.append(
            PageSettingField(
                label=spec.label,
                key=spec.key,
                value=value,
                control=spec.control,
                options=options,
            )
        )
    return tuple(fields)


def apply_settings_patch(
    fields: tuple[PageSettingField, ...],
    patch_settings: dict[str, str | None],
) -> tuple[PageSettingField, ...]:
    if not patch_settings:
        return fields
    merged: list[PageSettingField] = []
    for field in fields:
        if field.key in patch_settings and patch_settings[field.key] is not None:
            new_value = str(patch_settings[field.key])
            options = field.options
            if field.control == "select" and new_value not in options and options:
                options = (new_value, *options)
            merged.append(replace(field, value=new_value, options=options))
        else:
            merged.append(field)
    return tuple(merged)

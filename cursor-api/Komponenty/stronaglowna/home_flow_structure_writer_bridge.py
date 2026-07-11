"""HF-3B bridge: aktualizuje komunikat readiness w plannerze HF-3A."""

from __future__ import annotations


def install_home_flow_structure_writer_bridge() -> None:
    from . import home_flow_structure_gui as planner_gui

    current_build = planner_gui.build_structure_plan
    current_format = planner_gui.format_structure_plan
    if getattr(current_build, "_giclee_hf3b_writer_bridge", False):
        return

    def build_with_writer(*args, **kwargs):
        plan = dict(current_build(*args, **kwargs))
        plan["writer_available"] = True
        plan["blueprint_materialization_available"] = False
        return plan

    def format_with_writer(plan):
        text = current_format(plan)
        text = text.replace(
            "GOTOWE DO HF-3B (writer nie jest dostępny w tym etapie).",
            "GOTOWE DO HF-3B — użyj osobnego przycisku „Zastosuj szkic…”.",
        )
        if plan.get("warnings"):
            text += (
                "\n\nHF-3B stosuje wyłącznie reorder istniejących sekcji. "
                "Blueprinty nowych sekcji pozostają zablokowane do HF-3C."
            )
        return text

    setattr(build_with_writer, "_giclee_hf3b_writer_bridge", True)
    setattr(build_with_writer, "__wrapped__", current_build)
    setattr(format_with_writer, "__wrapped__", current_format)
    planner_gui.build_structure_plan = build_with_writer
    planner_gui.format_structure_plan = format_with_writer

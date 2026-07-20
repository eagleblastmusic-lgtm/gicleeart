"""Strona główna — GICLÉE HOME FLOW, sekcje, fazy i assety motywu."""

from .prehero_integration import install_prehero_integration
from .prehero_snippet_idempotency import install_prehero_snippet_idempotency_fix
from .prehero_defaults_fix import install_prehero_defaults_fix
from .prehero_full_generator import install_prehero_full_generator

# Najpierw rejestrujemy syntetyczną sekcję Pre-Hero. Część starszych modułów
# zachowuje referencję do HOME_ZONES w chwili importu.
install_prehero_integration()
install_prehero_snippet_idempotency_fix()
install_prehero_defaults_fix()
install_prehero_full_generator()

from .home_flow_phase_settings import install_home_flow_phase_settings
from .home_flow_phase_validation import install_home_flow_phase_validation
from .home_scroll_mode import install_home_scroll_mode

install_home_flow_phase_settings()
install_home_flow_phase_validation()
install_home_scroll_mode()

# Przechwytujemy oryginalny callback sekcji tylko po to, aby uzyskać bezpośredni
# dostęp do bazowego renderera _show_zone. Treeview nie steruje już panelem przez
# event_generate na ukrytym Listboxie.
from .home_flow_navigation_hotfix import install_home_flow_navigation_hotfix

install_home_flow_navigation_hotfix()

from .home_flow_gui import install_home_flow_gui
from .home_flow_phase_gui import install_home_flow_phase_gui
from .home_flow_phase_summary import install_home_flow_phase_summaries
from .home_flow_phase_inline import install_home_flow_phase_inline
from .home_flow_phase_inline_units import install_inline_phase_units
from .home_flow_direct_navigation import install_home_flow_direct_navigation
from .home_flow_structure_gui import install_home_flow_structure_gui
from .home_flow_structure_writer_bridge import install_home_flow_structure_writer_bridge
from .home_flow_structure_writer_gui import install_home_flow_structure_writer_gui
from .prehero_video_preview import install_prehero_video_preview

install_home_flow_phase_gui()
install_home_flow_phase_summaries()
install_home_flow_phase_inline()
install_inline_phase_units()
install_home_flow_direct_navigation()
install_prehero_video_preview()
install_home_flow_gui()
install_home_flow_structure_gui()
install_home_flow_structure_writer_bridge()
install_home_flow_structure_writer_gui()

from . import gui as _gui

_gui.APP_TITLE = "GICLÉE HOME FLOW — strona główna"

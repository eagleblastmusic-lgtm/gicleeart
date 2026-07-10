"""Strona główna — edycja sekcji landing page (templates/index.json + assety motywu)."""

from .prehero_integration import install_prehero_integration
from .prehero_snippet_idempotency import install_prehero_snippet_idempotency_fix

install_prehero_integration()
install_prehero_snippet_idempotency_fix()

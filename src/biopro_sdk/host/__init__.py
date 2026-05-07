"""Host Tier — Core-facing subsystems and utilities for the BioPro application and SDK CLI."""

from .trust_manager import TrustManager, VerificationResult, BIOPRO_ROOT_PUBLIC_KEY_HEX
from .trust_overrides import LocalTrustRegistry
from .trust_path import TrustChain
from .trust_storage import TrustCache
from .docs import PluginDocumentation, docs_registry
from .sign_plugin import sign_plugin

_AI_SYMBOLS = {"AIAssistant", "AIServerManager", "ai_manager"}

__all__ = [
    "TrustManager",
    "VerificationResult",
    "LocalTrustRegistry",
    "TrustChain",
    "TrustCache",
    "AIAssistant",
    "AIServerManager",
    "ai_manager",
    "PluginDocumentation",
    "docs_registry",
    "sign_plugin",
    "BIOPRO_ROOT_PUBLIC_KEY_HEX",
]


def __getattr__(name: str):
    """Lazy loader for AI symbols that depend on `requests`."""
    if name in _AI_SYMBOLS:
        from .ai import AIAssistant, AIServerManager, ai_manager  # noqa: PLC0415

        globals()["AIAssistant"] = AIAssistant
        globals()["AIServerManager"] = AIServerManager
        globals()["ai_manager"] = ai_manager
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

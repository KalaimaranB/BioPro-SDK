"""State definitions for the background task blueprint."""

from dataclasses import dataclass, field

from biopro_sdk.plugin import PluginState


@dataclass
class CalculationState(PluginState):
    """Model tracking user input and computation results."""

    iterations: int = 10
    delay_ms: int = 200
    results: list[float] = field(default_factory=list)

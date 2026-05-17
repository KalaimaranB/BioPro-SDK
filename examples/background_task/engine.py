"""Background mathematical engines running in thread pool workers."""

import math
import time
from typing import Any, cast

from biopro_sdk.plugin import AnalysisBase, PluginState
from biopro_sdk.plugin.logging import get_logger

from .state import CalculationState

logger = get_logger(__name__, "background_task")


class SimulationEngine(AnalysisBase):
    """Background simulator performing iterative math calculations."""

    def __init__(self) -> None:
        """Initialize the SimulationEngine using background task plugin credentials."""
        super().__init__(plugin_id="background_task")

    def run(self, state: PluginState | None = None) -> dict[str, Any]:
        """Run the simulation, updating progress signals.

        Args:
            state: The current state containing simulation arguments.

        Returns:
            A dictionary containing the calculated results.
        """
        calc_state = cast(CalculationState, state)
        logger.info(
            "Starting background calculation simulation (iterations: %d, delay: %dms)",
            calc_state.iterations,
            calc_state.delay_ms,
        )

        results: list[float] = []
        total = calc_state.iterations

        for i in range(total):
            # Check for early worker thread cancellation
            if self.is_cancelled():
                logger.warning("Simulation was canceled early by user request.")
                return {"results": results, "status": "canceled"}

            # Perform a placeholder calculation (e.g. logarithmic sine wave)
            val = math.sin(i * 0.1) * math.log(i + 2)
            results.append(val)

            # Sleep to simulate long-running tasks
            time.sleep(calc_state.delay_ms / 1000.0)

            # Report progress (0 to 100)
            progress_pct = int(((i + 1) / total) * 100)
            self.signals.analysis_progress.emit(progress_pct)

        logger.info("Background calculation completed successfully.")
        return {"results": results, "status": "completed"}

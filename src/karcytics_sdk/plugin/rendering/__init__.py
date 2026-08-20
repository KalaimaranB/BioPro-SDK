"""Generic rendering infrastructure shared by Karcytics plugins.

Every plugin that draws a canvas (flow-cytometry's scatter/density plots and
node graph, cytometrics' image canvas, synthetic-biology's circuit and
simulation views) previously reimplemented its own full-clear-and-rebuild
redraw logic from scratch, and flow-cytometry additionally invented a
private global lock to make matplotlib's Agg backend safe to touch from a
background thread. This subpackage promotes both patterns into reusable SDK
components:

- ``lock``: a shared, process-wide lock for non-thread-safe rasterization
  backends (``RasterLock``, ``MPL_RASTER_LOCK``).
- ``pipeline``: a compute/rasterize split (``RenderComputeStage``,
  ``RasterizeStage``, ``RenderData``) that lets expensive numpy/pandas work
  run fully in parallel off-thread, with only the short final rasterize step
  serialized through a ``RasterLock``.
- ``mpl_canvas``: ``LayeredMatplotlibCanvas``, a matplotlib
  ``FigureCanvasQTAgg`` base class wiring the pipeline above into a debounced
  async data layer plus a cheap synchronous overlay layer.
- ``graphics_scene``: ``DirtyTrackingGraphicsScene``/``DirtyTrackingGraphicsView``,
  a ``QGraphicsScene``/``QGraphicsView`` base defaulting to Qt's
  ``MinimalViewportUpdate`` instead of a plugin-authored full-viewport
  repaint on every item change.

See ``PluginBase.create_worker``/``start_worker``/``create_render_pipeline``
for the ergonomic entry points most plugin code should use instead of
constructing these classes directly.
"""

from .graphics_scene import DirtyTrackingGraphicsScene, DirtyTrackingGraphicsView
from .lock import MPL_RASTER_LOCK, RasterLock
from .mpl_canvas import LayeredMatplotlibCanvas
from .pipeline import (
    RasterizeStage,
    RasterizeToImageTask,
    RenderComputeStage,
    RenderData,
    RenderPipelineController,
)

__all__ = [
    "MPL_RASTER_LOCK",
    "DirtyTrackingGraphicsScene",
    "DirtyTrackingGraphicsView",
    "LayeredMatplotlibCanvas",
    "RasterLock",
    "RasterizeStage",
    "RasterizeToImageTask",
    "RenderComputeStage",
    "RenderData",
    "RenderPipelineController",
]

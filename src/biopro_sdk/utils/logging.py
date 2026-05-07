"""BioPro SDK Logging Utilities.

Provides BioPro-aware loggers that automatically attach plugin metadata
and route to the central diagnostic engine.
"""

import logging


class PluginLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that injects plugin_id into every log record."""

    def __init__(self, logger: logging.Logger, plugin_id: str):
        super().__init__(logger, {"plugin_id": plugin_id})
        self.plugin_id = plugin_id

    def process(self, msg, kwargs):
        # Ensure plugin_id is in the extra dict for the handler to find
        extra = kwargs.get("extra", {})
        extra["plugin_id"] = self.plugin_id
        kwargs["extra"] = extra
        return msg, kwargs


def get_logger(name: str, plugin_id: str | None = None) -> logging.Logger | PluginLoggerAdapter:
    """Get a logger instance, optionally adapted for a specific plugin.

    Args:
        name: The name of the logger (usually __name__)
        plugin_id: The ID of the plugin this logger belongs to

    Returns:
        A logging.Logger or PluginLoggerAdapter instance.
    """
    logger = logging.getLogger(name)
    if plugin_id:
        return PluginLoggerAdapter(logger, plugin_id)
    return logger

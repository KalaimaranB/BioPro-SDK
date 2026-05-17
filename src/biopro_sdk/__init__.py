"""BioPro SDK — Software Development Kit for BioPro desktop plugins.

Provides two main namespaces:
    - plugin: Clean API for plugin development with zero unnecessary dependencies.
    - host: Host-facing APIs for the Core application and SDK signing CLI.
"""

from . import host, plugin

__all__ = ["plugin", "host"]

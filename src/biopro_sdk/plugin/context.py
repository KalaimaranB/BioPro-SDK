from biopro_sdk.plugin.manifest import PluginManifest


class UndeclaredCapabilityAccess(Exception):
    """Raised when a plugin attempts to access an undeclared capability."""

    pass


class PluginContext:
    """Capability-scoped context passed to plugins upon initialization."""

    def __init__(self, services: dict, manifest: PluginManifest):
        self._services = services
        self._manifest = manifest

    def get(self, capability: str):
        """Retrieve a required capability if declared in the manifest."""
        if capability not in self._manifest.requires:
            raise UndeclaredCapabilityAccess(
                f"Plugin '{self._manifest.name}' accessed '{capability}' without declaring it in plugin.toml"
            )

        if capability not in self._services:
            raise RuntimeError(
                f"Capability '{capability}' was requested and declared, but the host environment did not provide it."
            )

        return self._services[capability]

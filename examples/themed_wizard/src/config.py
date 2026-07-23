"""Configuration management for the wizard blueprint plugin."""

from biopro_sdk.plugin import PluginConfig


class WizardSettings:
    """Wrapper that leverages PluginConfig to manage wizard settings."""

    def __init__(self):
        """Initialize settings and load preferences from disk."""
        self.config = PluginConfig("themed_wizard")

    @property
    def developer_role(self) -> str:
        """The role of the developer using this tool (default: 'Researcher')."""
        return self.config.get("developer_role", "Researcher")

    @developer_role.setter
    def developer_role(self, value: str) -> None:
        self.config.set("developer_role", value)
        self.config.save()

    @property
    def enable_gpu(self) -> bool:
        """Flag indicating if GPU acceleration is enabled (default: False)."""
        return self.config.get("enable_gpu", False)

    @enable_gpu.setter
    def enable_gpu(self, value: bool) -> None:
        self.config.set("enable_gpu", value)
        self.config.save()

    @property
    def setup_completed(self) -> bool:
        """Flag indicating if the onboarding wizard completed successfully."""
        return self.config.get("setup_completed", False)

    @setup_completed.setter
    def setup_completed(self, value: bool) -> None:
        self.config.set("setup_completed", value)
        self.config.save()

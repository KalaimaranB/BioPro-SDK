import dataclasses

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore


VALID_PROCESS_MODELS = ("in_process", "isolated")


@dataclasses.dataclass
class PluginManifest:
    name: str
    entry_point: str
    sdk_version: str
    requires: list[str] = dataclasses.field(default_factory=list)
    publishes: list[str] = dataclasses.field(default_factory=list)
    subscribes: list[str] = dataclasses.field(default_factory=list)
    process_model: str = "in_process"
    """Whether this plugin runs in the Hub's own interpreter ("in_process",
    the default — unchanged behavior for existing plugins) or in its own
    subprocess with its own interpreter ("isolated"). Isolated plugins reach
    Hub services through karcytics_sdk.host.core_services.CoreServicesClient
    instead of live objects in PluginContext's services dict.
    """

    def __post_init__(self) -> None:
        if self.process_model not in VALID_PROCESS_MODELS:
            raise ValueError(f"Invalid process_model '{self.process_model}' — must be one of {VALID_PROCESS_MODELS}.")

    @classmethod
    def from_toml(cls, toml_str: str) -> "PluginManifest":
        data = tomllib.loads(toml_str)
        plugin_data = data.get("plugin", {})
        if not plugin_data:
            raise ValueError("Manifest missing [plugin] section")

        return cls(
            name=plugin_data.get("name", "Unknown"),
            entry_point=plugin_data.get("entry_point", ""),
            sdk_version=plugin_data.get("sdk_version", "*"),
            requires=plugin_data.get("requires", []),
            publishes=plugin_data.get("publishes", []),
            subscribes=plugin_data.get("subscribes", []),
            process_model=plugin_data.get("process_model", "in_process"),
        )

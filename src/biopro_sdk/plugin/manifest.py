import dataclasses

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore


@dataclasses.dataclass
class PluginManifest:
    name: str
    entry_point: str
    sdk_version: str
    requires: list[str] = dataclasses.field(default_factory=list)
    publishes: list[str] = dataclasses.field(default_factory=list)
    subscribes: list[str] = dataclasses.field(default_factory=list)

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
        )

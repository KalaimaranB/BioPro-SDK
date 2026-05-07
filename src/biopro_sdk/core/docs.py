"""Simple Documentation System for BioPro SDK.

Allows plugins to register markdown files that act as help pages.
"""


class PluginDocumentation:
    """Registry for plugin help documentation."""

    def __init__(self):
        # Format: { plugin_id: { page_id: file_path } }
        self._registry: dict[str, dict[str, str]] = {}

    def register_page(self, plugin_id: str, page_id: str, file_path: str) -> None:
        """Register a markdown file as a help page.

        Args:
            plugin_id: The ID of the plugin (e.g. 'flow_cytometry')
            page_id: Identifier for the specific page (e.g. 'index', 'gating_help')
            file_path: Absolute path to the .md file.
        """
        if plugin_id not in self._registry:
            self._registry[plugin_id] = {}
        self._registry[plugin_id][page_id] = file_path

    def get_page(self, plugin_id: str, page_id: str) -> str | None:
        """Retrieve the file path for a registered documentation page.

        Args:
            plugin_id: The ID of the plugin.
            page_id: Identifier for the specific page.

        Returns:
            The file path if found, None otherwise.
        """
        return self._registry.get(plugin_id, {}).get(page_id)

    def get_all_pages(self, plugin_id: str) -> dict[str, str]:
        """Retrieve all registered pages for a given plugin."""
        return self._registry.get(plugin_id, {})


# Global registry
docs_registry = PluginDocumentation()

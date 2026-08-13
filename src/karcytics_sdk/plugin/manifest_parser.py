import tomllib
from pathlib import Path
from typing import Any


class ManifestValidationError(Exception):
    """Raised when a manifest fails validation."""

    pass


class ManifestParser:
    """Parses and validates plugin pyproject.toml files."""

    REQUIRED_KEYS = ["id", "name", "version", "description", "authors"]

    def parse(self, manifest_data: dict[str, Any]) -> dict[str, Any]:
        """Validate flat dictionary combined from pyproject.toml."""
        for key in self.REQUIRED_KEYS:
            if key not in manifest_data:
                raise ManifestValidationError(f"Missing required field: '{key}'")

        authors = manifest_data["authors"]
        if not isinstance(authors, list) or len(authors) == 0:
            raise ManifestValidationError("'authors' must be a non-empty array.")

        for idx, author in enumerate(authors):
            if not isinstance(author, dict):
                raise ManifestValidationError(f"Author at index {idx} must be an object.")
            if "name" not in author:
                raise ManifestValidationError(f"Author at index {idx} must contain 'name'.")
            if "role" not in author:
                raise ManifestValidationError("Author profile must contain 'role'.")
            if "permissions" in author:
                perms = author["permissions"]
                if not isinstance(perms, list) or not all(isinstance(p, str) for p in perms):
                    raise ManifestValidationError("Author 'permissions' must be a list of strings.")

        return manifest_data

    def parse_file(self, filepath: str | Path) -> dict[str, Any]:
        """Read and parse a pyproject.toml file."""
        filepath = Path(filepath)

        # Security/Sanity Check
        legacy_manifest = filepath.parent / "manifest.json"
        legacy_toml = filepath.parent / "plugin.toml"
        if legacy_manifest.exists() or legacy_toml.exists():
            print("\n⚠️  WARNING: Legacy manifest.json or plugin.toml found! These are deprecated.")
            print("⚠️  Please run 'karcytics-sdk migrate' to transition to pyproject.toml.\n")

        try:
            with open(filepath, "rb") as f:
                data = tomllib.load(f)

            project = data.get("project", {})
            plugin = data.get("tool", {}).get("biopro", {}).get("plugin", {})

            # Merge fields to present a unified V2 style dictionary to the rest of the application
            flat_manifest = {
                "name": project.get("name"),
                "version": project.get("version"),
                "description": project.get("description"),
                "core_dependencies": project.get("dependencies", []),
            }
            flat_manifest.update(plugin)

            # Ensure display_name and authors are set
            if "display_name" not in flat_manifest:
                flat_manifest["display_name"] = flat_manifest.get("name", "Unknown")
            if "authors" not in flat_manifest:
                flat_manifest["authors"] = project.get("authors", [])

            return self.parse(flat_manifest)
        except tomllib.TOMLDecodeError as e:
            raise ManifestValidationError(f"Invalid TOML format: {e}") from e
        except FileNotFoundError as e:
            raise ManifestValidationError(f"Plugin configuration not found: {filepath}") from e

import json
from typing import Any


class ManifestValidationError(Exception):
    """Raised when a manifest fails validation."""

    pass


class ManifestParser:
    """Parses and validates plugin manifest.json files (V2 Split Schema)."""

    REQUIRED_V2_KEYS = ["id", "name", "version", "description", "authors"]

    def parse(self, manifest_data: dict[str, Any]) -> dict[str, Any]:
        """Parse and validate manifest dictionary."""
        # 1. Hard check for legacy author field (No backwards compatibility)
        if "author" in manifest_data:
            raise ManifestValidationError(
                "Legacy 'author' field is no longer supported. Please migrate to 'authors' array and separate security.json."
            )

        # 2. Block any security hashes or signature properties inside manifest.json (SRP Enforcement)
        for forbidden_key in ["integrity", "hashes", "signed_by", "signature"]:
            if forbidden_key in manifest_data:
                raise ManifestValidationError(
                    f"Security field '{forbidden_key}' is not allowed in manifest.json. "
                    "All cryptographic parameters must reside in security.json."
                )

        # 3. Ensure it specifies manifest_version: 2
        if manifest_data.get("manifest_version") != 2:
            raise ManifestValidationError("Only manifest_version: 2 is supported.")

        # 4. Check required fields
        for key in self.REQUIRED_V2_KEYS:
            if key not in manifest_data:
                raise ManifestValidationError(f"Missing required field: '{key}'")

        # 5. Validate authors is a non-empty array
        authors = manifest_data["authors"]
        if not isinstance(authors, list) or len(authors) == 0:
            raise ManifestValidationError("'authors' must be a non-empty array.")

        # 6. Validate author profiles strictly (requiring Name & Role)
        for idx, author in enumerate(authors):
            if not isinstance(author, dict):
                raise ManifestValidationError(f"Author at index {idx} must be an object.")

            if "name" not in author:
                raise ManifestValidationError(f"Author at index {idx} must contain 'name'.")

            if "role" not in author:
                raise ManifestValidationError("Author profile must contain 'role'.")

            # If permissions exist, they must be a list of strings
            if "permissions" in author:
                perms = author["permissions"]
                if not isinstance(perms, list) or not all(isinstance(p, str) for p in perms):
                    raise ManifestValidationError("Author 'permissions' must be a list of strings.")

        return manifest_data

    def parse_file(self, filepath: str) -> dict[str, Any]:
        """Read and parse a manifest.json file."""
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
            return self.parse(data)
        except json.JSONDecodeError as e:
            raise ManifestValidationError(f"Invalid JSON format: {e}") from e
        except FileNotFoundError as e:
            raise ManifestValidationError(f"Manifest file not found: {filepath}") from e

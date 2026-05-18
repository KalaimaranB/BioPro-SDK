import hashlib
import json
from pathlib import Path
from typing import Any


class SecurityValidationError(Exception):
    """Raised when a security ledger fails validation."""

    pass


class ManifestHashMismatch(SecurityValidationError):
    """Raised when the cryptographic binding hash between manifest.json and security.json fails."""

    pass


class SecurityParser:
    """Parses and validates plugin security.json files (V1 Security Ledger Schema)."""

    REQUIRED_FIELDS = ["security_version", "plugin_id", "manifest_hash", "hashes"]

    def parse(self, security_data: dict[str, Any]) -> dict[str, Any]:
        """Parse and validate security dictionary."""
        # 1. Check required fields
        for key in self.REQUIRED_FIELDS:
            if key not in security_data:
                raise SecurityValidationError(f"Missing required security field: '{key}'")

        # 2. Enforce V1 security version (No backwards compatibility)
        if security_data.get("security_version") != 1:
            raise SecurityValidationError("Only security_version: 1 is supported.")

        # 3. Validate hashes is a dictionary
        hashes = security_data["hashes"]
        if not isinstance(hashes, dict):
            raise SecurityValidationError("'hashes' must be a dictionary.")

        # 4. Validate exclusions is a list if present
        if "exclusions" in security_data:
            exclusions = security_data["exclusions"]
            if not isinstance(exclusions, list):
                raise SecurityValidationError("'exclusions' must be a list of strings.")

        return security_data

    def parse_file(self, filepath: str) -> dict[str, Any]:
        """Read and parse a security.json file."""
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
            return self.parse(data)
        except json.JSONDecodeError as e:
            raise SecurityValidationError(f"Invalid JSON format: {e}") from e
        except FileNotFoundError as e:
            raise SecurityValidationError(f"Security file not found: {filepath}") from e

    def verify_manifest_binding(
        self, manifest_filepath: Path, security_data: dict[str, Any]
    ) -> None:
        """Verify the cryptographic hash binding of manifest.json against security.json."""
        if not manifest_filepath.exists():
            raise SecurityValidationError(f"Manifest file not found: {manifest_filepath}")

        # Calculate SHA-256 of manifest.json exactly as written on disk
        manifest_bytes = manifest_filepath.read_bytes()
        computed_hash = hashlib.sha256(manifest_bytes).hexdigest()

        expected_hash = security_data["manifest_hash"]
        if computed_hash != expected_hash:
            raise ManifestHashMismatch(
                "Cryptographic bind mismatch: manifest.json SHA-256 does not match security.json manifest_hash. "
                f"Expected: {expected_hash}, Computed: {computed_hash}"
            )

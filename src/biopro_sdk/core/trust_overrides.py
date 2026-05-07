"""Local Trust Overrides for BioPro.

Allows users to manually 'Verify' and trust locally modified plugins
on their specific machine, overriding standard signature checks.
Secured with transparent local background Machine Keys.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class LocalTrustRegistry:
    """Manages a registry of user-approved plugin snapshots secured by local Machine Keys."""

    def __init__(self):
        self.config_dir = Path.home() / ".biopro"
        self.storage_path = self.config_dir / "trust_overrides.json"
        self.private_key_path = self.config_dir / "machine_private.pem"
        self.signature_path = self.config_dir / "trust_overrides.sig"
        self._data: dict[str, dict[str, str]] = {}
        self._load()

    def _get_or_create_machine_key(self):
        """Retrieves or silently generates the local Ed25519 Machine Private Key on first boot."""
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ed25519

        self.config_dir.mkdir(parents=True, exist_ok=True)
        if not self.private_key_path.exists():
            private_key = ed25519.Ed25519PrivateKey.generate()
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            with open(self.private_key_path, "wb") as f:
                f.write(private_pem)
            logger.info("Generated new local Machine Key for signing local overrides.")
            return private_key
        else:
            with open(self.private_key_path, "rb") as f:
                private_pem = f.read()
            return serialization.load_pem_private_key(private_pem, password=None)

    def _load(self):
        """Load stored overrides from disk and verify local cryptographic signature."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "rb") as f:
                    data_bytes = f.read()

                # Verify local cryptographic signature
                if not self.signature_path.exists():
                    raise ValueError("Signature file is missing! Tampering suspected.")

                with open(self.signature_path, "rb") as f:
                    signature = f.read()

                private_key = self._get_or_create_machine_key()
                public_key = private_key.public_key()
                public_key.verify(signature, data_bytes)

                self._data = json.loads(data_bytes.decode("utf-8"))
                logger.debug("Successfully loaded and verified local trust overrides.")
            except Exception as e:
                logger.critical(
                    f"CRITICAL SECURITY LOCK: Local overrides signature invalid or file tampered! Ignoring overrides: {e}"
                )
                self._data = {}

    def save(self):
        """Persist overrides to disk and sign with local background machine key."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        data_bytes = json.dumps(self._data, indent=4).encode("utf-8")

        with open(self.storage_path, "wb") as f:
            f.write(data_bytes)

        try:
            private_key = self._get_or_create_machine_key()
            signature = private_key.sign(data_bytes)
            with open(self.signature_path, "wb") as f:
                f.write(signature)
        except Exception as e:
            logger.error(f"Failed to cryptographically sign local trust overrides: {e}")

    def is_locally_trusted(self, plugin_id: str, current_hashes: dict[str, str]) -> bool:
        """Check if the current state of a plugin matches a trusted local snapshot."""
        if plugin_id not in self._data:
            return False

        stored_snapshot = self._data[plugin_id]

        # All files in the snapshot must match the current state
        return stored_snapshot == current_hashes

    def trust_current_state(self, plugin_id: str, current_hashes: dict[str, str]):
        """Record the current state as trusted for this machine."""
        self._data[plugin_id] = current_hashes
        self.save()

    def remove_trust(self, plugin_id: str):
        """Remove a local trust override."""
        if plugin_id in self._data:
            del self._data[plugin_id]
            self.save()

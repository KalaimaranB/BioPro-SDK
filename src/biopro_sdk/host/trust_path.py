"""Data models and utilities for Hierarchical Trust Chains."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


@dataclass
class TrustLink:
    """A single link in the trust chain (Issuer -> Subject)."""

    subject_name: str
    subject_pub: str  # Hex encoded Ed25519 public key
    issuer_name: str
    signature: str  # Hex encoded signature

    def to_dict(self) -> dict:
        """Convert the trust link representation to a standard dictionary.

        Returns:
            A dictionary containing subject, issuer, and signature hex strings.
        """
        return asdict(self)


@dataclass
class TrustChain:
    """The full chain of trust for a plugin."""

    links: list[TrustLink]

    def to_json(self) -> str:
        """Serialize the entire trust chain to a formatted JSON string.

        Returns:
            A formatted JSON representation of all trust link dictionaries.
        """
        return json.dumps([link.to_dict() for link in self.links], indent=4)

    @classmethod
    def from_json(cls, json_str: str) -> "TrustChain":
        """Deserialize a trust chain from a raw JSON string.

        Args:
            json_str: The serialized trust chain string.

        Returns:
            An instantiated TrustChain model.
        """
        data = json.loads(json_str)
        links = [TrustLink(**item) for item in data]
        return cls(links=links)

    @classmethod
    def from_file(cls, path: Path) -> Optional["TrustChain"]:
        """Load and deserialize a trust chain file path.

        Args:
            path: Absolute file system Path to the trust chain file.

        Returns:
            The parsed TrustChain instance, or None if the file is missing or corrupt.
        """
        if not path.exists():
            return None
        try:
            with open(path) as f:
                return cls.from_json(f.read())
        except Exception:
            return None

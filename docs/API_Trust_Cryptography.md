# 🛡️ Cryptography & Security Module (`biopro_sdk.host`)

Technical specification for the secure cryptographic trust tree model, signature verification procedures, local registry overrides, and manifest parser paths.

---

## 🏛️ `TrustManager`

The primary verification engine used by the host application. It performs multi-stage checks before letting a plugin folder load.

### Method Signatures

#### `__init__(self, trust_roots_path: Path | None = None) -> None`
Initializes the manager, reading the public root keys registry.
*   **Parameters:**
    *   `trust_roots_path` (`Path | None`): Optional custom binary path containing approved public keys. Defaults to active environment trust locations.

#### `verify_plugin(self, plugin_dir: str | Path) -> tuple[bool, str]`
Performs a comprehensive, multi-step cryptographic verification check on a plugin folder.
*   **Parameters:**
    *   `plugin_dir` (`str | Path`): Path to the target plugin folder.
*   **Returns:**
    *   `tuple[bool, str]`: A tuple containing `(is_valid, reason_or_empty_str)`.
*   **Verification Steps Executed:**
    1.  **Integrity Scan:** Reads every file in the directory, matches its SHA-256 hash against the integrity dictionary in `manifest.json`.
    2.  **Canonical Signature Verification:** Verifies the canonicalized manifest string against the public developer key, using the signature block found in `signature.bin`.
    3.  **Certificate Chain Parsing:** Parses the developer certificate stub `dev_cert.bin` and verifies that it is signed by an approved public root authority.

---

## 🔑 `TrustOverrideRegistry`

Allows developers to establish local trust bypass stubs on their test machines, loading development plugins instantly without university/institutional delegation signatures.

### Method Signatures

#### `__init__(self) -> None`
Instantiates the registry loader, fetching serialized credentials from `~/.biopro/trust_overrides.json`.

#### `add_override(self, public_key_hex: str) -> None`
Adds a developer public key to the local trusted whitelist database.
*   **Parameters:**
    *   `public_key_hex` (`str`): The Ed25519 public key in hexadecimal string representation.

#### `is_overridden(self, public_key_hex: str) -> bool`
Returns `True` if the whitelisted developer key is whitelisted on this computer.

---

## 📄 PEM Key Utilities

Standard helpers facilitating seamless Ed25519 PKCS#8 key loading and signature formatting.

### Core Helpers

*   **`load_private_key_pem(pem_bytes: bytes) -> Ed25519PrivateKey`:** Parses private key bytes from PKCS#8 standard format.
*   **`load_public_key_pem(pem_bytes: bytes) -> Ed25519PublicKey`:** Parses public key bytes from SPKI standard format.
*   **`serialize_public_key_raw(pub_key: Ed25519PublicKey) -> bytes`:** Returns the raw 32-byte Ed25519 public key.
*   **`serialize_private_key_raw(priv_key: Ed25519PrivateKey) -> bytes`:** Returns the raw 32-byte Ed25519 private key.

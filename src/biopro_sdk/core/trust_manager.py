"""Trust Architecture Manager for BioPro.

Handles cryptographic integrity verification for plugins using Ed25519
signatures and Merkle-tree directory hashing. Supports a multi-level
Chain of Trust (Root -> Developer -> Plugin).
"""

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from .trust_overrides import LocalTrustRegistry
from .trust_path import TrustChain

logger = logging.getLogger(__name__)

# Hardcoded BioPro Authority Public Key (The Root of Trust)
# In production, this would be baked into the binary or stored in a secure enclave.
_FALLBACK_ROOT_PUBLIC_KEY_HEX = "08f4319b6f979057b36b0db2b8faaee6eff8782f3aafd5e924ba79b04d4c8366"
BIOPRO_ROOT_PUBLIC_KEY_HEX = os.getenv("BIOPRO_ROOT_PUBLIC_KEY_HEX", _FALLBACK_ROOT_PUBLIC_KEY_HEX)


@dataclass
class VerificationResult:
    """Result of a plugin trust verification check."""

    success: bool
    trust_level: str = "untrusted"
    error_message: str = ""
    trust_path: list[dict] | None = None
    developer_name: str | None = None
    developer_key: str | None = None
    calculated_hashes: dict | None = None


class TrustManager:
    """Manages the verification of plugin integrity and authorship."""

    # Common system noise and runtime output files that are implicitly ignored
    IGNORE_LIST = {
        ".DS_Store",
        "Thumbs.db",
        "__pycache__",
        ".git",
        ".github",
        ".vscode",
        ".idea",
        ".pytest_cache",
        ".venv",
        "venv",
        "cache",
        "results",
        "temp",
        "logs",
        "output",
        "dist",
        "build",
        "signature.bin",
        "trust_chain.json",
        "manifest.json",
        "dev_cert.bin",
    }

    # Files that MUST be signed and are never ignored
    MANDATORY_EXTENSIONS = {".py", ".pyw", ".json", ".yml", ".yaml", ".fcs"}

    def __init__(self, root_public_key: ed25519.Ed25519PublicKey | None = None):
        """Initialize the manager with a Root Public Key and local overrides."""
        self.primary_root = root_public_key
        self.trusted_roots: list[ed25519.Ed25519PublicKey] = []
        self._load_all_roots()

        self.overrides = LocalTrustRegistry()
        self._cache = None

    def _load_all_roots(self):
        """Load all trusted root keys including those in ~/.biopro/trusted_roots/."""
        # 1. Add Primary/Hardcoded Root
        self.trusted_roots = []
        if self.primary_root:
            self.trusted_roots.append(self.primary_root)
        else:
            try:
                hardcoded_root = ed25519.Ed25519PublicKey.from_public_bytes(
                    bytes.fromhex(BIOPRO_ROOT_PUBLIC_KEY_HEX)
                )
                self.trusted_roots.append(hardcoded_root)
            except Exception as e:
                logger.error(f"Failed to load hardcoded root key: {e}")

        # 2. Add Network and Personal Anchors from the user folder
        roots_dir = Path.home() / ".biopro" / "trusted_roots"
        roots_dir.mkdir(parents=True, exist_ok=True)

        for key_file in roots_dir.glob("*.pub"):
            try:
                with open(key_file, "rb") as f:
                    key_data = f.read()
                    if b"BEGIN PUBLIC KEY" in key_data:
                        pub_key = serialization.load_pem_public_key(key_data)
                    else:
                        pub_key = ed25519.Ed25519PublicKey.from_public_bytes(key_data)

                    if isinstance(pub_key, ed25519.Ed25519PublicKey):
                        self.trusted_roots.append(pub_key)
            except Exception as e:
                logger.error(f"Failed to load trusted anchor {key_file.name}: {e}")

    def trust_developer(self, developer_name: str, public_key_hex: str) -> bool:
        """Manually accepts a developer as a personal trust anchor."""
        try:
            pub_bytes = bytes.fromhex(public_key_hex)
            if len(pub_bytes) != 32:
                return False

            roots_dir = Path.home() / ".biopro" / "trusted_roots"
            roots_dir.mkdir(parents=True, exist_ok=True)

            # Save as a manual anchor
            safe_name = developer_name.lower().replace(" ", "_")
            key_path = roots_dir / f"manual_{safe_name}.pub"

            with open(key_path, "wb") as f:
                f.write(pub_bytes)

            # Reload keys immediately
            self._load_all_roots()
            logger.info(f"Personally accepted trust for developer: {developer_name}")

            # Clear performance cache for any plugins by this developer
            if self._cache:
                self._cache.data.clear()
                self._cache._save()

            return True
        except Exception as e:
            logger.error(f"Failed to manually trust developer {developer_name}: {e}")
            return False

    def _get_cache(self):
        if self._cache is None:
            try:
                from .trust_storage import TrustCache

                self._cache = TrustCache()
            except ImportError:
                self._cache = None
        return self._cache

    def verify_plugin(self, plugin_path: Path) -> VerificationResult:
        """Execute the full multi-layer verification for a plugin folder."""
        # DEBUG: Log to a specific file in the user's config directory
        debug_log_path = Path.home() / ".biopro" / "trust_debug.log"
        try:
            with open(debug_log_path, "a") as log:
                log.write(f"\nComparing {plugin_path.name}...\n")
        except Exception:
            pass  # Never let a debug log crash the boot sequence

        try:
            # 1. Performance Check: Trust Cache
            cache = self._get_cache()
            if cache and cache.is_trusted(plugin_path):
                cached_path = cache.data.get(plugin_path.name, {}).get("trust_path")
                return VerificationResult(
                    success=True, trust_level="verified_cache", trust_path=cached_path
                )

            # 2. Authenticity: Chain of Trust (Root -> Developer -> Plugin)
            auth_result = self._verify_signatures(plugin_path)

            # 3. Integrity: Deterministic Merkle Check
            integrity_result = self._check_integrity(plugin_path)

            # 4. If ANY standard check fails, check for manual user override
            if not auth_result.success or not integrity_result.success:
                hashes = integrity_result.calculated_hashes or {}
                if self.overrides.is_locally_trusted(plugin_path.name, hashes):
                    return VerificationResult(success=True, trust_level="verified_local")

                # If no override, return the specific failure but ALWAYS include calculated hashes
                # so the UI can offer to 'Lock' (snapshot) the current state.
                final_res = auth_result if not auth_result.success else integrity_result
                final_res.calculated_hashes = hashes

                if not auth_result.success:
                    try:
                        with open(debug_log_path, "a") as log:
                            log.write(f"Auth Failed: {auth_result.error_message}\n")
                    except Exception:
                        pass

                return final_res

            # 4. Finalize: Update Cache
            if cache:
                cache.mark_as_trusted(plugin_path, trust_path=auth_result.trust_path)

            return VerificationResult(
                success=True,
                trust_level="verified_developer",
                calculated_hashes=integrity_result.calculated_hashes,
                trust_path=auth_result.trust_path,
            )

        except Exception as e:
            logger.exception(f"Verification failed critically for {plugin_path.name}")
            return VerificationResult(
                success=False,
                error_message=f"Critical Verification Error: {str(e)}",
                calculated_hashes=integrity_result.calculated_hashes
                if "integrity_result" in locals()
                else None,
            )

    def _verify_signatures(self, plugin_path: Path) -> VerificationResult:
        """Verifies the multi-level trust chain and the plugin signature."""
        chain_file = plugin_path / "trust_chain.json"
        sig_file = plugin_path / "signature.bin"
        manifest_file = plugin_path / "manifest.json"

        if not chain_file.exists():
            return VerificationResult(
                success=False,
                error_message="Security Error: trust_chain.json missing. Plugin is untrusted.",
            )
        if not sig_file.exists():
            return VerificationResult(
                success=False,
                error_message="Security Error: signature.bin missing. Plugin integrity cannot be verified.",
            )

        try:
            # 1. Load the Trust Chain
            chain = TrustChain.from_file(chain_file)
            if not chain or not chain.links:
                return VerificationResult(
                    success=False, error_message="Invalid or empty trust chain."
                )

            # --- RECURSIVE LOGIC ---
            # A chain is [L0, L1, ..., Ln] where Ln is the Root-signed link and L0 is the Developer.
            # 1. Verify signatures: Li subject is signed by Li+1 subject.

            verified_links = []
            for i in range(len(chain.links) - 1):
                child = chain.links[i]
                parent = chain.links[i + 1]

                child_sub_bytes = bytes.fromhex(child.subject_pub)
                parent_sub_key = ed25519.Ed25519PublicKey.from_public_bytes(
                    bytes.fromhex(parent.subject_pub)
                )

                try:
                    parent_sub_key.verify(bytes.fromhex(child.signature), child_sub_bytes)
                    verified_links.append(
                        {"name": child.subject_name, "status": "verified", "key": child.subject_pub}
                    )
                except InvalidSignature:
                    return VerificationResult(
                        success=False,
                        error_message=f"Broken Trust Link: {parent.subject_name} signature for {child.subject_name} is invalid.",
                    )

            # 2. Verify TOP Link against Local Anchors
            top_link = chain.links[-1]
            top_sub_bytes = bytes.fromhex(top_link.subject_pub)
            top_sig_bytes = bytes.fromhex(top_link.signature)

            anchor_found = False
            for root_key in self.trusted_roots:
                try:
                    root_key.verify(top_sig_bytes, top_sub_bytes)
                    anchor_found = True
                    break
                except InvalidSignature:
                    continue

            if not anchor_found:
                # Check for direct trust (Subject is anchor)
                for root_key in self.trusted_roots:
                    try:
                        root_bytes = root_key.public_bytes(
                            encoding=serialization.Encoding.Raw,
                            format=serialization.PublicFormat.Raw,
                        )
                        if root_bytes == top_sub_bytes:
                            anchor_found = True
                            break
                    except Exception:
                        continue

            if not anchor_found:
                # Still return developer info so UI can offer manual trust
                return VerificationResult(
                    success=False,
                    trust_level="untrusted",
                    error_message=f"Untrusted Root: {top_link.subject_name} is not signed by a recognized BioPro Authority.",
                    developer_name=chain.links[0].subject_name,
                    developer_key=chain.links[0].subject_pub,
                )

            # Add the top link to verified links
            verified_links.append(
                {"name": top_link.subject_name, "status": "anchor", "key": top_link.subject_pub}
            )

            # Reorder for UI (BioPro -> ... -> Dev)
            full_path = [{"name": "BioPro Core", "status": "root"}] + list(reversed(verified_links))

            # 3. Verify Manifest Signature against Developer Key (Bottom Link)
            dev_link = chain.links[0]
            dev_public_key = ed25519.Ed25519PublicKey.from_public_bytes(
                bytes.fromhex(dev_link.subject_pub)
            )

            with open(sig_file, "rb") as f:
                plugin_signature = f.read()
            with open(manifest_file) as f:
                manifest_data = json.load(f)

            manifest_bytes = json.dumps(manifest_data, sort_keys=True).encode()
            try:
                dev_public_key.verify(plugin_signature, manifest_bytes)
            except InvalidSignature:
                return VerificationResult(
                    success=False,
                    error_message="Invalid Plugin Signature (Developer check failed).",
                )

            if manifest_data.get("id") != plugin_path.name:
                return VerificationResult(
                    success=False,
                    error_message="Identity Mismatch: Plugin ID does not match folder name.",
                )

            return VerificationResult(success=True, trust_path=full_path)

        except Exception as e:
            return VerificationResult(
                success=False, error_message=f"Chain Verification Error: {str(e)}"
            )

    def _check_integrity(self, plugin_path: Path) -> VerificationResult:
        """Verifies every file in the directory against the signed manifest hashes."""
        try:
            with open(plugin_path / "manifest.json") as f:
                manifest = json.load(f)

            signed_hashes = manifest.get("integrity", {}).get("hashes", {})
            if not signed_hashes:
                return VerificationResult(
                    success=False, error_message="Missing integrity manifest in manifest.json."
                )

            # 0. Load Custom Exclusions from Manifest (strip slashes for directory matching)
            raw_exclusions = manifest.get("integrity", {}).get("exclusions", [])
            custom_exclusions = {e.rstrip("/") for e in raw_exclusions}

            # Security: Standard app noise and security files are always ignored
            active_ignore = self.IGNORE_LIST | custom_exclusions

            # Walk directory and categorize
            found_files = set()
            found_hashes: dict[str, str] = {}  # Properly initialized for snapshotting
            integrity_passed = True
            error_msg = ""

            for root, dirs, files in os.walk(plugin_path):
                # Skip ignored directories (like __pycache__)
                dirs[:] = [d for d in dirs if d not in active_ignore]

                for file in files:
                    if file in active_ignore or file in [
                        "signature.bin",
                        "trust_chain.json",
                        "manifest.json",
                    ]:
                        continue

                    rel_path = os.path.relpath(os.path.join(root, file), plugin_path)
                    found_files.add(rel_path)

                    # ALWAYS calculate the hash so we can snapshot/lock the current state
                    calc_hash = self._hash_file(os.path.join(root, file))
                    found_hashes[rel_path] = calc_hash

                    # 1. Check for unauthorized files (Smart Strictness)
                    if rel_path not in signed_hashes:
                        if any(file.endswith(ext) for ext in self.MANDATORY_EXTENSIONS):
                            integrity_passed = False
                            if not error_msg:
                                error_msg = (
                                    f"Unauthorized File: {rel_path} is not in the signed manifest."
                                )
                        continue

                    # 2. Check File Hash
                    if calc_hash != signed_hashes.get(rel_path):
                        integrity_passed = False
                        if not error_msg:
                            error_msg = f"Integrity Mismatch: {rel_path} has been tampered with."

            # 3. Check for missing files
            for signed_path in signed_hashes:
                if signed_path not in found_files:
                    integrity_passed = False
                    if not error_msg:
                        error_msg = (
                            f"Missing File: {signed_path} was signed but is not present on disk."
                        )

            return VerificationResult(
                success=integrity_passed,
                trust_level="verified_developer" if integrity_passed else "untrusted",
                error_message=error_msg,
                calculated_hashes=found_hashes,
            )

        except Exception as e:
            return VerificationResult(
                success=False, error_message=f"Integrity Check Error: {str(e)}"
            )

    def _hash_file(self, full_path: str) -> str:
        """Utility to calculate SHA-256 for a file."""
        hasher = hashlib.sha256()
        with open(full_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

"""Trust Architecture Manager for BioPro.

Handles cryptographic integrity verification for plugins using Ed25519
signatures and Split-Manifest architecture, including double-signing
consensus verification (Signing RBAC) and covert backdoor audits.
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

from biopro_sdk.plugin.manifest_parser import ManifestParser
from biopro_sdk.plugin.security_parser import SecurityParser, SecurityValidationError
from .trust_overrides import LocalTrustRegistry
from .trust_path import TrustChain


logger = logging.getLogger(__name__)

# Hardcoded BioPro Authority Public Key (The Root of Trust)
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
        "project_signature.bin",
        "trust_chain.json",
        "manifest.json",
        "security.json",
        "dev_cert.bin",
    }

    # Files that MUST be signed and are never ignored in standard zones
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

            safe_name = developer_name.lower().replace(" ", "_")
            key_path = roots_dir / f"manual_{safe_name}.pub"

            with open(key_path, "wb") as f:
                f.write(pub_bytes)

            self._load_all_roots()
            logger.info(f"Personally accepted trust for developer: {developer_name}")

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
        debug_log_path = Path.home() / ".biopro" / "trust_debug.log"
        try:
            with open(debug_log_path, "a") as log:
                log.write(f"\nComparing {plugin_path.name}...\n")
        except Exception:
            pass

        try:
            cache = self._get_cache()
            if cache and cache.is_trusted(plugin_path):
                cached_path = cache.data.get(plugin_path.name, {}).get("trust_path")
                return VerificationResult(
                    success=True, trust_level="verified_cache", trust_path=cached_path
                )

            # 1. Authenticity: Double-Signing & RBAC Checks
            auth_result = self._verify_signatures(plugin_path)

            # 2. Integrity & Covert Backdoor Auditing
            integrity_result = self._check_integrity(plugin_path)

            if not auth_result.success or not integrity_result.success:
                hashes = integrity_result.calculated_hashes or {}
                if self.overrides.is_locally_trusted(plugin_path.name, hashes):
                    return VerificationResult(success=True, trust_level="verified_local")

                final_res = auth_result if not auth_result.success else integrity_result
                final_res.calculated_hashes = hashes

                try:
                    with open(debug_log_path, "a") as log:
                        log.write(f"Auth Failed: {final_res.error_message}\n")
                except Exception:
                    pass

                return final_res

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
        """Verifies multi-level trust chains, double-signing, and Signing RBAC."""
        chain_file = plugin_path / "trust_chain.json"
        sig_file = plugin_path / "signature.bin"
        project_sig_file = plugin_path / "project_signature.bin"
        manifest_file = plugin_path / "manifest.json"
        security_file = plugin_path / "security.json"

        if not chain_file.exists():
            return VerificationResult(
                success=False,
                error_message="Security Error: trust_chain.json missing. Plugin is untrusted.",
            )
        if not sig_file.exists() or not security_file.exists():
            return VerificationResult(
                success=False,
                error_message="Security Error: signature.bin or security.json missing.",
            )

        try:
            # 1. Parse & Verify manifest and security ledger Split-Manifest bindings
            parser = ManifestParser()
            with open(manifest_file, encoding="utf-8") as f:
                manifest_data = parser.parse(json.load(f))

            sec_parser = SecurityParser()
            security_data = sec_parser.parse_file(str(security_file))

            sec_parser.verify_manifest_binding(manifest_file, security_data)

            if manifest_data.get("id") != plugin_path.name:
                return VerificationResult(
                    success=False,
                    error_message="Identity Mismatch: Plugin ID does not match folder name.",
                )

            # 2. Load and verify trust links recursively
            chain = TrustChain.from_file(chain_file)
            if not chain or not chain.links:
                return VerificationResult(
                    success=False, error_message="Invalid or empty trust chain."
                )

            verified_dev_keys = {}
            verified_links = []
            
            # Map out recognized and verified links
            for i in range(len(chain.links)):
                link = chain.links[i]
                sub_bytes = bytes.fromhex(link.subject_pub)
                sig_bytes = bytes.fromhex(link.signature)

                has_parent_delegation = False
                if i + 1 < len(chain.links):
                    next_link = chain.links[i + 1]
                    if link.issuer_name == next_link.subject_name:
                        has_parent_delegation = True
                        parent_key = ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(next_link.subject_pub))
                        try:
                            parent_key.verify(sig_bytes, sub_bytes)
                            verified_dev_keys[link.subject_pub] = link.subject_name
                            verified_links.append(
                                {"name": link.subject_name, "status": "verified", "key": link.subject_pub}
                            )
                        except InvalidSignature:
                            return VerificationResult(
                                success=False,
                                error_message=f"Broken Trust Link: {next_link.subject_name} signature for {link.subject_name} is invalid.",
                            )

                if not has_parent_delegation:
                    anchor_found = False
                    for root_key in self.trusted_roots:
                        try:
                            root_key.verify(sig_bytes, sub_bytes)
                            anchor_found = True
                            break
                        except Exception:
                            continue

                    if not anchor_found:
                        # Check direct trust
                        for root_key in self.trusted_roots:
                            try:
                                root_bytes = root_key.public_bytes(
                                    encoding=serialization.Encoding.Raw,
                                    format=serialization.PublicFormat.Raw,
                                )
                                if root_bytes == sub_bytes:
                                    anchor_found = True
                                    break
                            except Exception:
                                continue

                    if anchor_found:
                        verified_dev_keys[link.subject_pub] = link.subject_name
                        verified_links.append(
                            {"name": link.subject_name, "status": "anchor", "key": link.subject_pub}
                        )
                    else:
                        return VerificationResult(
                            success=False,
                            error_message=f"Untrusted Root: {link.subject_name} is not signed by a recognized BioPro Authority.",
                            developer_name=link.subject_name,
                            developer_key=link.subject_pub,
                        )

            # Verify Leaf Developer signature on security.json canonical bytes
            canonical_bytes = json.dumps(security_data, sort_keys=True, separators=(',', ':')).encode('utf-8')
            
            dev_link = chain.links[0]
            if dev_link.subject_pub not in verified_dev_keys:
                return VerificationResult(
                    success=False,
                    error_message=f"Untrusted Root: {dev_link.subject_name} is not signed by a recognized BioPro Authority.",
                    developer_name=dev_link.subject_name,
                    developer_key=dev_link.subject_pub,
                )

            dev_public_key = ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(dev_link.subject_pub))
            dev_sig = sig_file.read_bytes()
            try:
                dev_public_key.verify(dev_sig, canonical_bytes)
            except InvalidSignature:
                return VerificationResult(
                    success=False,
                    error_message="Invalid Plugin Signature (Developer check failed).",
                )

            # 3. Enforce Signing RBAC and Consensus
            required_cosigners = []
            for author in manifest_data.get("authors", []):
                if "sign_code" in author.get("permissions", []):
                    required_cosigners.append(author["name"])

            verified_names = {link.subject_name for link in chain.links if link.subject_pub in verified_dev_keys}
            for cosigner in required_cosigners:
                if cosigner not in verified_names:
                    return VerificationResult(
                        success=False,
                        error_message=f"Co-Author Untrusted: Required co-signer '{cosigner}' has not signed or is untrusted.",
                    )

            # 4. Secondary CI/CD Double-Signature verification (if present)
            if project_sig_file.exists():
                project_link = chain.links[-1]
                project_public_key = ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(project_link.subject_pub))
                project_sig = project_sig_file.read_bytes()
                try:
                    project_public_key.verify(project_sig, canonical_bytes)
                except InvalidSignature:
                    return VerificationResult(
                        success=False,
                        error_message="Invalid Project CI Co-Signature (Project check failed).",
                    )

            full_path = [{"name": "BioPro Core", "status": "root"}] + list(reversed(verified_links))
            return VerificationResult(success=True, trust_path=full_path)

        except Exception as e:
            return VerificationResult(
                success=False, error_message=f"Chain Verification Error: {str(e)}"
            )

    def _check_integrity(self, plugin_path: Path) -> VerificationResult:
        """Verifies every file against the signed security hashes and performs covert backdoor audits."""
        try:
            security_file = plugin_path / "security.json"
            if not security_file.exists():
                return VerificationResult(
                    success=False, error_message="Missing security.json ledger."
                )

            sec_parser = SecurityParser()
            security_data = sec_parser.parse_file(str(security_file))

            signed_hashes = security_data.get("hashes", {})
            raw_exclusions = security_data.get("exclusions", [])
            custom_exclusions = {e.rstrip("/") for e in raw_exclusions}

            active_ignore = self.IGNORE_LIST | custom_exclusions

            found_files = set()
            found_hashes = {}
            integrity_passed = True
            error_msg = ""

            for root, dirs, files in os.walk(plugin_path):
                # Prune standard development and system virtual environments to avoid scanning overhead and false backdoor triggers
                dirs[:] = [d for d in dirs if d not in {".venv", "venv", ".git", ".github", ".vscode", ".idea", ".pytest_cache", "__pycache__"}]
                # Process every single file to run covert backdoor audit checks
                for file in files:
                    rel_path = os.path.relpath(os.path.join(root, file), plugin_path)

                    # Determine if this file falls within any active ignore directories or list
                    is_ignored = False
                    path_parts = rel_path.split(os.sep)
                    for part in path_parts:
                        if part in active_ignore:
                            is_ignored = True
                            break
                    if file in active_ignore:
                        is_ignored = True

                    # 1. Smart Covert Backdoor Audit: Detect unauthorized Python or script files hiding in ignored folders
                    if is_ignored:
                        executable_exts = {".py", ".pyw", ".sh", ".exe", ".bat"}
                        if any(file.endswith(ext) for ext in executable_exts):
                            if file not in ["signature.bin", "project_signature.bin", "dev_cert.bin"]:
                                return VerificationResult(
                                    success=False,
                                    error_message=f"Unauthorized Executable in Excluded Directory: Found '{rel_path}' inside an ignored zone.",
                                    calculated_hashes=found_hashes
                                )
                        continue

                    # Skip cryptographic verification assets
                    if file in ["signature.bin", "project_signature.bin", "trust_chain.json", "manifest.json", "security.json"]:
                        continue

                    found_files.add(rel_path)
                    calc_hash = self._hash_file(os.path.join(root, file))
                    found_hashes[rel_path] = calc_hash

                    # 2. Check for unauthorized executable files in standard plugin directories
                    if rel_path not in signed_hashes:
                        if any(file.endswith(ext) for ext in self.MANDATORY_EXTENSIONS):
                            integrity_passed = False
                            if not error_msg:
                                error_msg = f"Unauthorized File: {rel_path} is not in the signed security hashes."
                        continue

                    # 3. Check file hash match
                    if calc_hash != signed_hashes.get(rel_path):
                        integrity_passed = False
                        if not error_msg:
                            error_msg = f"Integrity Mismatch: {rel_path} has been tampered with."

            # 4. Check for missing files
            for signed_path in signed_hashes:
                if signed_path not in found_files:
                    integrity_passed = False
                    if not error_msg:
                        error_msg = f"Missing File: {signed_path} was signed but is not present on disk."

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

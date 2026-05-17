"""SDK CLI Utilities for BioPro developers.

Handles developer identity setup, plugin signing, and manifest generation.
"""

import argparse
import hashlib
import json
import logging
import os
import sys
from pathlib import Path
from typing import cast

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

logger = logging.getLogger(__name__)


class SDKCLI:
    """CLI handler for BioPro SDK operations."""

    def __init__(self):
        """Initialize the SDK CLI environment, setting default home paths."""
        self.biopro_dir = Path.home() / ".biopro"
        self.trusted_roots_dir = self.biopro_dir / "trusted_roots"

    def init_identity(self, is_project: bool = False) -> bool:
        """Bootstrap a local developer or project identity.

        Args:
            is_project: If True, run in Project (CI) mode — skips local root
                        generation and instead validates that a signing key already
                        exists at ~/.biopro/dev_private_key.pem (injected by CI secrets).

        Returns:
            bool: True if identity is successfully initialized/loaded, False otherwise.
        """
        self.biopro_dir.mkdir(parents=True, exist_ok=True)
        self.trusted_roots_dir.mkdir(parents=True, exist_ok=True)

        if is_project:
            # ── CI / Project Key Mode ──────────────────────────────────────
            print("--- BioPro Project Identity Setup (CI Mode) ---")
            priv_file = self.biopro_dir / "dev_private_key.pem"
            if not priv_file.exists():
                print("ERROR: No project key found at ~/.biopro/dev_private_key.pem")
                print("       Set the BIOPRO_PROJECT_PRIVATE_KEY GitHub Secret and ensure")
                print("       the CI workflow has written it to that path before calling this.")
                return False

            # Derive the public key from the existing private key and write the cert
            try:
                with open(priv_file, "rb") as f:
                    loaded_key = serialization.load_ssh_private_key(f.read(), password=None)
                    dev_private = cast(ed25519.Ed25519PrivateKey, loaded_key)

                dev_pub_raw = dev_private.public_key().public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw,
                )

                # Self-sign cert stub (root signature is in the trust_chain.json)
                cert_file = self.biopro_dir / "dev_cert.bin"
                stub_sig = dev_private.sign(dev_pub_raw)  # self-signed stub for local tooling
                with open(cert_file, "wb") as f:
                    f.write(dev_pub_raw + stub_sig)

                print(f"Project key loaded from:      {priv_file}")
                print(f"Project cert stub written to: {cert_file}")
                print("\nSUCCESS: Project identity ready. Use 'biopro-sdk sign <plugin_dir>' to sign.")
                return True
            except Exception as e:
                print(f"ERROR: Failed to load project key: {e}")
                return False

        # ── Developer / Local Mode ─────────────────────────────────────────
        try:
            print("--- BioPro Developer Identity Setup ---")

            # 1. Generate a local onboarding root (trusts this machine's work locally)
            root_private = ed25519.Ed25519PrivateKey.generate()
            root_public = root_private.public_key()

            root_pub_file = self.trusted_roots_dir / "onboarding_root.pub"
            root_pub_bytes = root_public.public_bytes(
                encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
            )
            with open(root_pub_file, "wb") as f:
                f.write(root_pub_bytes)
            print(f"Created Local Trust Root: {root_pub_file}")

            # 2. Generate developer keypair
            dev_private = ed25519.Ed25519PrivateKey.generate()
            dev_public = dev_private.public_key()

            dev_priv_file = self.biopro_dir / "dev_private_key.pem"
            dev_priv_bytes = dev_private.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.OpenSSH,
                encryption_algorithm=serialization.NoEncryption(),
            )
            with open(dev_priv_file, "wb") as f:
                f.write(dev_priv_bytes)
            print(f"Created Developer Private Key: {dev_priv_file}")

            # 3. Create dev_cert.bin (self-signed by local onboarding root)
            dev_pub_raw = dev_public.public_bytes(
                encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
            )
            signature = root_private.sign(dev_pub_raw)
            cert_file = self.biopro_dir / "dev_cert.bin"
            with open(cert_file, "wb") as f:
                f.write(dev_pub_raw + signature)

            print(f"Created Developer Certificate: {cert_file}")
            print("\nSUCCESS: Your local machine now trusts plugins signed with this identity.")
            print("Use 'biopro-sdk sign <plugin_dir>' to sign your work.")
            print("Run 'biopro-sdk evaluate <plugin_dir>' to validate compliance before a PR.")
            return True
        except Exception as e:
            print(f"ERROR: Failed to initialize developer identity: {e}")
            return False

    def sign_plugin(self, plugin_dir: str) -> bool:
        """Sign a plugin using the local developer identity.

        Returns:
            bool: True if plugin is successfully signed, False otherwise.
        """
        from biopro_sdk.host import TrustManager

        p_dir = Path(plugin_dir)
        cert_file = self.biopro_dir / "dev_cert.bin"
        priv_file = self.biopro_dir / "dev_private_key.pem"
        manifest_file = p_dir / "manifest.json"

        # Check for Identity first
        if not cert_file.exists() or not priv_file.exists():
            print("ERROR: Developer identity not found. Run 'biopro-sdk init-identity' first.")
            return False

        # Check for Target Manifest
        if not manifest_file.exists():
            print(f"ERROR: No manifest.json found in '{p_dir}'. Are you in the right plugin folder?")
            return False

        try:
            # 1. Load Keys
            with open(priv_file, "rb") as f:
                loaded_key = serialization.load_ssh_private_key(f.read(), password=None)
                dev_private = cast(ed25519.Ed25519PrivateKey, loaded_key)

            with open(manifest_file) as f:
                manifest = json.load(f)

            # 2. Calculate Integrity Hashes (Merkle-style)
            # Prune ignored directories to avoid over-inclusion (e.g. __pycache__)
            # We synchronize with the main TrustManager list
            ignore_list = TrustManager.IGNORE_LIST.union({"signature.bin", "dev_cert.bin", "manifest.json", ".venv"})
            hashes = {}

            for root, dirs, files in os.walk(p_dir):
                # Prune directories in-place to skip them entirely
                dirs[:] = [d for d in dirs if d not in ignore_list]

                for file in files:
                    if file in ignore_list:
                        continue
                    rel_path = os.path.relpath(os.path.join(root, file), p_dir)

                    hasher = hashlib.sha256()
                    with open(os.path.join(root, file), "rb") as f:
                        for chunk in iter(lambda: f.read(4096), b""):
                            hasher.update(chunk)
                    hashes[rel_path] = hasher.hexdigest()

            # 3. Update Manifest to V2 Schema
            if "integrity" not in manifest:
                manifest["integrity"] = {}
            manifest["integrity"]["hashes"] = hashes

            # Auto-migrate to V2 if needed
            manifest["manifest_version"] = 2
            if "signed_by" not in manifest:
                manifest["signed_by"] = {"entity_type": "developer", "entity_id": "local_dev"}
            if "authors" not in manifest and "author" in manifest:
                manifest["authors"] = [{"name": manifest.pop("author")}]
            elif "authors" not in manifest:
                manifest["authors"] = [{"name": "Local Developer"}]

            with open(manifest_file, "w") as f:
                json.dump(manifest, f, indent=4)

            # 4. Sign the Canonicalized Manifest
            manifest_bytes = json.dumps(manifest, sort_keys=True).encode()
            signature = dev_private.sign(manifest_bytes)

            # 5. Write artifacts to plugin folder
            with open(p_dir / "signature.bin", "wb") as f:
                f.write(signature)

            import shutil

            shutil.copy(cert_file, p_dir / "dev_cert.bin")

            print(f"Successfully signed plugin: {manifest.get('id', p_dir.name)}")
            return True
        except Exception as e:
            print(f"ERROR: Failed to sign plugin: {e}")
            return False

    def sign_all(self, parent_dir: str) -> bool:
        """Batch sign all valid plugins in a parent directory.

        Returns:
            bool: True if parent directory is scanned, regardless of individual plugin success.
                  False if parent directory does not exist or is invalid.
        """
        p_dir = Path(parent_dir)
        if not p_dir.is_dir():
            print(f"ERROR: '{p_dir}' is not a directory.")
            return False

        print(f"--- Batch Signing: {p_dir} ---")
        signed_count = 0
        total_plugins = 0
        for sub in p_dir.iterdir():
            if sub.is_dir() and (sub / "manifest.json").exists():
                total_plugins += 1
                print(f"Signing {sub.name}...")
                try:
                    if self.sign_plugin(str(sub)):
                        signed_count += 1
                except Exception as e:
                    print(f"  FAILED: {e}")

        print(f"--- Batch Complete: Signed {signed_count} out of {total_plugins} modules ---")
        return True

    def generate_sbom(self, output_format: str) -> bool:
        """Generates and prints the SBOM in the specified format.

        Returns:
            bool: True if generator is successfully called, False if not inside BioPro core.
        """
        try:
            # Use dynamic import to avoid squiggles in SDK-only environments
            import importlib

            biopro_core_sbom = importlib.import_module("biopro.core.sbom")
            generator = biopro_core_sbom.SBOMGenerator()

            if output_format == "--json":
                print(generator.to_json())
            else:
                print(generator.to_markdown())
            return True
        except ImportError:
            print("ERROR: SBOM generation is only supported when running inside the BioPro main application.")
            return False

    def evaluate_plugin(self, plugin_dir: str) -> bool:
        """Evaluate a plugin directory against BioPro QA, structure, and security standards.

        Returns:
            bool: True if the plugin evaluation passes with 0 critical failures, False otherwise.
        """
        p_dir = Path(plugin_dir)
        if not p_dir.is_dir():
            print(f"ERROR: '{p_dir}' is not a valid directory.")
            return False

        print("\n==========================================")
        print(f"🔍 BioPro SDK Plugin Evaluation: {p_dir.name}")
        print("==========================================\n")

        passed_checks = 0
        failed_checks = 0
        warnings = 0

        # --- 1. MANIFEST CHECK ---
        manifest_path = p_dir / "manifest.json"
        print("[1/3] Manifest Audit:")
        if not manifest_path.exists():
            print("  ❌ FAIL: manifest.json is missing.")
            failed_checks += 1
            manifest = None
        else:
            try:
                with open(manifest_path) as f:
                    manifest = json.load(f)
                print("  ✅ PASS: manifest.json is valid JSON.")
                passed_checks += 1

                # Check required fields for V2 schema
                required_keys = ["id", "name", "version", "description", "authors", "signed_by"]
                missing_keys = [k for k in required_keys if k not in manifest]
                if missing_keys:
                    print(f"  ❌ FAIL: Missing required V2 manifest keys: {missing_keys}")
                    failed_checks += 1
                elif manifest.get("manifest_version") != 2:
                    print("  ❌ FAIL: manifest_version must be exactly 2.")
                    failed_checks += 1
                else:
                    print("  ✅ PASS: All required V2 manifest keys are present.")
                    passed_checks += 1

                # Validate ID formatting (lowercase, snake_case)
                p_id = manifest.get("id", "")
                if not p_id.islower() or not p_id.replace("_", "").isalnum():
                    print(f"  ⚠️ WARN: Plugin ID '{p_id}' should be lowercase snake_case (e.g. 'my_plugin').")
                    warnings += 1
                else:
                    print(f"  ✅ PASS: Plugin ID '{p_id}' conforms to snake_case naming standards.")
                    passed_checks += 1

                # Validate Dependencies block if present
                deps = manifest.get("dependencies")
                if deps is not None:
                    if not isinstance(deps, dict):
                        print("  ❌ FAIL: 'dependencies' key in manifest.json must be a dictionary.")
                        failed_checks += 1
                    else:
                        print("  📦 Auditing Plugin Dependencies:")
                        all_pinned = True
                        for dep_name, dep_ver in deps.items():
                            if not isinstance(dep_ver, str):
                                print(f"    ❌ FAIL: Dependency version for '{dep_name}' must be a string.")
                                all_pinned = False
                                failed_checks += 1
                            elif any(op in dep_ver for op in [">", "<", "=", "~", "^", "*"]):
                                print(
                                    f"    ⚠️ WARN: Dependency '{dep_name}': '{dep_ver}' is not pinned. Recommend exact pinning for maintenance."
                                )
                                all_pinned = False
                                warnings += 1
                            else:
                                print(f"    ✅ PASS: '{dep_name}' is pinned to version '{dep_ver}'.")
                                passed_checks += 1
                        if all_pinned and deps:
                            print("  ✅ PASS: All declared dependencies are securely pinned.")
                            passed_checks += 1

            except Exception as e:
                print(f"  ❌ FAIL: Failed to parse manifest.json: {e}")
                failed_checks += 1
                manifest = None

        print()

        # --- 2. CODE & STRUCTURE AUDIT ---
        print("[2/3] Structure & SDK Compliance:")
        py_files = list(p_dir.glob("**/*.py"))
        if not py_files:
            print("  ❌ FAIL: No Python (.py) source files found in plugin.")
            failed_checks += 1
        else:
            print(f"  ✅ PASS: Found {len(py_files)} Python source files.")
            passed_checks += 1

            # Check for AnalysisBase subclassing
            has_analysis_base = False
            for pf in py_files:
                try:
                    content = pf.read_text(errors="ignore")
                    if "AnalysisBase" in content:
                        has_analysis_base = True
                        break
                except Exception:
                    pass

            if has_analysis_base:
                print("  ✅ PASS: Integrates correctly with BioPro SDK classes (AnalysisBase).")
                passed_checks += 1
            else:
                print(
                    "  ⚠️ WARN: No references to 'AnalysisBase' found. Ensure your plugin implements the core analysis interface."
                )
                warnings += 1

        print()

        # --- 3. TRUST & SIGNING AUDIT ---
        print("[3/3] Security & Trust Audit:")
        sig_file = p_dir / "signature.bin"
        cert_file = p_dir / "dev_cert.bin"

        if not sig_file.exists() or not cert_file.exists():
            print("  ⚠️ WARN: Plugin is currently unsigned (missing signature.bin or dev_cert.bin).")
            print("    Run 'biopro-sdk sign <plugin_dir>' to secure your plugin.")
            warnings += 1
        else:
            print("  ✅ PASS: Cryptographic signatures are present.")
            passed_checks += 1

            # Check integrity hashes
            if manifest and "integrity" in manifest and "hashes" in manifest["integrity"]:
                print("  ✅ PASS: Integrity hash block exists in manifest.")
                passed_checks += 1
            else:
                print("  ❌ FAIL: Cryptographic signatures present, but manifest integrity block is missing.")
                failed_checks += 1

        print("\n==========================================")
        print("Evaluation Complete:")
        print(f"  Passed: {passed_checks} | Failed: {failed_checks} | Warnings: {warnings}")
        print("==========================================")
        if failed_checks > 0:
            print("❌ STATUS: RED (Plugin has critical compliance issues. Please resolve before releasing.)\n")
            return False
        elif warnings > 0:
            print(
                "⚠️ STATUS: YELLOW (Plugin is functional but has warnings. Recommended to address before releasing.)\n"
            )
            return True
        else:
            print("✅ STATUS: GREEN (Plugin is fully compliant and ready for release!)\n")
            return True


def main():
    """Main CLI execution entry point mapping command subparsers to CLI actions."""
    # ── Legacy Compatibility Shim ───────────────────────────────────
    # If the user types: 'biopro-sdk sdk init-identity', we transparently
    # pop the 'sdk' word and warn the user.
    args_list = sys.argv[1:]
    if args_list and args_list[0] == "sdk":
        print("⚠️  DEPRECATION WARNING: Running with 'sdk' prefix is deprecated.", file=sys.stderr)
        print("   Use 'biopro-sdk <command>' directly instead.\n", file=sys.stderr)
        args_list.pop(0)

    # ── Modern Subparser Definition ──────────────────────────────────
    parser = argparse.ArgumentParser(
        prog="biopro-sdk",
        description="Software Development Kit and CLI for BioPro desktop plugins.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="SDK Commands")

    # Command: init-identity
    init_parser = subparsers.add_parser("init-identity", help="Bootstrap a local developer or project identity.")
    init_parser.add_argument(
        "--project", action="store_true", help="Run in CI/Project mode (skips local root cert gen)."
    )

    # Command: sign
    sign_parser = subparsers.add_parser("sign", help="Sign a plugin using the local developer identity.")
    sign_parser.add_argument("plugin_dir", type=str, help="Path to the plugin directory.")

    # Command: sign-all
    sign_all_parser = subparsers.add_parser("sign-all", help="Batch sign all valid plugins in a parent directory.")
    sign_all_parser.add_argument("parent_dir", type=str, help="Path to the parent directory containing plugins.")

    # Command: sbom
    sbom_parser = subparsers.add_parser("sbom", help="Generate and print the SBOM for dependency tracking.")
    sbom_group = sbom_parser.add_mutually_exclusive_group()
    sbom_group.add_argument("--json", action="store_true", help="Output SBOM in JSON format.")
    sbom_group.add_argument("--markdown", action="store_true", help="Output SBOM in Markdown format (default).")

    # Command: evaluate
    eval_parser = subparsers.add_parser(
        "evaluate", help="Evaluate a plugin directory against BioPro QA, structure, and security standards."
    )
    eval_parser.add_argument("plugin_dir", type=str, help="Path to the plugin directory.")

    # Parse arguments
    args = parser.parse_args(args_list)

    # ── Command Routing & Exit Code Verification ────────────────────
    cli = SDKCLI()
    exit_code = 0

    try:
        if args.command == "init-identity":
            success = cli.init_identity(is_project=args.project)
            if not success:
                exit_code = 1
        elif args.command == "sign":
            success = cli.sign_plugin(args.plugin_dir)
            if not success:
                exit_code = 1
        elif args.command == "sign-all":
            success = cli.sign_all(args.parent_dir)
            if not success:
                exit_code = 1
        elif args.command == "sbom":
            output_format = "--json" if args.json else "--markdown"
            success = cli.generate_sbom(output_format)
            if not success:
                exit_code = 1
        elif args.command == "evaluate":
            success = cli.evaluate_plugin(args.plugin_dir)
            if not success:
                exit_code = 1
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}", file=sys.stderr)
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()

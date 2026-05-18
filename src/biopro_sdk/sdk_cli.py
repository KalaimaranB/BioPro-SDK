"""SDK CLI Utilities for BioPro developers.

Handles developer identity setup, plugin signing, manifest generation, and compliance evaluation.
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from biopro_sdk.host.sign_plugin import PluginSigner


class SDKCLI:
    """CLI handler for BioPro SDK operations."""

    def __init__(self):
        self.signer = PluginSigner()

    def init_identity(self) -> bool:
        """Bootstrap a local developer or project identity."""
        try:
            self.signer.init_identity()
            print("\nSUCCESS: Developer identity initialized.")
            print("Use 'biopro-sdk sign <plugin_dir>' to sign your work.")
            return True
        except Exception as e:
            print(f"ERROR: Failed to initialize developer identity: {e}")
            return False

    def sign_plugin(self, plugin_dir: str) -> bool:
        """Sign a plugin using the local developer identity."""
        try:
            self.signer.sign_plugin(Path(plugin_dir))
            return True
        except Exception as e:
            print(f"ERROR: Failed to sign plugin: {e}")
            return False

    def project_sign_plugin(self, plugin_dir: str, project_private_key_pem: bytes) -> bool:
        """Co-sign a plugin's security ledger as the institutional Project CI runner."""
        try:
            self.signer.project_sign_plugin(Path(plugin_dir), project_private_key_pem)
            return True
        except Exception as e:
            print(f"ERROR: Project signing failed: {e}")
            return False

    def print_registry_entry(self) -> bool:
        """Export the JSON snippet for the central registry."""
        try:
            self.signer.print_registry_entry()
            return True
        except Exception as e:
            print(f"ERROR: Failed to fetch registry entry: {e}")
            return False

    def generate_sbom(self, output_format: str) -> bool:
        """Generates and prints the SBOM in the specified format."""
        try:
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

    def create_manifest(self, plugin_dir: str, id_arg: str | None = None, name_arg: str | None = None, version_arg: str | None = None, description_arg: str | None = None) -> bool:
        """Interactive/Scriptable bootstrapping for a V2 manifest.json."""
        p_dir = Path(plugin_dir)
        p_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = p_dir / "manifest.json"
        
        if manifest_path.exists():
            print(f"⚠️  manifest.json already exists at {manifest_path}. Aborting to prevent overwrite.")
            return False

        # Gather inputs or default
        p_id = id_arg or p_dir.name.lower().replace("-", "_").replace(" ", "_")
        p_name = name_arg or p_dir.name.title()
        p_version = version_arg or "1.0.0"
        p_description = description_arg or f"A high-performance BioPro data plugin analyzing {p_name}."

        manifest_data = {
            "manifest_version": 2,
            "id": p_id,
            "name": p_name,
            "version": p_version,
            "description": p_description,
            "authors": [
                {
                    "name": "Developer Name",
                    "role": "Developer",
                    "permissions": ["read_workspace", "write_assets"]
                }
            ],
            "custom_exclusions": []
        }

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=4)

        print(f"🎉 Successfully created V2 manifest at: {manifest_path}")
        print(json.dumps(manifest_data, indent=4))
        return True

    def bootstrap_plugin(self, plugin_dir: str) -> bool:
        """Create a complete boilerplate plugin skeleton with documentation and source template."""
        p_dir = Path(plugin_dir)
        p_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Create subfolders
        (p_dir / "src").mkdir(parents=True, exist_ok=True)
        (p_dir / "docs").mkdir(parents=True, exist_ok=True)
        
        # 2. Create manifest.json
        self.create_manifest(
            str(p_dir),
            id_arg=p_dir.name.lower().replace("-", "_").replace(" ", "_"),
            name_arg=p_dir.name.title(),
        )

        # 3. Create a clean __init__.py boilerplate implementing AnalysisBase
        init_file = p_dir / "src" / "__init__.py"
        init_content = """from biopro_sdk.plugin import AnalysisBase

class CustomAnalysisPlugin(AnalysisBase):
    \"\"\"Boilerplate analysis plugin demonstrating safe SDK interaction.\"\"\"

    def execute(self, workspace_context):
        \"\"\"Executes primary data processing workflow.

        Args:
            workspace_context: The host application environment and loaded data assets.
        \"\"\"
        self.logger.info("Executing custom boilerplate analysis workflow...")
        
        # Access workspace variables
        assets = workspace_context.get_assets()
        self.logger.info(f"Loaded {len(assets)} raw assets in current workspace.")
        
        # Complete work and publish progress
        self.publish_progress(100, "Boilerplate execution completed.")
        return {"status": "success", "processed_assets": len(assets)}
"""
        with open(init_file, "w", encoding="utf-8") as f:
            f.write(init_content)

        # 4. Create a README.md inside docs/
        readme_file = p_dir / "docs" / "01_getting_started.md"
        readme_content = f"""# Getting Started with {p_dir.name.title()}

Welcome to your freshly bootstrapped BioPro plugin!

## Architecture
This plugin is developed using the BioPro-SDK. It exposes a single data analysis pipeline extending `AnalysisBase`.

## Getting Started
1. Edit `src/__init__.py` to implement your custom data algorithms.
2. Maintain your documentation under the `docs/` folder for local integration with the BioPro Help Center.
3. Sign your plugin before loading using:
   ```bash
   biopro-sdk sign .
   ```
"""
        with open(readme_file, "w", encoding="utf-8") as f:
            f.write(readme_content)

        print(f"\n🚀 Successfully bootstrapped boilerplate plugin at: {p_dir}")
        print("Structure Created:")
        print("  ├── manifest.json")
        print("  ├── src/")
        print("  │   └── __init__.py  (Core plugin logic)")
        print("  └── docs/")
        print("      └── 01_getting_started.md (Documentation)")
        print("\nGet started by running:")
        print(f"  cd \"{p_dir}\" && biopro-sdk init-identity && biopro-sdk sign .")
        return True

    def evaluate_plugin(self, plugin_dir: str) -> bool:
        """Evaluate a plugin directory against BioPro QA, structure, and security standards."""
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
                required_keys = ["id", "name", "version", "description", "authors"]
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
                print("  ⚠️ WARN: No references to 'AnalysisBase' found. Ensure your plugin implements the core analysis interface.")
                warnings += 1

        print()

        # --- 3. TRUST & SIGNING AUDIT ---
        print("[3/3] Security & Trust Audit:")
        sig_file = p_dir / "signature.bin"
        security_file = p_dir / "security.json"
        trust_file = p_dir / "trust_chain.json"

        if not sig_file.exists() or not security_file.exists() or not trust_file.exists():
            print("  ⚠️ WARN: Plugin is currently unsigned or missing cryptography files.")
            print("    Run 'biopro-sdk sign <plugin_dir>' to secure your plugin.")
            warnings += 1
        else:
            print("  ✅ PASS: Cryptographic signatures and split-manifest ledger are present.")
            passed_checks += 1

        # --- 4. DEPENDENCY AUDIT ---
        dependencies = manifest.get("dependencies") if manifest else None
        if dependencies:
            print()
            print("Auditing Plugin Dependencies:")
            has_unpinned = False
            for dep, ver in dependencies.items():
                if ver.startswith(">") or ver.startswith("<") or ver.startswith("^") or ver.startswith("~"):
                    print(f"  ❌ FAIL: Dependency '{dep}' is not pinned. Recommend exact pinning (e.g., '{dep}': '1.0.0').")
                    has_unpinned = True
                    failed_checks += 1
                else:
                    print(f"  ✅ PASS: Dependency '{dep}' is pinned to version '{ver}'.")
                    passed_checks += 1
            if not has_unpinned:
                print("  ✅ PASS: All declared dependencies are securely pinned.")
                passed_checks += 1

        print("\n==========================================")
        print("Evaluation Complete:")
        print(f"  Passed: {passed_checks} | Failed: {failed_checks} | Warnings: {warnings}")
        print("==========================================")
        if failed_checks > 0:
            print("❌ STATUS: RED (Plugin has critical compliance issues. Please resolve before releasing.)\n")
            return False
        elif warnings > 0:
            print("⚠️ STATUS: YELLOW (Plugin is functional but has warnings. Recommended to address before releasing.)\n")
            return True
        else:
            print("✅ STATUS: GREEN (Plugin is fully compliant and ready for release!)\n")
            return True


def main():
    """Main CLI execution entry point mapping command subparsers to CLI actions."""
    # ── Legacy Compatibility Shim ───────────────────────────────────
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
    subparsers.add_parser("init-identity", help="Bootstrap a local developer or project identity.")

    # Command: sign
    sign_parser = subparsers.add_parser("sign", help="Sign a plugin using the local developer identity.")
    sign_parser.add_argument("plugin_dir", type=str, help="Path to the plugin directory.")

    # Command: project-sign
    proj_parser = subparsers.add_parser("project-sign", help="Co-sign a plugin's security ledger as the Project CI runner.")
    proj_parser.add_argument("plugin_dir", type=str, help="Path to the plugin directory.")
    proj_parser.add_argument(
        "--key-env",
        default="BIOPRO_PROJECT_PRIVATE_KEY",
        help="Environment variable containing Project private key PEM (default: BIOPRO_PROJECT_PRIVATE_KEY)",
    )

    # Command: registry
    subparsers.add_parser("registry", help="Export the JSON snippet for the central registry.")

    # Command: create-manifest
    manifest_parser = subparsers.add_parser("create-manifest", help="Bootstraps a fresh manifest.json for a plugin.")
    manifest_parser.add_argument("plugin_dir", type=str, help="Path to the plugin directory.")
    manifest_parser.add_argument("--id", type=str, help="Custom plugin ID (snake_case).")
    manifest_parser.add_argument("--name", type=str, help="Custom plugin display name.")
    manifest_parser.add_argument("--version", type=str, help="Custom plugin version.")
    manifest_parser.add_argument("--desc", type=str, help="Custom plugin description.")

    # Command: bootstrap
    boot_parser = subparsers.add_parser("bootstrap", help="Create a boilerplate plugin skeleton.")
    boot_parser.add_argument("plugin_dir", type=str, help="Path to the plugin directory.")

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
            success = cli.init_identity()
            if not success:
                exit_code = 1
        elif args.command == "sign":
            success = cli.sign_plugin(args.plugin_dir)
            if not success:
                exit_code = 1
        elif args.command == "project-sign":
            pem_str = os.environ.get(args.key_env)
            if not pem_str:
                print(f"ERROR: Project signing key not found in environment: {args.key_env}", file=sys.stderr)
                exit_code = 1
            else:
                success = cli.project_sign_plugin(args.plugin_dir, pem_str.encode("utf-8"))
                if not success:
                    exit_code = 1
        elif args.command == "registry":
            success = cli.print_registry_entry()
            if not success:
                exit_code = 1
        elif args.command == "create-manifest":
            success = cli.create_manifest(
                args.plugin_dir,
                id_arg=args.id,
                name_arg=args.name,
                version_arg=args.version,
                description_arg=args.desc
            )
            if not success:
                exit_code = 1
        elif args.command == "bootstrap":
            success = cli.bootstrap_plugin(args.plugin_dir)
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

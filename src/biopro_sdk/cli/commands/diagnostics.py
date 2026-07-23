def setup_diagnostics_parser(subparsers):
    # Command: sbom
    sbom_parser = subparsers.add_parser("sbom", help="Generates and prints the SBOM in the specified format.")
    sbom_parser.add_argument(
        "--format", type=str, choices=["--json", "--markdown"], default="--markdown", help="Output format"
    )
    sbom_parser.set_defaults(func=generate_sbom)

    # Command: evaluate
    eval_parser = subparsers.add_parser("evaluate", help="Perform comprehensive CLI evaluation of a plugin.")
    eval_parser.add_argument("plugin_dir", type=str, help="Path to the plugin directory.")
    eval_parser.set_defaults(func=evaluate_plugin)

    # Command: doctor
    doctor_parser = subparsers.add_parser("doctor", help="Evaluate a plugin against new SDK architecture.")
    doctor_parser.add_argument("plugin_dir", type=str, help="Path to the plugin directory.")
    doctor_parser.set_defaults(func=doctor_plugin)


def generate_sbom(args) -> bool:
    """Generates and prints the SBOM in the specified format."""
    try:
        import importlib

        biopro_core_sbom = importlib.import_module("biopro.core.sbom")
        generator = biopro_core_sbom.SBOMGenerator()

        if args.format == "--json":
            print(generator.to_json())
        else:
            print(generator.to_markdown())
        return True
    except ImportError:
        print("ERROR: SBOM generation is only supported when running inside the BioPro main application.")
        return False


def evaluate_plugin(args) -> bool:
    """Perform comprehensive CLI evaluation of a plugin."""
    import logging
    import sys
    from pathlib import Path

    from PyQt6.QtWidgets import QApplication

    from biopro_sdk.plugin.manifest_parser import ManifestParser

    print("Running Plugin Diagnostics Evaluator (evaluate)...")
    _app = QApplication(sys.argv)
    logging.basicConfig(level=logging.INFO)

    try:
        parser = ManifestParser()
        manifest = parser.parse_file(str(Path(args.plugin_dir) / "pyproject.toml"))
        print(f"Manifest parsed successfully: {manifest.get('id')} v{manifest.get('version')}")
        return True
    except Exception as e:
        print(f"Evaluation failed: {e}")
        return False


def doctor_plugin(args) -> bool:
    """Evaluate a plugin against new SDK architecture (plugin.toml, strict imports)."""
    print(f"Running Plugin Conformance Evaluator (doctor) on {args.plugin_dir}...")
    print("Note: Scaffolded for Phase 1. Full static/runtime checks to be implemented.")
    return True

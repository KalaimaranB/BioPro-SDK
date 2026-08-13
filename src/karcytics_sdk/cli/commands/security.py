from pathlib import Path

from karcytics_sdk.host.sign_plugin import PluginSigner


def setup_security_parser(subparsers):
    # Command: init-identity
    init_parser = subparsers.add_parser("init-identity", help="Bootstrap a local developer or project identity.")
    init_parser.add_argument("--out", type=str, help="Custom directory to output keys (optional)")
    init_parser.set_defaults(func=init_identity)

    # Command: sign
    sign_parser = subparsers.add_parser("sign", help="Sign a plugin using the local developer identity.")
    sign_parser.add_argument("plugin_dir", type=str, help="Path to the plugin directory.")
    sign_parser.set_defaults(func=sign_plugin)

    # Command: project-sign
    proj_parser = subparsers.add_parser(
        "project-sign", help="Co-sign a plugin's security ledger as the Project CI runner."
    )
    proj_parser.add_argument("plugin_dir", type=str, help="Path to the plugin directory.")
    proj_parser.add_argument(
        "--key-env",
        default="KARCYTICS_PROJECT_PRIVATE_KEY",
        help="Environment variable containing Project private key PEM (default: KARCYTICS_PROJECT_PRIVATE_KEY)",
    )
    proj_parser.add_argument(
        "--delegation",
        type=str,
        help="Path to runner delegation file to append to the trust chain (optional)",
    )
    proj_parser.set_defaults(func=project_sign_plugin)

    # Command: registry
    registry_parser = subparsers.add_parser("registry", help="Export the JSON snippet for the central registry.")
    registry_parser.set_defaults(func=print_registry_entry)

    # Command: delegate
    delegate_parser = subparsers.add_parser("delegate", help="Delegate trust to another developer's public key.")
    delegate_parser.add_argument("pub_path", type=str, help="Path to researcher's public.pub")
    delegate_parser.add_argument("name", type=str, help="Researcher's name")
    delegate_parser.add_argument("--authority", type=str, help="Path to authority private key (optional)")
    delegate_parser.set_defaults(func=delegate_identity)


def init_identity(args) -> bool:
    """Bootstrap a local developer or project identity."""
    out_path = Path(args.out) if hasattr(args, "out") and args.out else None
    signer = PluginSigner(out_path)
    try:
        signer.init_identity()
        print("\nSUCCESS: Developer identity initialized.")
        print("Use 'karcytics-sdk sign <plugin_dir>' to sign your work.")
        return True
    except Exception as e:
        print(f"ERROR: Failed to initialize developer identity: {e}")
        return False


def sign_plugin(args) -> bool:
    """Sign a plugin using the local developer identity."""
    signer = PluginSigner()
    try:
        signer.sign_plugin(Path(args.plugin_dir))
        return True
    except Exception as e:
        print(f"ERROR: Failed to sign plugin: {e}")
        return False


def project_sign_plugin(args) -> bool:
    """Co-sign a plugin's security ledger as the institutional Project CI runner."""
    import os

    signer = PluginSigner()
    pem_data = os.environ.get(args.key_env)
    if not pem_data:
        print(f"ERROR: Project private key environment variable {args.key_env} is not set.")
        return False
    try:
        delegation_path = Path(args.delegation) if hasattr(args, "delegation") and args.delegation else None
        signer.project_sign_plugin(Path(args.plugin_dir), pem_data.encode(), delegation_path)
        return True
    except Exception as e:
        print(f"ERROR: Project signing failed: {e}")
        return False


def delegate_identity(args) -> bool:
    """Delegate identity to another researcher's public key."""
    signer = PluginSigner()
    try:
        auth_path = Path(args.authority) if args.authority else None
        signer.delegate_identity(Path(args.pub_path), args.name, auth_path)
        return True
    except Exception as e:
        print(f"ERROR: Delegation failed: {e}")
        return False


def print_registry_entry(args) -> bool:
    """Export the JSON snippet for the central registry."""
    signer = PluginSigner()
    try:
        signer.print_registry_entry()
        return True
    except Exception as e:
        print(f"ERROR: Failed to fetch registry entry: {e}")
        return False

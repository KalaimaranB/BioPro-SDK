"""DEPRECATED: SDK CLI Utilities for Karcytics developers.

This module is deprecated. Please use the modular `karcytics_sdk.cli` package instead.
"""

import warnings

from karcytics_sdk.cli.commands import diagnostics, migrate, scaffold, security
from karcytics_sdk.cli.main import main

warnings.warn(
    "karcytics_sdk.sdk_cli is deprecated and will be removed in a future release. Please use karcytics_sdk.cli instead.",
    DeprecationWarning,
    stacklevel=2,
)


class SDKCLI:
    """Deprecated CLI handler for Karcytics SDK operations."""

    def __init__(self):
        from karcytics_sdk.host.sign_plugin import PluginSigner

        self.signer = PluginSigner()

    def init_identity(self) -> bool:
        return security.init_identity(None)

    def sign_plugin(self, plugin_dir: str) -> bool:
        import argparse

        args = argparse.Namespace()
        args.plugin_dir = plugin_dir
        return security.sign_plugin(args)

    def project_sign_plugin(self, plugin_dir: str, project_private_key_pem: bytes) -> bool:
        import os

        os.environ["__TMP_KEY"] = project_private_key_pem.decode()

        import argparse

        args = argparse.Namespace()
        args.plugin_dir = plugin_dir
        args.key_env = "__TMP_KEY"
        success = security.project_sign_plugin(args)
        del os.environ["__TMP_KEY"]
        return success

    def delegate_identity(self, pub_path: str, name: str, authority: str | None = None) -> bool:
        import argparse

        args = argparse.Namespace()
        args.pub_path = pub_path
        args.name = name
        args.authority = authority
        return security.delegate_identity(args)

    def print_registry_entry(self) -> bool:
        return security.print_registry_entry(None)

    def generate_sbom(self, output_format: str) -> bool:
        import argparse

        args = argparse.Namespace()
        args.format = output_format
        return diagnostics.generate_sbom(args)

    def evaluate_plugin(self, plugin_dir: str) -> bool:
        import argparse

        args = argparse.Namespace()
        args.plugin_dir = plugin_dir
        return diagnostics.evaluate_plugin(args)

    def create_manifest(
        self, plugin_dir: str, id_arg=None, name_arg=None, version_arg=None, description_arg=None
    ) -> bool:
        import argparse

        args = argparse.Namespace()
        args.plugin_dir = plugin_dir
        args.id = id_arg
        args.name = name_arg
        args.version = version_arg
        args.desc = description_arg
        return scaffold.create_manifest(args)

    def bootstrap_plugin(self, plugin_dir: str) -> bool:
        import argparse

        args = argparse.Namespace()
        args.plugin_dir = plugin_dir
        return scaffold.bootstrap_plugin(args)

    def doctor_plugin(self, plugin_dir: str) -> bool:
        import argparse

        args = argparse.Namespace()
        args.plugin_dir = plugin_dir
        return diagnostics.doctor_plugin(args)

    def init_plugin(self, plugin_name: str) -> bool:
        import argparse

        args = argparse.Namespace()
        args.plugin_name = plugin_name
        return scaffold.init_plugin(args)

    def migrate_plugin(self, plugin_dir: str) -> bool:
        import argparse

        args = argparse.Namespace()
        args.plugin_dir = plugin_dir
        return migrate.migrate_plugin(args)


if __name__ == "__main__":
    main()

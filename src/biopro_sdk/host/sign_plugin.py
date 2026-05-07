"""BioPro Plugin Signing Utility.

Calculates Merkle-Integrity hashes for a plugin directory and generates
an Ed25519 signature for the manifest.

Usage:
    python sign_plugin.py <plugin_dir> <dev_private_key_file> <dev_cert_file>
"""

import hashlib
import json
import os
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization

# Implicit Ignore List (Same as TrustManager)
IGNORE_LIST = {
    ".DS_Store",
    "Thumbs.db",
    "__pycache__",
    ".git",
    ".github",
    ".vscode",
    ".idea",
    ".pytest_cache",
}


def sign_plugin(plugin_dir: Path, private_key_path: Path, cert_path: Path):
    """Generates the signed manifest and signature artifacts."""
    print(f"Signing plugin: {plugin_dir}")

    # 1. Load Private Key
    with open(private_key_path, "rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)

    # 2. Load Manifest
    manifest_path = plugin_dir / "manifest.json"
    with open(manifest_path) as f:
        manifest = json.load(f)

    # 3. Calculate Merkle-Integrity
    hashes = {}
    for root, dirs, files in os.walk(plugin_dir):
        # Apply ignore list to directories
        dirs[:] = [d for d in dirs if d not in IGNORE_LIST]

        for file in sorted(files):
            if file in IGNORE_LIST or file in ["signature.bin", "dev_cert.bin", "manifest.json"]:
                continue

            rel_path = os.path.relpath(os.path.join(root, file), plugin_dir)
            hasher = hashlib.sha256()
            with open(os.path.join(root, file), "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            hashes[rel_path] = hasher.hexdigest()
            print(f"  + Hashed: {rel_path}")

    # 4. Update Manifest with Integrity data
    manifest["integrity"] = {"hashes": hashes, "dev_id": manifest.get("author", "unknown_dev")}

    # Save updated manifest (canonicalized)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=4)

    # 5. Generate Signature
    # We sign the JSON serialized with sorted keys to ensure determinism
    manifest_bytes = json.dumps(manifest, sort_keys=True).encode()
    signature = private_key.sign(manifest_bytes)

    with open(plugin_dir / "signature.bin", "wb") as f:
        f.write(signature)

    # 6. Embed Developer Certificate
    # We copy the provided cert content to dev_cert.bin in the plugin folder
    import shutil

    shutil.copy(cert_path, plugin_dir / "dev_cert.bin")

    print("\nSuccessfully signed plugin.")
    print(f"Artifacts created: {plugin_dir}/signature.bin, {plugin_dir}/dev_cert.bin")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python sign_plugin.py <plugin_dir> <private_key_pem> <dev_cert_bin>")
        sys.exit(1)

    sign_plugin(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))

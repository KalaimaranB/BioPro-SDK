# 🏁 Getting Started with BioPro SDK

This step-by-step tutorial walks you through setting up your local environment, generating a cryptographically secure Developer Identity, signing a template plugin, and simulating its execution on the host application.

---

## 🛠️ Step 1: Environment Setup

BioPro SDK utilizes **`uv`** for lightning-fast and highly secure dependency management. Follow these instructions to initialize your workspace:

### 1. Initialize Python Environment
Create a local Python virtual environment and activate it:
```bash
# Create virtual environment
uv venv

# Activate on macOS/Linux
source .venv/bin/activate

# Activate on Windows Powershell
.venv\Scripts\Activate.ps1
```

### 2. Install BioPro SDK in Editable Mode
Install the SDK and its required graphical dependencies into your virtualenv:
```bash
uv pip install -e .
```
This registers the global CLI shim `biopro-sdk` directly into your path!

---

## 🔑 Step 2: Initialize Your Developer Identity

To load plugins into a production instance of the host application, they must be signed by an approved private key. BioPro provides a standard command-line utility to bootstrap your development environment.

Run the onboarding command:
```bash
biopro-sdk init-identity
```

### What happens behind the scenes?
1.  **Generates an Ed25519 Private Key:** Writes a PKCS#8 pem file to `~/.biopro/id_ed25519`.
2.  **Establishes Local Trust Override:** Generates a public certificate stub `~/.biopro/dev_cert.bin` which self-signs your developer public key.
3.  **Bootstraps Onboarding Root:** Places an onboarding certificate into your local trusted registry, ensuring the host application recognizes your work.

---

## 🧪 Step 3: Run the Hello World Sandbox Template

The SDK comes with ready-made examples. Let's inspect, sign, and load the `hello_world` plugin.

### 1. View the Manifest
Every plugin is recognized by its `manifest.json`. Let's inspect `examples/hello_world/manifest.json`:
```json
{
    "id": "hello_world",
    "name": "Hello World Blueprint",
    "manifest_version": 2,
    "authors": [
        {
            "name": "BioPro SDK Team",
            "role": "Lead Developer"
        }
    ],
    "version": "1.0.0",
    "icon": "🧪",
    "description": "Minimal plugin blueprint demonstrating PyQt6 widgets and semantic buttons."
}
```

### 2. Sign the Plugin
Before loading, you must cryptographically sign the plugin assets. The CLI will crawl your files, compute a SHA256 integrity tree, and write standard verification block files.

Run the sign utility:
```bash
biopro-sdk sign examples/hello_world
```
**Output:**
```text
Updating manifest.json integrity records...
Signing plugin assets...
Successfully signed plugin: hello_world
```
This generates:
*   `examples/hello_world/signature.bin` (The cryptographic signature of the canonicalized manifest).
*   `examples/hello_world/dev_cert.bin` (The developer identity certificate verification stub).

---

## 🚀 Step 4: Simulate Plugin Execution

To test the loaded widget dynamically in a sandbox emulator, write a simple script:

`run_simulator.py`:
```python
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow

from biopro_sdk.host.trust_manager import TrustManager
from biopro_sdk.host.docs import get_panel_class_for_plugin

def main():
    app = QApplication(sys.argv)
    
    plugin_path = "examples/hello_world"
    
    # 1. Verify cryptographic integrity before loading
    trust_manager = TrustManager()
    is_valid, reason = trust_manager.verify_plugin(plugin_path)
    
    if not is_valid:
        print(f"ERROR: Plugin verification failed: {reason}")
        sys.exit(1)
        
    print("SUCCESS: Cryptographic signature verified successfully!")
    
    # 2. Dynamically resolve the plugin class
    panel_class = get_panel_class_for_plugin(plugin_path)
    panel = panel_class()
    
    # 3. Mount in MainWindow and display
    window = QMainWindow()
    window.setWindowTitle("BioPro Plugin Simulator")
    window.setCentralWidget(panel)
    window.resize(600, 400)
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
```

Run your simulator:
```bash
PYTHONPATH=src uv run python run_simulator.py
```
This loads your custom theme-compliant GUI dynamically, proving that your developer workspace is fully operational!

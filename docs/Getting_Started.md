# 🏁 Quickstart Guide

This step-by-step tutorial walks you through setting up your local environment, creating a new BioPro module from scratch, understanding the repository structure, and securing it with cryptographic signing.

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

### 2. Install BioPro SDK
Install the SDK into your virtual environment:
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
1.  **Generates an Ed25519 Private Key:** Writes a PKCS#8 pem file to `~/.biopro/dev_keys/private.key`.
2.  **Generates Public Key:** Writes a public certificate stub to `~/.biopro/dev_keys/public.pub`.
3.  **Local Registration:** The CLI establishes this key pair as your local developer identity for subsequent signing operations.

---

## 🏗️ Step 3: Bootstrap a New BioPro Module

Instead of creating files manually, you can use the SDK CLI to automatically scaffold a new plugin repository that conforms to the latest V2 architecture.

Run the bootstrap command:
```bash
biopro-sdk bootstrap my_first_plugin
```

### How to Organize a Repo
The bootstrap command creates the standard directory structure required by BioPro. Let's look at how your repo is organized:

```text
my_first_plugin/
├── pyproject.toml           # The plugin manifest and Python configuration
├── src/
│   └── __init__.py          # The core plugin logic and entry point
├── docs/
│   └── 01_getting_started.md # Local documentation for your plugin
└── .github/
    └── workflows/           # CI/CD pipelines (ci, deploy-docs, release)
```

* **`pyproject.toml`**: The split-manifest architecture uses this standard Python file to define your plugin ID, required SDK version, permissions, dependencies, and the `entry_point` for the BioPro host application.
* **`src/`**: All your Python source code lives here. The `__init__.py` file contains a class inheriting from `AnalysisBase` (or `PluginBase`) which serves as the entry point.
* **`docs/`**: Markdown documentation files that will be compiled into the BioPro Help Center.

---

## 🔐 Step 4: Security Signing

Before your plugin can be loaded by the BioPro host application, it must be cryptographically signed. The Trust Engine verifies that the code hasn't been tampered with.

Run the signing utility on your plugin directory:
```bash
biopro-sdk sign my_first_plugin
```

### What happens during signing?
1. **File Hashing:** The CLI crawls your `src/` and other critical directories, computing a SHA-256 integrity hash for every file.
2. **Ledger Generation:** A `security.json` ledger is generated, binding the hashes of your files to the hash of your `pyproject.toml`.
3. **Cryptographic Signature:** The ledger is signed with your developer private key, generating `signature.bin`.
4. **Trust Chain:** A `trust_chain.json` file is created to link your public key to the signature.

Your plugin directory will now have the necessary security assets:
```text
my_first_plugin/
├── pyproject.toml
├── security.json        # NEW: Integrity hashes
├── signature.bin        # NEW: Cryptographic signature
├── trust_chain.json     # NEW: Developer public key chain
├── src/
├── docs/
└── .github/
```

**Note:** You must re-run `biopro-sdk sign my_first_plugin` *every time* you modify your code before testing it in the host application!

---

## 🚀 Step 5: Validate Your Plugin

To ensure your newly created and signed plugin meets all BioPro SDK standards before distribution, you can run the built-in evaluator:

```bash
biopro-sdk evaluate my_first_plugin
```

This will run a 3-part audit:
1. **Manifest Audit:** Verifies the `pyproject.toml` configuration.
2. **Structure & SDK Compliance:** Checks that you are properly subclassing BioPro base classes like `AnalysisBase`.
3. **Security Audit:** Validates that the cryptographic signatures are present and correct.

If you get a green status, your plugin is ready to be loaded into the BioPro host application!

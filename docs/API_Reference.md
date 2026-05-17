# 🔍 API Reference Manual Overview

Welcome to the technical API Reference Manual for the **BioPro SDK**. This section provides complete type signatures, detailed docstring tables, and lifecycle contracts for every core class in the SDK.

---

## 🏛️ Submodule Index

To maintain optimal organization, the reference specifications have been structured into dedicated modules:

### 1. 🧬 [Core Plugin Module (`biopro_sdk.plugin`)](API_Plugin_Base.md)
Contains the foundation classes, protocol contracts, dynamic undo/redo checkpoint managers, and central thread-safe global event brokers.
*   **Core Interfaces:** `PluginBase`, `PluginState`, `CentralEventBus`, `PluginLoggerAdapter`.

### 2. 🎨 [UI & Component Module (`biopro_sdk.plugin.components`)](API_UI_Components.md)
Houses premium theme-aware PyQt6 widgets, semantic layout controls, and the multi-step onboarding guided wizard controllers.
*   **Core Interfaces:** `PrimaryButton`, `SecondaryButton`, `DangerButton`, `WizardPanel`, `WizardStep`.

### 3. ⚙️ [Background Concurrency Module (`biopro_sdk.plugin.analysis`)](API_Background_Engine.md)
Delineates heavy offscreen scientific math computations from graphic elements, managing thread-pools and progress proxies.
*   **Core Interfaces:** `AnalysisBase`, `AnalysisWorker`, `AnalysisRunnable`, `PluginSignals`.

### 4. 🛡️ [Security & Cryptography Module (`biopro_sdk.host`)](API_Trust_Cryptography.md)
Exposes host validation routines, trust override registries, and signature verification managers.
*   **Core Interfaces:** `TrustManager`, `TrustOverrideRegistry`, `TrustPathSerialization`.

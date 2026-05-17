"""BioPro SDK Contrib — Optional utilities to support plugin development.

Image utilities for common analysis operations. Use these to keep plugin
code DRY and focused on domain-specific logic.
"""

try:
    from biopro.shared.analysis.image_utils import (
        adjust_contrast,
        auto_detect_inversion,
        crop_to_content,
        enhance_for_band_detection,
        invert_image,
        load_and_convert,
        rotate_image,
    )
except ImportError:
    # Standalone fallback: raise ImportError only if called, keeping SDK CLI lightweight
    def _raise_import_error(*args, **kwargs):
        raise ImportError("This utility requires 'biopro-core' or 'scikit-image' to be installed.")

    adjust_contrast = _raise_import_error
    auto_detect_inversion = _raise_import_error
    crop_to_content = _raise_import_error
    enhance_for_band_detection = _raise_import_error
    invert_image = _raise_import_error
    load_and_convert = _raise_import_error
    rotate_image = _raise_import_error

__all__ = [
    "adjust_contrast",
    "load_and_convert",
    "auto_detect_inversion",
    "invert_image",
    "enhance_for_band_detection",
    "rotate_image",
    "crop_to_content",
]

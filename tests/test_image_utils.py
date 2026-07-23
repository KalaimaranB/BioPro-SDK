"""Tests for image loading and preprocessing utilities."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from biopro_sdk.contrib.image_utils import (
    auto_crop_to_bands,
    auto_detect_inversion,
    crop_to_content,
    invert_image,
    load_and_convert,
    rotate_image,
)


class TestLoadAndConvert:
    """Tests for the load_and_convert function."""

    def test_load_png_grayscale(self, tmp_path: Path) -> None:
        """Loading a PNG file should return a grayscale float64 array."""
        from skimage.io import imsave

        # Create a simple test image
        img = np.random.randint(0, 255, (50, 80), dtype=np.uint8)
        path = tmp_path / "test.png"
        imsave(str(path), img)

        result = load_and_convert(path)
        assert result.dtype == np.float64
        assert result.ndim == 2
        assert result.min() >= 0.0
        assert result.max() <= 1.0

    def test_load_rgb_as_grayscale(self, tmp_path: Path) -> None:
        """Loading an RGB image with as_grayscale=True should convert."""
        from skimage.io import imsave

        img = np.random.randint(0, 255, (50, 80, 3), dtype=np.uint8)
        path = tmp_path / "test_rgb.png"
        imsave(str(path), img)

        result = load_and_convert(path, as_grayscale=True)
        assert result.ndim == 2

    def test_load_rgb_keep_color(self, tmp_path: Path) -> None:
        """Loading with as_grayscale=False should preserve 3 channels."""
        from skimage.io import imsave

        img = np.random.randint(0, 255, (50, 80, 3), dtype=np.uint8)
        path = tmp_path / "test_rgb.png"
        imsave(str(path), img)

        result = load_and_convert(path, as_grayscale=False)
        assert result.ndim == 3
        assert result.shape[2] == 3

    def test_load_nonexistent_raises(self) -> None:
        """Loading a nonexistent file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_and_convert("/nonexistent/path.png")


class TestAutoDetectInversion:
    """Tests for auto_detect_inversion."""

    def test_dark_on_light_no_inversion(self) -> None:
        """Dark bands on light background should NOT need inversion."""
        image = np.ones((100, 100), dtype=np.float64) * 0.9  # Light bg
        image[30:70, 30:70] = 0.2  # Dark bands in center
        assert auto_detect_inversion(image) is False

    def test_light_on_dark_needs_inversion(self) -> None:
        """Light bands on dark background SHOULD need inversion."""
        image = np.ones((100, 100), dtype=np.float64) * 0.1  # Dark bg
        image[30:70, 30:70] = 0.8  # Light bands in center
        assert auto_detect_inversion(image) is True

    def test_uniform_image(self) -> None:
        """Uniform image should not crash."""
        image = np.ones((100, 100), dtype=np.float64) * 0.5
        # Should return some result without error
        result = auto_detect_inversion(image)
        assert isinstance(result, bool)


class TestInvertImage:
    """Tests for invert_image."""

    def test_inversion(self) -> None:
        """Inverting should flip pixel values (1 - x)."""
        image = np.array([[0.0, 0.5], [1.0, 0.25]])
        result = invert_image(image)
        np.testing.assert_array_almost_equal(result, np.array([[1.0, 0.5], [0.0, 0.75]]))

    def test_double_inversion(self) -> None:
        """Inverting twice should return the original."""
        image = np.random.rand(50, 50)
        result = invert_image(invert_image(image))
        np.testing.assert_array_almost_equal(result, image)


class TestRotateImage:
    """Tests for rotate_image."""

    def test_zero_rotation(self) -> None:
        """Zero rotation should return the same image."""
        image = np.random.rand(50, 80)
        result = rotate_image(image, 0.0)
        np.testing.assert_array_almost_equal(result, image)

    def test_rotation_changes_size(self) -> None:
        """Non-zero rotation should potentially change image dimensions."""
        image = np.random.rand(50, 80)
        result = rotate_image(image, 45.0)
        assert result.dtype == np.float64
        # Rotated image with resize=True should be different size
        assert result.shape != image.shape


class TestCropToContent:
    """Tests for crop_to_content."""

    def test_crop_all_white(self) -> None:
        """Cropping an all-white image should return the original."""
        image = np.ones((100, 100), dtype=np.float64)
        result = crop_to_content(image)
        assert result.shape == (100, 100)

    def test_crop_ignores_sparse_noise(self) -> None:
        """Cropping should remove borders when only tiny noisy pixels exist."""
        image = np.ones((100, 100), dtype=np.float64) * 0.8
        image[50, 50] = 0.1
        result = crop_to_content(image, padding=3)
        assert result.shape == (100, 100)

    def test_crop_removes_borders(self) -> None:
        """Cropping should remove white borders."""
        # 300x300 background with some noise
        np.random.seed(42)
        image = np.random.normal(0.9, 0.01, (300, 300))
        image = np.clip(image, 0.0, 1.0)
        # Stark dark box in the center
        image[100:200, 100:200] = np.random.normal(0.1, 0.01, (100, 100))
        image = np.clip(image, 0.0, 1.0)

        result = crop_to_content(image, padding=0)
        # Ensure the 300-height image was successfully cropped down
        # With noise, the exact boundaries might be slightly off due to min_content_fraction,
        # but it should be close to 100x100
        assert result.shape[0] < 150
        assert result.shape[1] < 150

    def test_auto_crop_to_bands_detects_band_region(self) -> None:
        """Auto-crop to bands should crop around dark horizontal band rows."""
        # 300x300 background
        np.random.seed(42)
        image = np.random.normal(0.9, 0.01, (300, 300))
        image = np.clip(image, 0.0, 1.0)

        # A perfectly shaped biological band (wide and short)
        image[140:160, 50:250] = np.random.normal(0.1, 0.01, (20, 200))
        image = np.clip(image, 0.0, 1.0)

        cropped = auto_crop_to_bands(image, vertical_padding_frac=0, horizontal_padding_frac=0)
        # It should be much shorter than 300
        assert 10 < cropped.shape[0] < 100

    def test_auto_crop_to_bands_no_band_returns_original(self) -> None:
        """If no band rows exist, auto_crop_to_bands should return original."""
        image = np.ones((80, 80), dtype=np.float64)
        cropped = auto_crop_to_bands(image)
        np.testing.assert_array_equal(cropped, image)

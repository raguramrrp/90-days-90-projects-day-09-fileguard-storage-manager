"""
Tests for Perceptual Hashing (dHash calculation, Hamming distance, visual similarity).
"""
import pytest
from fileguard.perceptual_hash import (
    calculate_hamming_distance, calculate_similarity_percent,
    is_pillow_available, compute_dhash
)


def test_hamming_distance_identical_hashes():
    h = "0123456789abcdef"
    dist = calculate_hamming_distance(h, h)
    assert dist == 0
    assert calculate_similarity_percent(dist) == 100.0


def test_hamming_distance_differing_hashes():
    # '0' in bin is 0000, '1' is 0001 (1 bit difference)
    h1 = "0000000000000000"
    h2 = "0000000000000001"
    dist = calculate_hamming_distance(h1, h2)
    assert dist == 1
    # (1.0 - (1 / 64.0)) * 100 = 98.44%
    assert calculate_similarity_percent(dist) == 98.44


def test_dhash_calculation_if_pillow(temp_dir):
    if not is_pillow_available():
        pytest.skip("Pillow not installed in environment")

    from PIL import Image
    img_path = temp_dir / "sample.png"
    img = Image.new("RGB", (64, 64), color="blue")
    img.save(img_path)

    h = compute_dhash(str(img_path))
    assert h is not None
    assert len(h) == 16  # 64-bit hex

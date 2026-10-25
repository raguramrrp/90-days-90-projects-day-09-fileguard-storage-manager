"""
Perceptual Hashing Module for FileGuard (Near-Duplicate Image Detection).
Uses difference hashing (dHash) to generate 64-bit visual fingerprints of images,
allowing visual similarity comparison across resized, recompressed, or slightly modified images.
"""
from pathlib import Path
from typing import Optional, Tuple, List, Dict
import os

try:
    from PIL import Image, ImageOps
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False


def is_pillow_available() -> bool:
    """Check if PIL/Pillow is installed and operational."""
    return HAS_PILLOW


def compute_dhash(image_path: str, hash_size: int = 8) -> Optional[str]:
    """
    Calculate the difference hash (dHash) of an image.
    1. Convert to grayscale.
    2. Resize to (hash_size + 1, hash_size) e.g., 9x8 = 72 pixels.
    3. Compare adjacent pixels horizontally.
    4. Build 64-bit integer, returned as 16-character hex string.
    """
    if not HAS_PILLOW:
        return None

    try:
        with Image.open(image_path) as img:
            # Convert to grayscale
            img = img.convert("L")
            # Resize with antialiasing
            img = img.resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
            if hasattr(img, "get_flattened_data"):
                pixels = list(img.get_flattened_data())
            else:
                pixels = list(img.getdata())

            difference = []
            for row in range(hash_size):
                row_offset = row * (hash_size + 1)
                for col in range(hash_size):
                    pixel_left = pixels[row_offset + col]
                    pixel_right = pixels[row_offset + col + 1]
                    difference.append(pixel_left > pixel_right)

            decimal_value = 0
            hex_string = []
            for index, value in enumerate(difference):
                if value:
                    decimal_value += 2 ** (index % 8)
                if (index % 8) == 7:
                    hex_string.append(hex(decimal_value)[2:].rjust(2, "0"))
                    decimal_value = 0

            return "".join(hex_string)
    except Exception:
        return None


def get_image_dimensions(image_path: str) -> Optional[Tuple[int, int]]:
    """Return (width, height) of image if readable."""
    if not HAS_PILLOW:
        return None
    try:
        with Image.open(image_path) as img:
            return img.size
    except Exception:
        return None


def calculate_hamming_distance(hash1: str, hash2: str) -> int:
    """
    Calculate Hamming distance (number of differing bits) between two hex hashes.
    Range: 0 (identical visual structure) to 64 (completely dissimilar).
    """
    if not hash1 or not hash2 or len(hash1) != len(hash2):
        return 64
    try:
        int1 = int(hash1, 16)
        int2 = int(hash2, 16)
        xor_result = int1 ^ int2
        return bin(xor_result).count("1")
    except ValueError:
        return 64


def calculate_similarity_percent(hamming_distance: int, max_bits: int = 64) -> float:
    """Calculate percentage similarity from hamming distance."""
    clamped_dist = max(0, min(max_bits, hamming_distance))
    return round((1.0 - (clamped_dist / float(max_bits))) * 100.0, 2)

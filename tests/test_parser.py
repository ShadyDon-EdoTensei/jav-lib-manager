"""Tests for video ID parser"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.parser import get_parser


def test_basic_parsing():
    """Test basic video ID parsing"""
    parser = get_parser()

    # Test cases: (filename, expected_id)
    test_cases = [
        ("ABC-123.mp4", "ABC-123"),
        ("ABC123.mp4", "ABC-123"),
        ("[ABC-123] Title.mp4", "ABC-123"),
        ("XYZ-456.H265.mp4", "XYZ-456"),
        ("DEF-789.FHD.mp4", "DEF-789"),
    ]

    for filename, expected_id in test_cases:
        result = parser.parse(filename)
        assert result == expected_id, f"Failed for {filename}: got {result}, expected {expected_id}"
        print(f"✓ {filename} -> {result}")


def test_edge_cases():
    """Test edge cases"""
    parser = get_parser()

    # Test invalid filenames
    invalid_cases = [
        "no-id-here.mp4",
        "12345.mp4",
        "just-text.txt",
    ]

    for filename in invalid_cases:
        result = parser.parse(filename)
        assert result is None or result == "", f"Expected None for {filename}, got {result}"
        print(f"✓ {filename} -> None (expected)")


if __name__ == "__main__":
    print("Running parser tests...")
    test_basic_parsing()
    test_edge_cases()
    print("\n✅ All tests passed!")

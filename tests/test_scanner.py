"""Tests for video file scanner"""

import sys
import os
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.scanner import get_scanner
from src.core.parser import get_parser


def test_scanner_finds_videos():
    """测试扫描器能找到视频文件"""
    # 创建临时测试目录
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建测试文件
        test_files = [
            "ABC-123.mp4",
            "DEF-456.mkv",
            "GHI-789.avi",
            "not-a-video.txt"
        ]

        for fname in test_files:
            fpath = os.path.join(tmpdir, fname)
            with open(fpath, 'w') as f:
                f.write("test")

        # 扫描
        scanner = get_scanner()
        results = scanner.scan(tmpdir)

        # 验证：应该找到 3 个视频文件
        assert len(results) == 3, f"Expected 3 videos, got {len(results)}"
        print(f"✓ 找到 {len(results)} 个视频文件")


def test_scanner_parses_ids():
    """测试扫描器能解析番号"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建测试视频
        test_file = os.path.join(tmpdir, "SSIS-123.mp4")
        with open(test_file, 'w') as f:
            f.write("test")

        scanner = get_scanner()
        results = scanner.scan(tmpdir)

        # 验证番号
        assert len(results) == 1
        assert results[0].code == "SSIS-123", f"Expected SSIS-123, got {results[0].code}"
        print(f"✓ 正确解析番号: {results[0].code}")


if __name__ == "__main__":
    print("Running scanner tests...")
    test_scanner_finds_videos()
    test_scanner_parses_ids()
    print("\n✅ All scanner tests passed!")

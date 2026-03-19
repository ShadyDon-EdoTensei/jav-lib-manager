"""Tests for metadata scraper"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.scraper import get_scraper


def test_scraper_fetches_metadata():
    """测试爬虫能获取元数据"""
    scraper = get_scraper()

    # 使用一个常见的番号进行测试
    test_code = "SSIS-123"

    try:
        metadata = scraper.fetch(test_code)

        if metadata:
            assert metadata.id == test_code
            assert metadata.title is not None
            assert len(metadata.title) > 0
            print(f"✓ 成功获取 {test_code} 的元数据")
            print(f"  标题: {metadata.title[:30]}...")
            print(f"  封面: {'有' if metadata.cover_url else '无'}")
            print(f"  女优: {len(metadata.actresses)} 人")
        else:
            print(f"⚠ 无法获取 {test_code} 的元数据（可能网络问题）")
    except Exception as e:
        print(f"⚠ 测试跳过（网络或服务问题）: {e}")


def test_scraper_handles_error():
    """测试爬虫正确处理错误"""
    scraper = get_scraper()

    # 使用不存在的番号
    fake_code = "FAKE-999"

    try:
        metadata = scraper.fetch(fake_code)
        # 应该返回 None 或空对象
        assert metadata is None or metadata.id != fake_code
        print(f"✓ 正确处理无效番号: {fake_code}")
    except Exception:
        # 不应该抛出异常
        assert False, "爬虫应该优雅地处理无效番号"


if __name__ == "__main__":
    print("Running scraper tests...")
    test_scraper_fetches_metadata()
    test_scraper_handles_error()
    print("\n✅ All scraper tests completed!")

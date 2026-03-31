"""Cover extraction and download helper tests."""

from src.core.cover_downloader import CoverDownloader
from src.core.scraper import _normalize_image_url


def test_normalize_image_url_handles_relative_paths():
    base_url = "https://javdb571.com"

    assert _normalize_image_url("//img.example.com/a.webp", base_url) == "https://img.example.com/a.webp"
    assert _normalize_image_url("/covers/a.jpg", base_url) == "https://javdb571.com/covers/a.jpg"
    assert _normalize_image_url("https://img.example.com/a.jpg", base_url) == "https://img.example.com/a.jpg"


def test_cover_downloader_builds_multiple_referers():
    downloader = CoverDownloader()

    referers = downloader._build_referer_candidates("https://javdb.vip/covers/a.jpg")

    assert referers[0] == "https://javdb.vip/"
    assert "https://javdb571.com/" in referers
    assert "https://javdb.com/" in referers

    downloader.close()

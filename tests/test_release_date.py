"""Release date parsing and backfill related tests."""

from datetime import date

from src.core.database import Database
from src.core.models import VideoMetadata, SourceType
from src.core.scraper import _parse_release_date, JavDBPlaywrightScraper, ScraperManager


class _FakePlaywrightMetadata:
    def __init__(self, release_date: str):
        self.id = "ABP-123"
        self.title = "Test Title"
        self.cover_url = "https://example.com/cover.jpg"
        self.release_date = release_date
        self.duration = "120"
        self.director = None
        self.studio = "Studio"
        self.label = "Label"
        self.series = "Series"
        self.actresses = ["A"]
        self.genres = ["Drama"]
        self.sample_images = []


class _FakePlaywrightScraper:
    def __init__(self, release_date: str):
        self._release_date = release_date

    def fetch(self, _code: str):
        return _FakePlaywrightMetadata(self._release_date)


def test_parse_release_date_formats():
    assert _parse_release_date("2024-01-31") == date(2024, 1, 31)
    assert _parse_release_date("2024/01/31") == date(2024, 1, 31)
    assert _parse_release_date("2024.01.31") == date(2024, 1, 31)
    assert _parse_release_date("invalid") is None


def test_playwright_scraper_maps_release_date():
    scraper = JavDBPlaywrightScraper(headless=True)
    scraper._get_scraper = lambda: _FakePlaywrightScraper("2024-03-11")

    metadata = scraper.fetch("ABP-123")

    assert metadata is not None
    assert metadata.release_date == date(2024, 3, 11)


def test_get_videos_missing_release_date(tmp_path):
    db_path = tmp_path / "library.db"
    db = Database(str(db_path))

    metadata_missing = VideoMetadata(
        id="AAA-001",
        title="No Date",
        cover_url=None,
        actresses=[],
        studio=None,
        label=None,
        series=None,
        genres=[],
        release_date=None,
        duration=None,
        source=SourceType.JAVDB,
    )

    metadata_has_date = VideoMetadata(
        id="BBB-002",
        title="Has Date",
        cover_url=None,
        actresses=[],
        studio=None,
        label=None,
        series=None,
        genres=[],
        release_date=date(2024, 1, 1),
        duration=None,
        source=SourceType.JAVDB,
    )

    assert db.add_video(metadata_missing, "C:/tmp/AAA-001.mp4", 100)
    assert db.add_video(metadata_has_date, "C:/tmp/BBB-002.mp4", 100)

    missing_codes = db.get_videos_missing_release_date()
    assert "AAA-001" in missing_codes
    assert "BBB-002" not in missing_codes

    assert db.update_release_date_if_missing("AAA-001", date(2024, 2, 2))
    assert not db.update_release_date_if_missing("BBB-002", date(2024, 2, 2))


def test_get_videos_needing_metadata_refresh(tmp_path):
    db_path = tmp_path / "library.db"
    db = Database(str(db_path))

    placeholder = VideoMetadata(
        id="AAA-001",
        title="AAA-001",
        cover_url=None,
        actresses=[],
        studio="磁鏈搜索引擎 / 關注演員、片商、類別等 / 功能增強及更優體驗",
        label=None,
        series=None,
        genres=[],
        release_date=None,
        duration=None,
        source=SourceType.JAVDB,
    )
    complete = VideoMetadata(
        id="BBB-002",
        title="Real Title",
        cover_url="https://example.com/b.jpg",
        actresses=["Actor A"],
        studio="Studio",
        label=None,
        series=None,
        genres=[],
        release_date=date(2024, 1, 1),
        duration=None,
        source=SourceType.JAVDB,
    )

    assert db.add_video(placeholder, "C:/tmp/AAA-001.mp4", 100)
    assert db.add_video(complete, "C:/tmp/BBB-002.mp4", 100)

    needing_refresh = db.get_videos_needing_metadata_refresh()
    assert "AAA-001" in needing_refresh
    assert "BBB-002" not in needing_refresh


def test_scraper_manager_skips_placeholder_metadata():
    placeholder = VideoMetadata(
        id="GOJU-261",
        title="GOJU-261",
        cover_url=None,
        actresses=[],
        studio="磁鏈搜索引擎 / 關注演員、片商、類別等 / 功能增強及更優體驗",
        label=None,
        series=None,
        genres=[],
        release_date=None,
        duration=None,
        source=SourceType.JAVDB,
    )

    assert ScraperManager._looks_like_placeholder(placeholder, "GOJU-261")

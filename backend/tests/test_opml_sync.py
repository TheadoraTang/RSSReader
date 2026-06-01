import asyncio
import unittest
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

from app.services import feed_service, opml_service


class FakeUploadFile:
    filename = "subscriptions.opml"

    def __init__(self, content: str) -> None:
        self.content = content.encode("utf-8")

    async def read(self) -> bytes:
        return self.content


class FakeOPMLRepository:
    def __init__(self) -> None:
        self.feeds = [
            {
                "id": 1,
                "title": "Existing",
                "url": "https://example.com/existing.xml",
                "site_url": "https://example.com",
                "description": None,
                "last_sync_at": None,
                "created_at": datetime.now(timezone.utc),
            }
        ]
        self.logs = []

    def list_feeds(self):
        return list(self.feeds)

    def create_feed(self, payload):
        url = str(payload.url)
        if url == "https://example.com/failing.xml":
            raise ValueError("Failed to parse feed: unavailable")
        feed = {
            "id": len(self.feeds) + 1,
            "title": payload.title or url,
            "url": url,
            "site_url": None,
            "description": None,
            "last_sync_at": datetime.now(timezone.utc),
            "created_at": datetime.now(timezone.utc),
        }
        self.feeds.append(feed)
        return feed

    def log_feed_event(self, feed_id, url, status, message):
        self.logs.append({"feed_id": feed_id, "url": url, "status": status, "message": message})


class FakeSyncRepository:
    def list_feeds(self):
        return [
            {"id": 1, "title": "Working", "url": "https://example.com/working.xml"},
            {"id": 2, "title": "Broken", "url": "https://example.com/broken.xml"},
        ]

    def sync_feed(self, feed_id):
        if feed_id == 2:
            raise ValueError("network error")
        return {
            "id": 1,
            "title": "Working",
            "url": "https://example.com/working.xml",
            "site_url": None,
            "description": None,
            "last_sync_at": datetime.now(timezone.utc),
            "created_at": datetime.now(timezone.utc),
        }


class OPMLServiceTest(unittest.TestCase):
    def test_parse_nested_opml_deduplicates_feed_urls(self):
        items = opml_service.parse_opml_feeds(
            """
            <opml version="2.0">
              <body>
                <outline text="Folder">
                  <outline text="One" type="rss" xmlUrl="https://example.com/one.xml" />
                  <outline text="Duplicate" type="rss" xmlUrl="https://example.com/one.xml" />
                </outline>
              </body>
            </opml>
            """
        )

        self.assertEqual(items, [{"url": "https://example.com/one.xml", "title": "One"}])

    def test_import_opml_reports_imported_skipped_and_failed_items(self):
        old_repository = opml_service.repository
        fake_repository = FakeOPMLRepository()
        opml_service.repository = fake_repository
        try:
            report = asyncio.run(
                opml_service.import_opml(
                    FakeUploadFile(
                        """
                        <opml version="2.0">
                          <body>
                            <outline text="Existing" xmlUrl="https://example.com/existing.xml" />
                            <outline text="New Feed" xmlUrl="https://example.com/new.xml" />
                            <outline text="Invalid" xmlUrl="not-a-url" />
                            <outline text="Failing" xmlUrl="https://example.com/failing.xml" />
                          </body>
                        </opml>
                        """
                    )
                )
            )
        finally:
            opml_service.repository = old_repository

        self.assertEqual(report["total"], 4)
        self.assertEqual(report["imported"], 1)
        self.assertEqual(report["skipped"], 1)
        self.assertEqual(report["failed"], 2)
        self.assertEqual([item["status"] for item in report["results"]], ["skipped", "imported", "failed", "failed"])
        self.assertEqual(len(fake_repository.logs), 2)

    def test_export_opml_uses_current_repository_feeds(self):
        old_repository = opml_service.repository
        fake_repository = FakeOPMLRepository()
        opml_service.repository = fake_repository
        try:
            xml_text = opml_service.export_opml()
        finally:
            opml_service.repository = old_repository

        root = ET.fromstring(xml_text)
        outlines = [item for item in root.iter("outline")]
        self.assertEqual(len(outlines), 1)
        self.assertEqual(outlines[0].attrib["xmlUrl"], "https://example.com/existing.xml")
        self.assertEqual(outlines[0].attrib["htmlUrl"], "https://example.com")


class SyncAllServiceTest(unittest.TestCase):
    def test_sync_all_keeps_syncing_when_one_feed_fails(self):
        old_repository = feed_service.repository
        feed_service.repository = FakeSyncRepository()
        try:
            report = feed_service.sync_all_feeds()
        finally:
            feed_service.repository = old_repository

        self.assertEqual(report["total"], 2)
        self.assertEqual(report["success"], 1)
        self.assertEqual(report["failed"], 1)
        self.assertEqual(report["results"][0]["status"], "success")
        self.assertEqual(report["results"][1]["status"], "failed")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from datetime import datetime, timezone
from xml.etree import ElementTree as ET

from pydantic import ValidationError

from app.repositories import repository
from app.schemas import FeedCreate


def parse_opml_feeds(text: str) -> list[dict[str, str | None]]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise ValueError(f"Invalid OPML XML: {exc}") from exc

    feeds: list[dict[str, str | None]] = []
    seen_urls: set[str] = set()
    for outline in root.iter():
        if _local_name(outline.tag).lower() != "outline":
            continue
        attributes = {_local_name(key).lower(): value for key, value in outline.attrib.items()}
        url = _normalize_text(attributes.get("xmlurl"))
        if not url or url in seen_urls:
            continue
        title = _normalize_text(attributes.get("title")) or _normalize_text(attributes.get("text"))
        feeds.append({"url": url, "title": title})
        seen_urls.add(url)

    return feeds


async def import_opml(file):
    content = await file.read()
    text = _decode_opml(content)
    feed_items = parse_opml_feeds(text)
    existing_feeds = {feed["url"].strip(): feed for feed in repository.list_feeds()}
    seen_urls = set(existing_feeds)
    results = []

    for item in feed_items:
        url = item["url"] or ""
        title = item.get("title")
        if url in seen_urls:
            results.append(
                {
                    "url": url,
                    "title": title,
                    "status": "skipped",
                    "message": "Feed already exists.",
                    "feed": existing_feeds.get(url),
                }
            )
            continue

        try:
            feed = repository.create_feed(FeedCreate(title=title, url=url))
        except ValidationError as exc:
            message = _validation_message(exc)
            _log_failed_import(url, message)
            results.append(
                {
                    "url": url,
                    "title": title,
                    "status": "failed",
                    "message": message,
                    "feed": None,
                }
            )
            continue
        except ValueError as exc:
            message = str(exc)
            status = "skipped" if "already exists" in message.lower() else "failed"
            if status == "failed":
                _log_failed_import(url, message)
            results.append(
                {
                    "url": url,
                    "title": title,
                    "status": status,
                    "message": message,
                    "feed": None,
                }
            )
            if status == "skipped":
                seen_urls.add(url)
            continue

        existing_feeds[url] = feed
        seen_urls.add(url)
        results.append(
            {
                "url": url,
                "title": title or feed["title"],
                "status": "imported",
                "message": "Feed imported and synced.",
                "feed": feed,
            }
        )

    return {
        "total": len(results),
        "imported": sum(1 for item in results if item["status"] == "imported"),
        "skipped": sum(1 for item in results if item["status"] == "skipped"),
        "failed": sum(1 for item in results if item["status"] == "failed"),
        "results": results,
    }


def export_opml():
    root = ET.Element("opml", {"version": "2.0"})
    head = ET.SubElement(root, "head")
    ET.SubElement(head, "title").text = "RSSReader Subscriptions"
    ET.SubElement(head, "dateCreated").text = datetime.now(timezone.utc).isoformat()
    body = ET.SubElement(root, "body")

    for feed in repository.list_feeds():
        title = feed.get("title") or feed["url"]
        attributes = {
            "text": title,
            "title": title,
            "type": "rss",
            "xmlUrl": feed["url"],
        }
        if feed.get("site_url"):
            attributes["htmlUrl"] = feed["site_url"]
        ET.SubElement(body, "outline", attributes)

    return "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n" + ET.tostring(root, encoding="unicode")


def _decode_opml(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def _local_name(value: str) -> str:
    return value.rsplit("}", 1)[-1]


def _normalize_text(value: str | None) -> str | None:
    normalized = (value or "").strip()
    return normalized or None


def _validation_message(exc: ValidationError) -> str:
    first = exc.errors()[0] if exc.errors() else {}
    return str(first.get("msg") or "Invalid feed URL")


def _log_failed_import(url: str, message: str) -> None:
    if hasattr(repository, "log_feed_event"):
        repository.log_feed_event(None, url, "failed", message)

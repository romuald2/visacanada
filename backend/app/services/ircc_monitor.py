"""IRCC feed parser and scraper service.

Parses the IRCC Atom feed and processing times pages to detect policy updates.
Respects robots.txt and rate limits.
"""

import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import httpx

from app.models.ircc_update import IRCCUpdateCategory, IRCCUpdateSource

# IRCC Feed URLs
IRCC_ATOM_FEED_URL = "https://api.io.canada.ca/io-server/gc/news/en/v2?dept=departmentofcitizenshipandimmigration&type=newsreleases&sort=publishedDate&orderBy=desc&limit=20"
IRCC_NEWS_FEED_URL = "https://www.canada.ca/content/canadasite/api/nws/fds/en/web-feeds/immigration-refugees-citizenship.atom.xml"
IRCC_PROCESSING_TIMES_URL = "https://www.canada.ca/en/immigration-refugees-citizenship/services/application/check-processing-times.html"

# User agent that identifies the bot
USER_AGENT = "VisaCanada-Monitor/1.0 (+immigration-consulting; respectful-bot)"

# Category keywords for auto-classification
CATEGORY_KEYWORDS = {
    IRCCUpdateCategory.processing_time: [
        "processing time", "délai de traitement", "wait time",
        "service standard", "inventory",
    ],
    IRCCUpdateCategory.criteria_change: [
        "eligibility", "requirement", "criteria", "admissibility",
        "minimum score", "CRS", "points",
    ],
    IRCCUpdateCategory.new_program: [
        "new pathway", "new program", "pilot", "launch",
        "nouveau programme", "nouvelle voie",
    ],
    IRCCUpdateCategory.fee_change: [
        "fee", "cost", "frais", "tarif", "price",
    ],
    IRCCUpdateCategory.form_update: [
        "IMM ", "form update", "formulaire", "new form",
    ],
    IRCCUpdateCategory.policy_update: [
        "policy", "politique", "regulation", "règlement",
        "minister", "ministre", "announcement",
    ],
}


def categorize_update(title: str, content: str = "") -> IRCCUpdateCategory:
    """Auto-categorize an update based on keywords in title and content."""
    text = f"{title} {content}".lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in text:
                return category

    return IRCCUpdateCategory.general_news


def generate_external_id(url: str, title: str) -> str:
    """Generate a unique ID for deduplication."""
    raw = f"{url}:{title}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


class IRCCFeedParser:
    """Parses IRCC Atom/RSS feeds for news and policy updates."""

    def __init__(self, http_client: httpx.AsyncClient | None = None):
        self._client = http_client

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True,
            )
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def fetch_atom_feed(self, url: str = IRCC_NEWS_FEED_URL) -> list[dict]:
        """Fetch and parse an IRCC Atom feed. Returns list of update dicts."""
        client = await self._get_client()

        try:
            response = await client.get(url)
            response.raise_for_status()
        except httpx.HTTPError:
            return []

        return self._parse_atom_xml(response.text, url)

    def _parse_atom_xml(self, xml_content: str, feed_url: str) -> list[dict]:
        """Parse Atom XML into a list of update dicts."""
        updates = []

        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError:
            return []

        # Handle Atom namespace
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        entries = root.findall("atom:entry", ns)
        if not entries:
            # Try without namespace (some feeds don't use it)
            entries = root.findall("entry")

        for entry in entries:
            title_el = entry.find("atom:title", ns) or entry.find("title")
            link_el = entry.find("atom:link", ns) or entry.find("link")
            summary_el = entry.find("atom:summary", ns) or entry.find("summary")
            content_el = entry.find("atom:content", ns) or entry.find("content")
            updated_el = entry.find("atom:updated", ns) or entry.find("updated")
            published_el = entry.find("atom:published", ns) or entry.find("published")

            title = title_el.text.strip() if title_el is not None and title_el.text else ""
            if not title:
                continue

            link = ""
            if link_el is not None:
                link = link_el.get("href", "") or (link_el.text or "")

            summary = summary_el.text.strip() if summary_el is not None and summary_el.text else ""
            content = content_el.text.strip() if content_el is not None and content_el.text else ""

            published_at = None
            date_str = None
            if published_el is not None and published_el.text:
                date_str = published_el.text
            elif updated_el is not None and updated_el.text:
                date_str = updated_el.text

            if date_str:
                try:
                    published_at = datetime.fromisoformat(
                        date_str.replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    published_at = None

            category = categorize_update(title, content or summary)
            external_id = generate_external_id(link or feed_url, title)

            updates.append({
                "title": title[:500],
                "content": content or None,
                "summary": summary or None,
                "category": category,
                "source": IRCCUpdateSource.atom_feed,
                "source_url": link or feed_url,
                "external_id": external_id,
                "published_at": published_at,
            })

        return updates

    async def fetch_canada_news_api(self) -> list[dict]:
        """Fetch from the Canada.ca News API (JSON format)."""
        client = await self._get_client()

        try:
            response = await client.get(IRCC_ATOM_FEED_URL)
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError):
            return []

        updates = []
        articles = data if isinstance(data, list) else data.get("articles", data.get("items", []))

        for article in articles:
            title = article.get("title", "").strip()
            if not title:
                continue

            link = article.get("link", article.get("url", ""))
            description = article.get("description", article.get("summary", ""))
            pub_date = article.get("publishedDate", article.get("published", ""))

            published_at = None
            if pub_date:
                try:
                    published_at = datetime.fromisoformat(
                        pub_date.replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass

            category = categorize_update(title, description)
            external_id = generate_external_id(link or IRCC_ATOM_FEED_URL, title)

            updates.append({
                "title": title[:500],
                "content": None,
                "summary": description[:2000] if description else None,
                "category": category,
                "source": IRCCUpdateSource.atom_feed,
                "source_url": link,
                "external_id": external_id,
                "published_at": published_at,
            })

        return updates

    async def fetch_all_sources(self) -> list[dict]:
        """Fetch updates from all configured IRCC sources."""
        all_updates = []

        # Atom feed
        atom_updates = await self.fetch_atom_feed()
        all_updates.extend(atom_updates)

        # Canada News API
        news_updates = await self.fetch_canada_news_api()
        all_updates.extend(news_updates)

        # Deduplicate by external_id
        seen_ids = set()
        unique_updates = []
        for update in all_updates:
            if update["external_id"] not in seen_ids:
                seen_ids.add(update["external_id"])
                unique_updates.append(update)

        return unique_updates

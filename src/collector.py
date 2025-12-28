import logging
import random
import time
from datetime import datetime, timedelta
from urllib.parse import urljoin
from xml.etree import ElementTree

import feedparser
import requests
from dateutil import parser as date_parser
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

LOGGER = logging.getLogger(__name__)


def create_session(timeout: int, max_retries: int) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=max_retries,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update(
        {
            "User-Agent": "JuejinWeeklyDigestBot/1.0 (+https://juejin.cn)",
        }
    )
    session.request_timeout = timeout
    return session


def _sleep(min_seconds: float, max_seconds: float) -> None:
    time.sleep(random.uniform(min_seconds, max_seconds))


def fetch_rss_items(session: requests.Session, feed_urls: list[str]) -> list[dict]:
    items: list[dict] = []
    for feed_url in feed_urls:
        try:
            LOGGER.info("Fetching RSS feed: %s", feed_url)
            response = session.get(feed_url, timeout=session.request_timeout)
            response.raise_for_status()
            parsed = feedparser.parse(response.text)
            for entry in parsed.entries:
                items.append(
                    {
                        "title": entry.get("title", "").strip(),
                        "url": entry.get("link", "").strip(),
                        "published": entry.get("published")
                        or entry.get("updated"),
                        "summary": entry.get("summary", "").strip(),
                        "source": "rss",
                    }
                )
        except requests.RequestException as exc:
            LOGGER.warning("RSS feed failed: %s (%s)", feed_url, exc)
    return items


def fetch_sitemap_urls(
    session: requests.Session,
    sitemap_urls: list[str],
    days: int,
    max_urls: int = 200,
    max_sitemaps: int = 5,
) -> list[dict]:
    items: list[dict] = []
    cutoff = datetime.utcnow() - timedelta(days=days)
    for sitemap_url in sitemap_urls[:max_sitemaps]:
        try:
            LOGGER.info("Fetching sitemap: %s", sitemap_url)
            response = session.get(sitemap_url, timeout=session.request_timeout)
            response.raise_for_status()
            root = ElementTree.fromstring(response.text)
            namespace = ""
            if root.tag.startswith("{"):
                namespace = root.tag.split("}")[0] + "}"

            loc_nodes = root.findall(f"{namespace}url/{namespace}loc")
            lastmod_nodes = root.findall(f"{namespace}url/{namespace}lastmod")
            for idx, loc_node in enumerate(loc_nodes):
                if len(items) >= max_urls:
                    return items
                url = loc_node.text.strip() if loc_node.text else ""
                lastmod = None
                if idx < len(lastmod_nodes) and lastmod_nodes[idx].text:
                    lastmod = lastmod_nodes[idx].text.strip()
                if lastmod:
                    try:
                        lastmod_dt = date_parser.parse(lastmod)
                        if lastmod_dt.replace(tzinfo=None) < cutoff:
                            continue
                    except (ValueError, TypeError):
                        pass
                if url:
                    items.append(
                        {
                            "title": "",
                            "url": url,
                            "published": lastmod,
                            "summary": "",
                            "source": "sitemap",
                        }
                    )
        except requests.RequestException as exc:
            LOGGER.warning("Sitemap failed: %s (%s)", sitemap_url, exc)
    return items


def fetch_tag_urls(
    session: requests.Session,
    tag_urls: list[str],
    max_urls: int = 200,
    sleep_min: float = 0.5,
    sleep_max: float = 1.5,
) -> list[dict]:
    from bs4 import BeautifulSoup

    items: list[dict] = []
    for tag_url in tag_urls:
        try:
            LOGGER.info("Fetching tag page: %s", tag_url)
            response = session.get(tag_url, timeout=session.request_timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            for link in soup.find_all("a", href=True):
                href = link["href"].strip()
                if "/post/" in href:
                    url = urljoin(tag_url, href)
                    items.append(
                        {
                            "title": link.get_text(strip=True),
                            "url": url,
                            "published": None,
                            "summary": "",
                            "source": "tag",
                        }
                    )
                if len(items) >= max_urls:
                    break
            _sleep(sleep_min, sleep_max)
        except requests.RequestException as exc:
            LOGGER.warning("Tag page failed: %s (%s)", tag_url, exc)
    return items


def collect_items(session: requests.Session, config: dict) -> list[dict]:
    sources = config.get("sources", {})
    rss_feeds = sources.get("rss_feeds", [])
    sitemap_urls = sources.get("sitemap_urls", [])
    tag_urls = sources.get("tag_urls", [])
    days = config.get("app", {}).get("max_days", 7)

    items = fetch_rss_items(session, rss_feeds)
    if items:
        LOGGER.info("Collected %s items from RSS", len(items))
        return items

    items = fetch_sitemap_urls(session, sitemap_urls, days)
    if items:
        LOGGER.info("Collected %s items from sitemap", len(items))
        return items

    items = fetch_tag_urls(
        session,
        tag_urls,
        sleep_min=config.get("app", {}).get("sleep_min", 0.5),
        sleep_max=config.get("app", {}).get("sleep_max", 1.5),
    )
    LOGGER.info("Collected %s items from tag pages", len(items))
    return items

import logging
import random
import time

from bs4 import BeautifulSoup
import requests

LOGGER = logging.getLogger(__name__)


def _sleep(min_seconds: float, max_seconds: float) -> None:
    time.sleep(random.uniform(min_seconds, max_seconds))


def fetch_content(
    session: requests.Session,
    url: str,
    timeout: int,
    sleep_min: float,
    sleep_max: float,
) -> dict:
    try:
        LOGGER.info("Fetching article: %s", url)
        response = session.get(url, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        LOGGER.warning("Failed to fetch article %s: %s", url, exc)
        return {"content": "", "title": "", "author": "", "tags": []}

    soup = BeautifulSoup(response.text, "html.parser")
    for node in soup(["script", "style", "noscript"]):
        node.decompose()

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    author = ""
    author_meta = soup.find("meta", attrs={"name": "author"})
    if author_meta and author_meta.get("content"):
        author = author_meta["content"].strip()

    tags = [tag.get_text(strip=True) for tag in soup.select("a.tag-link")]

    text = soup.get_text(separator=" ", strip=True)
    _sleep(sleep_min, sleep_max)
    return {"content": text, "title": title, "author": author, "tags": tags}

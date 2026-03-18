"""Base scraper class with common HTTP utilities."""

import random
import time
from abc import ABC, abstractmethod
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import REQUEST_TIMEOUT, REQUEST_DELAY, MAX_RETRIES, USER_AGENTS


class TenderItem:
    """Represents a single tender/bid result."""

    def __init__(
        self,
        title: str,
        source: str,
        source_url: Optional[str] = None,
        publish_date: Optional[str] = None,
        deadline: Optional[str] = None,
        budget: Optional[str] = None,
        region: Optional[str] = None,
        category: Optional[str] = None,
        raw_content: Optional[str] = None,
    ):
        self.title = title.strip()
        self.source = source
        self.source_url = source_url
        self.publish_date = publish_date
        self.deadline = deadline
        self.budget = budget
        self.region = region
        self.category = category
        self.raw_content = raw_content

    def __repr__(self):
        return f"TenderItem(title={self.title!r}, source={self.source!r})"


class BaseScraper(ABC):
    """Base class for all scrapers."""

    source_name: str = "unknown"
    source_key: str = "unknown"

    def __init__(self):
        self.session = self._make_session()

    def _make_session(self) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=MAX_RETRIES,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update({"User-Agent": random.choice(USER_AGENTS)})
        return session

    def _get(self, url: str, params: Optional[dict] = None, **kwargs) -> Optional[requests.Response]:
        try:
            time.sleep(REQUEST_DELAY + random.uniform(0, 1))
            resp = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            print(f"[{self.source_name}] GET {url} failed: {e}")
            return None

    def _post(self, url: str, data: Optional[dict] = None, json: Optional[dict] = None, **kwargs) -> Optional[requests.Response]:
        try:
            time.sleep(REQUEST_DELAY + random.uniform(0, 1))
            resp = self.session.post(url, data=data, json=json, timeout=REQUEST_TIMEOUT, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            print(f"[{self.source_name}] POST {url} failed: {e}")
            return None

    @abstractmethod
    def search(self, keyword: str, page: int = 1) -> list[TenderItem]:
        """Search for tenders matching the keyword."""
        ...

    def search_all_pages(self, keyword: str, max_pages: int = 5) -> list[TenderItem]:
        """Search across multiple pages."""
        results = []
        for page in range(1, max_pages + 1):
            items = self.search(keyword, page)
            if not items:
                break
            results.extend(items)
        return results

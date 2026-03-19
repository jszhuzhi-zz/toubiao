"""Scraper for 标标达 (bbda.com)."""

import re
from typing import Optional

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, TenderItem


class BBDAScraper(BaseScraper):
    """标标达爬虫"""

    source_name = "标标达"
    source_key = "bbda"
    base_url = "https://www.bbda.com"

    def __init__(self):
        super().__init__()
        self._fetched = False  # bbda ignores keyword; only fetch the list once per run

    def search(self, keyword: str, page: int = 1) -> list[TenderItem]:
        # bbda.com does NOT filter by keyword server-side — the same general
        # list is returned regardless of the keyword param.  Pagination is
        # handled by search_all_pages() below, so this method is a no-op.
        return []

    def search_all_pages(self, keyword: str, max_pages: int = 5) -> list[TenderItem]:
        # Override: scrape the general recent-bids list exactly once per
        # scraper instance (ignore keyword — db deduplication handles repeats).
        if self._fetched:
            return []
        self._fetched = True

        results = []
        for page in range(1, max_pages + 1):
            page_suffix = page - 1
            url = f"{self.base_url}/bidlist/i_zhaobiao_0_{page_suffix}.html"
            resp = self._get(url, headers={
                "Referer": "https://www.bbda.com/",
                "Accept-Language": "zh-CN,zh;q=0.9",
            })
            if not resp:
                break
            items = self._parse(resp.content)
            if not items:
                break
            results.extend(items)
        return results

    def _parse(self, html) -> list[TenderItem]:
        soup = BeautifulSoup(html, "lxml")
        items = []

        for item in soup.select("a.recommend-item"):
            title_tag = item.select_one(".right_item_title")
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            href = item.get("href", "")
            url = (self.base_url + href) if href and not href.startswith("http") else href

            bottom = item.select_one(".bottom-row")
            bottom_text = bottom.get_text(" ", strip=True) if bottom else ""

            publish_date = self._extract_date(bottom_text)
            region = self._extract_region(bottom_text)

            full_text = item.get_text(" ", strip=True)

            items.append(TenderItem(
                title=title,
                source=self.source_name,
                source_url=url,
                publish_date=publish_date,
                region=region,
                raw_content=full_text[:500],
            ))

        return items

    def _extract_date(self, text: str) -> Optional[str]:
        m = re.search(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})", text)
        if m:
            return m.group(1).replace("/", "-")
        return None

    def _extract_region(self, text: str) -> Optional[str]:
        provinces = [
            "北京", "上海", "天津", "重庆", "广东", "浙江", "江苏", "山东",
            "四川", "湖北", "湖南", "福建", "陕西", "辽宁", "河南", "河北",
            "安徽", "云南", "贵州", "广西", "内蒙古", "新疆", "西藏",
            "黑龙江", "吉林", "甘肃", "青海", "宁夏", "海南", "深圳",
        ]
        for p in provinces:
            if p in text:
                return p
        return None

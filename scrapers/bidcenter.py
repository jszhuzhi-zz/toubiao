"""Scraper for 中国招标投标公共服务平台 (bidcenter.com.cn)."""

import re
from typing import Optional

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, TenderItem


class BidCenterScraper(BaseScraper):
    """中国招标投标公共服务平台爬虫"""

    source_name = "中国招标投标公共服务平台"
    source_key = "bidcenter"
    search_url = "https://www.bidcenter.com.cn/search.html"

    def search(self, keyword: str, page: int = 1) -> list[TenderItem]:
        params = {
            "q": keyword,
            "pn": str(page),
            "tr": "3",  # 最近3个月
        }

        resp = self._get(self.search_url, params=params, headers={
            "Referer": "https://www.bidcenter.com.cn/",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        if not resp:
            return []

        resp.encoding = resp.apparent_encoding or "utf-8"
        return self._parse(resp.text)

    def _parse(self, html: str) -> list[TenderItem]:
        soup = BeautifulSoup(html, "lxml")
        items = []

        selectors = [
            "ul.searchResult li",
            ".result-list li",
            ".search-result .item",
            "div.notice-item",
        ]

        li_elements = []
        for sel in selectors:
            li_elements = soup.select(sel)
            if li_elements:
                break

        for li in li_elements:
            title_tag = li.select_one("a.title, h3 a, .notice-title a, a[href*='notice']")
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            if not title:
                continue

            url = title_tag.get("href", "")
            if url and not url.startswith("http"):
                url = "https://www.bidcenter.com.cn" + url

            text = li.get_text(" ", strip=True)
            publish_date = self._extract_date(text)
            region = self._extract_region(li)
            budget = self._extract_budget(text)
            category = self._extract_category(li)

            items.append(TenderItem(
                title=title,
                source=self.source_name,
                source_url=url,
                publish_date=publish_date,
                region=region,
                budget=budget,
                category=category,
                raw_content=text[:500],
            ))

        return items

    def _extract_date(self, text: str) -> Optional[str]:
        m = re.search(r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})", text)
        if m:
            return re.sub(r"[年月]", "-", m.group(1)).strip("-")
        return None

    def _extract_region(self, li) -> Optional[str]:
        for span in li.select("span, .area, .region"):
            t = span.get_text(strip=True)
            if len(t) <= 6 and any(p in t for p in ["省", "市", "区", "自治区"]):
                return t
        return None

    def _extract_budget(self, text: str) -> Optional[str]:
        m = re.search(r"预算[：:]\s*([^\s，,。]+)", text)
        if m:
            return m.group(1)
        m = re.search(r"([0-9,.]+\s*[万亿]元)", text)
        return m.group(1) if m else None

    def _extract_category(self, li) -> Optional[str]:
        cat_tag = li.select_one(".category, .type, [class*='type']")
        if cat_tag:
            return cat_tag.get_text(strip=True)
        return None

"""Scraper for 中国政府采购网 (ccgp.gov.cn)."""

import re
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, TenderItem


class CCGPScraper(BaseScraper):
    """中国政府采购网爬虫"""

    source_name = "中国政府采购网"
    source_key = "ccgp"
    base_url = "https://search.ccgp.gov.cn/bxsearch"

    def search(self, keyword: str, page: int = 1) -> list[TenderItem]:
        params = {
            "searchtype": "1",
            "page_index": str(page),
            "bidSort": "0",
            "pinMu": "0",
            "bidSize": "20",
            "timeType": "6",
            "dbselect": "bidx",
            "kw": keyword,
            "start_time": "",
            "end_time": "",
            "pcodeJoint": "0",
        }

        resp = self._get(self.base_url, params=params, headers={
            "Referer": "https://www.ccgp.gov.cn/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        if not resp:
            return []

        return self._parse(resp.text)

    def _parse(self, html: str) -> list[TenderItem]:
        soup = BeautifulSoup(html, "lxml")
        items = []

        for li in soup.select("ul.vT-srch-result-list-bid li"):
            title_tag = li.select_one("a")
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            url = title_tag.get("href", "")
            if url and not url.startswith("http"):
                url = urljoin("https://www.ccgp.gov.cn", url)

            # Extract metadata from list item text
            text = li.get_text(" ", strip=True)
            publish_date = self._extract_date(text)
            region = self._extract_region(li)
            budget = self._extract_budget(text)

            items.append(TenderItem(
                title=title,
                source=self.source_name,
                source_url=url,
                publish_date=publish_date,
                region=region,
                budget=budget,
                raw_content=text,
            ))

        return items

    def _extract_date(self, text: str) -> Optional[str]:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", text)
        return m.group(1) if m else None

    def _extract_region(self, li) -> Optional[str]:
        region_tag = li.select_one(".vT-srch-result-list-bid-region, [class*='region']")
        if region_tag:
            return region_tag.get_text(strip=True)
        # Try to find province names in text
        text = li.get_text(" ", strip=True)
        provinces = [
            "北京", "上海", "天津", "重庆", "广东", "浙江", "江苏", "山东",
            "四川", "湖北", "湖南", "福建", "陕西", "辽宁", "河南", "河北",
            "安徽", "云南", "贵州", "广西", "内蒙古", "新疆", "西藏",
            "黑龙江", "吉林", "甘肃", "青海", "宁夏", "海南",
        ]
        for p in provinces:
            if p in text:
                return p
        return None

    def _extract_budget(self, text: str) -> Optional[str]:
        m = re.search(r"预算[金额]*[：:]\s*([0-9,.万亿元]+)", text)
        if m:
            return m.group(1)
        m = re.search(r"([0-9,.]+\s*万元)", text)
        return m.group(1) if m else None

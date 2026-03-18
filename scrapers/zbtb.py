"""Scraper for 招标天下 (zbtb.cn)."""

import re
from typing import Optional

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, TenderItem


class ZBTBScraper(BaseScraper):
    """招标天下爬虫"""

    source_name = "招标天下"
    source_key = "zbtb"
    search_url = "https://www.zbtb.cn/index/search.html"

    def search(self, keyword: str, page: int = 1) -> list[TenderItem]:
        params = {
            "keyword": keyword,
            "page": str(page),
            "type": "0",  # 0=全部
        }

        resp = self._get(self.search_url, params=params, headers={
            "Referer": "https://www.zbtb.cn/",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        if not resp:
            return []

        return self._parse(resp.text)

    def _parse(self, html: str) -> list[TenderItem]:
        soup = BeautifulSoup(html, "lxml")
        items = []

        for item in soup.select(".search-list .item, .result-item, li.tender-item"):
            title_tag = item.select_one("a.title, h3 a, .name a, a[href*='detail']")
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            url = title_tag.get("href", "")
            if url and not url.startswith("http"):
                url = "https://www.zbtb.cn" + url

            text = item.get_text(" ", strip=True)
            publish_date = self._extract_date(text)
            region = self._extract_region(text)
            budget = self._extract_budget(text)

            items.append(TenderItem(
                title=title,
                source=self.source_name,
                source_url=url,
                publish_date=publish_date,
                region=region,
                budget=budget,
                raw_content=text[:500],
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

    def _extract_budget(self, text: str) -> Optional[str]:
        m = re.search(r"([0-9,.]+\s*[万亿]元)", text)
        return m.group(1) if m else None

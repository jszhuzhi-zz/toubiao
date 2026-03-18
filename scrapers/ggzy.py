"""Scraper for 全国公共资源交易平台 (ggzy.gov.cn)."""

import re
from typing import Optional

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, TenderItem


class GGZYScraper(BaseScraper):
    """全国公共资源交易平台爬虫"""

    source_name = "全国公共资源交易平台"
    source_key = "ggzy"
    search_url = "https://deal.ggzy.gov.cn/ds/deal/dealList_find.jsp"

    def search(self, keyword: str, page: int = 1) -> list[TenderItem]:
        # GGZY uses POST with form data
        data = {
            "DEAL_STAGE": "1000",    # 招标公告
            "DEAL_TYPE": "01",       # 工程类
            "DEAL_TIME": "0",        # 不限时间
            "BID_INVITE_TYPE": "00",
            "keyWord": keyword,
            "pageNo": str(page),
            "pageSize": "15",
            "AREA_ID": "00",         # 全国
            "sourceType": "1",
        }

        resp = self._post(self.search_url, data=data, headers={
            "Referer": "https://deal.ggzy.gov.cn/",
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Requested-With": "XMLHttpRequest",
        })
        if not resp:
            return []

        try:
            json_data = resp.json()
            return self._parse_json(json_data)
        except Exception:
            return self._parse_html(resp.text)

    def _parse_json(self, data: dict) -> list[TenderItem]:
        items = []
        records = data.get("data", data.get("rows", data.get("records", [])))
        if not isinstance(records, list):
            return []

        for r in records:
            title = r.get("DEAL_NAME", r.get("projectName", ""))
            if not title:
                continue

            items.append(TenderItem(
                title=title,
                source=self.source_name,
                source_url=r.get("url", r.get("detailUrl", "")),
                publish_date=r.get("DEAL_TIME", r.get("publishTime", "")),
                deadline=r.get("BID_OPEN_TIME", ""),
                budget=r.get("DEAL_MONEY", r.get("budget", "")),
                region=r.get("AREA_NAME", r.get("region", "")),
                category=r.get("DEAL_TYPE_NAME", ""),
            ))

        return items

    def _parse_html(self, html: str) -> list[TenderItem]:
        soup = BeautifulSoup(html, "lxml")
        items = []

        for tr in soup.select("table.deal-list tr, tbody tr"):
            cells = tr.select("td")
            if len(cells) < 3:
                continue

            title_tag = tr.select_one("a")
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            url = title_tag.get("href", "")

            text = tr.get_text(" ", strip=True)
            publish_date = self._extract_date(text)
            region = cells[-1].get_text(strip=True) if len(cells) > 3 else None

            items.append(TenderItem(
                title=title,
                source=self.source_name,
                source_url=url,
                publish_date=publish_date,
                region=region,
                raw_content=text[:300],
            ))

        return items

    def _extract_date(self, text: str) -> Optional[str]:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", text)
        return m.group(1) if m else None

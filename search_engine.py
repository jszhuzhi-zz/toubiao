"""Core search and keyword matching engine."""

import re
from typing import Optional

from config import DEFAULT_KEYWORDS, get_keywords
from database import insert_tender
from scrapers.base import TenderItem


def find_matched_keywords(text: str, keywords: Optional[list[str]] = None) -> list[str]:
    """Find which keywords appear in the text (case-insensitive)."""
    if keywords is None:
        keywords = get_keywords()

    text_lower = text.lower()
    matched = []
    for kw in keywords:
        # For English keywords (VR, MR, AR), match as whole word
        if re.match(r'^[A-Za-z]+$', kw):
            if re.search(r'\b' + re.escape(kw) + r'\b', text, re.IGNORECASE):
                matched.append(kw)
        else:
            if kw.lower() in text_lower:
                matched.append(kw)

    return matched


def is_relevant(item: TenderItem, keywords: Optional[list[str]] = None) -> list[str]:
    """Check if a tender item is relevant. Returns matched keywords or empty list."""
    search_text = " ".join(filter(None, [item.title, item.raw_content]))
    return find_matched_keywords(search_text, keywords)


def categorize_item(matched_keywords: list[str]) -> str:
    """Categorize a tender by which keyword groups match."""
    categories = []
    for cat_name, kws in DEFAULT_KEYWORDS.items():
        if any(kw in matched_keywords for kw in kws):
            categories.append(cat_name)
    return "+".join(categories) if categories else "其他"


def save_item(item: TenderItem, matched_keywords: list[str]) -> bool:
    """Save a tender item to the database."""
    category = categorize_item(matched_keywords)
    return insert_tender(
        title=item.title,
        source=item.source,
        source_url=item.source_url,
        publish_date=item.publish_date,
        deadline=item.deadline,
        budget=item.budget,
        region=item.region,
        category=category,
        matched_keywords=matched_keywords,
        raw_content=item.raw_content,
    )


def run_search(
    scraper_list,
    keywords: Optional[list[str]] = None,
    max_pages: int = 3,
    on_progress=None,
) -> dict:
    """
    Run search across all scrapers for all keywords.
    Returns summary stats.
    """
    if keywords is None:
        keywords = get_keywords()

    stats = {
        "searched": 0,
        "found": 0,
        "saved": 0,
        "duplicates": 0,
        "by_source": {},
    }

    # Deduplicate: use a set of representative keywords to search
    # (don't search every keyword - group by representative terms)
    search_terms = _get_search_terms()

    for scraper in scraper_list:
        source_stats = {"found": 0, "saved": 0}

        for term in search_terms:
            if on_progress:
                on_progress(f"[{scraper.source_name}] 搜索: {term}")

            items = scraper.search_all_pages(term, max_pages=max_pages)
            stats["searched"] += 1

            for item in items:
                matched = is_relevant(item, keywords)
                if not matched:
                    # Still check title directly since content may be truncated
                    matched = find_matched_keywords(item.title, keywords)

                if matched:
                    source_stats["found"] += 1
                    stats["found"] += 1
                    saved = save_item(item, matched)
                    if saved:
                        source_stats["saved"] += 1
                        stats["saved"] += 1
                    else:
                        stats["duplicates"] += 1

        stats["by_source"][scraper.source_name] = source_stats

    return stats


def _get_search_terms() -> list[str]:
    """Get representative search terms (deduplicated) for querying APIs."""
    # Use a subset of keywords to avoid too many requests
    # These are the most distinctive/effective search terms
    return [
        "文旅",
        "智慧文旅",
        "旅游景区",
        "博物馆",
        "虚拟现实",
        "VR",
        "MR",
        "增强现实",
        "沉浸式",
        "元宇宙",
        "数字孪生",
        "智慧景区",
    ]

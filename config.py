"""Configuration for the tender tracking system."""

import json
import os
from pathlib import Path

# Data directory
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "tenders.db"

# Default keywords for filtering
DEFAULT_KEYWORDS = {
    "文旅": [
        "文旅", "文化旅游", "智慧文旅", "旅游景区", "景区管理", "文化馆",
        "博物馆", "旅游局", "文化局", "文旅局", "旅游信息化", "景区票务",
        "文化产业", "旅游平台", "游客服务", "文旅融合", "旅游大数据",
        "文化遗址", "遗产保护", "文物保护", "旅游导览", "智慧景区",
        "演艺", "剧院", "文化中心", "艺术中心",
    ],
    "VR/MR": [
        "VR", "MR", "AR", "XR", "虚拟现实", "混合现实", "增强现实",
        "元宇宙", "metaverse", "沉浸式", "全息", "数字孪生", "虚拟仿真",
        "虚拟体验", "头盔显示", "头显", "HMD", "空间计算",
        "虚拟展览", "数字展厅", "数字化展示", "互动展示",
    ],
}

# Combined keyword list for quick matching
ALL_KEYWORDS = []
for category, kws in DEFAULT_KEYWORDS.items():
    ALL_KEYWORDS.extend(kws)

# Search sources
SOURCES = {
    "ccgp": {
        "name": "中国政府采购网",
        "url": "https://search.ccgp.gov.cn/bxsearch",
        "enabled": True,
    },
    "bidcenter": {
        "name": "中国招标投标公共服务平台",
        "url": "https://www.bidcenter.com.cn",
        "enabled": True,
    },
    "chinatender": {
        "name": "中国采购与招标网",
        "url": "https://www.chinabidding.com",
        "enabled": True,
    },
    "ggzy": {
        "name": "全国公共资源交易平台",
        "url": "https://deal.ggzy.gov.cn",
        "enabled": True,
    },
    "zbtb": {
        "name": "招标天下",
        "url": "https://www.zbtb.cn",
        "enabled": True,
    },
    "bbda": {
        "name": "标标达",
        "url": "https://www.bbda.com",
        "enabled": True,
    },
}

# HTTP request settings
REQUEST_TIMEOUT = 30
REQUEST_DELAY = 2  # seconds between requests to avoid rate limiting
MAX_RETRIES = 3

# User agents to rotate
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

# Config file path for user overrides
CONFIG_FILE = DATA_DIR / "config.json"


def load_user_config() -> dict:
    """Load user configuration overrides."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}


def save_user_config(config: dict):
    """Save user configuration."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_keywords() -> list[str]:
    """Get all active keywords (user overrides + defaults)."""
    user_config = load_user_config()
    if "keywords" in user_config:
        return user_config["keywords"]
    return ALL_KEYWORDS

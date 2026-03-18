# 投标追踪搜索器

专注于**文旅系统**和**VR/MR**相关招标信息的自动追踪工具。

## 功能

- 多平台同时搜索（中国政府采购网、全国公共资源交易平台等5个主流平台）
- 智能关键词过滤，区分"文旅"和"VR/MR"两大类目
- 本地 SQLite 数据库，自动去重
- 定时自动抓取，无需人工干预
- 支持按关键词、地区、日期过滤查询
- 支持 CSV 导出

## 安装

```bash
pip install -r requirements.txt
```

## 使用

```bash
# 抓取最新招标（首次使用或手动刷新）
python main.py fetch

# 查看所有招标
python main.py list

# 只看最近7天
python main.py list --days 7

# 搜索特定关键词
python main.py search "虚拟现实"
python main.py search "博物馆"

# 按地区过滤
python main.py list --region 广东

# 导出为CSV
python main.py list --export results.csv

# 查看某条详情
python main.py detail 1

# 查看统计信息
python main.py stats

# 管理关键词
python main.py keywords              # 查看当前关键词
python main.py keywords --add "剧院"  # 添加自定义关键词
python main.py keywords --remove "演艺"  # 删除关键词
python main.py keywords --reset      # 重置为默认

# 定时自动抓取（每60分钟一次）
python main.py schedule
python main.py schedule --interval 30  # 每30分钟
```

## 数据来源

| 平台 | 说明 |
|------|------|
| 中国政府采购网 (ccgp.gov.cn) | 政府采购核心平台 |
| 全国公共资源交易平台 (ggzy.gov.cn) | 工程招标为主 |
| 中国招标投标公共服务平台 (bidcenter.com.cn) | 全类型招标 |
| 中国采购与招标网 (chinabidding.com) | 全类型招标 |
| 招标天下 (zbtb.cn) | 聚合搜索 |

## 关键词分类

**文旅类：** 文旅、智慧文旅、旅游景区、博物馆、文化馆、智慧景区、旅游信息化…

**VR/MR类：** VR、MR、AR、XR、虚拟现实、混合现实、增强现实、元宇宙、沉浸式、全息…

#!/usr/bin/env python3
"""
投标追踪搜索器 - 跟踪文旅系统和VR/MR相关招标信息

Usage:
    python main.py fetch          # 抓取最新招标信息
    python main.py list           # 查看已收集的招标
    python main.py search <关键词>  # 搜索特定关键词
    python main.py stats          # 查看统计信息
    python main.py keywords       # 查看/管理关键词
    python main.py schedule       # 定时自动抓取
"""

import sys
import csv
import io
from datetime import datetime
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box
from rich.text import Text

import database
import config
from search_engine import run_search

console = Console()


def get_scrapers(sources: Optional[tuple] = None):
    """Instantiate scrapers for specified sources (or all enabled)."""
    from scrapers.ccgp import CCGPScraper
    from scrapers.bidcenter import BidCenterScraper
    from scrapers.chinatender import ChinaTenderScraper
    from scrapers.ggzy import GGZYScraper
    from scrapers.zbtb import ZBTBScraper

    all_scrapers = {
        "ccgp": CCGPScraper,
        "bidcenter": BidCenterScraper,
        "chinatender": ChinaTenderScraper,
        "ggzy": GGZYScraper,
        "zbtb": ZBTBScraper,
    }

    if sources:
        return [cls() for key, cls in all_scrapers.items() if key in sources]

    # Use enabled ones from config
    enabled = [k for k, v in config.SOURCES.items() if v.get("enabled")]
    return [cls() for key, cls in all_scrapers.items() if key in enabled]


def render_tenders_table(rows, title: str = "招标信息"):
    table = Table(
        title=title,
        box=box.ROUNDED,
        show_lines=True,
        expand=True,
        title_style="bold cyan",
    )
    table.add_column("序号", style="dim", width=4, justify="right")
    table.add_column("标题", min_width=30, max_width=60, no_wrap=False)
    table.add_column("来源", width=14, style="blue")
    table.add_column("日期", width=11, style="green")
    table.add_column("地区", width=8)
    table.add_column("预算", width=12, style="yellow")
    table.add_column("匹配关键词", width=20, style="magenta")

    for i, row in enumerate(rows, 1):
        kw_text = row["matched_keywords"] or ""
        # Highlight VR/MR keywords differently
        kw_parts = kw_text.split(",")
        kw_display = " ".join(f"[{kw}]" for kw in kw_parts if kw)

        table.add_row(
            str(i),
            row["title"],
            row["source"],
            row["publish_date"] or "-",
            row["region"] or "-",
            row["budget"] or "-",
            kw_display,
        )

    console.print(table)


@click.group()
def cli():
    """投标追踪搜索器 - 文旅/VR/MR相关招标监控工具"""
    database.init_db()


@cli.command()
@click.option("--source", "-s", multiple=True,
              help="指定数据源 (ccgp/bidcenter/chinatender/ggzy/zbtb)")
@click.option("--pages", "-p", default=3, show_default=True,
              help="每个关键词抓取页数")
@click.option("--verbose", "-v", is_flag=True, help="显示详细进度")
def fetch(source, pages, verbose):
    """抓取最新招标信息"""
    scrapers = get_scrapers(source if source else None)
    if not scrapers:
        console.print("[red]没有可用的数据源[/red]")
        return

    source_names = ", ".join(s.source_name for s in scrapers)
    console.print(Panel(
        f"[bold]开始抓取招标信息[/bold]\n"
        f"数据源: {source_names}\n"
        f"每词页数: {pages}",
        title="投标追踪器",
        style="cyan",
    ))

    progress_messages = []

    def on_progress(msg: str):
        if verbose:
            console.print(f"  [dim]{msg}[/dim]")
        progress_messages.append(msg)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("正在搜索...", total=None)

        def _progress(msg):
            progress.update(task, description=msg)
            on_progress(msg)

        stats = run_search(scrapers, max_pages=pages, on_progress=_progress)

    # Summary
    console.print("\n")
    console.print(Panel(
        f"[green]✓ 搜索完成[/green]\n\n"
        f"发现相关招标: [bold yellow]{stats['found']}[/bold yellow] 条\n"
        f"新增入库: [bold green]{stats['saved']}[/bold green] 条\n"
        f"重复跳过: [dim]{stats['duplicates']}[/dim] 条",
        title="抓取结果",
        style="green",
    ))

    for src_name, src_stats in stats["by_source"].items():
        console.print(f"  {src_name}: 发现 {src_stats['found']} 条, 新增 {src_stats['saved']} 条")


@cli.command("list")
@click.option("--keyword", "-k", default=None, help="过滤关键词")
@click.option("--region", "-r", default=None, help="过滤地区")
@click.option("--source", "-s", default=None, help="过滤来源")
@click.option("--days", "-d", default=None, type=int, help="最近N天")
@click.option("--limit", "-n", default=30, show_default=True, help="显示条数")
@click.option("--offset", default=0, help="分页偏移")
@click.option("--export", "-e", type=click.Path(), default=None,
              help="导出到CSV文件")
def list_tenders(keyword, region, source, days, limit, offset, export):
    """查看已收集的招标信息"""
    rows = database.query_tenders(
        keyword=keyword,
        source=source,
        region=region,
        days=days,
        limit=limit,
        offset=offset,
    )

    if not rows:
        console.print("[yellow]没有找到匹配的招标信息。运行 'python main.py fetch' 先抓取数据。[/yellow]")
        return

    title_parts = ["招标信息"]
    if keyword:
        title_parts.append(f"关键词: {keyword}")
    if region:
        title_parts.append(f"地区: {region}")
    if days:
        title_parts.append(f"最近{days}天")

    title = " | ".join(title_parts)

    if export:
        _export_csv(rows, export)
        console.print(f"[green]已导出 {len(rows)} 条到 {export}[/green]")
    else:
        render_tenders_table(rows, title)
        total = database.count_tenders(keyword=keyword, days=days)
        console.print(f"\n[dim]显示 {offset+1}-{offset+len(rows)} / 共 {total} 条[/dim]")
        if offset + len(rows) < total:
            console.print(f"[dim]查看更多: python main.py list --offset {offset+limit}[/dim]")


def _export_csv(rows, filepath: str):
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["标题", "来源", "发布日期", "截止日期", "地区", "预算", "类别", "匹配关键词", "链接", "抓取时间"])
        for row in rows:
            writer.writerow([
                row["title"],
                row["source"],
                row["publish_date"] or "",
                row["deadline"] or "",
                row["region"] or "",
                row["budget"] or "",
                row["category"] or "",
                row["matched_keywords"] or "",
                row["source_url"] or "",
                row["fetched_at"],
            ])


@cli.command()
@click.argument("query")
@click.option("--limit", "-n", default=20, show_default=True)
def search(query, limit):
    """在已收集数据中搜索"""
    rows = database.query_tenders(keyword=query, limit=limit)
    if not rows:
        console.print(f"[yellow]没有找到包含 '{query}' 的招标信息[/yellow]")
        return
    render_tenders_table(rows, f"搜索: {query}")
    console.print(f"\n[dim]共 {len(rows)} 条结果[/dim]")


@cli.command()
def stats():
    """查看数据库统计信息"""
    s = database.get_stats()

    console.print(Panel(
        f"[bold]数据库统计[/bold]\n\n"
        f"总招标数: [bold yellow]{s['total']}[/bold yellow]\n"
        f"最近7天新增: [bold green]{s['recent_7d']}[/bold green]",
        title="统计信息",
        style="cyan",
    ))

    if s["by_source"]:
        table = Table(title="按来源统计", box=box.SIMPLE)
        table.add_column("数据源", style="blue")
        table.add_column("数量", justify="right", style="yellow")
        for src, cnt in s["by_source"]:
            table.add_row(src, str(cnt))
        console.print(table)

    # Category breakdown
    with database.get_conn() as conn:
        cats = conn.execute(
            "SELECT category, COUNT(*) as cnt FROM tenders WHERE category IS NOT NULL GROUP BY category ORDER BY cnt DESC"
        ).fetchall()
    if cats:
        table2 = Table(title="按类别统计", box=box.SIMPLE)
        table2.add_column("类别", style="magenta")
        table2.add_column("数量", justify="right", style="yellow")
        for row in cats:
            table2.add_row(row["category"], str(row["cnt"]))
        console.print(table2)


@cli.command()
@click.option("--add", "-a", multiple=True, help="添加关键词")
@click.option("--remove", "-r", multiple=True, help="删除关键词")
@click.option("--reset", is_flag=True, help="重置为默认关键词")
def keywords(add, remove, reset):
    """查看和管理搜索关键词"""
    if reset:
        user_cfg = config.load_user_config()
        user_cfg.pop("keywords", None)
        config.save_user_config(user_cfg)
        console.print("[green]已重置为默认关键词[/green]")
        return

    current = config.get_keywords()

    if add or remove:
        if add:
            for kw in add:
                if kw not in current:
                    current.append(kw)
                    console.print(f"[green]+ 已添加: {kw}[/green]")
        if remove:
            for kw in remove:
                if kw in current:
                    current.remove(kw)
                    console.print(f"[red]- 已删除: {kw}[/red]")
        user_cfg = config.load_user_config()
        user_cfg["keywords"] = current
        config.save_user_config(user_cfg)

    # Display current keywords by category
    console.print("\n[bold]当前关键词:[/bold]\n")
    for cat_name, kws in config.DEFAULT_KEYWORDS.items():
        active = [kw for kw in kws if kw in current]
        console.print(f"  [cyan]{cat_name}[/cyan]: {', '.join(active)}")

    custom = [kw for kw in current if not any(
        kw in kws for kws in config.DEFAULT_KEYWORDS.values()
    )]
    if custom:
        console.print(f"  [magenta]自定义[/magenta]: {', '.join(custom)}")

    console.print(f"\n  共 [bold]{len(current)}[/bold] 个关键词")


@cli.command()
@click.option("--interval", "-i", default=60, show_default=True,
              help="抓取间隔（分钟）")
@click.option("--pages", "-p", default=2, show_default=True)
def schedule(interval, pages):
    """定时自动抓取（后台持续运行）"""
    import schedule as sched
    import time

    def job():
        console.print(f"\n[cyan][{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始定时抓取...[/cyan]")
        scrapers = get_scrapers()
        stats = run_search(scrapers, max_pages=pages)
        console.print(f"[green]完成: 发现 {stats['found']} 条, 新增 {stats['saved']} 条[/green]")

    console.print(Panel(
        f"[bold]定时抓取已启动[/bold]\n"
        f"抓取间隔: 每 {interval} 分钟\n"
        f"按 Ctrl+C 停止",
        style="cyan",
    ))

    job()  # Run immediately
    sched.every(interval).minutes.do(job)

    try:
        while True:
            sched.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        console.print("\n[yellow]定时任务已停止[/yellow]")


@cli.command()
@click.argument("tender_id", type=int)
def detail(tender_id):
    """查看招标详情"""
    with database.get_conn() as conn:
        row = conn.execute("SELECT * FROM tenders WHERE id = ?", (tender_id,)).fetchone()

    if not row:
        console.print(f"[red]找不到 ID={tender_id} 的招标记录[/red]")
        return

    console.print(Panel(
        f"[bold]{row['title']}[/bold]\n\n"
        f"来源: [blue]{row['source']}[/blue]\n"
        f"发布日期: [green]{row['publish_date'] or '未知'}[/green]\n"
        f"截止日期: {row['deadline'] or '未知'}\n"
        f"地区: {row['region'] or '未知'}\n"
        f"预算: [yellow]{row['budget'] or '未知'}[/yellow]\n"
        f"类别: {row['category'] or '未知'}\n"
        f"匹配关键词: [magenta]{row['matched_keywords'] or ''}[/magenta]\n"
        f"链接: [underline]{row['source_url'] or '无'}[/underline]\n"
        f"抓取时间: [dim]{row['fetched_at']}[/dim]",
        title=f"招标详情 #{tender_id}",
        style="cyan",
    ))

    if row["raw_content"]:
        console.print(Panel(row["raw_content"], title="原始内容", style="dim"))


if __name__ == "__main__":
    cli()

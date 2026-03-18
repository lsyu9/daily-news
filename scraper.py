#!/usr/bin/env python3
"""
Daily News Scraper
==================
每天由 GitHub Actions 自动运行，从多个 RSS 源爬取新闻，
生成 data.json 供前端 index.html 读取展示。

支持的新闻源：
- Polymarket Blog
- CoinDesk (加密/宏观)
- Hacker News (科技)
- GitHub Trending

可自行在 NEWS_SOURCES 中添加更多 RSS 源。
"""

import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

# ============================================================
# 配置区：在这里添加/修改你的 RSS 新闻源
# ============================================================
NEWS_SOURCES = [
    {
        "name": "Polymarket 动态",
        "rss_url": "https://polymarket.com/blog/rss.xml",
        "max_items": 3,
    },
    {
        "name": "CoinDesk",
        "rss_url": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "max_items": 3,
    },
    {
        "name": "Hacker News",
        "rss_url": "https://hnrss.org/frontpage",
        "max_items": 3,
    },
    {
        "name": "GitHub Trending",
        "rss_url": "https://rsshub.app/github/trending/daily/any",
        "max_items": 3,
    },
]

# 输出文件路径（相对于仓库根目录）
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")


def fetch_rss(url, timeout=15):
    """获取 RSS XML 内容"""
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; DailyNewsBot/1.0)"
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  ⚠️ 无法获取 {url}: {e}")
        return None


def strip_html(text):
    """移除 HTML 标签，只保留纯文本"""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", "", text)
    clean = clean.strip()
    # 截断过长的摘要
    if len(clean) > 200:
        clean = clean[:200] + "..."
    return clean


def parse_rss(xml_text, source_name, max_items=5):
    """解析 RSS/Atom XML，返回新闻列表"""
    items = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        print(f"  ⚠️ XML 解析失败 ({source_name}): {e}")
        return items

    # 处理 RSS 2.0 格式
    for item in root.iter("item"):
        if len(items) >= max_items:
            break
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "#").strip()
        desc = item.findtext("description", "").strip()
        pub_date = item.findtext("pubDate", "").strip()

        if title:
            items.append({
                "source": source_name,
                "title": title,
                "summary": strip_html(desc),
                "time": pub_date if pub_date else datetime.now().strftime("%Y-%m-%d %H:%M"),
                "url": link,
            })

    # 如果没找到 RSS item，尝试 Atom 格式
    if not items:
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.iter("{http://www.w3.org/2005/Atom}entry"):
            if len(items) >= max_items:
                break
            title = ""
            title_el = entry.find("atom:title", ns)
            if title_el is not None and title_el.text:
                title = title_el.text.strip()

            link = "#"
            link_el = entry.find("atom:link", ns)
            if link_el is not None:
                link = link_el.get("href", "#")

            summary = ""
            summary_el = entry.find("atom:summary", ns) or entry.find("atom:content", ns)
            if summary_el is not None and summary_el.text:
                summary = strip_html(summary_el.text)

            pub_date = ""
            date_el = entry.find("atom:published", ns) or entry.find("atom:updated", ns)
            if date_el is not None and date_el.text:
                pub_date = date_el.text.strip()

            if title:
                items.append({
                    "source": source_name,
                    "title": title,
                    "summary": summary,
                    "time": pub_date if pub_date else datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "url": link,
                })

    return items


def main():
    print("🚀 Daily News Scraper 启动...")
    print(f"📅 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📝 输出路径: {OUTPUT_FILE}")
    print("=" * 50)

    all_news = []

    for source in NEWS_SOURCES:
        name = source["name"]
        url = source["rss_url"]
        max_items = source.get("max_items", 5)

        print(f"\n📡 正在抓取: {name}")
        print(f"   URL: {url}")

        xml_text = fetch_rss(url)
        if xml_text:
            news_items = parse_rss(xml_text, name, max_items)
            print(f"   ✅ 获取到 {len(news_items)} 条新闻")
            all_news.extend(news_items)
        else:
            print(f"   ❌ 跳过 {name}")

    # 如果所有源都失败了，生成一条提示
    if not all_news:
        print("\n⚠️ 所有新闻源均获取失败，生成默认占位数据...")
        all_news.append({
            "source": "系统通知",
            "title": "新闻源暂时不可用",
            "summary": "所有 RSS 新闻源当前无法访问，请稍后刷新页面重试，或检查网络连接与 RSS 源配置。",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "url": "#",
        })

    # 生成 UTC+8 北京时间戳
    beijing_tz = timezone(timedelta(hours=8))
    updated_at = datetime.now(beijing_tz).strftime("%Y-%m-%d %H:%M:%S")

    output_data = {
        "updated_at": updated_at,
        "news": all_news,
    }

    # 写入 JSON 文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)

    print(f"\n{'=' * 50}")
    print(f"✅ 完成！共生成 {len(all_news)} 条新闻")
    print(f"📄 已写入: {OUTPUT_FILE}")
    print(f"🕒 更新时间: {updated_at}")


if __name__ == "__main__":
    main()

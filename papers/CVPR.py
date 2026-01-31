"""
CVPR 论文爬虫
从 https://openaccess.thecvf.com/CVPR{year} 爬取论文。
- 2018 及以后：页面按 Day 分页，解析 dt.ptitle + dd。
- 2017 及以前：单页列出所有论文，无 day 分页，解析标题链接与 bibtex 中的 author。
输出格式与项目内其他 JSON 一致：title, authors, pdf_link, source, year。
"""
import requests
from bs4 import BeautifulSoup
import json
import re
import os
from typing import List, Dict

# ========== 可修改参数 ==========
# 修改年份即可爬取对应年份的 CVPR 论文
YEAR = 2013

BASE_URL = "https://openaccess.thecvf.com"
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
}


def fetch_page(url: str) -> str:
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"请求失败 {url}: {e}")
        return ""


def get_day_links(conference_url: str) -> List[str]:
    """从会议主页解析所有 day 链接（如 2020-06-16），去重后返回。"""
    html = fetch_page(conference_url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    days = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        m = re.search(r"[?&]day=([^&\s]+)", href)
        if m:
            day = m.group(1).strip()
            if day and day not in days:
                days.append(day)
    return sorted(days)


def parse_papers_from_html(html: str, base_url: str, year: int) -> List[Dict]:
    """解析 2018 及以后的新版页面结构（dt.ptitle + dd）。"""
    soup = BeautifulSoup(html, "html.parser")
    papers = []
    for dt in soup.find_all("dt", class_="ptitle"):
        title_anchor = dt.find("a")
        if not title_anchor:
            continue
        title = title_anchor.get_text(strip=True)
        href = title_anchor.get("href", "")
        if not href:
            continue
        pdf_href = href.replace("/html/", "/papers/").replace(".html", ".pdf")
        pdf_link = base_url + "/" + pdf_href if not pdf_href.startswith("http") else pdf_href

        authors = []
        dd = dt.find_next_sibling("dd")
        if dd:
            raw = dd.get_text(strip=True)
            raw = re.sub(r"\[.*?\]", "", raw)
            authors = [a.strip() for a in raw.split(",") if a.strip()]

        papers.append({
            "title": title,
            "authors": authors,
            "pdf_link": pdf_link,
            "source": "CVPR",
            "year": year,
        })
    return papers


def parse_papers_from_html_legacy(html: str, base_url: str, year: int) -> List[Dict]:
    """解析 2017 及以前的旧版页面：单页列出所有论文，无 day 分页；标题链到 html，PDF 从路径推导；作者从 bibtex 的 author 行解析。"""
    papers = []
    content_prefix = f"content_cvpr_{year}"
    # 所有指向 content_cvpr_YYYY/html/*.html 的链接即论文标题链接
    title_link_re = re.compile(
        r'<a\s+href="(' + re.escape(content_prefix) + r'/html/[^"]+\.html)"[^>]*>([^<]+)</a>',
        re.IGNORECASE | re.DOTALL
    )
    # bibtex 中 author = { ... }
    author_re = re.compile(r'author\s*=\s*\{([^}]+)\}', re.IGNORECASE)

    title_matches = list(title_link_re.finditer(html))
    author_blocks = author_re.findall(html)

    for i, m in enumerate(title_matches):
        href, title = m.group(1), m.group(2).strip()
        if not title:
            continue
        # PDF 路径：2017 及以前为 base/content_cvpr_YYYY/papers/xxx.pdf（无 CVPR{year} 段）
        pdf_path = href.replace("/html/", "/papers/").replace(".html", ".pdf")
        pdf_link = f"{base_url}/{pdf_path}" if not pdf_path.startswith("http") else pdf_path

        authors = []
        if i < len(author_blocks):
            raw = author_blocks[i].strip()
            # bibtex 里作者用 " and " 分隔
            authors = [a.strip() for a in re.split(r"\s+and\s+", raw) if a.strip()]

        papers.append({
            "title": title,
            "authors": authors,
            "pdf_link": pdf_link,
            "source": "CVPR",
            "year": year,
        })
    return papers


def scrape_cvpr(year: int = None) -> List[Dict]:
    year = year if year is not None else YEAR
    conference_url = f"{BASE_URL}/CVPR{year}"

    # 2017 及以前：单页列出所有论文，无 day 分页，使用旧版解析
    if year <= 2017:
        print(f"使用旧版单页解析 (CVPR {year})")
        html = fetch_page(conference_url)
        if not html:
            print("请求会议主页失败。")
            return []
        papers = parse_papers_from_html_legacy(html, BASE_URL, year)
        print(f"从主页解析到 {len(papers)} 篇论文")
        return papers

    # 2018 及以后：按 day 分页抓取
    days = get_day_links(conference_url)
    if not days:
        print("未从主页解析到任何 day 链接，请检查页面结构或网络。")
        return []
    print(f"从主页解析到 {len(days)} 个会议日: {days}")
    all_papers = []
    for day in days:
        url = f"{conference_url}?day={day}"
        print(f"正在抓取: {url}")
        html = fetch_page(url)
        if not html:
            continue
        papers = parse_papers_from_html(html, BASE_URL, year)
        all_papers.extend(papers)
        print(f"  Day {day} 得到 {len(papers)} 篇")
    return all_papers


def save_to_json(papers: List[Dict], filename: str = None, year: int = None) -> str:
    year = year if year is not None else YEAR
    if filename is None:
        filename = os.path.join(OUTPUT_DIR, f"CVPR{year}papers.json")
    else:
        filename = os.path.join(OUTPUT_DIR, filename)
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(papers, f, ensure_ascii=False, indent=2)
    print(f"已保存 {len(papers)} 篇到 {filename}")
    return filename


def main():
    papers = scrape_cvpr(year=YEAR)
    if papers:
        save_to_json(papers, year=YEAR)
        print(f"共爬取 CVPR {YEAR} 论文 {len(papers)} 篇")
    else:
        print("未获取到任何论文。")


if __name__ == "__main__":
    main()

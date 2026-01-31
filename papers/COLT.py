import requests
from bs4 import BeautifulSoup
import json
import os

# ========== 可修改参数 ==========
# 修改年份后，请同步修改下方 PMLR_VOLUME_URL（不同年份对应不同卷号，如 2025 年为 v291）
YEAR = 2014
PMLR_VOLUME_URL = "https://proceedings.mlr.press/v35/"

def scrape_colt_papers(year=None, volume_url=None):
    year = year if year is not None else YEAR
    url = volume_url or PMLR_VOLUME_URL

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        papers_data = []
        
        # PMLR 页面通常将每篇论文包裹在 class="paper" 的 div 中
        paper_divs = soup.find_all('div', class_='paper')
        
        print(f"找到 {len(paper_divs)} 篇论文，开始解析...")

        for div in paper_divs:
            # 1. 获取标题
            title_tag = div.find('p', class_='title')
            title = title_tag.get_text(strip=True) if title_tag else "N/A"
            
            # 2. 获取作者 (PMLR通常用逗号分隔)
            authors = []
            authors_tag = div.find('span', class_='authors')
            if authors_tag:
                # 清理作者文本，移除多余空白
                author_text = authors_tag.get_text(strip=True)
                # 分割并去除每个名字的首尾空格
                authors = [a.strip() for a in author_text.split(',')]
            
            # 3. 获取PDF链接
            pdf_link = "N/A"
            links_container = div.find('p', class_='links')
            if links_container:
                # 寻找包含 'Download PDF' 或类似文本的链接，或者检查 href 后缀
                for link in links_container.find_all('a'):
                    if 'pdf' in link.get('href', '').lower() or 'pdf' in link.get_text().lower():
                        pdf_link = link['href']
                        break
            
            # 4. 构建数据字典 (保持与AAAI2021papers.json格式一致)
            paper_info = {
                "title": title,
                "authors": authors,
                "pdf_link": pdf_link,
                "source": "COLT",
                "year": year
            }
            
            papers_data.append(paper_info)

        return papers_data

    except Exception as e:
        print(f"爬取过程中出现错误: {e}")
        return []

if __name__ == "__main__":
    papers = scrape_colt_papers(year=YEAR)

    if papers:
        # 输出文件固定保存在 papers 文件夹
        papers_dir = os.path.dirname(os.path.abspath(__file__))
        output_file = os.path.join(papers_dir, f"COLT{YEAR}papers.json")
        os.makedirs(papers_dir, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(papers, f, indent=4, ensure_ascii=False)
        print(f"成功爬取 {len(papers)} 篇论文，已保存至 {output_file}")
    else:
        print("未获取到论文数据。")
import requests
from bs4 import BeautifulSoup
import json
import re
import time
import os
from typing import List, Dict

def extract_year_from_url(url: str) -> int:
    """
    从URL中提取年份
    
    Args:
        url: PDF链接或论文链接
    
    Returns:
        年份,默认返回2024
    """
    # 尝试从URL中匹配4位数年份
    # 常见格式: /papers/eccv_2024/, /ECCV2024/, /2024/
    year_pattern = r'(?:eccv[_-]?|/)?(\d{4})'
    matches = re.findall(year_pattern, url, re.IGNORECASE)
    
    for match in matches:
        year = int(match)
        # 确保是合理的ECCV年份范围 (2000-2030)
        if 2000 <= year <= 2030:
            return year
    
    # 如果无法从URL提取,返回默认值
    return 2024


def scrape_eccv2024_papers() -> List[Dict]:
    """
    爬取ECCV2024所有论文信息
    
    Returns:
        包含所有论文信息的列表
    """
    base_url = "https://www.ecva.net/papers.php"
    papers = []
    
    print("开始爬取ECCV2024论文...")
    
    try:
        # 发送请求
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(base_url, headers=headers, timeout=30)
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        # 解析HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找所有论文条目
        # ECCV通常使用dt标签表示论文标题,dd标签表示作者信息
        paper_titles = soup.find_all('dt', class_='ptitle')
        
        for idx, title_tag in enumerate(paper_titles):
            try:
                # 提取标题
                title_link = title_tag.find('a')
                if not title_link:
                    continue
                    
                title = title_link.text.strip()
                
                # 提取PDF链接
                pdf_link = title_link.get('href', '')
                if pdf_link and not pdf_link.startswith('http'):
                    pdf_link = f"https://www.ecva.net/{pdf_link}"
                
                # 从PDF链接中提取年份
                year = extract_year_from_url(pdf_link)
                
                # 提取作者信息 (通常在下一个dd标签中)
                authors = []
                next_dd = title_tag.find_next_sibling('dd')
                if next_dd:
                    author_text = next_dd.text.strip()
                    # 清理并分割作者名字
                    authors = [author.strip() for author in author_text.split(',') if author.strip()]
                
                # 构建论文信息
                paper_info = {
                    "title": title,
                    "authors": authors,
                    "pdf_link": pdf_link,
                    "source": "ECCV",
                    "year": year
                }
                
                papers.append(paper_info)
                
                # 显示进度
                if (idx + 1) % 50 == 0:
                    print(f"已爬取 {idx + 1} 篇论文...")
                
            except Exception as e:
                print(f"处理第 {idx + 1} 篇论文时出错: {str(e)}")
                continue
        
        print(f"\n爬取完成!共获取 {len(papers)} 篇论文")
        
    except requests.RequestException as e:
        print(f"网络请求错误: {str(e)}")
        print("\n备选方案:尝试使用OpenAccess CVF...")
        return scrape_eccv2024_from_cvf()
    
    return papers


def save_to_json(papers: List[Dict], filename: str = "eccv2024_papers.json"):
    """
    将论文信息保存为JSON文件
    
    Args:
        papers: 论文信息列表
        filename: 输出文件名
    """
    # 确保保存到papers文件夹
    if not filename.startswith('papers/'):
        filename = os.path.join('papers', filename)
    
    # 确保papers文件夹存在
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(papers, f, ensure_ascii=False, indent=2)
    
    print(f"\n论文信息已保存至 {filename}")


if __name__ == "__main__":
    # 爬取论文
    papers = scrape_eccv2024_papers()
    
    # 保存为JSON
    if papers:
        save_to_json(papers)
        
        # 显示前3篇作为示例
        print("\n前3篇论文示例:")
        print(json.dumps(papers[:3], ensure_ascii=False, indent=2))
        
        # 统计各年份论文数量
        year_counts = {}
        for paper in papers:
            year = paper['year']
            year_counts[year] = year_counts.get(year, 0) + 1
        
        print("\n各年份论文统计:")
        for year in sorted(year_counts.keys()):
            print(f"  {year}: {year_counts[year]} 篇")     
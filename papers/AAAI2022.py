import requests
from bs4 import BeautifulSoup
import json
import time
import os
from typing import List, Dict
import re
from urllib.parse import urljoin

class AAAIScraper:
    """AAAI 论文爬虫（支持多年份）"""
    
    def __init__(self, year: int = 2022):
        """
        初始化爬虫
        
        Args:
            year: 会议年份，默认为2022
        """
        self.year = year
        self.base_url = "https://aaai.org"
        # 根据年份生成对应的 proceedings URL
        # AAAI 卷号规律：volume = year - 1986 (例如：2020=34, 2021=35, 2022=36)
        volume_map = {
            2010: 24, 2011: 25, 2012: 26, 2013: 27, 2014: 28, 2015: 29,
            2016: 30, 2017: 31, 2018: 32, 2019: 33, 2020: 34, 2021: 35,
            2022: 36, 2023: 37, 2024: 38, 2025: 39, 2026: 40, 2027: 41
        }
        # 如果年份不在映射中，使用公式计算：volume = year - 1986
        volume = volume_map.get(year, year - 1986 if year >= 1980 else 36)
        self.proceedings_url = f"https://aaai.org/proceeding/aaai-{volume}-{year}/"
        self.headers = {    
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.papers = []
        self.track_urls = []
    
    def get_track_urls(self) -> List[str]:
        """从主页面获取所有轨道的URL"""
        print(f"正在获取轨道列表页面: {self.proceedings_url}")
        
        try:
            response = requests.get(self.proceedings_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找所有轨道链接
            # 链接格式类似: /proceeding/01-aaai-22-technical-tracks-1/
            track_links = soup.find_all('a', href=re.compile(r'/proceeding/\d+-.*'))
            
            for link in track_links:
                href = link.get('href', '')
                if href:
                    full_url = urljoin(self.base_url, href)
                    if full_url not in self.track_urls:
                        self.track_urls.append(full_url)
            
            print(f"找到 {len(self.track_urls)} 个轨道")
            return self.track_urls[:-2]
            
        except Exception as e:
            print(f"获取轨道列表时出错: {e}")
            return []
    
    def scrape_track_papers(self, track_url: str) -> List[Dict]:
        """爬取单个轨道的所有论文"""
        print(f"\n正在爬取轨道: {track_url}")
        
        papers = []
        
        try:
            response = requests.get(track_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找所有论文条目
            # 论文通常在 <li> 中，每个 <li> 包含一篇论文
            # 格式: <li> <h5> <a>标题</a> </h5> 作者 页码 <a>PDF</a> </li>
            
            # 查找所有包含论文标题链接的 <li> 元素
            list_items = soup.find_all('li')
            
            for li in list_items:
                try:
                    # 查找标题链接 (h5 > a)
                    title_elem = li.find('h5')
                    if not title_elem:
                        continue
                    
                    title_link = title_elem.find('a')
                    if not title_link:
                        continue
                    
                    title = title_link.get_text(strip=True)
                    if not title or len(title) < 5:
                        continue
                    
                    # 提取作者 - 在标题链接后面，PDF链接前面
                    # 作者通常在 h5 后面的文本中
                    paper_info = {
                        'title': title,
                        'authors': [],
                        'pdf_link': '',
                        'source': 'AAAI',
                        'year': self.year
                    }
                    
                    # 获取 h5 后面的所有文本节点
                    text_parts = []
                    for elem in li.children:
                        if hasattr(elem, 'get_text'):
                            text = elem.get_text(strip=True)
                            if text and text != title:
                                text_parts.append(text)
                    
                    # 查找 PDF 链接
                    pdf_link = li.find('a', href=re.compile(r'\.pdf$|/download/|cdn\.aaai\.org'))
                    if pdf_link:
                        pdf_href = pdf_link.get('href', '')
                        if pdf_href:
                            paper_info['pdf_link'] = urljoin(self.base_url, pdf_href)
                    
                    # 提取作者 - 通常在标题和页码之间
                    # 尝试从 li 的文本内容中提取
                    li_text = li.get_text()
                    # 移除标题
                    li_text = li_text.replace(title, '', 1).strip()
                    # 移除页码（通常是数字-数字格式）
                    li_text = re.sub(r'\d+-\d+', '', li_text).strip()
                    # 移除 PDF 文本
                    li_text = re.sub(r'PDF', '', li_text, flags=re.IGNORECASE).strip()
                    
                    # 作者通常用逗号分隔
                    if li_text:
                        # 尝试分割作者
                        authors = [a.strip() for a in li_text.split(',') if a.strip() and len(a.strip()) > 2]
                        if authors:
                            paper_info['authors'] = authors
                    
                    # 如果没找到作者，尝试从 h5 后面的直接文本节点获取
                    if not paper_info['authors']:
                        # 查找 h5 后面的文本
                        next_sibling = title_elem.next_sibling
                        if next_sibling and hasattr(next_sibling, 'strip'):
                            author_text = next_sibling.strip()
                            if author_text and len(author_text) > 2:
                                authors = [a.strip() for a in author_text.split(',') if a.strip()]
                                if authors:
                                    paper_info['authors'] = authors
                    
                    if paper_info['title']:
                        papers.append(paper_info)
                        
                except Exception as e:
                    print(f"处理论文时出错: {e}")
                    continue
            
            print(f"从该轨道爬取了 {len(papers)} 篇论文")
            return papers
            
        except Exception as e:
            print(f"爬取轨道 {track_url} 时出错: {e}")
            return []
    
    def scrape_all_papers(self) -> List[Dict]:
        """爬取所有论文"""
        print("=" * 60)
        print(f"开始爬取 AAAI {self.year} 论文")
        print("=" * 60)
        
        # 获取所有轨道URL
        track_urls = self.get_track_urls()
        
        if not track_urls:
            print("未找到任何轨道，请检查网站结构")
            return []
        
        # 遍历每个轨道
        for idx, track_url in enumerate(track_urls, 1):
            print(f"\n[{idx}/{len(track_urls)}] 处理轨道...")
            papers = self.scrape_track_papers(track_url)
            self.papers.extend(papers)
            
            # 添加延迟，避免请求过快
            time.sleep(1)
        
        print(f"\n总共爬取了 {len(self.papers)} 篇论文")
        return self.papers
    
    def save_to_json(self, filename: str = None):
        """保存为JSON文件"""
        if filename is None:
            filename = f"AAAI{self.year}papers.json"
        
        # 确保保存到papers文件夹
        if not filename.startswith('papers/'):
            filename = os.path.join('papers', filename)
        
        # 确保papers文件夹存在
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.papers, f, ensure_ascii=False, indent=2)
            print(f"\n已保存到 {filename}")
            print(f"总共保存了 {len(self.papers)} 篇论文")
        except Exception as e:
            print(f"保存文件时出错: {e}")
    
    def print_summary(self):
        """打印统计信息"""
        if not self.papers:
            print("没有获取到论文数据")
            return
        
        print("\n" + "="*50)
        print(f"AAAI {self.year} 论文统计")
        print("="*50)
        print(f"总论文数: {len(self.papers)}")
        print(f"有PDF链接的论文: {sum(1 for p in self.papers if p.get('pdf_link'))}")
        print(f"有作者信息的论文: {sum(1 for p in self.papers if p.get('authors'))}")
        print("\n前5篇论文示例:")
        for i, paper in enumerate(self.papers[:5], 1):
            print(f"\n{i}. {paper.get('title', 'N/A')}")
            authors = paper.get('authors', [])
            if authors:
                print(f"   作者: {', '.join(authors[:3])}{'...' if len(authors) > 3 else ''}")
            pdf_link = paper.get('pdf_link', '')
            if pdf_link:
                print(f"   PDF: {pdf_link}")


def main():
    """主函数"""
    # 可以在这里修改年份
    year = 2020
    
    # 创建爬虫实例
    scraper = AAAIScraper(year=year)
    
    # 爬取所有论文
    papers = scraper.scrape_all_papers()
    
    # 打印统计信息
    scraper.print_summary()
    
    # 保存为JSON文件
    scraper.save_to_json()
    
    print("\n爬取完成！")


if __name__ == "__main__":
    main()

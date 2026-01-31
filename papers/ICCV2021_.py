import requests
from bs4 import BeautifulSoup
import json
import time
import os
from typing import List, Dict
import re

class CVPRScraper:
    """CVPR 论文爬虫"""
    
    def __init__(self, year: int = 2025):
        """
        初始化爬虫
        
        Args:
            year: 会议年份，默认为2025
        """
        self.year = year
        self.base_url = "https://openaccess.thecvf.com"
        self.conference_url = f"{self.base_url}/ICCV{year}"
        self.headers = {    
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.papers = []
    
    def get_paper_list_page(self, day: str = "all") -> str:
        """获取论文列表页面"""
        url = f"{self.conference_url}?day={day}"
        print(f"正在获取页面: {url}")
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"获取页面失败: {e}")
            return None
    
    def parse_paper_info(self, paper_element) -> Dict:
        """解析单篇论文信息"""
        paper_info = {
            'title': '',
            'authors': [],
            'pdf_link': '',
            'bibtex': '',
            'source': 'ICCV',
            'year': self.year
        }
        
        try:
            # 提取标题
            title_elem = paper_element.find('dt', class_='ptitle')
            if title_elem:
                title_link = title_elem.find('a')
                if title_link:
                    paper_info['title'] = title_link.get_text(strip=True)
                    paper_info['pdf_link'] = self.base_url + title_link.get('href', '')
            
            # 提取作者
            authors_elem = paper_element.find('dd')
            if authors_elem:
                authors_text = authors_elem.get_text(strip=True)
                # 清理作者名字
                authors = [a.strip() for a in authors_text.split(',') if a.strip()]
                paper_info['authors'] = authors
            
            # 查找PDF链接 (通常在链接中)
            pdf_links = paper_element.find_all('a', href=re.compile(r'\.pdf$'))
            if pdf_links:
                paper_info['pdf_link'] = self.base_url + pdf_links[0].get('href', '')
            
        except Exception as e:
            print(f"解析论文信息时出错: {e}")
        
        return paper_info
    
    def scrape_all_papers(self) -> List[Dict]:
        """爬取所有论文"""
        print(f"开始爬取CVPR {self.year}所有论文...")
        
        # 获取所有论文页面
        html_content = self.get_paper_list_page(day="all")
        
        if not html_content:
            print("无法获取页面内容")
            return []
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 查找所有论文条目
        # 通常论文列表使用 <dl> 标签或特定class
        paper_elements = soup.find_all('dt', class_='ptitle')
        
        print(f"找到 {len(paper_elements)} 篇论文")
        
        for idx, paper_elem in enumerate(paper_elements, 1):
            # 获取包含该论文的父元素（通常是dt和dd的组合）
            parent = paper_elem.parent
            
            paper_info = {
                'title': '',
                'authors': [],
                'pdf_link': '',
                'source': 'ICCV',
                'year': self.year
            }
            
            try:
                # 提取标题和论文主页链接
                title_link = paper_elem.find('a')
                if title_link:
                    paper_info['title'] = title_link.get_text(strip=True)
                    href = title_link.get('href', '')
                    if href:
                        paper_page_url = self.base_url + href
                        # 将HTML链接转换为PDF链接
                        # CVPR的PDF链接格式：将 html/ 替换为 papers/，将 .html 替换为 .pdf
                        pdf_href = href.replace('/html/', '/papers/').replace('.html', '.pdf')
                        paper_info['pdf_link'] = self.base_url + pdf_href
                
                # 提取作者 - 通常在下一个dd元素中
                next_dd = paper_elem.find_next_sibling('dd')
                if next_dd:
                    authors_text = next_dd.get_text(strip=True)
                    # 移除可能的链接标记
                    authors_text = re.sub(r'\[.*?\]', '', authors_text)
                    authors = [a.strip() for a in authors_text.split(',') if a.strip()]
                    paper_info['authors'] = authors
                
                if paper_info['title']:
                    self.papers.append(paper_info)
                    if idx % 100 == 0:
                        print(f"已处理 {idx} 篇论文...")
            
            except Exception as e:
                print(f"处理第 {idx} 篇论文时出错: {e}")
                continue
        
        print(f"成功爬取 {len(self.papers)} 篇论文")
        return self.papers
    
    def save_to_json(self, filename: str = None):
        """保存为JSON文件"""
        if filename is None:
            filename = f"cvpr{self.year}_papers.json"
        
        # 确保保存到papers文件夹
        if not filename.startswith('papers/'):
            filename = os.path.join('papers', filename)
        
        # 确保papers文件夹存在
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.papers, f, ensure_ascii=False, indent=2)
            print(f"数据已保存到 {filename}")
            print(f"总共保存了 {len(self.papers)} 篇论文")
        except Exception as e:
            print(f"保存文件时出错: {e}")
    
    def print_summary(self):
        """打印统计信息"""
        if not self.papers:
            print("没有爬取到论文数据")
            return
        
        print("\n" + "="*50)
        print(f"CVPR {self.year} 论文统计")
        print("="*50)
        print(f"总论文数: {len(self.papers)}")
        print(f"有PDF链接的论文: {sum(1 for p in self.papers if p['pdf_link'])}")
        print(f"有作者信息的论文: {sum(1 for p in self.papers if p['authors'])}")
        print("\n前5篇论文示例:")
        for i, paper in enumerate(self.papers[:5], 1):
            print(f"\n{i}. {paper['title']}")
            print(f"   作者: {', '.join(paper['authors'][:3])}{'...' if len(paper['authors']) > 3 else ''}")
            print(f"   PDF: {paper['pdf_link']}")


def main():
    """主函数"""
    # 可以在这里修改年份
    year = 2020
    
    # 创建爬虫实例
    scraper = CVPRScraper(year=year)
    
    # 爬取所有论文
    papers = scraper.scrape_all_papers()
    
    # 打印统计信息
    scraper.print_summary()
    
    # 保存为JSON文件
    scraper.save_to_json(f"ICCV{year}papers.json")
    
    print("\n爬取完成！")


if __name__ == "__main__":
    main()
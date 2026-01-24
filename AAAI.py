import requests
from bs4 import BeautifulSoup
import json
import time
from typing import List, Dict
import re
from urllib.parse import urljoin, urlparse

class AAAIScraper:
    """AAAI 2025 论文爬虫"""
    
    def __init__(self, year: int = 2025):
        """
        初始化爬虫
        
        Args:
            year: 会议年份，默认为2025
        """
        self.year = year
        self.base_url = "https://aaai.org"
        self.ojs_base_url = "https://ojs.aaai.org"
        self.proceedings_url = f"{self.base_url}/proceeding/aaai-37-2023/"
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
            # 链接格式类似: https://ojs.aaai.org/index.php/AAAI/issue/view/624
            track_urls = []
            
            # 查找所有包含 "issue/view" 的链接
            links = soup.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                if 'ojs.aaai.org' in href and 'issue/view' in href:
                    # 确保是完整的URL
                    if href.startswith('http'):
                        track_urls.append(href)
                    elif href.startswith('/'):
                        track_urls.append(self.ojs_base_url + href)
                    else:
                        track_urls.append(urljoin(self.ojs_base_url, href))
            
            # 去重
            track_urls = list(set(track_urls))
            
            # 舍弃最后一个轨道
            if track_urls:
                track_urls = track_urls[:-1]
                print(f"找到 {len(track_urls)} 个轨道（已舍弃最后一个）")
            else:
                print(f"找到 {len(track_urls)} 个轨道")
            
            return track_urls
            
        except Exception as e:
            print(f"获取轨道列表失败: {e}")
            return []
    
    def parse_paper_from_article(self, article_elem, track_name: str = "") -> Dict:
        """从文章元素解析论文信息"""
        paper_info = {
            'title': '',
            'authors': [],
            'pdf_link': '',
            'source': 'AAAI',
            'year': self.year,
            'track': track_name
        }
        
        try:
            # 提取标题 - 查找包含 "article/view" 但不包含 PDF 的链接
            title_links = article_elem.find_all('a', href=re.compile(r'article/view'))
            title_link = None
            
            for link in title_links:
                href = link.get('href', '')
                # 标题链接通常是 article/view/数字，不包含 /download/ 或 .pdf
                if 'article/view' in href and '/download/' not in href and '.pdf' not in href:
                    # 检查链接文本是否看起来像标题（不是"PDF"）
                    link_text = link.get_text(strip=True)
                    if link_text and link_text.upper() != 'PDF' and len(link_text) > 10:
                        title_link = link
                        break
            
            if title_link:
                paper_info['title'] = title_link.get_text(strip=True)
                article_url = title_link.get('href', '')
                if article_url:
                    if not article_url.startswith('http'):
                        article_url = urljoin(self.ojs_base_url, article_url)
                    paper_info['article_url'] = article_url
            
            # 提取作者 - 作者通常在标题后的文本节点中
            # 获取整个元素的文本，然后解析
            full_text = article_elem.get_text(separator='\n', strip=True)
            lines = [line.strip() for line in full_text.split('\n') if line.strip()]
            
            # 查找作者行：通常在标题后，包含多个逗号分隔的名字
            found_title = False
            for line in lines:
                # 如果找到了标题行
                if paper_info['title'] and paper_info['title'] in line:
                    found_title = True
                    continue
                
                # 标题后的第一行如果包含逗号分隔的名字，很可能是作者
                if found_title:
                    # 检查是否是作者行（包含逗号，且看起来像名字）
                    if ',' in line and len(line) > 10:
                        # 排除页码行（如 "3-11"）
                        if not re.match(r'^\d+-\d+$', line):
                            authors = [a.strip() for a in line.split(',') if a.strip()]
                            # 验证：作者名通常至少2个字符
                            if len(authors) >= 1 and all(len(a) >= 2 for a in authors):
                                paper_info['authors'] = authors
                                break
                    # 如果下一行是页码，说明作者行已经过了
                    elif re.match(r'^\d+-\d+$', line):
                        break
            
            # 如果还没找到作者，尝试从所有行中查找
            if not paper_info['authors']:
                for line in lines:
                    # 跳过标题行和页码行
                    if paper_info['title'] and paper_info['title'] in line:
                        continue
                    if re.match(r'^\d+-\d+$', line):
                        continue
                    if 'PDF' in line.upper():
                        continue
                    
                    # 查找包含多个逗号分隔名字的行
                    if ',' in line and len(line) > 10:
                        authors = [a.strip() for a in line.split(',') if a.strip()]
                        if len(authors) >= 1 and all(len(a) >= 2 for a in authors):
                            # 进一步验证：名字通常不全是数字
                            if not all(a.isdigit() for a in authors):
                                paper_info['authors'] = authors
                                break
            
            # 提取PDF链接
            pdf_links = article_elem.find_all('a', href=True)
            for link in pdf_links:
                href = link.get('href', '')
                link_text = link.get_text(strip=True).upper()
                
                # PDF链接通常包含 article/view/数字/数字 或 .pdf
                if ('PDF' in link_text or '.pdf' in href or '/download/' in href) and 'article/view' in href:
                    if href.startswith('http'):
                        paper_info['pdf_link'] = href
                    else:
                        paper_info['pdf_link'] = urljoin(self.ojs_base_url, href)
                    break
            
        except Exception as e:
            print(f"解析论文信息时出错: {e}")
        
        return paper_info
    
    def scrape_track_papers(self, track_url: str) -> List[Dict]:
        """爬取单个轨道的所有论文"""
        print(f"\n正在爬取轨道: {track_url}")
        
        papers = []
        
        try:
            response = requests.get(track_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 获取轨道名称
            track_name = ""
            title_elem = soup.find('h1')
            if title_elem:
                track_name = title_elem.get_text(strip=True)
            
            # 查找所有论文条目
            # 论文通常在 <li> 中，每个 <li> 包含一篇论文
            paper_elements = []
            
            # 方法1: 查找所有包含 "article/view" 链接的 <li> 元素
            list_items = soup.find_all('li')
            for li in list_items:
                # 检查是否包含论文标题链接（不是PDF链接）
                title_links = li.find_all('a', href=re.compile(r'article/view'))
                for link in title_links:
                    href = link.get('href', '')
                    link_text = link.get_text(strip=True).upper()
                    # 标题链接不是PDF链接
                    if 'article/view' in href and '/download/' not in href and link_text != 'PDF':
                        # 检查链接文本是否像标题
                        if len(link.get_text(strip=True)) > 10:
                            paper_elements.append(li)
                            break
            
            # 方法2: 如果没找到，尝试查找包含论文信息的其他容器
            if not paper_elements:
                # 查找所有包含 "article/view" 链接的元素
                article_links = soup.find_all('a', href=re.compile(r'article/view'))
                seen_parents = set()
                
                for link in article_links:
                    href = link.get('href', '')
                    link_text = link.get_text(strip=True).upper()
                    
                    # 跳过PDF链接
                    if link_text == 'PDF' or '/download/' in href:
                        continue
                    
                    # 查找包含该链接的父容器
                    parent = link.parent
                    while parent and parent.name != 'body':
                        if parent.name in ['li', 'div', 'article', 'section', 'p']:
                            parent_id = id(parent)
                            if parent_id not in seen_parents:
                                seen_parents.add(parent_id)
                                text = parent.get_text(strip=True)
                                # 确保有足够的内容（标题+作者）
                                if len(text) > 50:
                                    paper_elements.append(parent)
                            break
                        parent = parent.parent
            
            # 去重
            seen = set()
            unique_elements = []
            for elem in paper_elements:
                elem_id = id(elem)
                if elem_id not in seen:
                    seen.add(elem_id)
                    unique_elements.append(elem)
            
            print(f"找到 {len(unique_elements)} 篇论文")
            
            # 解析每篇论文
            for idx, paper_elem in enumerate(unique_elements, 1):
                paper_info = self.parse_paper_from_article(paper_elem, track_name)
                
                if paper_info['title']:
                    papers.append(paper_info)
                    if idx % 50 == 0:
                        print(f"  已处理 {idx} 篇论文...")
                
                # 添加延迟以避免请求过快
                time.sleep(0.05)
            
            print(f"成功爬取 {len(papers)} 篇论文")
            
        except Exception as e:
            print(f"爬取轨道 {track_url} 时出错: {e}")
            import traceback
            traceback.print_exc()
        
        return papers
    
    def get_pdf_link_from_article_page(self, article_url: str) -> str:
        """从文章页面获取PDF链接"""
        try:
            response = requests.get(article_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找PDF下载链接
            pdf_link = soup.find('a', href=re.compile(r'\.pdf$|/download/'))
            if pdf_link:
                href = pdf_link.get('href', '')
                if href.startswith('http'):
                    return href
                else:
                    return urljoin(self.ojs_base_url, href)
        except Exception as e:
            print(f"获取PDF链接失败 {article_url}: {e}")
        
        return ""
    
    def scrape_all_papers(self) -> List[Dict]:
        """爬取所有论文"""
        print(f"开始爬取AAAI {self.year}所有论文...")
        
        # 获取所有轨道URL
        self.track_urls = self.get_track_urls()
        
        if not self.track_urls:
            print("未找到任何轨道，尝试使用预定义的轨道ID")
            # 如果无法从主页面获取，使用已知的轨道ID范围
            base_issue_id = 624  # 第一个轨道的ID
            self.track_urls = [
                f"{self.ojs_base_url}/index.php/AAAI/issue/view/{base_issue_id + i}"
                for i in range(27)  # 共27个轨道（舍弃最后一个，原本28个）
            ]
            print(f"使用预定义轨道ID，共 {len(self.track_urls)} 个轨道（已舍弃最后一个）")
        
        print(f"共需要爬取 {len(self.track_urls)} 个轨道")
        
        # 爬取每个轨道
        for idx, track_url in enumerate(self.track_urls, 1):
            print(f"\n[{idx}/{len(self.track_urls)}] 处理轨道...")
            papers = self.scrape_track_papers(track_url)
            self.papers.extend(papers)
            
            # 添加延迟
            time.sleep(1)
        
        # # 对于没有PDF链接的论文，尝试从文章页面获取
        # print("\n正在补充PDF链接...")
        # for idx, paper in enumerate(self.papers, 1):
        #     if not paper.get('pdf_link') and paper.get('article_url'):
        #         pdf_link = self.get_pdf_link_from_article_page(paper['article_url'])
        #         if pdf_link:
        #             paper['pdf_link'] = pdf_link
        #         if idx % 10 == 0:
        #             print(f"  已处理 {idx}/{len(self.papers)} 篇论文...")
        #         time.sleep(0.5)
        
        print(f"\n成功爬取 {len(self.papers)} 篇论文")
        return self.papers
    
    def save_to_json(self, filename: str = None):
        """保存为JSON文件"""
        if filename is None:
            filename = f"AAAI{self.year}_papers.json"
        try:
            # 移除 track 和 article_url 字段
            papers_to_save = []
            for paper in self.papers:
                paper_copy = {k: v for k, v in paper.items() if k not in ['track', 'article_url']}
                papers_to_save.append(paper_copy)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(papers_to_save, f, ensure_ascii=False, indent=2)
            print(f"数据已保存到 {filename}")
            print(f"总共保存了 {len(papers_to_save)} 篇论文")
        except Exception as e:
            print(f"保存文件时出错: {e}")
    
    def print_summary(self):
        """打印统计信息"""
        if not self.papers:
            print("没有爬取到论文数据")
            return
        
        print("\n" + "="*50)
        print(f"AAAI {self.year} 论文统计")
        print("="*50)
        print(f"总论文数: {len(self.papers)}")
        print(f"有PDF链接的论文: {sum(1 for p in self.papers if p.get('pdf_link'))}")
        print(f"有作者信息的论文: {sum(1 for p in self.papers if p.get('authors'))}")
        print(f"轨道数: {len(set(p.get('track', '') for p in self.papers))}")
        print("\n前5篇论文示例:")
        for i, paper in enumerate(self.papers[:5], 1):
            print(f"\n{i}. {paper['title']}")
            if paper.get('authors'):
                print(f"   作者: {', '.join(paper['authors'][:3])}{'...' if len(paper['authors']) > 3 else ''}")
            if paper.get('pdf_link'):
                print(f"   PDF: {paper['pdf_link']}")
            if paper.get('track'):
                print(f"   轨道: {paper['track']}")


def main():
    """主函数"""
    year = 2023
    
    # 创建爬虫实例
    scraper = AAAIScraper(year=year)
    
    # 爬取所有论文
    papers = scraper.scrape_all_papers()
    
    # 打印统计信息
    scraper.print_summary()
    
    # 保存为JSON文件
    scraper.save_to_json(f"AAAI{year}papers.json")
    
    print("\n爬取完成！")


if __name__ == "__main__":
    main()

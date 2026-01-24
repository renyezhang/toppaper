import json
import time
import os
from typing import List, Dict

try:
    import openreview
    from openreview.api import OpenReviewClient
except ImportError:
    print("正在尝试安装 openreview-py...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "openreview-py"])
    import openreview
    from openreview.api import OpenReviewClient


class COLMScraper:
    def __init__(self, year: int = 2024):
        """
        初始化COLM爬虫
        
        Args:
            year: 会议年份，默认为2024
        """
        self.year = year
        self.papers = []
        
        # COLM仅使用v2版本API
        self.api_version = 2
        self.base_url = "https://api2.openreview.net"
        self.client = OpenReviewClient(baseurl=self.base_url)
        # v2 使用 venueid
        self.venue_id = f"colmweb.org/COLM/{year}/Conference"

    def get_all_papers(self) -> List[Dict]:
        """
        获取所有论文
        
        Returns:
            论文信息列表
        """
        print(f"开始获取 COLM {self.year} 所有论文 (API v{self.api_version})...")
        
        try:
            # === API v2 逻辑 ===
            print(f"Target Venue ID: {self.venue_id}")
            submissions = self.client.get_all_notes(content={'venueid': self.venue_id})

            # 将迭代器转换为列表以获取长度
            submissions_list = list(submissions)
            print(f"找到 {len(submissions_list)} 篇论文")

            for idx, note in enumerate(submissions_list, 1):
                try:
                    paper_info = self._parse_note(note)
                    if paper_info['title']:
                        self.papers.append(paper_info)
                    
                    if idx % 100 == 0:
                        print(f"已处理 {idx} 篇论文...")
                        
                except Exception as e:
                    # 某些特殊 note 可能缺少字段，跳过即可
                    print(f"处理第 {idx} 篇论文时出错: {e}")
                    continue

            print(f"成功获取 {len(self.papers)} 篇论文")
            return self.papers

        except Exception as e:
            print(f"获取论文时出错: {e}")
            print("提示：请检查 Venue ID 是否正确，或访问 OpenReview 对应年份的 URL 确认。")
            return []

    def _parse_note(self, note) -> Dict:
        """
        解析 API v2 的 Note 对象
        
        Args:
            note: OpenReview Note 对象
            
        Returns:
            解析后的论文信息字典
        """
        info = {
            'title': '',
            'authors': [],
            'pdf_link': '',
            'source': 'COLM',
            'year': self.year
        }
        
        # === 解析 API v2 ===
        if hasattr(note, 'content'):
            # 标题
            if 'title' in note.content:
                title_val = note.content['title']
                if isinstance(title_val, dict):
                    info['title'] = title_val.get('value', '')
                else:
                    info['title'] = title_val
            
            # 作者
            if 'authors' in note.content:
                authors_val = note.content['authors']
                if isinstance(authors_val, dict):
                    info['authors'] = authors_val.get('value', [])
                elif isinstance(authors_val, list):
                    info['authors'] = authors_val
                else:
                    info['authors'] = []
            
            # PDF链接
            if 'pdf' in note.content:
                pdf_val = note.content['pdf']
                if isinstance(pdf_val, dict):
                    pdf_val = pdf_val.get('value', '')
                
                if pdf_val:
                    # 如果有PDF，使用note.id构建PDF链接
                    info['pdf_link'] = f"https://openreview.net/pdf?id={note.id}"
            
            # 如果没有从content中获取到PDF，但note有id，尝试构建PDF链接
            if not info['pdf_link'] and hasattr(note, 'id'):
                info['pdf_link'] = f"https://openreview.net/pdf?id={note.id}"

        return info

    def save_to_json(self, filename: str = None):
        """
        保存为JSON文件
        
        Args:
            filename: 输出文件名，如果为None则自动生成
        """
        if filename is None:
            filename = f"COLM{self.year}papers.json"
        
        # 确保保存到papers文件夹
        if not filename.startswith('papers/'):
            filename = os.path.join('papers', filename)
        
        # 确保papers文件夹存在
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.papers, f, ensure_ascii=False, indent=2)
            print(f"已保存到 {filename}")
            print(f"总共保存了 {len(self.papers)} 篇论文")
        except Exception as e:
            print(f"保存文件时出错: {e}")

    def print_summary(self):
        """打印统计信息"""
        if not self.papers:
            print("没有获取到论文数据")
            return
        
        print("\n" + "="*50)
        print(f"COLM {self.year} 论文统计")
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
    year = 2023
    
    # 创建爬虫实例
    scraper = COLMScraper(year=year)
    
    # 获取所有论文
    papers = scraper.get_all_papers()
    
    # 打印统计信息
    scraper.print_summary()
    
    # 保存为JSON文件
    scraper.save_to_json()
    
    print("\n获取完成！")


if __name__ == "__main__":
    main()

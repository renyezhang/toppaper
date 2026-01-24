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

class UnifiedICLRScraper:
    def __init__(self, year: int = 2023):
        self.year = year
        self.papers = []
        
        # === 关键点：根据年份判断使用哪个 API 版本 ===
        if self.year >= 2024:
            self.api_version = 2
            self.base_url = "https://api2.openreview.net"
            self.client = OpenReviewClient(baseurl=self.base_url)
            # v2 使用 venueid
            self.venue_id = f"ICLR.cc/{year}/Conference"
        else:
            self.api_version = 1
            self.base_url = "https://api.openreview.net"
            # v1 使用旧版 Client
            self.client = openreview.Client(baseurl=self.base_url)
            # v1 通常使用 invitation ID
            self.invitation_id = f"ICLR.cc/{year}/Conference/-/Blind_Submission"

    def get_all_papers(self) -> List[Dict]:
        print(f"开始获取 ICLR {self.year} 所有论文 (API v{self.api_version})...")
        
        try:
            if self.api_version == 2:
                # === API v2 逻辑 (2024+) ===
                print(f"Target Venue ID: {self.venue_id}")
                submissions = self.client.get_all_notes(content={'venueid': self.venue_id})
            else:
                # === API v1 逻辑 (2023及以前) ===
                print(f"Target Invitation: {self.invitation_id}")
                # v1 使用 tools.iterget_notes 比较稳妥，或者直接 get_notes
                submissions = openreview.tools.iterget_notes(
                    self.client, 
                    invitation=self.invitation_id
                )

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
                    continue

            print(f"成功获取 {len(self.papers)} 篇论文")
            return self.papers

        except Exception as e:
            print(f"获取论文时出错: {e}")
            if self.api_version == 1:
                print("提示：旧年份的 Invitation ID 可能会有所不同，请检查 OpenReview 对应年份的 URL。")
            return []

    def _parse_note(self, note) -> Dict:
        """统一解析 v1 和 v2 的 Note 对象"""
        info = {
            'title': '',
            'authors': [],
            'pdf_link': '',
            'source': 'ICLR',
            'year': self.year
        }
        
        # === 解析 API v2 ===
        if self.api_version == 2:
            if hasattr(note, 'content'):
                # 标题
                if 'title' in note.content:
                    info['title'] = note.content['title'].get('value', '')
                
                # 作者
                if 'authors' in note.content:
                    info['authors'] = note.content['authors'].get('value', [])
                
                # PDF
                if 'pdf' in note.content:
                    pdf_val = note.content['pdf'].get('value', '')
                    if pdf_val:
                        info['pdf_link'] = f"https://openreview.net/pdf?id={note.id}"

        # === 解析 API v1 ===
        else:
            if hasattr(note, 'content'):
                # v1 直接是值，不需要 .get('value')
                info['title'] = note.content.get('title', '')
                info['authors'] = note.content.get('authors', [])
                
                # v1 的 PDF 处理
                if 'pdf' in note.content:
                    # 以前有时是相对路径
                    info['pdf_link'] = f"https://openreview.net/pdf?id={note.id}"

        return info

    def save_to_json(self, filename: str = None):
        if filename is None:
            filename = f"ICLR{self.year}papers.json"
        
        # 确保保存到papers文件夹
        if not filename.startswith('papers/'):
            filename = os.path.join('papers', filename)
        
        # 确保papers文件夹存在
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.papers, f, ensure_ascii=False, indent=2)
        print(f"已保存到 {filename}")

def main():
    # 测试 2023 (API v1)
    # 也可以改为 2025 (API v2) 来测试兼容性
    target_year = 2017
    
    scraper = UnifiedICLRScraper(year=target_year)
    scraper.get_all_papers()
    scraper.save_to_json()

if __name__ == "__main__":
    main()
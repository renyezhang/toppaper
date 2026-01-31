import requests
from bs4 import BeautifulSoup
import json
import time
import os

def get_ijcai_papers(year=2025):
    # IJCAI Proceedings 的基础 URL
    base_url = f"https://www.ijcai.org/proceedings/{year}/"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    print(f"正在请求页面: {base_url} ...")
    
    try:
        response = requests.get(base_url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 用于存储所有论文数据的列表
    papers_list = []
    
    # IJCAI 的论文列表通常包含在 class 为 'paper_wrapper' 的 div 中
    # 注意：如果2025年网页结构发生重大变化，需要根据实际 HTML 修改此处选择器
    paper_containers = soup.find_all('div', class_='paper_wrapper')

    print(f"找到 {len(paper_containers)} 篇论文，开始解析...")

    for container in paper_containers:
        try:
            # 1. 获取标题
            title_div = container.find('div', class_='title')
            if not title_div:
                continue
            title = title_div.get_text(strip=True)

            # 2. 获取作者
            authors_div = container.find('div', class_='authors')
            authors = []
            if authors_div:
                authors_text = authors_div.get_text(strip=True)
                # 作者通常用逗号分隔
                authors = [a.strip() for a in authors_text.split(',')]

            # 3. 获取 PDF 链接
            pdf_link = ""
            details_div = container.find('div', class_='details')
            if details_div:
                links = details_div.find_all('a')
                for link in links:
                    href = link.get('href')
                    text = link.get_text(strip=True).lower()
                    
                    # 寻找包含 PDF 的链接
                    if href and 'pdf' in text:
                        # 处理相对路径
                        if not href.startswith('http'):
                            pdf_link = base_url.rstrip('/') + '/' + href.lstrip('/')
                        else:
                            pdf_link = href
                        break

            # 4. 构建数据对象
            paper_data = {
                "title": title,
                "authors": authors,
                "pdf_link": pdf_link,
                "source": "IJCAI",
                "year": year
            }
            
            # 注意：IJCAI 主列表通常不包含 github 代码链接。
            # 如果需要代码链接，通常需要爬取 ArXiv 或 PapersWithCode 的关联数据。
            # 为了保持格式一致，如果能从 details div 中找到 explicit 的 code 链接则添加，否则忽略
            
            papers_list.append(paper_data)

        except Exception as e:
            print(f"解析某篇论文时出错: {e}")
            continue

    return papers_list

def save_to_json(data, filename):
    # 确保保存到papers文件夹
    if not filename.startswith('papers/'):
        filename = os.path.join('papers', filename)
    
    # 确保papers文件夹存在
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"数据已保存至 {filename}")

if __name__ == "__main__":
    # 可以在这里修改年份
    year = 2017
    papers = get_ijcai_papers(year)
    
    if papers:
        # 保存结果到papers文件夹
        save_to_json(papers, f'IJCAI{year}papers.json')
        
        # 打印统计信息
        print(f"\n总共爬取了 {len(papers)} 篇论文")
        
    else:
        print("未找到论文数据，请检查年份是否已发布或网络连接。")
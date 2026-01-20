import json
import time
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os


def search_paper_in_edge(paper_title, driver, wait):
    """
    在Edge浏览器中搜索论文并返回前5个结果网址
    
    Args:
        paper_title: 论文标题
        driver: Edge WebDriver实例
        wait: WebDriverWait实例
    
    Returns:
        list: 前5个搜索结果网址
    """
    search_url = f"https://www.bing.com/search?q={paper_title}"
    driver.get(search_url)
    time.sleep(2)
    
    results = []
    try:
        result_elements = wait.until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.b_algo h2 a"))
        )[:5]
        
        for element in result_elements:
            href = element.get_attribute("href")
            if href:
                results.append(href)
    
    except Exception as e:
        print(f"搜索 '{paper_title}' 时出错: {e}")
    
    return results


def main():
    # 读取papers.json文件
    json_file = "papers.json"
    
    if not os.path.exists(json_file):
        print(f"错误: 找不到文件 {json_file}")
        return
    
    with open(json_file, 'r', encoding='utf-8') as f:
        papers = json.load(f)
    
    print(f"成功读取 {len(papers)} 篇论文")
    
    # 配置Edge浏览器
    edge_options = Options()
    edge_options.add_argument("--headless")  # 无头模式，不显示浏览器窗口
    edge_options.add_argument("--disable-gpu")
    edge_options.add_argument("--no-sandbox")
    edge_options.add_argument("--disable-dev-shm-usage")
    edge_options.add_argument("--disable-blink-features=AutomationControlled")
    edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    edge_options.add_experimental_option("useAutomationExtension", False)
    
    # 初始化Edge WebDriver
    driver = None
    try:
        driver = webdriver.Edge(options=edge_options)
        wait = WebDriverWait(driver, 10)
        
        for i, paper in enumerate(papers, 1):
            title = paper.get("title", "")
            if not title:
                continue

            if "code" in paper:
                print(f"[{i}/{len(papers)}] 跳过: {title[:50]}... (已有code)")
                continue
            
            print(f"[{i}/{len(papers)}] 正在搜索: {title[:50]}...")
            
            try:
                urls = search_paper_in_edge(title, driver, wait)
                print(f"  找到 {len(urls)} 个结果")

                for j, url in enumerate(urls, 1):
                    print(f"    {j}. {url}")

                    if "github.com" in url.lower() and "code" not in paper:
                        paper["code"] = url
                        print(f"    → 发现GitHub链接，已添加为code")

                        with open(json_file, 'w', encoding='utf-8') as f:
                            json.dump(papers, f, ensure_ascii=False, indent=2)
                        print(f"    → 已保存到 {json_file}")
                        break
            
            except Exception as e:
                print(f"  搜索失败: {e}")
            
            time.sleep(1)

        print(f"\n搜索完成！")
    
    except Exception as e:
        print(f"初始化Edge WebDriver时出错: {e}")
        print("请确保已安装Edge WebDriver并配置好环境变量")
    
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    main()

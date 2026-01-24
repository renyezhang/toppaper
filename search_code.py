import json
import time
import random
import os
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- 配置参数 ---
JSON_FILE = "AAAI2025papers.json"
RESTART_EVERY_N = 200  # 每爬取多少篇论文后重启一次浏览器
MIN_DELAY = 5  # 最小等待秒数
MAX_DELAY = 10  # 最大等待秒数


def init_driver():
    """初始化 Edge WebDriver"""
    edge_options = Options()
    # edge_options.add_argument("--headless") # 调试时建议注释掉这行，可以看到浏览器界面

    edge_options.add_argument("--disable-gpu")
    edge_options.add_argument("--no-sandbox")
    edge_options.add_argument("--disable-dev-shm-usage")
    edge_options.add_argument("--disable-blink-features=AutomationControlled")
    edge_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    edge_options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Edge(options=edge_options)

    # 屏蔽 webdriver 特征
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
            })
        """
    })

    return driver


def search_paper_in_edge(paper_title, driver, wait):
    """搜索论文并返回前5个结果"""
    # 搜索策略：标题精确匹配 + github 关键词
    query = f'"{paper_title}"'
    search_url = f"https://www.bing.com/search?q={query}"

    try:
        driver.get(search_url)
    except Exception as e:
        print(f"  [!] 页面加载异常: {e}")
        return []

    time.sleep(random.uniform(1.5, 3))  # 模拟浏览页面

    results = []
    try:
        # 获取搜索结果列表
        result_elements = wait.until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.b_algo h2 a"))
        )[:5]  # 限制前5个

        for element in result_elements:
            href = element.get_attribute("href")
            if href:
                results.append(href)
    except Exception as e:
        print(f"  [!] 未获取到结果元素: {e}")

    return results


def save_json(data):
    """保存数据"""
    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    if not os.path.exists(JSON_FILE):
        print(f"错误: 找不到文件 {JSON_FILE}")
        return

    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        papers = json.load(f)

    total_papers = len(papers)
    print(f"=== 开始任务：共 {total_papers} 篇论文 ===")

    driver = None
    wait = None

    try:
        driver = init_driver()
        wait = WebDriverWait(driver, 10)
        processed_count = 0

        for i, paper in enumerate(papers, 1):
            title = paper.get("title", "")
            if not title: continue

            # 跳过已有的
            if "code" in paper and paper["code"]:
                print(f"[{i}/{total_papers}] 跳过 (已有): {title[:20]}...")
                continue

            # 定期重启浏览器
            if processed_count >= RESTART_EVERY_N:
                print(f"\n>>> 正在重启浏览器以重置 Session...\n")
                driver.quit()
                time.sleep(5)
                driver = init_driver()
                wait = WebDriverWait(driver, 10)
                processed_count = 0

            print(f"[{i}/{total_papers}] 搜索: {title[:30]}...")

            urls = search_paper_in_edge(title, driver, wait)
            processed_count += 1

            # --- 修改部分：打印所有找到的结果 ---
            found_github = False
            if urls:
                print(f"    > 找到 {len(urls)} 个相关结果:")
                for j, url in enumerate(urls, 1):
                    # 打印每一条结果
                    print(f"      {j}. {url}")

                    # 检查是否是 GitHub 且还未找到
                    if not found_github and "github.com" in url.lower():
                        paper["code"] = url
                        print(f"      ↑ [MATCH] 发现目标代码库！")
                        found_github = True
                        save_json(papers)  # 立即保存
            else:
                print("    > 未找到任何结果 (可能需人工验证)")
            # -------------------------------------

            # 随机延时
            sleep_time = random.uniform(MIN_DELAY, MAX_DELAY)
            print(f"    (等待 {sleep_time:.1f}s...)")
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n用户中断程序，已保存进度。")
    except Exception as e:
        print(f"\n发生错误: {e}")
    finally:
        if driver:
            driver.quit()
        print("=== 结束 ===")


if __name__ == "__main__":
    main()
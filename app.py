import requests
from bs4 import BeautifulSoup
import random
import time
from fake_useragent import UserAgent

# 代理伺服器池
proxy_pool = [
    "http://proxy1.com:8080",
    "http://proxy2.com:8080",
    "http://proxy3.com:8080",
    # 添加更多的代理伺服器地址
]

# 用戶代理池
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edge/91.0.864.48",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 OPR/77.0.4054.172",
    # 添加更多的 User-Agent
]

# 隨機選擇代理和 User-Agent
def get_random_proxy():
    return random.choice(proxy_pool)

def get_random_user_agent():
    return random.choice(user_agents)

# 抓取 Google Scholar 搜尋結果
def fetch_google_scholar(keyword):
    search_url = f"https://scholar.google.com/scholar?q={keyword}"
    
    headers = {
        "User-Agent": get_random_user_agent(),
    }

    # 隨機選擇代理
    proxies = {
        "http": get_random_proxy(),
        "https": get_random_proxy(),
    }

    try:
        # 發送請求
        response = requests.get(search_url, headers=headers, proxies=proxies, timeout=10)
        response.raise_for_status()  # 如果請求失敗，會拋出異常
        
        soup = BeautifulSoup(response.text, "html.parser")

        results = []
        for item in soup.find_all("div", class_="gs_ri"):
            title = item.find("h3", class_="gs_rt").get_text()
            link = item.find("h3", class_="gs_rt").find("a")["href"] if item.find("h3", class_="gs_rt").find("a") else "#"
            author_pub = item.find("div", class_="gs_a").get_text()
            publication = item.find("div", class_="gs_a").get_text()
            
            results.append({
                "title": title,
                "link": link,
                "author": author_pub,
                "publication": publication
            })

            # 隨機延遲，增加延遲時間來模擬人類行為
            time.sleep(random.uniform(3, 6))  # 3到6秒的隨機延遲

        return results, None
    except requests.exceptions.RequestException as e:
        return [], f"請求錯誤：{e}，請稍後再試。"

# 範例使用：
keyword = "人力資源"
papers, error = fetch_google_scholar(keyword)

if papers:
    for i, paper in enumerate(papers, 1):
        print(f"{i}. {paper['title']} - {paper['link']}")
        print(f"作者: {paper['author']}")
        print(f"發表於: {paper['publication']}")
        print("-" * 80)
else:
    print(f"發生錯誤: {error}")

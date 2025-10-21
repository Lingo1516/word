from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import random
import time

# 設定 Chrome 驅動選項
chrome_options = Options()
chrome_options.add_argument("--headless")  # 無頭模式，不顯示瀏覽器視窗
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")

# 使用 ChromeDriver 啟動瀏覽器
driver = webdriver.Chrome(executable_path='/path/to/chromedriver', options=chrome_options)

def fetch_google_scholar(keyword):
    search_url = f"https://scholar.google.com/scholar?q={keyword}"

    # 打開 Google Scholar
    driver.get(search_url)

    # 等待頁面加載
    time.sleep(random.uniform(3, 6))  # 模擬人類行為，隨機延遲

    # 搜尋結果
    results = []
    try:
        # 擷取搜尋結果
        papers = driver.find_elements(By.CLASS_NAME, "gs_ri")
        
        for paper in papers:
            title = paper.find_element(By.CLASS_NAME, "gs_rt").text
            link = paper.find_element(By.CLASS_NAME, "gs_rt").find_element(By.TAG_NAME, "a").get_attribute("href")
            author_pub = paper.find_element(By.CLASS_NAME, "gs_a").text
            
            results.append({
                "title": title,
                "link": link,
                "author": author_pub,
            })
            
            # 隨機延遲
            time.sleep(random.uniform(3, 6))

    except Exception as e:
        print(f"錯誤：{e}")
    
    return results

# 範例使用：
keyword = "人力資源"
papers = fetch_google_scholar(keyword)

if papers:
    for i, paper in enumerate(papers, 1):
        print(f"{i}. {paper['title']} - {paper['link']}")
        print(f"作者: {paper['author']}")
        print("-" * 80)
else:
    print("未能抓取到文獻資料")

# 關閉瀏覽器
driver.quit()

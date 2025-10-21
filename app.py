import time
import random
import chromedriver_autoinstaller
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json
import csv
from datetime import datetime

class GoogleScholarScraper:
    def __init__(self, headless=True):
        """初始化爬蟲"""
        chromedriver_autoinstaller.install()
        
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        # 加入 User-Agent 模擬真實瀏覽器
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
    
    def fetch_papers(self, keyword, max_pages=1, year_start=None, year_end=None):
        """
        抓取學術論文
        :param keyword: 搜尋關鍵字
        :param max_pages: 最多抓取幾頁 (每頁約10篇)
        :param year_start: 起始年份
        :param year_end: 結束年份
        """
        all_results = []
        
        for page in range(max_pages):
            start = page * 10
            search_url = f"https://scholar.google.com/scholar?start={start}&q={keyword}"
            
            # 加入年份篩選
            if year_start and year_end:
                search_url += f"&as_ylo={year_start}&as_yhi={year_end}"
            
            print(f"\n正在抓取第 {page + 1} 頁...")
            print(f"URL: {search_url}")
            
            try:
                self.driver.get(search_url)
                time.sleep(random.uniform(3, 6))
                
                # 檢查是否被 CAPTCHA 阻擋
                if "sorry" in self.driver.current_url.lower():
                    print("⚠️ 被 Google 偵測到機器人行為，請稍後再試")
                    break
                
                # 等待搜尋結果載入
                papers = self.wait.until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, "gs_ri"))
                )
                
                page_results = self._parse_papers(papers)
                all_results.extend(page_results)
                
                print(f"✓ 成功抓取 {len(page_results)} 篇論文")
                
                # 隨機延遲，避免被偵測
                time.sleep(random.uniform(5, 10))
                
            except TimeoutException:
                print(f"⚠️ 第 {page + 1} 頁載入超時")
                break
            except Exception as e:
                print(f"❌ 錯誤：{e}")
                break
        
        return all_results
    
    def _parse_papers(self, papers):
        """解析論文資訊"""
        results = []
        
        for paper in papers:
            try:
                # 標題和連結
                title_elem = paper.find_element(By.CLASS_NAME, "gs_rt")
                title = title_elem.text
                
                try:
                    link = title_elem.find_element(By.TAG_NAME, "a").get_attribute("href")
                except NoSuchElementException:
                    link = "N/A"
                
                # 作者、期刊、年份資訊
                author_pub = paper.find_element(By.CLASS_NAME, "gs_a").text
                
                # 摘要
                try:
                    abstract = paper.find_element(By.CLASS_NAME, "gs_rs").text
                except NoSuchElementException:
                    abstract = "N/A"
                
                # 引用次數
                try:
                    citation_elem = paper.find_element(By.XPATH, ".//a[contains(text(), '引用次數')]")
                    citations = citation_elem.text.split("引用次數：")[-1] if "引用次數" in citation_elem.text else "0"
                except NoSuchElementException:
                    try:
                        citation_elem = paper.find_element(By.XPATH, ".//a[contains(text(), 'Cited by')]")
                        citations = citation_elem.text.split("Cited by ")[-1] if "Cited by" in citation_elem.text else "0"
                    except:
                        citations = "0"
                
                # 相關文章連結
                try:
                    related_link = paper.find_element(By.XPATH, ".//a[contains(text(), '相關文章') or contains(text(), 'Related articles')]").get_attribute("href")
                except NoSuchElementException:
                    related_link = "N/A"
                
                results.append({
                    "title": title,
                    "link": link,
                    "author_publication": author_pub,
                    "abstract": abstract,
                    "citations": citations,
                    "related_link": related_link,
                })
                
            except Exception as e:
                print(f"⚠️ 解析單篇論文時發生錯誤：{e}")
                continue
        
        return results
    
    def save_to_json(self, data, filename=None):
        """儲存為 JSON 格式"""
        if filename is None:
            filename = f"scholar_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n✓ 已儲存至 {filename}")
    
    def save_to_csv(self, data, filename=None):
        """儲存為 CSV 格式"""
        if filename is None:
            filename = f"scholar_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        if not data:
            print("⚠️ 沒有資料可儲存")
            return
        
        with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        print(f"✓ 已儲存至 {filename}")
    
    def close(self):
        """關閉瀏覽器"""
        self.driver.quit()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 使用範例
if __name__ == "__main__":
    # 使用 context manager 確保資源正確釋放
    with GoogleScholarScraper(headless=True) as scraper:
        # 搜尋參數
        keyword = "人力資源管理"
        max_pages = 2  # 抓取 2 頁 (約 20 篇論文)
        year_start = 2020  # 2020 年之後的論文
        year_end = 2024
        
        print(f"🔍 開始搜尋：{keyword}")
        print(f"📅 年份範圍：{year_start} - {year_end}")
        print(f"📄 頁數：{max_pages}")
        
        # 抓取論文
        papers = scraper.fetch_papers(
            keyword=keyword,
            max_pages=max_pages,
            year_start=year_start,
            year_end=year_end
        )
        
        # 顯示結果
        if papers:
            print(f"\n{'='*80}")
            print(f"總共抓取到 {len(papers)} 篇論文：")
            print(f"{'='*80}\n")
            
            for i, paper in enumerate(papers, 1):
                print(f"{i}. 📚 {paper['title']}")
                print(f"   🔗 連結: {paper['link']}")
                print(f"   ✍️  {paper['author_publication']}")
                print(f"   📊 引用次數: {paper['citations']}")
                print(f"   📝 摘要: {paper['abstract'][:100]}..." if len(paper['abstract']) > 100 else f"   📝 摘要: {paper['abstract']}")
                print(f"   {'-'*76}")
            
            # 儲存結果
            scraper.save_to_json(papers)
            scraper.save_to_csv(papers)
        else:
            print("\n❌ 未能抓取到文獻資料")

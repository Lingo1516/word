import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json
import csv
from datetime import datetime
import os

class GoogleScholarScraper:
    def __init__(self, headless=True):
        """初始化爬蟲"""
        chrome_options = Options()
        
        # 必要的 Chrome 選項
        if headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # User-Agent
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
        
        # 排除自動化標記
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            # 嘗試使用系統的 ChromeDriver（適用於 Streamlit Cloud）
            if os.path.exists('/usr/bin/chromedriver'):
                service = Service('/usr/bin/chromedriver')
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            elif os.path.exists('/usr/local/bin/chromedriver'):
                service = Service('/usr/local/bin/chromedriver')
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                # 如果沒有指定路徑，讓 Selenium 自動尋找
                self.driver = webdriver.Chrome(options=chrome_options)
            
            # 移除 webdriver 標記
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": self.driver.execute_script("return navigator.userAgent").replace('Headless', '')
            })
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.wait = WebDriverWait(self.driver, 15)
            print("✓ Chrome 瀏覽器啟動成功")
            
        except Exception as e:
            print(f"❌ 瀏覽器啟動失敗：{e}")
            print("\n💡 解決方案：")
            print("1. 確保已安裝 Chrome 和 ChromeDriver")
            print("2. 如果在 Streamlit Cloud，請確認 packages.txt 包含：")
            print("   chromium")
            print("   chromium-driver")
            raise
    
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
            
            try:
                self.driver.get(search_url)
                time.sleep(random.uniform(4, 7))
                
                # 檢查是否被 CAPTCHA 阻擋
                if "sorry" in self.driver.current_url.lower() or "captcha" in self.driver.page_source.lower():
                    print("⚠️ 被 Google 偵測到機器人行為，請稍後再試")
                    print("💡 建議：增加延遲時間或減少抓取頁數")
                    break
                
                # 等待搜尋結果載入
                try:
                    papers = self.wait.until(
                        EC.presence_of_all_elements_located((By.CLASS_NAME, "gs_ri"))
                    )
                except TimeoutException:
                    print("⚠️ 找不到搜尋結果，可能是網路問題或被阻擋")
                    break
                
                page_results = self._parse_papers(papers)
                all_results.extend(page_results)
                
                print(f"✓ 成功抓取 {len(page_results)} 篇論文")
                
                # 隨機延遲，避免被偵測
                if page < max_pages - 1:  # 不是最後一頁才延遲
                    delay = random.uniform(6, 12)
                    print(f"⏳ 等待 {delay:.1f} 秒後繼續...")
                    time.sleep(delay)
                
            except Exception as e:
                print(f"❌ 第 {page + 1} 頁發生錯誤：{e}")
                break
        
        return all_results
    
    def _parse_papers(self, papers):
        """解析論文資訊"""
        results = []
        
        for idx, paper in enumerate(papers, 1):
            try:
                # 標題和連結
                title_elem = paper.find_element(By.CLASS_NAME, "gs_rt")
                title = title_elem.text.strip()
                
                try:
                    link = title_elem.find_element(By.TAG_NAME, "a").get_attribute("href")
                except NoSuchElementException:
                    link = "N/A"
                
                # 作者、期刊、年份資訊
                try:
                    author_pub = paper.find_element(By.CLASS_NAME, "gs_a").text.strip()
                except NoSuchElementException:
                    author_pub = "N/A"
                
                # 摘要
                try:
                    abstract = paper.find_element(By.CLASS_NAME, "gs_rs").text.strip()
                except NoSuchElementException:
                    abstract = "N/A"
                
                # 引用次數
                citations = "0"
                try:
                    cite_links = paper.find_elements(By.CLASS_NAME, "gs_fl")
                    for link_elem in cite_links:
                        text = link_elem.text
                        if "引用次數" in text or "Cited by" in text:
                            citations = text.split("：")[-1].split()[-1] if "：" in text else text.split()[-1]
                            break
                except:
                    pass
                
                # 相關文章連結
                try:
                    related_links = paper.find_elements(By.CLASS_NAME, "gs_fl")
                    related_link = "N/A"
                    for link_elem in related_links:
                        if "相關文章" in link_elem.text or "Related articles" in link_elem.text:
                            related_link = link_elem.find_element(By.TAG_NAME, "a").get_attribute("href")
                            break
                except:
                    related_link = "N/A"
                
                if title:  # 只加入有標題的結果
                    results.append({
                        "序號": len(results) + 1,
                        "title": title,
                        "link": link,
                        "author_publication": author_pub,
                        "abstract": abstract,
                        "citations": citations,
                        "related_link": related_link,
                    })
                
            except Exception as e:
                print(f"⚠️ 解析第 {idx} 篇論文時發生錯誤：{e}")
                continue
        
        return results
    
    def save_to_json(self, data, filename=None):
        """儲存為 JSON 格式"""
        if not data:
            print("⚠️ 沒有資料可儲存")
            return
        
        if filename is None:
            filename = f"scholar_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✓ 已儲存至 {filename}")
            return filename
        except Exception as e:
            print(f"❌ 儲存 JSON 失敗：{e}")
            return None
    
    def save_to_csv(self, data, filename=None):
        """儲存為 CSV 格式"""
        if not data:
            print("⚠️ 沒有資料可儲存")
            return
        
        if filename is None:
            filename = f"scholar_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        try:
            with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            print(f"✓ 已儲存至 {filename}")
            return filename
        except Exception as e:
            print(f"❌ 儲存 CSV 失敗：{e}")
            return None
    
    def close(self):
        """關閉瀏覽器"""
        try:
            self.driver.quit()
            print("✓ 瀏覽器已關閉")
        except Exception as e:
            print(f"⚠️ 關閉瀏覽器時發生錯誤：{e}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 使用範例
if __name__ == "__main__":
    try:
        # 使用 context manager 確保資源正確釋放
        with GoogleScholarScraper(headless=True) as scraper:
            # 搜尋參數
            keyword = "人力資源管理"
            max_pages = 1  # 建議從 1 頁開始測試
            year_start = 2020
            year_end = 2024
            
            print(f"🔍 開始搜尋：{keyword}")
            print(f"📅 年份範圍：{year_start} - {year_end}")
            print(f"📄 頁數：{max_pages}")
            print("="*80)
            
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
                print(f"✓ 總共抓取到 {len(papers)} 篇論文")
                print(f"{'='*80}\n")
                
                for paper in papers:
                    print(f"{paper['序號']}. 📚 {paper['title']}")
                    print(f"   🔗 {paper['link']}")
                    print(f"   ✍️  {paper['author_publication']}")
                    print(f"   📊 引用: {paper['citations']}")
                    if paper['abstract'] != "N/A":
                        abstract_preview = paper['abstract'][:150] + "..." if len(paper['abstract']) > 150 else paper['abstract']
                        print(f"   📝 {abstract_preview}")
                    print(f"   {'-'*76}")
                
                # 儲存結果
                print("\n💾 儲存結果...")
                scraper.save_to_json(papers)
                scraper.save_to_csv(papers)
                
            else:
                print("\n❌ 未能抓取到文獻資料")
                print("💡 可能原因：")
                print("   1. 網路連線問題")
                print("   2. 被 Google Scholar 阻擋")
                print("   3. 搜尋關鍵字沒有結果")
                
    except KeyboardInterrupt:
        print("\n⚠️ 使用者中斷程式")
    except Exception as e:
        print(f"\n❌ 程式執行失敗：{e}")
        print("\n💡 請檢查：")
        print("   1. Chrome 和 ChromeDriver 是否已正確安裝")
        print("   2. 網路連線是否正常")
        print("   3. 是否有足夠的系統權限")

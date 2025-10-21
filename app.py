import time
import random
import json
import csv
from datetime import datetime

# 測試版本 - 不使用 Selenium
print("=" * 80)
print("Google Scholar 爬蟲 - 測試版本")
print("=" * 80)

def test_imports():
    """測試套件是否正確安裝"""
    print("\n📦 測試套件安裝...")
    
    try:
        import selenium
        print(f"✓ Selenium 版本: {selenium.__version__}")
    except ImportError as e:
        print(f"❌ Selenium 未安裝: {e}")
        return False
    
    try:
        from selenium import webdriver
        print("✓ Selenium Webdriver 可用")
    except ImportError as e:
        print(f"❌ Webdriver 匯入失敗: {e}")
        return False
    
    return True

def test_chromedriver():
    """測試 ChromeDriver 是否可用"""
    print("\n🔍 測試 ChromeDriver...")
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        import os
        
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        
        # 測試不同的 ChromeDriver 路徑
        paths_to_test = [
            None,  # 讓 Selenium 自動尋找
            '/usr/bin/chromedriver',
            '/usr/local/bin/chromedriver',
            'chromedriver'
        ]
        
        for path in paths_to_test:
            try:
                print(f"\n嘗試路徑: {path if path else '自動偵測'}")
                
                if path and os.path.exists(path):
                    service = Service(path)
                    driver = webdriver.Chrome(service=service, options=chrome_options)
                elif path is None:
                    driver = webdriver.Chrome(options=chrome_options)
                else:
                    continue
                
                print(f"✓ Chrome 啟動成功！")
                print(f"✓ Chrome 版本: {driver.capabilities['browserVersion']}")
                print(f"✓ ChromeDriver 版本: {driver.capabilities['chrome']['chromedriverVersion'].split()[0]}")
                
                # 測試訪問網頁
                print("\n測試訪問 Google...")
                driver.get("https://www.google.com")
                time.sleep(2)
                print(f"✓ 頁面標題: {driver.title}")
                
                driver.quit()
                return True
                
            except Exception as e:
                print(f"✗ 失敗: {str(e)[:100]}")
                continue
        
        print("\n❌ 所有路徑都失敗")
        return False
        
    except Exception as e:
        print(f"❌ ChromeDriver 測試失敗: {e}")
        return False

class SimpleScholarScraper:
    """簡化版爬蟲 - 用於測試"""
    
    def __init__(self):
        print("\n🚀 初始化爬蟲...")
        
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        import os
        
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        try:
            # 嘗試啟動 Chrome
            if os.path.exists('/usr/bin/chromedriver'):
                service = Service('/usr/bin/chromedriver')
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                self.driver = webdriver.Chrome(options=chrome_options)
            
            print("✓ 瀏覽器啟動成功")
            
        except Exception as e:
            print(f"❌ 瀏覽器啟動失敗: {e}")
            raise
    
    def test_search(self, keyword="machine learning"):
        """測試搜尋功能"""
        print(f"\n🔍 測試搜尋: {keyword}")
        
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            url = f"https://scholar.google.com/scholar?q={keyword}"
            print(f"訪問: {url}")
            
            self.driver.get(url)
            time.sleep(5)
            
            print(f"✓ 當前 URL: {self.driver.current_url}")
            print(f"✓ 頁面標題: {self.driver.title}")
            
            # 檢查是否被阻擋
            if "sorry" in self.driver.current_url.lower():
                print("⚠️ 被 Google 阻擋（CAPTCHA）")
                return []
            
            # 嘗試找到搜尋結果
            wait = WebDriverWait(self.driver, 10)
            papers = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "gs_ri")))
            
            print(f"✓ 找到 {len(papers)} 篇論文")
            
            results = []
            for i, paper in enumerate(papers[:3], 1):  # 只抓前3篇測試
                try:
                    title = paper.find_element(By.CLASS_NAME, "gs_rt").text
                    print(f"\n{i}. {title[:80]}...")
                    results.append({"title": title})
                except Exception as e:
                    print(f"⚠️ 解析第 {i} 篇失敗: {e}")
            
            return results
            
        except Exception as e:
            print(f"❌ 搜尋失敗: {e}")
            
            # 保存截圖用於除錯
            try:
                screenshot_path = "error_screenshot.png"
                self.driver.save_screenshot(screenshot_path)
                print(f"📸 已保存截圖: {screenshot_path}")
            except:
                pass
            
            return []
    
    def close(self):
        """關閉瀏覽器"""
        try:
            self.driver.quit()
            print("\n✓ 瀏覽器已關閉")
        except:
            pass

# ============ 主程式 ============
if __name__ == "__main__":
    print("\n開始測試...\n")
    
    # 步驟 1: 測試套件
    if not test_imports():
        print("\n❌ 請先安裝必要套件:")
        print("pip install selenium")
        exit(1)
    
    # 步驟 2: 測試 ChromeDriver
    if not test_chromedriver():
        print("\n" + "=" * 80)
        print("❌ ChromeDriver 無法運行")
        print("=" * 80)
        print("\n💡 解決方案：")
        print("\n【方案 1】使用 webdriver-manager (推薦)")
        print("pip install webdriver-manager")
        print("\n然後在程式中加入:")
        print("from webdriver_manager.chrome import ChromeDriverManager")
        print("service = Service(ChromeDriverManager().install())")
        
        print("\n【方案 2】手動安裝 ChromeDriver")
        print("Ubuntu/Debian:")
        print("  sudo apt-get update")
        print("  sudo apt-get install -y chromium-browser chromium-chromedriver")
        
        print("\nmacOS:")
        print("  brew install --cask google-chrome")
        print("  brew install chromedriver")
        
        print("\nWindows:")
        print("  1. 下載 ChromeDriver: https://chromedriver.chromium.org/")
        print("  2. 放到 PATH 路徑中")
        
        print("\n【方案 3】使用替代方案")
        print("考慮使用 Google Scholar API 或其他學術資料庫 API")
        exit(1)
    
    # 步驟 3: 測試實際搜尋
    print("\n" + "=" * 80)
    print("開始實際搜尋測試")
    print("=" * 80)
    
    try:
        scraper = SimpleScholarScraper()
        results = scraper.test_search("人工智慧")
        
        if results:
            print(f"\n✓✓✓ 測試成功！找到 {len(results)} 篇論文")
        else:
            print("\n⚠️ 沒有找到結果，但程式可以運行")
        
        scraper.close()
        
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        print("\n詳細錯誤:")
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("測試完成")
    print("=" * 80)

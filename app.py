import streamlit as st
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
import subprocess
import sys
import urllib.parse
import time
import random

# --- 雲端環境設定區塊 ---
# 這個區塊確保在 Streamlit Cloud 上能自動安裝並設定好 Playwright

@st.cache_resource
def _install_playwright_core():
    """核心安裝函式，會被快取。"""
    try:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"], 
            check=True,
            capture_output=True,
            text=True
        )
    except Exception as e:
        raise RuntimeError(f"安裝 Playwright 瀏覽器失敗: {e}") from e

def setup_environment():
    """處理使用者介面的包裝函式。"""
    try:
        _install_playwright_core()
    except Exception as e:
        st.error(e)
        st.stop()

# 應用程式啟動時，先執行環境設定
with st.spinner("正在設定雲端執行環境，請稍候..."):
    setup_environment()

# --- 設定區塊結束 ---


# 抓取 Google 學術搜尋結果的函數
def fetch_google_scholar(keyword):
    """
    使用 Playwright 前往 Google 學術搜尋，抓取文獻標題和連結。
    """
    results = []
    # 將關鍵字進行 URL 編碼，避免特殊字元問題
    encoded_keyword = urllib.parse.quote(keyword)
    # 新增 hl=zh-TW 參數來指定繁體中文介面
    target_url = f'https://scholar.google.com/scholar?hl=zh-TW&q={encoded_keyword}'
    page = None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
                java_script_enabled=True,
                # 模擬台灣時區和語言
                locale="zh-TW",
                timezone_id="Asia/Taipei"
            )
            page = context.new_page()
            
            page.goto(target_url, timeout=60000, wait_until='domcontentloaded')
            
            # 隨機延遲 1 到 3 秒，模擬真人行為
            time.sleep(random.uniform(1, 3))

            # 等待搜尋結果的容器出現
            page.wait_for_selector('#gs_res_ccl_mid', timeout=30000)

            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            paper_blocks = soup.find_all('div', class_='gs_r gs_or gs_scl')

            for block in paper_blocks:
                title_element = block.find('h3', class_='gs_rt')
                if title_element and title_element.a:
                    title = title_element.a.text
                    link = title_element.a['href']
                    author_element = block.find('div', class_='gs_a')
                    author = author_element.text if author_element else "作者資訊未提供"
                    snippet_element = block.find('div', class_='gs_rs')
                    snippet = snippet_element.text if snippet_element else ""

                    results.append({
                        "title": title,
                        "link": link,
                        "author": author,
                        "snippet": snippet
                    })
            
            browser.close()
            return results, None # 成功時回傳結果和空的截圖

    except PlaywrightTimeoutError:
        st.error("頁面加載超時。Google 可能顯示了 CAPTCHA 驗證，或是暫時阻擋了請求。")
        screenshot_bytes = None
        if page:
            try:
                screenshot_bytes = page.screenshot()
            except Exception:
                pass # 截圖失敗也沒關係
        return [], screenshot_bytes # 失敗時回傳空結果和截圖
    except Exception as e:
        st.error(f"抓取資料時發生未預期的錯誤：{e}")
        return [], None

# Streamlit 應用主函數
def main():
    st.set_page_config(layout="wide", page_title="Google 學術搜尋爬取工具")
    st.title("🔎 Google 學術搜尋爬取工具")
    st.write("輸入關鍵字，即可抓取相關的學術文獻標題、作者與連結。")

    keyword = st.text_input("輸入您想要搜尋的關鍵字（例如：Machine Learning）", "")

    if st.button('開始搜尋', type="primary"):
        if keyword:
            with st.spinner(f'正在 Google 學術搜尋中搜尋「{keyword}」...'):
                papers, screenshot = fetch_google_scholar(keyword)
            
            if papers:
                st.success(f"成功抓取到 {len(papers)} 筆文獻結果：")
                for i, paper in enumerate(papers, 1):
                    st.markdown(f"### {i}. [{paper['title']}]({paper['link']})")
                    st.caption(f"**作者:** {paper['author']}")
                    if paper['snippet']:
                        st.markdown(f"> {paper['snippet']}")
                    st.divider()
            else:
                st.warning("未能抓取到任何文獻，請嘗試更換關鍵字。")

            if screenshot:
                st.subheader("🕵️‍♂️ 除錯資訊：案發現場截圖")
                st.image(screenshot, caption="這是爬蟲超時前看到的最後畫面，請檢查是否有 CAPTCHA。")
        else:
            st.warning("請先輸入要搜尋的關鍵字。")

if __name__ == "__main__":
    main()


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
    encoded_keyword = urllib.parse.quote(keyword)
    target_url = f'https://scholar.google.com/scholar?hl=zh-TW&q={encoded_keyword}'
    page = None
    captcha_detected = False

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
                java_script_enabled=True,
                locale="zh-TW",
                timezone_id="Asia/Taipei",
                # 新增更詳細的瀏覽器指紋
                viewport={'width': 1920, 'height': 1080},
                screen={'width': 1920, 'height': 1080},
                color_scheme='dark',
            )
            page = context.new_page()
            
            page.goto(target_url, timeout=60000, wait_until='domcontentloaded')
            
            # --- 終極策略：智慧型等待與 CAPTCHA 偵測 ---
            # 1. 檢查是否一開始就被 CAPTCHA 擋住
            if page.locator('iframe[src*="recaptcha"]').count() > 0:
                captcha_detected = True
                raise PlaywrightTimeoutError("偵測到 CAPTCHA，無法繼續。")

            # 2. 使用 networkidle 智慧型等待，確保頁面完全載入
            page.wait_for_load_state('networkidle', timeout=30000)
            time.sleep(random.uniform(1, 2)) # 等待後再稍作停留

            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            paper_blocks = soup.find_all('div', class_='gs_r gs_or gs_scl')

            # 如果找不到結果，也當作是被擋了，拍張照看看
            if not paper_blocks:
                 raise PlaywrightTimeoutError("頁面已載入，但找不到搜尋結果區塊。")

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
                        "title": title, "link": link, "author": author, "snippet": snippet
                    })
            
            browser.close()
            return results, None, False

    except PlaywrightTimeoutError as e:
        error_message = f"頁面加載超時或結構不符：{e}"
        if captcha_detected:
            error_message = "很抱歉，Google 偵測到自動化行為並顯示了 CAPTCHA (我不是機器人) 驗證，因此無法繼續抓取。"
        
        screenshot_bytes = None
        if page:
            try:
                screenshot_bytes = page.screenshot()
            except Exception:
                pass
        return [], screenshot_bytes, error_message
    except Exception as e:
        return [], None, f"抓取資料時發生未預期的錯誤：{e}"

# Streamlit 應用主函數
def main():
    st.set_page_config(layout="wide", page_title="Google 學術搜尋爬取工具")
    st.title("🔎 Google 學術搜尋爬取工具")
    st.write("輸入關鍵字，即可抓取相關的學術文獻標題、作者與連結。")

    keyword = st.text_input("輸入您想要搜尋的關鍵字（例如：Machine Learning）", "")

    if st.button('開始搜尋', type="primary"):
        if keyword:
            with st.spinner(f'正在 Google 學術搜尋中搜尋「{keyword}」...'):
                papers, screenshot, error = fetch_google_scholar(keyword)
            
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

            if error:
                st.error(error) # 顯示更詳細的錯誤訊息

            if screenshot:
                st.subheader("🕵️‍♂️ 除錯資訊：案發現場截圖")
                st.image(screenshot, caption="這是爬蟲超時前看到的最後畫面。")
        else:
            st.warning("請先輸入要搜尋的關鍵字。")

if __name__ == "__main__":
    main()


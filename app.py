import streamlit as st
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
import subprocess
import sys
import time

# --- 自動安裝 Playwright 瀏覽器的設定區塊 ---

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

with st.spinner("正在設定執行環境，請稍候..."):
    setup_environment()
st.toast("✅ 環境設定完成！", icon="🎉")

# --- 設定區塊結束 ---


# 使用 Playwright 抓取學術文獻的函數
def fetch_academic_papers(keyword):
    """
    使用 Playwright 前往華藝線上圖書館，抓取文獻標題。
    如果失敗，會回傳螢幕截圖和 HTML 原始碼以供除錯。
    """
    screenshot_bytes = None
    html_content = ""
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
                viewport={'width': 1280, 'height': 800} # 設定視窗大小
            )
            page = context.new_page()

            # --- 變更：改用更簡單的標準搜尋頁面 ---
            # 有時候進階搜尋頁面會有更強的反爬蟲機制
            target_url = f'https://www.airitilibrary.com/search?q={keyword}'
            
            page.goto(target_url, timeout=60000, wait_until='domcontentloaded')
            
            # --- 處理 Cookie 同意按鈕 ---
            try:
                cookie_button_selector = 'a.cookie_btn:has-text("我同意")'
                page.locator(cookie_button_selector).click(timeout=10000)
                st.toast("已自動點擊 Cookie 同意按鈕", icon="🍪")
                time.sleep(2) # 點擊後等待一下
            except PlaywrightTimeoutError:
                pass 
            
            # 等待搜尋結果容器元素出現
            page.wait_for_selector('div.search_result_list', timeout=30000)

            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            titles = soup.find_all('h3', class_='title')
            titles_text = [title.text.strip() for title in titles]

            context.close()
            browser.close()
            
            return titles_text, None, None # 成功時回傳標題
            
    except PlaywrightTimeoutError as e:
        st.error("頁面加載超時，已擷取當前畫面以供除錯。")
        # --- 新增：錯誤時擷取畫面和原始碼 ---
        try:
            screenshot_bytes = page.screenshot()
            html_content = page.content()
        except Exception as screenshot_error:
            st.warning(f"擷取除錯資訊時發生額外錯誤: {screenshot_error}")
        # 即使出錯也要確保瀏覽器關閉
        if 'browser' in locals() and browser.is_connected():
            browser.close()
        return [], screenshot_bytes, html_content # 失敗時回傳除錯資訊

    except Exception as e:
        st.error(f"抓取資料時發生未預期的錯誤：{e}")
        if 'browser' in locals() and browser.is_connected():
            browser.close()
        return [], None, None

# Streamlit 應用主函數
def main():
    st.title("華藝線上圖書館文獻爬取")
    st.write("輸入關鍵字，點擊按鈕後，程式會自動前往華藝線上圖書館抓取相關的文獻標題。")

    keyword = st.text_input("輸入您想要搜尋的關鍵字（例如：策略管理）", "")

    if st.button('抓取學術文獻'):
        if keyword:
            with st.spinner(f'正在搜尋「{keyword}」的相關文獻...'):
                titles, screenshot, html = fetch_academic_papers(keyword)
            
            if titles:
                st.success(f"成功抓取到 {len(titles)} 筆文獻標題：")
                with st.expander("點此查看所有標題"):
                    for i, title in enumerate(titles, 1):
                        st.write(f"{i}. {title}")
            else:
                st.warning("未能抓取到任何文獻。")

            # --- 新增：如果收到除錯資訊，就顯示出來 ---
            if screenshot:
                st.subheader("🕵️‍♂️ 除錯資訊：案發現場截圖")
                st.image(screenshot, caption="這是爬蟲超時前看到的最後畫面")
            
            if html:
                with st.expander("點此查看當時的網頁原始碼"):
                    st.code(html, language='html')
        else:
            st.warning("請先輸入要搜尋的關鍵字。")

if __name__ == "__main__":
    main()


import streamlit as st
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
import subprocess
import sys
import time

# --- 自動安裝 Playwright 瀏覽器的設定區塊 (已修正) ---

@st.cache_resource
def _install_playwright_core():
    """
    這是核心的安裝函式，只包含安裝邏輯，沒有任何 Streamlit 介面指令。
    這個函式將被快取。如果安裝失敗，它會拋出一個例外。
    """
    try:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"], 
            check=True,
            capture_output=True,
            text=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        # 將原始錯誤包裝成一個新的例外，以便上層函式捕捉
        raise RuntimeError(f"安裝 Playwright 瀏覽器失敗，錯誤訊息：{e.stderr}") from e
    except Exception as e:
        raise RuntimeError(f"環境設定時發生未預期的錯誤：{e}") from e

def setup_environment():
    """
    這是一個處理使用者介面的包裝函式。
    它會呼叫被快取的核心函式，並顯示進度條和錯誤訊息。
    """
    try:
        # 呼叫核心安裝函式。如果已經快取，這裡會立刻返回。
        _install_playwright_core()
    except Exception as e:
        # 如果核心函式在首次執行時拋出例外，就在這裡顯示錯誤並停止。
        st.error(e)
        st.stop()

# 應用程式啟動時，先執行環境設定
# 我們在主流程中顯示 spinner，因為 setup_environment 本身不應包含 UI
with st.spinner("正在設定執行環境，請稍候..."):
    setup_environment()
st.toast("✅ 環境設定完成！", icon="🎉")

# --- 設定區塊結束 ---


# 使用 Playwright 抓取學術文獻的函數
def fetch_academic_papers(keyword):
    """
    使用 Playwright 前往華藝線上圖書館，根據關鍵字抓取文獻標題。
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            target_url = f'https://www.airitilibrary.com/advsearch?keyword={keyword}'
            
            # 前往目標頁面，使用 domcontentloaded 加快初步載入速度
            page.goto(target_url, timeout=60000, wait_until='domcontentloaded')
            
            # --- 新增：處理 Cookie 同意按鈕 ---
            # 給予頁面短暫時間渲染，然後嘗試點擊 Cookie 按鈕
            try:
                # 等待「我同意」按鈕出現（最多等5秒），如果出現就點擊它
                cookie_button_selector = 'a.cookie_btn:has-text("我同意")'
                page.locator(cookie_button_selector).click(timeout=5000)
                st.toast("已自動點擊 Cookie 同意按鈕", icon="🍪")
                # 點擊後多等待一秒，確保頁面反應
                time.sleep(1)
            except PlaywrightTimeoutError:
                # 如果5秒內沒找到按鈕，代表它可能不存在，直接忽略此錯誤繼續執行
                pass 
            # --- 新增結束 ---
            
            # 現在才等待我們真正需要的搜尋結果容器元素出現
            page.wait_for_selector('div.search_result_list', timeout=30000)

            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            titles = soup.find_all('h3', class_='title')
            titles_text = [title.text.strip() for title in titles]

            context.close()
            browser.close()
            
            return titles_text
    except PlaywrightTimeoutError:
        st.error("頁面加載超時。這很可能是因為目標網站啟動了反爬蟲機制，或是網站結構已更改。請稍後再試。")
        return []
    except Exception as e:
        st.error(f"抓取資料時發生未預期的錯誤：{e}")
        return []

# Streamlit 應用主函數
def main():
    st.title("華藝線上圖書館文獻爬取")
    st.write("輸入關鍵字，點擊按鈕後，程式會自動前往華藝線上圖書館抓取相關的文獻標題。")

    keyword = st.text_input("輸入您想要搜尋的關鍵字（例如：策略管理）", "")

    if st.button('抓取學術文獻'):
        if keyword:
            with st.spinner(f'正在搜尋「{keyword}」的相關文獻，請稍候...'):
                titles = fetch_academic_papers(keyword)
            
            if titles:
                st.success(f"成功抓取到 {len(titles)} 筆文獻標題：")
                with st.expander("點此查看所有標題"):
                    for i, title in enumerate(titles, 1):
                        st.write(f"{i}. {title}")
            else:
                st.warning("未能抓取到任何文獻，請檢查關鍵字是否正確，或該關鍵字可能沒有相關結果。")
        else:
            st.warning("請先輸入要搜尋的關鍵字。")

# 確保在直接運行此程式時，執行 main 函數
if __name__ == "__main__":
    main()


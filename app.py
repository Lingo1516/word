import streamlit as st
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
import subprocess
import sys

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
            
            # --- 新增：模擬真實使用者瀏覽器 ---
            # 設定一個常見的 User-Agent，降低被網站偵測為爬蟲的機率
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"
            )
            page = context.new_page()
            # --- 新增結束 ---

            target_url = f'https://www.airitilibrary.com/advsearch?keyword={keyword}'
            
            # 前往目標頁面，並等待頁面網路活動基本停止，這對動態載入的網站更穩定
            page.goto(target_url, timeout=60000, wait_until='networkidle')
            
            # 等待搜尋結果的容器元素出現
            page.wait_for_selector('div.search_result_list', timeout=30000)

            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            titles = soup.find_all('h3', class_='title')
            titles_text = [title.text.strip() for title in titles]

            # 關閉瀏覽器上下文和瀏覽器本身
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


import streamlit as st
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
import subprocess
import sys

# --- 自動安裝 Playwright 瀏覽器的設定區塊 ---
@st.cache_resource
def install_playwright_browsers():
    """
    在 Streamlit Cloud 環境中自動安裝 Playwright 所需的瀏覽器。
    使用 st.cache_resource 快取，確保這個函數在每次部署中只會被執行一次。
    """
    with st.spinner("正在設定執行環境，請稍候..."):
        try:
            # 執行 playwright install 指令來下載瀏覽器
            # 使用 sys.executable 確保我們使用的是當前 Python 環境中的 playwright
            subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"], 
                check=True,
                capture_output=True, # 捕捉輸出，避免顯示在 Streamlit 介面上
                text=True
            )
            st.toast("✅ 環境設定完成！", icon="🎉")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            st.error(f"安裝 Playwright 瀏覽器失敗，錯誤訊息：{e.stderr}")
            st.stop() # 如果安裝失敗，則停止應用程式執行
        except Exception as e:
            st.error(f"發生未預期的錯誤於環境設定：{e}")
            st.stop()

# 應用程式啟動時，先執行環境設定
install_playwright_browsers()
# --- 設定區塊結束 ---


# 使用 Playwright 抓取學術文獻的函數
def fetch_academic_papers(keyword):
    """
    使用 Playwright 前往華藝線上圖書館，根據關鍵字抓取文獻標題。
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            target_url = f'https://www.airitilibrary.com/advsearch?keyword={keyword}'
            page.goto(target_url, timeout=60000)
            page.wait_for_selector('div.search_result_list', timeout=30000)
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            titles = soup.find_all('h3', class_='title')
            titles_text = [title.text.strip() for title in titles]
            browser.close()
            return titles_text
    except PlaywrightTimeoutError:
        st.error("頁面加載超時，可能是網路問題或網站結構已更改。請稍後再試。")
        return []
    except Exception as e:
        st.error(f"發生未預期的錯誤：{e}")
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


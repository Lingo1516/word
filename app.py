import streamlit as st
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
import time

# --- 在本機執行時，不再需要複雜的環境設定 ---

# 使用 Playwright 抓取學術文獻的函數
def fetch_academic_papers(keyword):
    """
    使用 Playwright 前往華藝線上圖書館，抓取文獻標題。
    如果失敗，會回傳螢幕截圖和 HTML 原始碼以供除錯。
    """
    page = None
    
    try:
        with sync_playwright() as p:
            st.info("1. 正在啟動瀏覽器...")
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
                viewport={'width': 1280, 'height': 800}
            )
            page = context.new_page()

            target_url = f'https://www.airitilibrary.com/search?q={keyword}'
            st.info(f"2. 正在前往目標網址：{target_url}")
            page.goto(target_url, timeout=60000, wait_until='domcontentloaded')
            
            st.info("3. 正在尋找 Cookie 同意按鈕...")
            try:
                cookie_button_selector = 'a.cookie_btn:has-text("我同意")'
                page.locator(cookie_button_selector).click(timeout=10000)
                st.toast("已自動點擊 Cookie 同意按鈕", icon="🍪")
                time.sleep(2)
            except PlaywrightTimeoutError:
                st.info("找不到 Cookie 按鈕，可能無需點擊。")
                pass 
            
            st.info("4. 正在等待搜尋結果載入...")
            page.wait_for_selector('div.search_result_list', timeout=30000)
            st.info("5. 成功找到搜尋結果！正在解析內容...")

            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            titles = soup.find_all('h3', class_='title')
            titles_text = [title.text.strip() for title in titles]
            
            return titles_text, None, None # 成功時回傳標題
            
    except PlaywrightTimeoutError:
        st.error("頁面加載超時。請確認您的 VPN 已連線。")
        screenshot_bytes = None
        html_content = ""
        try:
            if page:
                screenshot_bytes = page.screenshot()
                html_content = page.content()
        except Exception as screenshot_error:
            st.warning(f"擷取除錯資訊時發生額外錯誤: {screenshot_error}")
        return [], screenshot_bytes, html_content

    except Exception as e:
        st.error(f"抓取資料時發生未預期的錯誤：{e}")
        return [], None, None

# Streamlit 應用主函數
def main():
    st.title("華藝線上圖書館文獻爬取")
    st.write("輸入關鍵字，點擊按鈕後，程式會自動前往華藝線上圖書館抓取相關的文獻標題。")

    keyword = st.text_input("輸入您想要搜尋的關鍵字（例如：策略管理）", "")

    if st.button('抓取學術文獻'):
        if keyword:
            titles, screenshot, html = fetch_academic_papers(keyword)
            
            if titles:
                st.success(f"成功抓取到 {len(titles)} 筆文獻標題：")
                with st.expander("點此查看所有標題"):
                    for i, title in enumerate(titles, 1):
                        st.write(f"{i}. {title}")
            else:
                st.warning("未能抓取到任何文獻。")

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


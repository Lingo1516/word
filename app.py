import streamlit as st
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup

# 使用 Playwright 抓取學術文獻的函數
def fetch_academic_papers(keyword):
    """
    使用 Playwright 前往華藝線上圖書館，根據關鍵字抓取文獻標題。
    """
    try:
        with sync_playwright() as p:
            # 使用 Chromium 瀏覽器
            browser = p.chromium.launch(headless=True)  # headless 模式不顯示瀏覽器視窗
            page = browser.new_page()

            # 華藝線上圖書館的搜尋頁面，根據關鍵字搜尋
            target_url = f'https://www.airitilibrary.com/advsearch?keyword={keyword}'
            page.goto(target_url, timeout=60000) # 增加頁面加載超時時間為 60 秒

            # 等待網頁的搜尋結果容器加載完成
            # 這比只等待 h3.title 更穩定，因為容器會先出現
            page.wait_for_selector('div.search_result_list', timeout=30000) # 等待 30 秒

            # 獲取頁面內容
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # 抓取文獻標題
            titles = soup.find_all('h3', class_='title')
            # 使用 .text.strip() 來清理標題前後多餘的空白
            titles_text = [title.text.strip() for title in titles]

            # 關閉瀏覽器
            browser.close()

            return titles_text
    except PlaywrightTimeoutError:
        # 如果等待元素時發生超時，返回錯誤訊息
        st.error("頁面加載超時，可能是網路問題或網站結構已更改。請稍後再試。")
        return []
    except Exception as e:
        # 捕捉其他可能的錯誤
        st.error(f"發生未預期的錯誤：{e}")
        return []

# Streamlit 應用主函數
def main():
    # 顯示標題
    st.title("華藝線上圖書館文獻爬取")
    st.write("輸入關鍵字，點擊按鈕後，程式會自動前往華藝線上圖書館抓取相關的文獻標題。")

    # 讓用戶輸入搜尋關鍵字
    keyword = st.text_input("輸入您想要搜尋的關鍵字（例如：策略管理）", "")

    # 抓取文獻資料的按鈕
    if st.button('抓取學術文獻'):
        if keyword:
            # 顯示載入中的提示
            with st.spinner(f'正在搜尋「{keyword}」的相關文獻，請稍候...'):
                # 呼叫爬蟲函數抓取文獻
                titles = fetch_academic_papers(keyword)
            
            # 顯示結果
            if titles:
                st.success(f"成功抓取到 {len(titles)} 筆文獻標題：")
                # 使用 st.expander 來顯示結果，避免佔用太多版面
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

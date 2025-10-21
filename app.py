import streamlit as st
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# 使用 Playwright 抓取學術文獻的函數
def fetch_academic_papers(keyword):
    with sync_playwright() as p:
        # 使用 Chromium 瀏覽器
        browser = p.chromium.launch(headless=True)  # headless 模式不顯示瀏覽器視窗
        page = browser.new_page()

        # 華藝線上圖書館的搜尋頁面，根據關鍵字搜尋
        target_url = f'https://www.airitilibrary.com/advsearch?keyword={keyword}'
        page.goto(target_url)

        # 等待網頁加載完成
        page.wait_for_selector('h3.title')  # 等待標題元素加載完成

        # 獲取頁面內容
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')

        # 抓取文獻標題
        titles = soup.find_all('h3', class_='title')
        titles_text = [title.get_text() for title in titles]

        # 關閉瀏覽器
        browser.close()

        return titles_text

# Streamlit 應用主函數
def main():
    # 顯示標題
    st.title("華藝線上圖書館文獻爬取")

    # 讓用戶輸入搜尋關鍵字
    keyword = st.text_input("輸入您想要搜尋的關鍵字（例如：策略管理）")

    # 抓取文獻資料的按鈕
    if st.button('抓取學術文獻'):
        if keyword:
            # 呼叫爬蟲函數抓取文獻
            titles = fetch_academic_papers(keyword)
            
            # 顯示結果
            if titles:
                st.write("爬取到的文獻標題：")
                for title in titles:
                    st.write(title)
            else:
                st.write("未能抓取到文獻，請檢查關鍵字或重新嘗試。")
        else:
            st.write("請輸入搜尋的關鍵字")

# 確保在直接運行此程式時，執行 main 函數
if __name__ == "__main__":
    main()

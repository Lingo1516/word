import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

# 設置 Selenium 使用無頭模式（不打開瀏覽器視窗）
def setup_driver():
    options = Options()
    options.add_argument("--headless")  # 不顯示瀏覽器
    options.add_argument("--disable-gpu")
    driver = webdriver.Chrome(options=options)
    return driver

# 根據關鍵字抓取文獻的函數
def fetch_academic_papers(keyword):
    driver = setup_driver()

    # 華藝線上圖書館的搜尋頁面，根據關鍵字搜尋
    target_url = f'https://www.airitilibrary.com/advsearch?keyword={keyword}'
    driver.get(target_url)

    # 等待頁面加載完成，並抓取頁面內容
    driver.implicitly_wait(10)  # 等待最大 10 秒

    # 獲取頁面 HTML 內容
    page_source = driver.page_source
    driver.quit()  # 關閉瀏覽器

    # 解析 HTML 內容
    soup = BeautifulSoup(page_source, 'html.parser')

    # 抓取文獻標題
    titles = soup.find_all('h3', class_='title')
    titles_text = [title.get_text() for title in titles]

    # 返回文獻標題
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

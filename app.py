import streamlit as st
import requests
from bs4 import BeautifulSoup

# 設定 Cookies（請將您的 Cookies 貼到這裡）
cookies = {
    'your_cookie_name': 'your_cookie_value',
    # 根據您的 Cookie 內容填寫其他項目
}

# 根據關鍵字抓取文獻的函數
def fetch_academic_papers(keyword):
    session = requests.Session()  # 創建一個會話

    # 設定 Cookies 來模擬登錄
    session.cookies.update(cookies)

    # 華藝線上圖書館的搜尋頁面，根據關鍵字搜尋
    target_url = f'https://www.airitilibrary.com/advsearch?keyword={keyword}'
    
    # 發送 GET 請求
    response = session.get(target_url)
    response.encoding = 'utf-8'
    
    # 解析 HTML 內容
    soup = BeautifulSoup(response.text, 'html.parser')

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

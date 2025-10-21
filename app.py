import streamlit as st
import requests
from bs4 import BeautifulSoup

# 根據關鍵字抓取文獻的函數
def fetch_academic_papers(keyword):
    session = requests.Session()  # 創建一個會話

    # 設置 User-Agent 標頭來模擬瀏覽器請求
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    # 華藝線上圖書館的搜尋頁面，根據關鍵字搜尋
    target_url = f'https://www.airitilibrary.com/advsearch?keyword={keyword}'
    
    # 發送 GET 請求，並添加 headers
    response = session.get(target_url, headers=headers)
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

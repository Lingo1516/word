import streamlit as st
import requests
from bs4 import BeautifulSoup

# 爬取華藝線上圖書館文獻標題的函數
def fetch_academic_papers():
    session = requests.Session()

    # 華藝線上圖書館的文獻搜尋頁面
    target_url = 'https://www.airitilibrary.com/advsearch'
    
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

    # 抓取文獻資料的按鈕
    if st.button('抓取學術文獻'):
        # 呼叫爬蟲函數抓取文獻
        titles = fetch_academic_papers()
        
        # 顯示結果
        if titles:
            st.write("爬取到的文獻標題：")
            for title in titles:
                st.write(title)
        else:
            st.write("未能抓取到文獻，請檢查網絡連接或重新嘗試。")

# 確保在直接運行此程式時，執行 main 函數
if __name__ == "__main__":
    main()

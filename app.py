import streamlit as st
import requests
from bs4 import BeautifulSoup

# 爬取華藝線上圖書館文獻標題的函數
def fetch_academic_papers(username, password):
    login_url = 'https://www.airitilibrary.com/'  # 華藝線上圖書館登入頁面
    session = requests.Session()
    
    # 登入資料
    login_data = {'username': username, 'password': password}
    login_response = session.post(login_url, data=login_data)

    # 檢查是否登入成功
    if login_response.status_code != 200:
        return f"登入失敗，請檢查帳號或密碼"

    # 爬取文獻資料頁面
    target_url = 'https://www.airitilibrary.com/advsearch'  # 文獻搜尋頁面
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

    # 用戶輸入帳號和密碼
    username = st.text_input("輸入華藝線上圖書館的帳號")
    password = st.text_input("輸入華藝線上圖書館的密碼", type="password")

    # 抓取文獻資料的按鈕
    if st.button('抓取學術文獻'):
        if username and password:
            # 呼叫爬蟲函數抓取文獻
            titles = fetch_academic_papers(username, password)
            
            # 顯示結果
            if isinstance(titles, list):
                st.write("爬取到的文獻標題：")
                for title in titles:
                    st.write(title)
            else:
                st.write(titles)  # 顯示錯誤訊息（例如登入失敗）
        else:
            st.write("請填寫帳號和密碼")

if __name__ == "__main__


import streamlit as st
import requests
from bs4 import BeautifulSoup
import random
import time

# 抓取 Google Scholar 搜尋結果的函式
def fetch_google_scholar(keyword):
    """抓取 Google Scholar 搜尋結果"""
    search_url = f"https://scholar.google.com/scholar?q={keyword}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        # 直接發送 GET 請求
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()  # 若請求失敗，會拋出異常
        soup = BeautifulSoup(response.text, "html.parser")

        results = []
        for item in soup.find_all("div", class_="gs_ri"):
            title = item.find("h3", class_="gs_rt").get_text()
            link = item.find("h3", class_="gs_rt").find("a")["href"] if item.find("h3", class_="gs_rt").find("a") else "#"
            author_pub = item.find("div", class_="gs_a").get_text()
            publication = item.find("div", class_="gs_a").get_text()
            
            results.append({
                "title": title,
                "link": link,
                "author": author_pub,
                "publication": publication
            })

            # 隨機延遲，模擬人類行為
            time.sleep(random.uniform(1, 2))

        return results, None
    except requests.exceptions.RequestException as e:
        return [], f"請求錯誤：{e}，請稍後再試。"

# Streamlit 主函式
def main():
    st.set_page_config(layout="wide", page_title="Google Scholar 搜尋工具")
    st.title("🔎 Google Scholar 搜尋工具")
    st.write("輸入關鍵字，即可抓取相關的學術文獻資料。")
    
    keyword = st.text_input("輸入關鍵字", "")

    if st.button('開始搜尋'):
        if keyword:
            with st.spinner(f'搜尋「{keyword}」中...'):
                papers, error = fetch_google_scholar(keyword)

            if papers:
                st.success(f"成功抓取到 {len(papers)} 筆文獻結果：")
                for i, paper in enumerate(papers, 1):
                    st.markdown(f"### {i}. [{paper['title']}]({paper['link']})")
                    st.caption(f"**作者與發表資訊:** {paper['author']}")
                    st.markdown(f"**發表於:** {paper['publication']}")
                    st.divider()

            else:
                st.warning("未能抓取到文獻，請嘗試更換關鍵字或稍後再試。")

            if error:
                st.error(error)
        else:
            st.warning("請先輸入關鍵字。")

if __name__ == "__main__":
    main()

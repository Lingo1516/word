import streamlit as st
import requests
from bs4 import BeautifulSoup
import random
import time

# --- 設定代理伺服器 ---
# 使用免費代理伺服器，增加搜尋成功機率
@st.cache_resource
def setup_proxy():
    try:
        proxies = {
            "http": "http://your_proxy_here",
            "https": "https://your_proxy_here",
        }
        # 測試代理伺服器是否有效
        response = requests.get("https://scholar.google.com", proxies=proxies, timeout=10)
        if response.status_code == 200:
            return proxies
        else:
            st.warning("代理伺服器無法連線，將嘗試直接連線。")
            return None
    except Exception as e:
        st.warning(f"代理伺服器設定失敗，錯誤：{e}")
        return None

# 使用代理進行搜尋的函式
def fetch_google_scholar(keyword, proxies=None):
    """抓取 Google Scholar 搜尋結果"""
    search_url = f"https://scholar.google.com/scholar?q={keyword}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    
    try:
        response = requests.get(search_url, headers=headers, proxies=proxies)
        response.raise_for_status()  # 如果請求失敗，會拋出異常
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

    # 設置代理
    with st.spinner("正在設定代理伺服器，請稍候..."):
        proxies = setup_proxy()

    if st.button('開始搜尋'):
        if keyword:
            with st.spinner(f'搜尋「{keyword}」中...'):
                papers, error = fetch_google_scholar(keyword, proxies)

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

import streamlit as st
from scholarly import scholarly, ProxyGenerator
import time
import random

# --- 動態搜尋方案：啟用代理伺服器 ---
# 我們將使用免費的代理伺服器來嘗試繞過 Google 的 IP 封鎖。
# 這會增加搜尋時間，且成功率無法保證。

@st.cache_resource
def setup_proxy():
    """設定並測試代理伺服器，此過程將被快取。"""
    try:
        pg = ProxyGenerator()
        # 我們需要一個能用的代理伺服器
        success = pg.FreeProxies()
        if not success:
            st.warning("無法找到可用的免費代理伺服器，將嘗試直接連線。")
            return None
        scholarly.use_proxy(pg)
        return pg
    except Exception as e:
        st.warning(f"設定代理時發生錯誤：{e}，將嘗試直接連線。")
        return None

# 應用程式啟動時，先設定代理
with st.spinner("正在尋找並設定代理伺服器，請稍候..."):
    setup_proxy()

# 抓取 Google 學術搜尋結果的函數
def fetch_google_scholar(keyword):
    """
    使用 scholarly 函式庫來搜尋 Google 學術。
    """
    results = []
    try:
        # search_pubs 會回傳一個產生器 (generator)
        search_query = scholarly.search_pubs(keyword)
        
        # 我們只取前10筆結果，避免請求時間過長
        for i, pub in enumerate(search_query):
            if i >= 10:
                break
                
            bib = pub.get('bib', {})
            title = bib.get('title', '標題未提供')
            author = bib.get('author', '作者未提供')
            if isinstance(author, list):
                author = ', '.join(author)
            
            publication = pub.get('bib', {}).get('venue', '出版資訊未提供')
            link = pub.get('pub_url', '#')

            results.append({
                "title": title,
                "link": link,
                "author": author,
                "publication": publication
            })
            # 增加隨機延遲，模擬真人行為
            time.sleep(random.uniform(0.5, 1.5))

        return results, None

    except Exception as e:
        error_message = f"搜尋時發生錯誤：{e}。這很可能是因為 Google 暫時封鎖了我們的請求 IP，請稍後再試。"
        return [], error_message

# Streamlit 應用主函數
def main():
    st.set_page_config(layout="wide", page_title="Google 學術搜尋工具")
    st.title("🔎 Google 學術搜尋工具 (動態版)")
    st.write("輸入關鍵字，即可即時抓取相關的學術文獻標題、作者與連結。")
    st.warning("⚠️ **請注意**：此動態版本在雲端平台上的成功率不穩定，若搜尋失敗，請稍後再試。")

    keyword = st.text_input("輸入您想要搜尋的關鍵字（例如：人工智慧）", "")

    if st.button('開始搜尋', type="primary"):
        if keyword:
            with st.spinner(f'正在透過代理伺服器即時搜尋「{keyword}」...'):
                papers, error = fetch_google_scholar(keyword)
            
            if papers:
                st.success(f"成功抓取到 {len(papers)} 筆文獻結果：")
                for i, paper in enumerate(papers, 1):
                    st.markdown(f"### {i}. [{paper['title']}]({paper['link']})")
                    st.caption(f"**作者:** {paper['author']}")
                    st.markdown(f"**發表於:** {paper['publication']}")
                    st.divider()
            else:
                st.warning("未能抓取到任何文獻，請嘗試更換關鍵字。")

            if error:
                st.error(error)
        else:
            st.warning("請先輸入要搜尋的關鍵字。")

if __name__ == "__main__":
    main()


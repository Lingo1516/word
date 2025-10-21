import streamlit as st
from scholarly import scholarly
import time

# --- 在這個版本中，我們移除了有問題的代理伺服器設定 ---
# --- 程式將使用更直接的方式進行網路請求 ---

# 抓取 Google 學術搜尋結果的函數
def fetch_google_scholar(keyword):
    """
    使用 scholarly 函式庫來搜尋 Google 學術。
    這個方法更穩定，更不容易被阻擋。
    """
    results = []
    try:
        # --- 修正：根據 scholarly 最新版本，設定語言的方式 ---
        scholarly.set_language('zh-TW')
        
        # search_pubs 會回傳一個產生器 (generator)
        search_query = scholarly.search_pubs(keyword)
        
        # 我們只取前10筆結果，避免請求時間過長
        for i, pub in enumerate(search_query):
            if i >= 10:
                break
                
            # 'bib' 字典中包含了我們需要的資訊
            bib = pub.get('bib', {})
            title = bib.get('title', '標題未提供')
            author = bib.get('author', '作者未提供')
            # 將作者列表轉換為字串
            if isinstance(author, list):
                author = ', '.join(author)
            
            publication = bib.get('venue', '出版資訊未提供')
            link = pub.get('pub_url', '#') # 取得文章的 Google Scholar 連結

            results.append({
                "title": title,
                "link": link,
                "author": author,
                "publication": publication
            })
            # 每次查詢後稍微休息一下，避免請求過於頻繁
            time.sleep(0.5)

        return results, None # 成功時回傳結果

    except Exception as e:
        # 處理 scholarly 可能遇到的各種網路或解析錯誤
        error_message = f"搜尋時發生錯誤：{e}。這可能是因為請求過於頻繁或 Google 暫時封鎖了 IP，請稍後再試。"
        return [], error_message

# Streamlit 應用主函數
def main():
    st.set_page_config(layout="wide", page_title="Google 學術搜尋工具")
    st.title("🔎 Google 學術搜尋工具 (最終修正版)")
    st.write("輸入關鍵字，即可抓取相關的學術文獻標題、作者與連結。採用 `scholarly` 函式庫，成功率更高。")

    keyword = st.text_input("輸入您想要搜尋的關鍵字（例如：人工智慧）", "")

    if st.button('開始搜尋', type="primary"):
        if keyword:
            with st.spinner(f'正在搜尋「{keyword}」...'):
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
                st.error(error) # 顯示錯誤訊息
        else:
            st.warning("請先輸入要搜尋的關鍵字。")

if __name__ == "__main__":
    main()


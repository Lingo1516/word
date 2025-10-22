import streamlit as st
import pandas as pd
import time
import urllib.parse

# --- 專業版架構：從外部 CSV 檔案載入大規模資料集，並提供分類與分頁功能 ---

# 使用快取功能來讀取資料，確保只在需要時讀取一次，提升效能
@st.cache_data
def load_data():
    """從 CSV 檔案載入文獻資料庫"""
    try:
        df = pd.read_csv("papers_db.csv")
        return df
    except FileNotFoundError:
        st.error("錯誤：找不到 'papers_db.csv' 資料庫檔案。請確認檔案已上傳至儲存庫。")
        return pd.DataFrame()

# 載入資料
df = load_data()

# 在 session state 中初始化分頁狀態
if 'page' not in st.session_state:
    st.session_state.page = 0

def main():
    st.set_page_config(layout="wide", page_title="商管學術資料庫")
    st.title("📚 商管學術文獻資料庫")

    total_papers = len(df)
    st.write(f"輸入關鍵字或篩選分類，即可從我們 **{total_papers}** 筆豐富的企管與商學資料庫中，搜尋相關的學術文獻。")
    st.info("ℹ️ **說明**：此版本從獨立的 `papers_db.csv` 檔案載入資料，並提供專業的分類篩選與分頁功能，確保了應用的穩定性與擴充性。")

    # --- 篩選介面 ---
    st.sidebar.header("🔍 篩選條件")
    
    # 分類篩選
    categories = ["所有分類"] + sorted(df['category'].unique().tolist())
    selected_category = st.sidebar.selectbox("文獻分類", categories)

    # 關鍵字搜尋
    keyword = st.sidebar.text_input("關鍵字搜尋（可篩選標題、作者等）")
    
    # --- 資料篩選邏輯 ---
    filtered_df = df.copy()
    if selected_category != "所有分類":
        filtered_df = filtered_df[filtered_df['category'] == selected_category]
    
    if keyword:
        keyword_lower = keyword.lower()
        filtered_df = filtered_df[filtered_df.apply(lambda row: keyword_lower in str(row).lower(), axis=1)]

    total_results = len(filtered_df)
    st.header(f"📊 搜尋結果 ({total_results} 筆)")

    # --- 分頁系統 ---
    items_per_page = 10
    total_pages = (total_results + items_per_page - 1) // items_per_page
    
    if total_pages > 0:
        # 確保當前頁碼在有效範圍內
        if st.session_state.page >= total_pages:
            st.session_state.page = total_pages - 1
        
        start_idx = st.session_state.page * items_per_page
        end_idx = start_idx + items_per_page
        
        # 顯示分頁導航
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("⬅️ 上一頁", disabled=(st.session_state.page == 0)):
                st.session_state.page -= 1
                st.rerun() # 重新整理頁面
        with col3:
            if st.button("下一頁 ➡️", disabled=(st.session_state.page >= total_pages - 1)):
                st.session_state.page += 1
                st.rerun() # 重新整理頁面
        with col2:
            st.markdown(f"<div style='text-align: center;'>頁碼: {st.session_state.page + 1} / {total_pages}</div>", unsafe_allow_html=True)

        # 顯示當前頁的結果
        for index, paper in filtered_df.iloc[start_idx:end_idx].iterrows():
            with st.container(border=True):
                st.markdown(f"##### [{paper['title']}]({paper['link']})")
                st.caption(f"**分類:** {paper.get('category', 'N/A')} | **作者:** {paper.get('author', 'N/A')} | **發表於:** {paper.get('publication', 'N/A')}")
    else:
        st.warning("找不到符合條件的文獻。")

    # 提供外部搜尋連結
    if keyword:
        st.sidebar.markdown("---")
        encoded_keyword = urllib.parse.quote(keyword.encode('big5'))
        ndltd_url = f"https://ndltd.ncl.edu.tw/cgi-bin/gs32/gsweb.cgi?o=dnclcdr&s={encoded_keyword}"
        st.sidebar.markdown(f"想看更多即時結果嗎？\n\n[在 NDLTD 網站上查找「{keyword}」]({ndltd_url})")

if __name__ == "__main__":
    main()


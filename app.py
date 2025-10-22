import streamlit as st
import pandas as pd
import time
import urllib.parse

# --- 專業版架構：從外部 CSV 檔案載入大規模資料集，並提供專業的管理與匯出功能 ---

# 使用快取功能來讀取資料，確保只在需要時讀取一次，提升效能
@st.cache_data
def load_data():
    """從 CSV 檔案載入文獻資料庫"""
    try:
        df = pd.read_csv("papers_db.csv")
        # 確保年份是整數，方便排序
        df['year'] = pd.to_numeric(df['year'], errors='coerce').fillna(0).astype(int)
        return df
    except FileNotFoundError:
        st.error("錯誤：找不到 'papers_db.csv' 資料庫檔案。請確認檔案已上傳至儲存庫。")
        return pd.DataFrame()

# 載入資料
df = load_data()

def main():
    st.set_page_config(layout="wide", page_title="商管學術文獻管理平台")
    st.title("📚 商管學術文獻管理平台")

    total_papers = len(df)
    st.write(f"篩選並管理我們 **{total_papers}** 筆豐富的企管與商學資料庫。")
    st.info("ℹ️ **說明**：此版本從獨立的 `papers_db.csv` 檔案載入資料，並提供專業的分類篩選、APA 引用與 CSV 匯出功能。")

    # --- 篩選介面 ---
    st.sidebar.header("🔍 篩選與搜尋")
    
    # 分類篩選
    categories = ["所有分類"] + sorted(df['category'].unique().tolist())
    selected_category = st.sidebar.selectbox("文獻分類", categories)

    # 關鍵字搜尋
    keyword = st.sidebar.text_input("關鍵字搜尋（可篩選標題、摘要等）")
    
    # --- 資料篩選邏輯 ---
    filtered_df = df.copy()
    if selected_category != "所有分類":
        filtered_df = filtered_df[filtered_df['category'] == selected_category]
    
    if keyword:
        keyword_lower = keyword.lower()
        filtered_df = filtered_df[filtered_df.apply(lambda row: keyword_lower in str(row).lower(), axis=1)]

    total_results = len(filtered_df)
    st.header(f"📊 搜尋結果 ({total_results} 筆)")

    if not filtered_df.empty:
        # --- 專業表格視圖 ---
        st.dataframe(filtered_df, use_container_width=True)
        
        st.subheader("📄 文獻詳細資料與引用")
        
        # --- 匯出功能 ---
        csv_data = filtered_df.to_csv(index=False).encode('utf-8-sig')
        st.sidebar.download_button(
            label="📥 下載篩選結果 (CSV)",
            data=csv_data,
            file_name=f"filtered_papers_{time.strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )
        
        # --- APA 格式產生器與詳細資料 ---
        for index, paper in filtered_df.iterrows():
            apa_citation = (
                f"{paper.get('author', 'N/A')} ({paper.get('year', 'N/A')}). "
                f"*{paper.get('title', 'N/A')}* "
                f"[{paper.get('publication', 'N/A')}]({paper.get('link', '#')})."
            )
            with st.expander(f"**{paper.get('title', 'N/A')}**"):
                st.markdown(f"**作者:** {paper.get('author', 'N/A')}")
                st.markdown(f"**年份:** {paper.get('year', 'N/A')}")
                st.markdown(f"**分類:** {paper.get('category', 'N/A')}")
                
                st.markdown("**摘要:**")
                st.info(paper.get('abstract', '無摘要資訊'))
                
                st.markdown("**關鍵字:**")
                st.success(paper.get('keywords', '無關鍵字'))
                
                st.markdown("**APA 7 引用格式:**")
                st.code(apa_citation, language='text')

    else:
        st.warning("找不到符合條件的文獻。")

    # 外部搜尋連結
    st.sidebar.markdown("---")
    encoded_keyword = urllib.parse.quote(keyword.encode('big5')) if keyword else ""
    ndltd_url = f"https://ndltd.ncl.edu.tw/cgi-bin/gs32/gsweb.cgi?o=dnclcdr&s={encoded_keyword}"
    st.sidebar.markdown(f"想看更多即時結果嗎？\n\n[在 NDLTD 網站上查找「{keyword}」]({ndltd_url})")


if __name__ == "__main__":
    main()


import streamlit as st
import pandas as pd
import time

# --- 終極架構：一個專業的資料庫檢視、篩選與匯出平台 ---
# 這個平台專門用來管理由您的 AI 研究助理為您客製化搜集的文獻資料。

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
        st.error("⚠️ 錯誤：找不到 'papers_db.csv' 資料庫檔案。")
        st.info("請確認您已經將由 AI 助理提供的 `papers_db.csv` 檔案上傳至您的 GitHub 儲存庫。")
        return pd.DataFrame()

# 載入資料
df = load_data()

def main():
    st.set_page_config(layout="wide", page_title="學術文獻資料庫管理平台")
    st.title("📚 學術文獻資料庫管理平台")

    total_papers = len(df)
    st.write(f"目前您的專屬資料庫中共有 **{total_papers}** 筆文獻。")

    # --- 全新的協作模式說明 ---
    with st.container(border=True):
        st.subheader("💡 這是一個全新的工作模式")
        st.markdown("""
        這個平台是您個人的學術資料庫。它 100% 穩定，並且可以無限擴充。
        
        **如何擴充您的資料庫？**
        1.  **下達指令**：直接在左邊的聊天室告訴您的 AI 助理您需要的研究主題（例如：「請幫我搜集50筆關於『供應鏈金融』的論文」）。
        2.  **接收資料**：您的助理會為您產生一份全新的 `papers_db.csv` 檔案。
        3.  **更新資料庫**：將新的檔案內容更新到您 GitHub 上的 `papers_db.csv`，您的平台就會自動更新！
        """)

    # --- 篩選與管理介面 ---
    st.sidebar.header("🔍 篩選與匯出")
    
    # 分類篩選
    if not df.empty and 'category' in df.columns:
        categories = ["所有分類"] + sorted(df['category'].unique().tolist())
        selected_category = st.sidebar.selectbox("文獻分類", categories)
    else:
        selected_category = "所有分類"

    # 關鍵字搜尋
    keyword = st.sidebar.text_input("關鍵字篩選（可搜尋標題、摘要等）")
    
    # --- 資料篩選邏輯 ---
    filtered_df = df.copy()
    if selected_category != "所有分類":
        filtered_df = filtered_df[filtered_df['category'] == selected_category]
    
    if keyword:
        keyword_lower = keyword.lower()
        filtered_df = filtered_df[filtered_df.apply(lambda row: keyword_lower in str(row).lower(), axis=1)]

    total_results = len(filtered_df)
    st.header(f"📊 篩選結果 ({total_results} 筆)")

    if not filtered_df.empty:
        # --- 專業表格視圖 ---
        st.dataframe(filtered_df, use_container_width=True, height=300)
        
        # --- 匯出功能 ---
        csv_data = filtered_df.to_csv(index=False).encode('utf-8-sig')
        st.sidebar.download_button(
            label="📥 下載篩選結果 (CSV)",
            data=csv_data,
            file_name=f"My_Research_{time.strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
            type="primary"
        )
        
        st.subheader("📄 文獻詳細資料與引用")
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
        st.warning("找不到符合條件的文獻。請調整您的篩選條件。")

if __name__ == "__main__":
    main()


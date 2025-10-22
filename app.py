import streamlit as st
import pandas as pd
import time

# --- 極簡、高效的個人化文獻資料庫 ---
# 專注於核心功能：檢視、篩選、匯出。

# 使用快取功能來讀取資料，確保只在需要時讀取一次
@st.cache_data
def load_data():
    """從 CSV 檔案載入文獻資料庫"""
    try:
        # 讀取簡化後的 CSV 檔案
        df = pd.read_csv("papers_db.csv")
        # 確保年份是整數
        df['year'] = pd.to_numeric(df['year'], errors='coerce').fillna(0).astype(int)
        return df
    except FileNotFoundError:
        st.error("⚠️ 錯誤：找不到 'papers_db.csv' 資料庫檔案。")
        st.info("請確認您已經將由 AI 助理提供的 `papers_db.csv` 檔案上傳至您的 GitHub 儲存庫。")
        return pd.DataFrame()

# 載入資料
df = load_data()

def main():
    st.set_page_config(layout="wide", page_title="個人化文獻資料庫")
    st.title("📚 個人化文獻資料庫")

    total_papers = len(df)
    st.write(f"目前您的資料庫中共有 **{total_papers}** 筆文獻。")

    # --- 協作模式說明 ---
    with st.container(border=True):
        st.subheader("💡 AI 助理協作模式")
        st.markdown("""
        這個平台是您個人的學術資料庫，100% 穩定且可無限擴充。
        
        **如何擴充您的資料庫？**
        1.  **向您的 AI 助理下達指令**：直接在左邊的聊天室告訴助理您需要的研究主題（例如：「請幫我搜集50筆關於『供應鏈金融』的論文」）。
        2.  **接收「新的資料庫檔案」**：您的助理會為您產生一份全新的、符合您需求的 `papers_db.csv` 檔案。
        3.  **更新您的 GitHub**：將這份 **新的資料庫檔案** 更新到您 GitHub 上的 `papers_db.csv`，您的平台就會自動載入最新的資料！
        """)

    # --- 篩選與管理介面 ---
    st.sidebar.header("🔍 篩選與匯出")
    
    # 關鍵字搜尋
    keyword = st.sidebar.text_input("關鍵字篩選（可搜尋標題、關鍵字等）")
    
    # --- 資料篩選邏輯 ---
    filtered_df = df.copy()
    if keyword:
        keyword_lower = keyword.lower()
        # 在所有欄位中進行搜尋
        filtered_df = filtered_df[filtered_df.apply(lambda row: keyword_lower in str(row).lower(), axis=1)]

    total_results = len(filtered_df)
    st.header(f"📊 篩選結果 ({total_results} 筆)")

    if not filtered_df.empty:
        # --- 專業表格視圖 ---
        st.dataframe(filtered_df, use_container_width=True, height=500)
        
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
    else:
        st.warning("找不到符合條件的文獻。請調整您的篩選條件。")

if __name__ == "__main__":
    main()


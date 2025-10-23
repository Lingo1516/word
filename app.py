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
    # 新增：處理可能的 CSV 格式錯誤
    except pd.errors.ParserError:
        st.error("⚠️ 錯誤：'papers_db.csv' 檔案格式有誤，無法解析。")
        st.info("請檢查您上傳的 CSV 檔案格式是否正確，或向您的 AI 助理索取一份格式正確的檔案。")
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
        st.subheader("💡 AI 助理協作模式")
        st.markdown("""
        這個平台是您個人的學術資料庫，100% 穩定且可無限擴充。側邊欄的「下載」按鈕是讓您匯出 **目前篩選的結果**，方便您做報告。

        **如何擴充您的「資料庫本身」？**
        1.  **向您的 AI 助理下達指令**：直接在左邊的聊天室告訴助理您需要的研究主題（例如：「請幫我搜集50筆關於『供應鏈金融』的論文」）。
        2.  **接收「新的資料庫檔案」**：您的助理會為您產生一份全新的、內容更豐富的 `papers_db.csv` 檔案。
        3.  **更新您的 GitHub**：將這份 **新的資料庫檔案** 更新到您 GitHub 上的 `papers_db.csv`，您的平台就會自動載入最新的資料！
        """)

    # --- 篩選與管理介面 ---
    st.sidebar.header("🔍 篩選與匯出")

    # 分類篩選
    if not df.empty and 'category' in df.columns:
        # 處理可能的 NaN 值
        categories = ["所有分類"] + sorted(df['category'].dropna().unique().tolist())
        selected_category = st.sidebar.selectbox("文獻分類", categories)
    else:
        selected_category = "所有分類"
        # 只有在 df 不是空的但缺少欄位時才警告
        if not df.empty:
             st.sidebar.warning("CSV 缺少 'category' 欄位。")


    # 關鍵字搜尋
    keyword = st.sidebar.text_input("關鍵字篩選（可搜尋標題、摘要等）")

    # 年份範圍篩選 (如果資料庫中有年份欄位)
    if not df.empty and 'year' in df.columns:
        # 檢查年份是否都是數字，避免轉換錯誤
        if pd.api.types.is_numeric_dtype(df['year']):
            min_year, max_year = int(df['year'].min()), int(df['year'].max())
            # 確保 min_year <= max_year
            if min_year <= max_year:
                selected_years = st.sidebar.slider(
                    "年份範圍",
                    min_value=min_year,
                    max_value=max_year,
                    value=(min_year, max_year) # 預設選取所有年份
                )
                year_start, year_end = selected_years
            else: # 如果年份資料異常
                 year_start, year_end = None, None
                 st.sidebar.warning("年份資料異常，無法篩選。")
        else:
             year_start, year_end = None, None
             st.sidebar.warning("年份欄位包含非數字，無法篩選。")

    else:
        year_start, year_end = None, None
        if not df.empty:
            st.sidebar.warning("CSV 缺少 'year' 欄位。")


    # 每頁顯示筆數選項
    items_per_page = st.sidebar.selectbox(
        "每頁顯示筆數",
        options=[10, 25, 50, 100],
        index=1  # 預設為每頁 25 筆
    )

    # --- 資料篩選邏輯 ---
    filtered_df = df.copy()
    if selected_category != "所有分類" and 'category' in filtered_df.columns:
        # 確保篩選前欄位存在
        filtered_df = filtered_df[filtered_df['category'] == selected_category]

    if year_start is not None and year_end is not None and 'year' in filtered_df.columns:
        # 確保篩選前欄位存在且年份有效
         if pd.api.types.is_numeric_dtype(filtered_df['year']):
            filtered_df = filtered_df[(filtered_df['year'] >= year_start) & (filtered_df['year'] <= year_end)]

    if keyword:
        keyword_lower = keyword.lower()
        # 在所有欄位中進行搜尋 (更穩健的作法)
        try:
            # 將所有欄位轉為字串再搜尋，避免非字串欄位錯誤
            filtered_df = filtered_df[filtered_df.astype(str).apply(lambda row: keyword_lower in row.to_string().lower(), axis=1)]
        except Exception as e: # 捕捉可能的錯誤
             st.error(f"關鍵字篩選時發生錯誤: {e}")
             filtered_df = pd.DataFrame() # 清空結果避免後續錯誤

    total_results = len(filtered_df)
    st.header(f"📊 篩選結果 ({total_results} 筆)")

    if not filtered_df.empty:
        # --- 分頁邏輯 ---
        if 'page' not in st.session_state:
            st.session_state.page = 1

        total_pages = max(1, (total_results + items_per_page - 1) // items_per_page) # 確保至少有一頁

        if st.session_state.page > total_pages: st.session_state.page = 1 # 重設頁碼
        start_index = (st.session_state.page - 1) * items_per_page
        end_index = start_index + items_per_page
        paginated_df = filtered_df.iloc[start_index:end_index]

        # --- 專業表格視圖 ---
        available_columns = [col for col in ["title", "author", "year", "publication", "category", "keywords"] if col in paginated_df.columns]
        st.dataframe(paginated_df[available_columns], use_container_width=True, height=400)

        # --- 匯出功能 ---
        csv_data = filtered_df.to_csv(index=False).encode('utf-8-sig')
        st.sidebar.download_button(
            label="📥 下載篩選結果 (CSV)", data=csv_data,
            file_name=f"My_Research_{time.strftime('%Y%m%d')}.csv", mime="text/csv",
            use_container_width=True, type="primary"
        )

        st.subheader("📄 文獻詳細資料與引用")
        # --- APA 格式產生器與詳細資料 ---
        for index, paper in paginated_df.iterrows():
            apa_citation = (
                f"{paper.get('author', 'N/A')} ({paper.get('year', 'N/A')}). "
                f"*{paper.get('title', 'N/A')}* "
                f"[{paper.get('publication', 'N/A')}]({paper.get('link', '#')})." # 假設 CSV 中仍有 link 欄位
            )
            with st.expander(f"**{paper.get('title', '標題未提供')}** ({paper.get('year', '年份未提供')})"):
                st.markdown(f"**作者:** {paper.get('author', 'N/A')}")
                st.markdown(f"**年份:** {paper.get('year', 'N/A')}")
                if 'category' in paper: st.markdown(f"**分類:** {paper.get('category', 'N/A')}")
                if 'publication' in paper: st.markdown(f"**來源:** {paper.get('publication', 'N/A')}")

                # 只有在欄位存在且值不是 NaN 時才顯示
                if 'abstract' in paper and pd.notna(paper['abstract']):
                    st.markdown("**摘要:**"); st.info(paper['abstract'])
                if 'keywords' in paper and pd.notna(paper['keywords']):
                    st.markdown("**關鍵字:**"); st.success(paper['keywords'])

                st.markdown("**APA 7 引用格式 (參考):**"); st.code(apa_citation, language='text')

        # --- 頁面導覽按鈕 ---
        st.divider()
        col1, col2, col3 = st.columns([2, 3, 2])
        with col1:
            if st.session_state.page > 1:
                if st.button("⬅️ 上一頁", use_container_width=True): st.session_state.page -= 1; st.rerun()
        with col2:
            st.markdown(f"<p style='text-align: center;'><b>第 {st.session_state.page} 頁 / 共 {total_pages} 頁</b></p>", unsafe_allow_html=True)
        with col3:
            if st.session_state.page < total_pages:
                if st.button("下一頁 ➡️", use_container_width=True): st.session_state.page += 1; st.rerun()

    elif df.empty:
         st.warning("請先透過左側聊天室向 AI 助理索取 `papers_db.csv` 資料庫檔案，並將其上傳至 GitHub。")
    else:
        st.warning("找不到符合條件的文獻。請調整您的篩選條件，或向 AI 助理索取更多相關資料。")

if __name__ == "__main__":
    main()


import streamlit as st
import pandas as pd
import time

# -------------------------------------------
# 📦 高效快取：避免重複讀取 CSV 加速啟動
# -------------------------------------------
@st.cache_data
def load_data(file_path="papers_db.csv"):
    """從 CSV 載入學術文獻資料，並確保欄位型別一致"""
    try:
        df = pd.read_csv(file_path)
        if 'year' in df:
            df['year'] = pd.to_numeric(df['year'], errors='coerce').fillna(0).astype(int)
        return df
    except FileNotFoundError:
        st.error("⚠️ 找不到 papers_db.csv，請確認檔案已正確上傳。")
        return pd.DataFrame()
    except pd.errors.ParserError:
        st.error("⚠️ CSV 格式錯誤，請檢查檔案內容。")
        return pd.DataFrame()


# -------------------------------------------
# 📋 主平台函式（整合篩選 + 匯出 + 分頁）
# -------------------------------------------
def main():
    st.set_page_config(page_title="學術文獻資料庫平台", layout="wide")
    st.title("📚 AI 助理・學術文獻資料庫管理系統")

    df = load_data()
    total_records = len(df)
    st.caption(f"目前資料庫共 {total_records} 筆文獻")

    # ------------------------------
    # 🔧 側邊選單
    # ------------------------------
    st.sidebar.header("🔍 篩選條件")

    # 分類
    category = "所有分類"
    if not df.empty and 'category' in df.columns:
        categories = ["所有分類"] + sorted(df['category'].dropna().unique())
        category = st.sidebar.selectbox("選擇文獻分類", categories)

    # 關鍵字
    keyword = st.sidebar.text_input("輸入關鍵字（搜尋標題、摘要）")

    # 年份範圍
    if not df.empty and 'year' in df.columns:
        min_y, max_y = int(df['year'].min()), int(df['year'].max())
        year_range = st.sidebar.slider("年份範圍", min_y, max_y, (min_y, max_y))
    else:
        year_range = None

    # 每頁顯示數量
    per_page = st.sidebar.selectbox("顯示筆數", [10, 25, 50, 100], index=1)

    # ------------------------------
    # 🔍 篩選邏輯
    # ------------------------------
    filtered = df.copy()
    if category != "所有分類" and 'category' in filtered.columns:
        filtered = filtered[filtered['category'] == category]

    if year_range and 'year' in filtered.columns:
        filtered = filtered[(filtered['year'] >= year_range[0]) & (filtered['year'] <= year_range[1])]

    if keyword.strip():
        filtered = filtered[filtered.apply(
            lambda r: keyword.lower() in str(r.to_dict()).lower(), axis=1
        )]

    total_filtered = len(filtered)
    st.subheader(f"📊 篩選結果：{total_filtered} 筆")

    # ------------------------------
    # 📄 分頁邏輯
    # ------------------------------
    if total_filtered > 0:
        total_pages = (total_filtered - 1) // per_page + 1
        page = st.session_state.get("page", 1)

        if page > total_pages:  # 若上一輪頁碼超出範圍
            page = 1
            st.session_state["page"] = 1

        start = (page - 1) * per_page
        end = start + per_page
        page_df = filtered.iloc[start:end]

        # --------------------------
        # 📋 表格顯示
        # --------------------------
        cols = [c for c in ["title", "author", "year", "publication", "category", "keywords"] if c in page_df.columns]
        st.dataframe(page_df[cols], height=400, use_container_width=True)

        # --------------------------
        # 💾 匯出 CSV
        # --------------------------
        csv_data = filtered.to_csv(index=False).encode("utf-8-sig")
        st.sidebar.download_button(
            "📥 下載結果 CSV",
            csv_data,
            file_name=f"Filtered_Papers_{time.strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

        # --------------------------
        # 🧾 詳細資訊 + 引用格式
        # --------------------------
        st.divider()
        st.subheader("📄 文獻詳情與 APA 引用格式")
        for _, paper in page_df.iterrows():
            with st.expander(f"{paper.get('title', '未命名')} ({paper.get('year', 'N/A')})"):
                st.write(f"作者：{paper.get('author', '未知')}")
                if 'publication' in paper:
                    st.write(f"來源：{paper['publication']}")
                if 'abstract' in paper and pd.notna(paper['abstract']):
                    st.info(paper['abstract'])
                if 'keywords' in paper and pd.notna(paper['keywords']):
                    st.success(f"關鍵字：{paper['keywords']}")
                apa = f"{paper.get('author','N/A')} ({paper.get('year','N/A')}). *{paper.get('title','N/A')}*. [{paper.get('publication','N/A')}]({paper.get('link','#')})."
                st.code(apa)

        # --------------------------
        # ⬅️ 分頁控制
        # --------------------------
        st.divider()
        c1, c2, c3 = st.columns([2, 3, 2])
        with c1:
            if page > 1 and st.button("⬅️ 上一頁", use_container_width=True):
                st.session_state.page = page - 1
                st.rerun()
        with c2:
            st.markdown(f"<p style='text-align:center'>第 {page} 頁 / 共 {total_pages} 頁</p>", unsafe_allow_html=True)
        with c3:
            if page < total_pages and st.button("下一頁 ➡️", use_container_width=True):
                st.session_state.page = page + 1
                st.rerun()
    else:
        st.warning("沒有找到符合條件的文獻，請調整篩選條件或更新資料庫。")


# -------------------------------------------
# 🚀 啟動 Streamlit 主程式
# -------------------------------------------
if __name__ == "__main__":
    main()

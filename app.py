import streamlit as st
import pandas as pd

st.set_page_config(page_title="AI論文即時檢視平台", layout="wide")
st.title("📄 AI 助理・論文資料即時檢視")

uploaded_file = st.file_uploader("請上傳論文資料檔案（CSV格式）", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.success(f"成功載入 {len(df)} 筆文獻資料")
    
    # 篩選分類
    if "category" in df.columns:
        categories = ["所有分類"] + sorted(df["category"].dropna().unique())
        selected_category = st.selectbox("分類篩選", categories)
        if selected_category != "所有分類":
            df = df[df["category"] == selected_category]
    
    # 篩選年份
    if "year" in df.columns:
        min_year, max_year = df["year"].min(), df["year"].max()
        year_range = st.slider("年份範圍", int(min_year), int(max_year), (int(min_year), int(max_year)))
        df = df[(df["year"] >= year_range[0]) & (df["year"] <= year_range[1])]
    
    # 關鍵字搜尋
    keyword = st.text_input("關鍵字搜尋（可搜標題、摘要）")
    if keyword.strip():
        df = df[df.apply(lambda row: keyword.lower() in str(row.to_dict()).lower(), axis=1)]
    
    st.write(f"搜尋結果共 {len(df)} 筆")
    
    cols = [col for col in ["title", "author", "year", "publication", "category", "keywords"] if col in df.columns]
    st.dataframe(df[cols], height=400, use_container_width=True)
    
    # 匯出搜尋結果
    csv_data = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "📥 下載篩選結果 CSV",
        csv_data,
        file_name="search_result.csv",
        mime="text/csv"
    )
    
    # 詳細資訊（APA格式、摘要、關鍵字等）
    st.subheader("📑 詳細資料與APA引用格式")
    for _, paper in df.iterrows():
        with st.expander(f"{paper.get('title', '未命名')} ({paper.get('year', 'N/A')})"):
            st.write(f"作者：{paper.get('author', '未知')}")
            if "publication" in paper: st.write(f"來源：{paper['publication']}")
            if "abstract" in paper and pd.notna(paper["abstract"]): st.info(paper["abstract"])
            if "keywords" in paper and pd.notna(paper["keywords"]): st.success(f"關鍵字：{paper['keywords']}")
            apa = f"{paper.get('author', 'N/A')} ({paper.get('year', 'N/A')}). *{paper.get('title', 'N/A')}*. [{paper.get('publication', 'N/A')}]({paper.get('link', '#')})."
            st.code(apa)
else:
    st.info("請上傳論文資料 CSV 檔案，不需本地資料庫，隨用即分析。")


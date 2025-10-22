import streamlit as st
import re
from bs4 import BeautifulSoup
import pandas as pd

# ----------------------------------------------------------------------
# 區塊 1：Streamlit 介面主體
# ----------------------------------------------------------------------

def main():
    st.set_page_config(layout="wide", page_title="文獻資料擷取")
    
    st.title("📚 文獻資料擷取工具 (人機協作版)")
    st.markdown("""
    由於目標網站 (如 NTNU) 設有嚴格的 `403` 反爬蟲機制，全自動爬蟲已被封鎖。
    本工具採用**人機協作**模式，請依照以下步驟操作：
    """)

    with st.container(border=True):
        
        st.subheader("步驟 1：取得目標網頁")
        doi_input = st.text_input(
            "請在這裡貼上單一的 DOI (例如 10.6345/NTNU202200459)："
        )
        
        if doi_input:
            # 產生標準的 DOI 連結
            doi_url = f"https://doi.org/{doi_input.split('doi.org/')[-1]}"
            st.link_button("🔗 點此在新分頁中打開 DOI 網頁", doi_url, use_container_width=True, type="secondary")
        
        # 顯示一個文字區域，讓使用者貼上 HTML
        st.subheader("步驟 2：將網頁原始碼貼到下方")
        html_input = st.text_area(
            "請在上方的新分頁中，手動複製網頁原始碼 (通常是按右鍵 -> 檢視網頁原始碼)，然後全部貼到這裡。",
            height=300
        )
        
        if st.button("🚀 從 HTML 原始碼中擷取資料", use_container_width=True, type="primary"):
            if not html_input:
                st.warning("請貼上 HTML 原始碼。")
            else:
                st.header("📊 擷取結果表格")
                
                # --- 使用 BeautifulSoup 解析使用者貼上的 HTML ---
                try:
                    soup = BeautifulSoup(html_input, 'html.parser')
                    
                    # --- 1. 嘗試擷取標題 ---
                    title_tag = soup.find("meta", attrs={"name": "DC.Title"})
                    if not title_tag: title_tag = soup.find("meta", property="og:title")
                    title = title_tag.get('content', '標題抓取失敗').strip() if title_tag else (soup.title.string.strip() if soup.title else '標題抓取失敗')
                    
                    # --- 2. 嘗試擷取摘要 ---
                    abstract_tag = soup.find("meta", attrs={"name": "DC.Description"})
                    if not abstract_tag: abstract_tag = soup.find("meta", property="og:description")
                    abstract = abstract_tag.get('content', '[摘要抓取失敗]').strip() if abstract_tag else '[無法在HTML中定位到摘要]'
                    
                    # --- 3. 嘗試擷取作者 ---
                    author_tags = soup.find_all("meta", attrs={"name": "DC.Creator"})
                    if not author_tags: author_tags = soup.find_all("meta", attrs={"name": "citation_author"})
                    if author_tags:
                        authors = ', '.join([tag.get('content', '').strip() for tag in author_tags])
                    else:
                        authors = '[作者抓取失敗]'

                    # --- 4. 嘗試擷取年份 ---
                    year_tag = soup.find("meta", attrs={"name": "DC.Date"})
                    if not year_tag: year_tag = soup.find("meta", attrs={"name": "citation_publication_date"})
                    if year_tag:
                        date_str = year_tag.get('content', '').strip()
                        match = re.search(r'\b(19[5-9]\d|20[0-4]\d|2050)\b', date_str) 
                        year = match.group(0) if match else date_str
                    else:
                        year = '[年份抓取失敗]'

                    # --- 顯示表格 ---
                    result_data = {
                        "Authors": [authors],
                        "Year": [year],
                        "Title": [title],
                        "Abstract": [abstract],
                        "DOI": [doi_input if doi_input else "N/A"]
                    }
                    df = pd.DataFrame(result_data)
                    st.dataframe(df, use_container_width=True)

                    # --- 提供下載按鈕 ---
                    @st.cache_data
                    def convert_df_to_csv(df_to_convert):
                        return df_to_convert.to_csv(index=False).encode('utf-8-sig')

                    csv_data = convert_df_to_csv(df)

                    st.download_button(
                        label="📥 下載這筆資料 (CSV)",
                        data=csv_data,
                        file_name="paper_data.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                except Exception as e:
                    st.error(f"HTML 解析錯誤：{e}")

if __name__ == "__main__":
    main()

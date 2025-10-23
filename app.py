import streamlit as st
import requests
import pandas as pd
import time
import urllib.parse
from datetime import datetime # 匯入 datetime 模組取得當前年份

# 頁面設定
st.set_page_config(
    page_title="國際期刊文獻搜尋器 (Crossref API)",
    page_icon="🌍",
    layout="wide"
)

st.title("🌍 國際期刊文獻搜尋器 (Crossref API)")
st.markdown("您可以選擇預設關鍵字、年份範圍或自行輸入，程式會將所有條件組合進行搜尋。")

# --- 預設商管關鍵字 ---
BUSINESS_KEYWORDS = [
    "Management", "Marketing", "Finance", "Accounting", "Human Resources",
    "Strategy", "Supply Chain", "Logistics", "Operations Management", "Business Ethics",
    "Corporate Social Responsibility", "Entrepreneurship", "Innovation", "International Business", "Organizational Behavior"
]

# --- 使用者輸入介面 ---
st.subheader("請設定您的搜尋條件")

# 關鍵字輸入區塊
col_keyword1, col_keyword2 = st.columns([2, 1])
with col_keyword1:
    selected_keywords = st.multiselect(
        "📚 選擇預設關鍵字 (可複選)",
        options=BUSINESS_KEYWORDS,
        default=[]
    )
with col_keyword2:
    custom_keyword = st.text_input(
        "⌨️ 或輸入自訂關鍵字 (英文)",
        placeholder="例如：digital transformation"
    )

# 年份篩選區塊
current_year = datetime.now().year
col_year1, col_year2, col_slider = st.columns([1, 1, 2])
with col_year1:
    year_start = st.number_input("⏳ 起始年份", min_value=1900, max_value=current_year, value=current_year - 5) # 預設最近五年
with col_year2:
    year_end = st.number_input("⌛ 結束年份", min_value=1900, max_value=current_year, value=current_year)
with col_slider:
    max_results = st.slider("📈 最多顯示幾筆結果", min_value=5, max_value=100, value=20, step=5)


# --- Crossref API 搜尋函數 ---
@st.cache_data(ttl=3600) # 快取搜尋結果一小時
def search_crossref(query_list, start_year, end_year, rows=20):
    """
    使用 Crossref API 搜尋學術文獻，加入年份篩選和摘要請求。
    """
    base_url = "https://api.crossref.org/works"
    
    combined_query = " ".join(query_list)
    encoded_query = urllib.parse.quote(combined_query)
    
    mailto = "streamlit.app.user@example.com"
    params = {
        'query.bibliographic': encoded_query,
        'rows': rows,
        'mailto': mailto,
        # 嘗試請求摘要 (abstract)，並加入年份篩選
        'select': 'DOI,title,author,issued,container-title,publisher,type,abstract',
        'filter': f'from-pub-date:{start_year}-01-01,until-pub-date:{end_year}-12-31' # 使用 from/until pub date
    }
    headers = {
        'User-Agent': 'StreamlitApp/1.0 (mailto:streamlit.app.user@example.com)'
    }

    results = []
    error_message = None

    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=20)
        response.raise_for_status()
        data = response.json()

        if data['status'] == 'ok' and data['message']['items']:
            for item in data['message']['items']:
                title = item.get('title', ["N/A"])[0]
                authors = ", ".join([f"{author.get('given', '')} {author.get('family', '')}".strip()
                                     for author in item.get('author', [])]) or "N/A"
                issued_parts = item.get('issued', {}).get('date-parts', [[None]])[0]
                year = issued_parts[0] if issued_parts[0] else "N/A"
                journal = ", ".join(item.get('container-title', ["N/A"]))
                publisher = item.get('publisher', "N/A")
                doi = item.get('DOI', "N/A")
                doi_url = f"https://doi.org/{doi}" if doi != "N/A" else "#"
                doc_type = item.get('type', 'N/A').replace('-', ' ').title()
                # 提取摘要，移除 HTML 標籤 (Crossref 摘要可能包含 JATS XML 標籤)
                abstract_raw = item.get('abstract', "摘要未提供")
                # 簡單的 HTML 標籤移除 (可能不完美)
                import re
                abstract = re.sub('<[^<]+?>', '', abstract_raw) if abstract_raw != "摘要未提供" else abstract_raw


                results.append({
                    "Title": title, "Authors": authors, "Year": year,
                    "Journal/Book": journal, "Publisher": publisher, "Type": doc_type,
                    "DOI": doi, "Link": doi_url, "Abstract": abstract # 加入摘要欄位
                })
        elif data['status'] == 'ok' and not data['message']['items']:
             error_message = "找不到符合條件的文獻。"
        else:
            error_message = f"API 回應錯誤: {data.get('message-type', 'unknown')}"

    except requests.exceptions.Timeout:
        error_message = "連線逾時，請稍後再試。"
    except requests.exceptions.RequestException as e:
        error_message = f"API 請求錯誤：{e}"
    except Exception as e:
        error_message = f"處理資料時發生未知錯誤：{e}"

    return results, error_message

# --- 搜尋按鈕與結果顯示 ---
st.divider()

if st.button("🚀 開始搜尋", type="primary", use_container_width=True):
    final_query_list = selected_keywords + ([custom_keyword] if custom_keyword else [])

    if not final_query_list:
        st.error("❌ 請至少選擇或輸入一個關鍵字")
    elif year_start > year_end:
         st.error("❌ 起始年份不能晚於結束年份")
    else:
        search_term_display = " & ".join(final_query_list)
        year_range_display = f" ({year_start}-{year_end})"
        with st.spinner(f"🔍 正在搜尋「{search_term_display}」{year_range_display}..."):
            # 傳入年份參數
            results, error = search_crossref(final_query_list, year_start, year_end, max_results)

        if error:
            st.error(f"❌ {error}")
        elif not results:
            st.warning("⚠️ 找不到相關文獻")
        else:
            st.success(f"✅ 成功找到 {len(results)} 筆文獻！")
            
            df_results = pd.DataFrame(results)
            # 在表格中也顯示摘要欄位，但可能太長，所以主要在下方顯示
            display_columns = ["Title", "Authors", "Year", "Journal/Book", "Type", "DOI"]
            st.dataframe(df_results[display_columns], use_container_width=True, height=300)

            # --- 匯出功能 (包含摘要) ---
            st.sidebar.header("💾 匯出結果")
            # 確保匯出的 CSV 包含摘要
            csv_data = df_results.to_csv(index=False).encode('utf-8-sig')
            st.sidebar.download_button(
                label="📥 下載 CSV 檔案 (含摘要)",
                data=csv_data,
                file_name=f"crossref_{'_'.join(final_query_list)}_{year_start}-{year_end}_{time.strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
                type="primary"
            )

            # --- 顯示詳細資料與摘要 ---
            st.subheader("📄 文獻詳細資料與摘要")
            for i, paper in enumerate(results):
                apa_citation = f"{paper['Authors']} ({paper['Year']}). {paper['Title']}. *{paper['Journal/Book']}*. {paper['Publisher']}. {paper['Link']}"
                with st.expander(f"**{i+1}. {paper['Title']}** ({paper['Year']})", expanded=(i < 3)): # 預設展開前三筆
                    st.markdown(f"**作者:** {paper['Authors']}")
                    st.markdown(f"**發表於:** *{paper['Journal/Book']}*")
                    st.markdown(f"**出版商:** {paper['Publisher']}")
                    st.markdown(f"**文件類型:** {paper['Type']}")
                    st.markdown(f"**DOI:** [{paper['DOI']}]({paper['Link']})")

                    st.markdown("**摘要:**")
                    # 如果摘要太長，可以用 st.text_area 顯示並限制高度，或直接顯示
                    if paper['Abstract'] != "摘要未提供":
                        st.info(paper['Abstract'])
                    else:
                        st.caption(paper['Abstract']) # 顯示 "摘要未提供"

                    st.markdown("**APA 7 引用格式 (參考):**")
                    st.code(apa_citation, language='text')

# --- 側邊欄說明 ---
with st.sidebar:
    st.header("📖 使用說明")
    st.markdown("""
    ### ✨ 功能特色
    - 🌍 即時搜尋 **Crossref** 國際學術資料庫
    - 📚 提供 **15 個**常用商管關鍵字
    - ➕ 支援**複選**與**自訂**關鍵字 (AND 邏輯)
    - 📅 **年份範圍**篩選
    - 📄 顯示**摘要** (若可用)
    - 📊 表格化呈現結果
    - 💾 匯出 CSV 檔案 (含摘要)
    - 📄 提供 APA 格式範例

    ### ⚠️ 注意事項
    - 摘要資訊不一定可用。
    - 年份篩選基於出版日期，可能包含部分超出範圍的邊緣結果。
    """)
    st.divider()
    st.caption("Data retrieved via Crossref API.")

# 頁尾
st.divider()
st.caption("⚠️ 本工具僅供學術研究參考，請遵守 Crossref API 使用條款。")


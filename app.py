import streamlit as st
import requests
import pandas as pd
import time
import urllib.parse

# 頁面設定
st.set_page_config(
    page_title="國際期刊文獻搜尋器 (Crossref API)",
    page_icon="🌍",
    layout="wide"
)

st.title("🌍 國際期刊文獻搜尋器 (Crossref API)")
st.markdown("您可以選擇預設關鍵字或自行輸入，程式會將所有關鍵字組合 (AND) 進行搜尋。")

# --- 預設商管關鍵字 ---
BUSINESS_KEYWORDS = [
    "Management", "Marketing", "Finance", "Accounting", "Human Resources",
    "Strategy", "Supply Chain", "Logistics", "Operations Management", "Business Ethics",
    "Corporate Social Responsibility", "Entrepreneurship", "Innovation", "International Business", "Organizational Behavior"
]

# --- 使用者輸入介面 ---
st.subheader("請設定您的搜尋條件")

col1, col2 = st.columns([2, 1])
with col1:
    selected_keywords = st.multiselect(
        "📚 選擇預設關鍵字 (可複選)",
        options=BUSINESS_KEYWORDS,
        default=[] # 預設不選取
    )
with col2:
    custom_keyword = st.text_input(
        "⌨️ 或輸入自訂關鍵字 (英文)",
        placeholder="例如：digital transformation"
    )

max_results = st.slider("📈 最多顯示幾筆結果", min_value=5, max_value=100, value=20, step=5)

# --- Crossref API 搜尋函數 ---
@st.cache_data(ttl=3600) # 快取搜尋結果一小時
def search_crossref(query_list, rows=20):
    """
    使用 Crossref API 搜尋學術文獻。
    query_list: 包含多個關鍵字的列表
    """
    base_url = "https://api.crossref.org/works"
    
    # 將所有關鍵字用空格連接，代表 AND 邏輯
    combined_query = " ".join(query_list)
    encoded_query = urllib.parse.quote(combined_query)
    
    mailto = "streamlit.app.user@example.com"
    params = {
        'query.bibliographic': encoded_query,
        'rows': rows,
        'mailto': mailto,
        'select': 'DOI,title,author,issued,container-title,publisher,type'
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

                results.append({
                    "Title": title, "Authors": authors, "Year": year,
                    "Journal/Book": journal, "Publisher": publisher, "Type": doc_type,
                    "DOI": doi, "Link": doi_url
                })
        # Check if items list is empty even if status is ok
        elif data['status'] == 'ok' and not data['message']['items']:
             error_message = "找不到符合所有關鍵字的文獻。" # More specific message
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
    # 組合所有關鍵字
    final_query_list = selected_keywords + ([custom_keyword] if custom_keyword else [])

    if not final_query_list:
        st.error("❌ 請至少選擇或輸入一個關鍵字")
    else:
        search_term_display = " & ".join(final_query_list) # 用 & 符號顯示組合
        with st.spinner(f"🔍 正在透過 Crossref API 搜尋「{search_term_display}」..."):
            results, error = search_crossref(final_query_list, max_results)

        if error:
            st.error(f"❌ {error}")
        elif not results:
            st.warning("⚠️ 找不到相關文獻")
        else:
            st.success(f"✅ 成功找到 {len(results)} 筆文獻！")
            
            df_results = pd.DataFrame(results)
            display_columns = ["Title", "Authors", "Year", "Journal/Book", "Type", "DOI"]
            st.dataframe(df_results[display_columns], use_container_width=True, height=400) # 增加表格高度

            # --- 匯出功能 ---
            st.sidebar.header("💾 匯出結果")
            csv_data = df_results.to_csv(index=False).encode('utf-8-sig')
            st.sidebar.download_button(
                label="📥 下載 CSV 檔案",
                data=csv_data,
                file_name=f"crossref_{'_'.join(final_query_list)}_{time.strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
                type="primary"
            )

            # --- 顯示 APA 格式 (前幾筆) ---
            st.subheader("📄 APA 7 引用格式 (部分範例)")
            for i, paper in enumerate(results[:5]): # 只顯示前 5 筆 APA
                apa_citation = f"{paper['Authors']} ({paper['Year']}). {paper['Title']}. *{paper['Journal/Book']}*. {paper['Publisher']}. {paper['Link']}"
                st.markdown(f"**{i+1}.** {apa_citation}")
                st.divider()

# --- 側邊欄說明 ---
with st.sidebar:
    st.header("📖 使用說明")
    st.markdown("""
    ### ✨ 功能特色
    - 🌍 即時搜尋 **Crossref** 國際學術資料庫
    - 📚 提供 **15 個**常用商管關鍵字
    - ➕ 支援**複選**與**自訂**關鍵字 (以 AND 邏輯組合)
    - 📊 表格化呈現結果
    - 💾 匯出 CSV 檔案
    - 📄 提供 APA 格式範例

    ### ⚠️ 注意事項
    - 組合越多關鍵字，結果越精確，但也可能找不到文獻。
    - API 搜尋速度可能受網路影響。
    """)
    st.divider()
    st.caption("Data retrieved via Crossref API.")

# 頁尾
st.divider()
st.caption("⚠️ 本工具僅供學術研究參考，請遵守 Crossref API 使用條款。")


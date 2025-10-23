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
st.markdown("輸入英文關鍵字，即可透過 Crossref API 即時搜尋國際學術文獻。")

# --- 使用者輸入 ---
col1, col2 = st.columns([3, 1])
with col1:
    keyword = st.text_input("🔍 搜尋關鍵字 (請輸入英文)", placeholder="例如：machine learning, supply chain")
with col2:
    max_results = st.number_input("最多顯示幾筆", min_value=5, max_value=100, value=20, step=5)

# --- Crossref API 搜尋函數 ---
@st.cache_data(ttl=3600) # 快取搜尋結果一小時，避免重複請求
def search_crossref(query, rows=20):
    """
    使用 Crossref API 搜尋學術文獻。
    """
    base_url = "https://api.crossref.org/works"
    # 使用 urllib.parse.quote 來處理特殊字元
    encoded_query = urllib.parse.quote(query)
    # Crossref API 建議在請求中包含 mailto 參數，說明是誰在請求
    mailto = "streamlit.app.user@example.com" # 可以用一個通用的郵箱
    params = {
        'query.bibliographic': encoded_query,
        'rows': rows,
        'mailto': mailto,
        'select': 'DOI,title,author,issued,container-title,publisher,type' # 指定我們需要的欄位
    }
    headers = {
        'User-Agent': 'StreamlitApp/1.0 (mailto:streamlit.app.user@example.com)' # 提供 User-Agent
    }

    results = []
    error_message = None

    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=20)
        response.raise_for_status() # 如果狀態碼不是 2xx，則拋出例外
        data = response.json()

        if data['status'] == 'ok' and data['message']['items']:
            for item in data['message']['items']:
                # 提取需要的資訊
                title = item.get('title', ["標題未提供"])[0] # title 可能是個列表
                authors = ", ".join([f"{author.get('given', '')} {author.get('family', '')}".strip()
                                     for author in item.get('author', [])]) or "作者未提供"
                
                # 處理年份
                issued_parts = item.get('issued', {}).get('date-parts', [[None]])[0]
                year = issued_parts[0] if issued_parts[0] else "年份未提供"

                journal = ", ".join(item.get('container-title', ["期刊/書籍未提供"])) # container-title 也可能是列表
                publisher = item.get('publisher', "出版商未提供")
                doi = item.get('DOI', "DOI 未提供")
                doi_url = f"https://doi.org/{doi}" if doi != "DOI 未提供" else "#"
                doc_type = item.get('type', '類型未提供').replace('-', ' ').title() # 格式化文件類型

                results.append({
                    "Title": title,
                    "Authors": authors,
                    "Year": year,
                    "Journal/Book": journal,
                    "Publisher": publisher,
                    "Type": doc_type,
                    "DOI": doi,
                    "Link": doi_url
                })
        else:
            error_message = "找不到相關文獻，或 API 回應格式錯誤。"

    except requests.exceptions.Timeout:
        error_message = "連線逾時，請稍後再試。"
    except requests.exceptions.RequestException as e:
        error_message = f"API 請求錯誤：{e}"
    except Exception as e:
        error_message = f"處理資料時發生未知錯誤：{e}"

    return results, error_message

# --- 搜尋按鈕與結果顯示 ---
if st.button("🚀 開始搜尋", type="primary", use_container_width=True):
    if not keyword:
        st.error("❌ 請輸入搜尋關鍵字")
    else:
        with st.spinner(f"🔍 正在透過 Crossref API 搜尋「{keyword}」..."):
            results, error = search_crossref(keyword, max_results)

        if error:
            st.error(f"❌ {error}")
        elif not results:
            st.warning("⚠️ 找不到相關文獻")
        else:
            st.success(f"✅ 成功找到 {len(results)} 筆文獻！")
            
            # --- 使用 DataFrame 顯示結果 ---
            df_results = pd.DataFrame(results)
            
            # 調整顯示欄位順序
            display_columns = ["Title", "Authors", "Year", "Journal/Book", "Publisher", "Type", "DOI"]
            st.dataframe(df_results[display_columns], use_container_width=True)

            # --- 匯出功能 ---
            st.sidebar.header("💾 匯出結果")
            csv_data = df_results.to_csv(index=False).encode('utf-8-sig')
            st.sidebar.download_button(
                label="📥 下載 CSV 檔案",
                data=csv_data,
                file_name=f"crossref_{keyword.replace(' ', '_')}_{time.strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
                type="primary"
            )

            # --- 顯示 APA 格式 (前幾筆) ---
            st.subheader("📄 APA 7 引用格式 (部分範例)")
            for i, paper in enumerate(results[:5]): # 只顯示前 5 筆 APA
                # 簡易 APA 格式產生 (僅供參考)
                apa_citation = f"{paper['Authors']} ({paper['Year']}). {paper['Title']}. *{paper['Journal/Book']}*. {paper['Publisher']}. {paper['Link']}"
                st.markdown(f"**{i+1}.** {apa_citation}")
                st.divider()


# --- 側邊欄說明 ---
with st.sidebar:
    st.header("📖 使用說明")
    st.markdown("""
    ### ✨ 功能特色
    - 🌍 即時搜尋 **Crossref** 國際學術資料庫
    - 🔑 支援英文關鍵字搜尋
    - 📊 表格化呈現結果
    - 💾 匯出 CSV 檔案
    - 📄 提供 APA 格式範例

    ### ⚠️ 注意事項
    - API 搜尋速度可能受網路影響。
    - Crossref 主要提供**元資料** (標題、作者、期刊等)，不一定包含摘要。
    - 結果涵蓋大量 SCI/SSCI 期刊，但不限於此。
    """)
    st.divider()
    st.caption("Data retrieved via Crossref API.")

# 頁尾
st.divider()
st.caption("⚠️ 本工具僅供學術研究參考，請遵守 Crossref API 使用條款。")


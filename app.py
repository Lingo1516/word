import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime
import re # 用於清理摘要中的特殊字元

# 頁面設定
st.set_page_config(
    page_title="國際學術文獻搜尋器 (Semantic Scholar API)",
    page_icon="💡",
    layout="wide"
)

st.title("💡 國際學術文獻搜尋器 (Semantic Scholar API)")
st.markdown("輸入英文關鍵字，即可透過 Semantic Scholar API 即時搜尋國際學術文獻（通常包含摘要）。")

# --- 使用者輸入介面 ---
st.subheader("請設定您的搜尋條件")

col_keyword, col_year = st.columns([2, 1])
with col_keyword:
    keyword = st.text_input("🔍 搜尋關鍵字 (英文)", placeholder="例如：organizational behavior, machine learning")
with col_year:
    # Semantic Scholar API 的年份篩選比較特殊，通常建議獲取後再篩選
    # 但我們可以先設定一個目標範圍
    current_year = datetime.now().year
    year_start, year_end = st.select_slider(
        '📅 選擇年份範圍 (API 會盡力符合)',
        options=range(1980, current_year + 1),
        value=(current_year - 5, current_year)
    )

max_results = st.slider("📈 最多顯示幾筆結果 (API 上限約 100)", min_value=5, max_value=100, value=20, step=5)


# --- Semantic Scholar API 搜尋函數 ---
# 使用 Streamlit 的快取機制
@st.cache_data(ttl=3600) # 快取結果一小時
def search_semantic_scholar(query, start_year, end_year, limit=20):
    """
    使用 Semantic Scholar API 搜尋學術文獻。
    """
    base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
    
    # Semantic Scholar 的年份篩選是在 query 中指定
    year_filter = f"{start_year}-{end_year}"
    
    params = {
        'query': query,
        'year': year_filter, # 加入年份篩選條件
        'limit': limit,
        # 請求更多欄位，包含摘要 (abstract) 和期刊資訊 (venue)
        'fields': 'title,authors,year,abstract,venue,publicationVenue,journal,externalIds,url'
    }
    headers = {
        # Semantic Scholar API 建議提供 User-Agent，但非強制
        'User-Agent': 'StreamlitApp/1.0 (mailto:streamlit.app.user@example.com)'
        # Semantic Scholar 未來可能需要 API Key，目前不需
        # 'x-api-key': 'YOUR_API_KEY' # 如果需要 API Key，請填寫於此
    }

    results = []
    error_message = None

    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=30) # 增加 timeout 時間
        response.raise_for_status()
        data = response.json()

        # Semantic Scholar 回應結構與 Crossref 不同
        papers = data.get('data', [])

        if papers:
            for item in papers:
                title = item.get('title', "N/A")
                # 作者資訊格式不同
                authors = ", ".join([author.get('name', 'N/A') for author in item.get('authors', [])]) or "N/A"
                year = item.get('year', "N/A")
                
                # 期刊/會議資訊可能在不同欄位
                journal_info = item.get('journal')
                venue = item.get('venue') or item.get('publicationVenue', {}).get('name')
                if journal_info and journal_info.get('name'):
                    journal_venue = journal_info.get('name')
                elif venue:
                     journal_venue = venue
                else:
                    journal_venue = "N/A"
                    
                # 嘗試獲取 DOI
                doi = item.get('externalIds', {}).get('DOI', "N/A")
                doi_url = f"https://doi.org/{doi}" if doi != "N/A" else item.get('url', '#') # 如果沒 DOI，用 S2 連結

                # 獲取摘要，並做簡單清理
                abstract_raw = item.get('abstract', "摘要未提供")
                # 移除多餘空白和換行
                abstract = ' '.join(abstract_raw.split()) if abstract_raw and abstract_raw != "摘要未提供" else abstract_raw

                results.append({
                    "Title": title,
                    "Authors": authors,
                    "Year": year,
                    "Journal/Venue": journal_venue, # 更改欄位名稱
                    "DOI": doi,
                    "Link": doi_url,
                    "Abstract": abstract
                })
        # 檢查 total，如果為 0 表示沒找到
        elif data.get('total', 0) == 0:
            error_message = "找不到符合條件的文獻。"
        else:
            # 其他可能的 API 錯誤
             error_message = f"API 回應異常: {data.get('message', '未知錯誤')}"


    except requests.exceptions.Timeout:
        error_message = "連線 Semantic Scholar API 逾時，請稍後再試。"
    except requests.exceptions.RequestException as e:
        error_message = f"API 請求錯誤：{e}"
    except Exception as e:
        error_message = f"處理資料時發生未知錯誤：{e}"

    return results, error_message

# --- 搜尋按鈕與結果顯示 ---
st.divider()

if st.button("🚀 開始搜尋", type="primary", use_container_width=True):
    if not keyword:
        st.error("❌ 請輸入搜尋關鍵字")
    else:
        year_range_display = f" ({year_start}-{year_end})"
        with st.spinner(f"🔍 正在透過 Semantic Scholar API 搜尋「{keyword}」{year_range_display}..."):
            # 傳入年份參數
            results, error = search_semantic_scholar(keyword, year_start, year_end, max_results)

        if error:
            st.error(f"❌ {error}")
        elif not results:
            st.warning("⚠️ 找不到相關文獻")
        else:
            st.success(f"✅ 成功找到 {len(results)} 筆文獻！")

            df_results = pd.DataFrame(results)
            display_columns = ["Title", "Authors", "Year", "Journal/Venue", "DOI"]
            st.dataframe(df_results[display_columns], use_container_width=True, height=300)

            # --- 匯出功能 (包含摘要) ---
            st.sidebar.header("💾 匯出結果")
            csv_data = df_results.to_csv(index=False).encode('utf-8-sig')
            st.sidebar.download_button(
                label="📥 下載 CSV 檔案 (含摘要)",
                data=csv_data,
                file_name=f"semantic_scholar_{keyword.replace(' ', '_')}_{year_start}-{year_end}_{time.strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
                type="primary"
            )

            # --- 顯示詳細資料與摘要 ---
            st.subheader("📄 文獻詳細資料與摘要")
            for i, paper in enumerate(results):
                # 簡易 APA 格式產生 (僅供參考)
                apa_citation = f"{paper['Authors']} ({paper['Year']}). {paper['Title']}. *{paper['Journal/Venue']}*. {paper['Link']}"
                with st.expander(f"**{i+1}. {paper['Title']}** ({paper['Year']})", expanded=(i < 3)): # 預設展開前三筆
                    st.markdown(f"**作者:** {paper['Authors']}")
                    st.markdown(f"**發表於:** *{paper['Journal/Venue']}*")
                    st.markdown(f"**DOI:** [{paper['DOI']}]({paper['Link']})")

                    st.markdown("**摘要:**")
                    if paper['Abstract'] != "摘要未提供" and paper['Abstract'] is not None:
                        # 使用 st.text_area 讓長摘要可以滾動
                        st.text_area(f"摘要_{i}", paper['Abstract'], height=150, disabled=True, label_visibility="collapsed")
                    else:
                        st.caption("摘要未提供")

                    st.markdown("**APA 7 引用格式 (參考):**")
                    st.code(apa_citation, language='text')

# --- 側邊欄說明 ---
with st.sidebar:
    st.header("📖 使用說明")
    st.markdown("""
    ### ✨ 功能特色
    - 🌍 即時搜尋 **Semantic Scholar** 國際學術資料庫
    - 🔑 支援英文關鍵字搜尋
    - 📅 **年份範圍**篩選 (API 會盡力符合)
    - 📄 顯示**摘要** (若 API 有提供)
    - 📊 表格化呈現結果
    - 💾 匯出 CSV 檔案 (含摘要)
    - 📄 提供 APA 格式範例

    ### ⚠️ 注意事項
    - Semantic Scholar API **強烈建議**提供摘要。
    - 年份篩選是建議值，API 可能返回部分超出範圍的結果。
    - 未來可能需要申請 API Key 以提高請求限制。
    """)
    st.divider()
    st.caption("Data retrieved via Semantic Scholar API.")

# 頁尾
st.divider()
st.caption("⚠️ 本工具僅供學術研究參考。")


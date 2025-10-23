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
st.markdown("您可以選擇預設關鍵字或自行輸入 (以 AND 組合)，並設定年份範圍。")

# --- 設定冷卻時間（秒） ---
COOLDOWN_SECONDS = 15 # 稍微延長冷卻時間
if 'last_search_time' not in st.session_state:
    st.session_state.last_search_time = 0

# --- 預設商管關鍵字（包含中英文） ---
BUSINESS_KEYWORDS_DICT = [
    {"en": "Management", "zh": "管理學"},
    {"en": "Marketing", "zh": "市場行銷"},
    {"en": "Finance", "zh": "財務金融"},
    {"en": "Accounting", "zh": "會計學"},
    {"en": "Human Resources", "zh": "人力資源"},
    {"en": "Strategy", "zh": "策略管理"},
    {"en": "Supply Chain", "zh": "供應鏈管理"},
    {"en": "Logistics", "zh": "物流管理"},
    {"en": "Operations Management", "zh": "營運管理"},
    {"en": "Business Ethics", "zh": "商業倫理"},
    {"en": "Corporate Social Responsibility", "zh": "企業社會責任"},
    {"en": "Entrepreneurship", "zh": "創業精神"},
    {"en": "Innovation", "zh": "創新管理"},
    {"en": "International Business", "zh": "國際企業"},
    {"en": "Organizational Behavior", "zh": "組織行為"}
]

# --- 使用者輸入介面 ---
st.subheader("請設定您的搜尋條件")

col_keyword1, col_keyword2 = st.columns([2, 1])
with col_keyword1:
    selected_keyword_dicts = st.multiselect(
        "📚 選擇預設關鍵字 (可複選)",
        options=BUSINESS_KEYWORDS_DICT,
        format_func=lambda keyword_dict: f"{keyword_dict['en']} ({keyword_dict['zh']})",
        default=[]
    )
    selected_keywords_en = [k['en'] for k in selected_keyword_dicts]
with col_keyword2:
    custom_keyword = st.text_input(
        "⌨️ 或輸入自訂關鍵字 (英文)",
        placeholder="例如：digital transformation"
    )

current_year = datetime.now().year
col_year1, col_year2, col_slider = st.columns([1, 1, 2])
with col_year1:
    year_start = st.number_input("⏳ 起始年份", min_value=1980, max_value=current_year, value=current_year - 5)
with col_year2:
    year_end = st.number_input("⌛ 結束年份", min_value=1980, max_value=current_year, value=current_year)
with col_slider:
    max_results = st.slider("📈 最多顯示幾筆結果 (API 上限約 100)", min_value=5, max_value=100, value=20, step=5)

# --- Semantic Scholar API 搜尋函數 (保持不變) ---
@st.cache_data(ttl=3600)
def search_semantic_scholar(query_list, start_year, end_year, limit=20):
    # ... (省略未變更的 API 呼叫函數內容) ...
    base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
    combined_query = " ".join(query_list)
    year_filter = f"{start_year}-{end_year}"
    params = {
        'query': combined_query, 'year': year_filter, 'limit': limit,
        'fields': 'title,authors,year,abstract,venue,publicationVenue,journal,externalIds,url'
    }
    headers = {'User-Agent': 'StreamlitApp/1.0 (mailto:streamlit.app.user@example.com)'}
    results = []
    error_message = None

    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=30)
        if response.status_code == 429:
             # 從 Header 讀取建議等待時間，若無則用預設值
             # 將讀取到的字串轉為整數，若轉換失敗也用預設值
             try:
                 retry_after = int(response.headers.get("Retry-After", COOLDOWN_SECONDS))
             except (ValueError, TypeError):
                 retry_after = COOLDOWN_SECONDS
             error_message = f"請求過於頻繁 (429)。API 建議等待 {retry_after} 秒後再試。"
             return results, error_message

        response.raise_for_status()
        data = response.json()
        papers = data.get('data', [])

        if papers:
            for item in papers:
                title = item.get('title', "N/A")
                authors = ", ".join([author.get('name', 'N/A') for author in item.get('authors', [])]) or "N/A"
                year = item.get('year', "N/A")
                journal_info = item.get('journal')
                venue = item.get('venue') or item.get('publicationVenue', {}).get('name')
                if journal_info and journal_info.get('name'):
                    journal_venue = journal_info.get('name')
                elif venue:
                     journal_venue = venue
                else:
                    journal_venue = "N/A"
                doi = item.get('externalIds', {}).get('DOI', "N/A")
                doi_url = f"https://doi.org/{doi}" if doi != "N/A" else item.get('url', '#')
                abstract_raw = item.get('abstract', "摘要未提供")
                abstract = ' '.join(abstract_raw.split()) if abstract_raw and abstract_raw != "摘要未提供" else abstract_raw
                results.append({
                    "Title": title, "Authors": authors, "Year": year,
                    "Journal/Venue": journal_venue,
                    "DOI": doi, "Link": doi_url, "Abstract": abstract
                })
        elif data.get('total', 0) == 0:
            error_message = "找不到符合條件的文獻。"
        else:
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

# --- 優化：持續顯示冷卻狀態 ---
current_time = time.time()
time_since_last_search = current_time - st.session_state.last_search_time
remaining_cooldown = COOLDOWN_SECONDS - time_since_last_search

# 用於顯示冷卻/錯誤訊息的 placeholder
status_placeholder = st.empty()

# 判斷按鈕是否應啟用
can_search = remaining_cooldown <= 0

if not can_search:
    # 如果在冷卻中，持續顯示提示訊息
    status_placeholder.warning(f"⏳ 冷卻中，請等待 {int(remaining_cooldown) + 1} 秒...")

# 顯示搜尋按鈕，根據冷卻狀態決定是否禁用
search_button_clicked = st.button("🚀 開始搜尋", type="primary", use_container_width=True, disabled=not can_search)

if search_button_clicked and can_search: # 只有在可以搜尋且按鈕被點擊時才執行
    # 清空之前的狀態提示
    status_placeholder.empty()

    final_query_list = selected_keywords_en + ([custom_keyword] if custom_keyword else [])
    if not final_query_list:
        st.error("❌ 請至少選擇或輸入一個關鍵字")
    elif year_start > year_end:
         st.error("❌ 起始年份不能晚於結束年份")
    else:
        # 更新上次搜尋時間
        st.session_state.last_search_time = time.time() # 用 time.time() 獲取當前時間

        search_term_display = " & ".join(final_query_list)
        year_range_display = f" ({year_start}-{year_end})"
        with st.spinner(f"🔍 正在搜尋「{search_term_display}」{year_range_display}..."):
            results, error = search_semantic_scholar(final_query_list, year_start, year_end, max_results)

        if error:
            # 將錯誤訊息顯示在 placeholder 區域
            status_placeholder.error(f"❌ {error}")
        elif not results:
            st.warning("⚠️ 找不到相關文獻")
        else:
            st.success(f"✅ 成功找到 {len(results)} 筆文獻！")
            df_results = pd.DataFrame(results)
            display_columns = ["Title", "Authors", "Year", "Journal/Venue", "DOI"]
            # 增加表格高度以顯示更多內容
            st.dataframe(df_results[display_columns], use_container_width=True, height=400)

            st.sidebar.header("💾 匯出結果")
            csv_data = df_results.to_csv(index=False).encode('utf-8-sig')
            st.sidebar.download_button(
                label="📥 下載 CSV 檔案 (含摘要)",
                data=csv_data,
                file_name=f"semantic_scholar_{'_'.join(final_query_list)}_{year_start}-{year_end}_{time.strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
                type="primary"
            )

            st.subheader("📄 文獻詳細資料與摘要")
            # 預設展開筆數改為 5 筆
            for i, paper in enumerate(results):
                apa_citation = f"{paper['Authors']} ({paper['Year']}). {paper['Title']}. *{paper['Journal/Venue']}*. {paper['Link']}"
                with st.expander(f"**{i+1}. {paper['Title']}** ({paper['Year']})", expanded=(i < 5)): # 預設展開前五筆
                    st.markdown(f"**作者:** {paper['Authors']}")
                    st.markdown(f"**發表於:** *{paper['Journal/Venue']}*")
                    st.markdown(f"**DOI:** [{paper['DOI']}]({paper['Link']})")
                    st.markdown("**摘要:**")
                    if paper['Abstract'] != "摘要未提供" and paper['Abstract'] is not None:
                        st.text_area(f"摘要_{i}", paper['Abstract'], height=150, disabled=True, label_visibility="collapsed")
                    else:
                        st.caption("摘要未提供")
                    st.markdown("**APA 7 引用格式 (參考):**")
                    st.code(apa_citation, language='text')

# --- 側邊欄說明 ---
with st.sidebar:
    st.header("📖 使用說明")
    st.markdown(f"""
    ### ✨ 功能特色
    - 🌍 即時搜尋 **Semantic Scholar** 國際學術資料庫
    - 📚 提供 **15 個**常用商管關鍵字 (含中文)
    - ➕ 支援**複選**與**自訂**關鍵字 (AND 邏輯)
    - 📅 **年份範圍**篩選
    - 📄 顯示**摘要** (若 API 有提供)
    - 📊 表格化呈現結果
    - 💾 匯出 CSV 檔案 (含摘要)
    - 📄 提供 APA 格式範例

    ### ⚠️ 注意事項
    - 為避免觸發 API 流量限制，每次搜尋需間隔 **{COOLDOWN_SECONDS} 秒**。應用程式會提示剩餘等待時間，並暫時禁用搜尋按鈕。
    - 若多人同時使用，仍可能遇到 API 限制 (429 錯誤)，請稍後再試。
    - 摘要資訊不一定可用。
    """)
    st.divider()
    st.caption("Data retrieved via Semantic Scholar API.")

# 頁尾
st.divider()
st.caption("⚠️ 本工具僅供學術研究參考。")


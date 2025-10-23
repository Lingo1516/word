import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime
import re # 用於清理摘要中的特殊字元

# 頁面設定
st.set_page_config(
    page_title="國際學術文獻搜尋器 (OpenAlex API)",
    page_icon="✨",
    layout="wide"
)

st.title("✨ 國際學術文獻搜尋器 (OpenAlex API)")
st.markdown("輸入英文關鍵字，即可透過 OpenAlex API 即時搜尋國際學術文獻（摘要提供率高）。")

# --- 設定冷卻時間（秒） ---
# OpenAlex 的免費 polite pool 建議每秒不超過 10 次請求，設 2 秒應該足夠
COOLDOWN_SECONDS = 2
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
    max_results = st.slider("📈 最多顯示幾筆結果 (API 上限 200)", min_value=5, max_value=50, value=20, step=5) # OpenAlex 每頁最多 200，但預設顯示 50

# --- OpenAlex API 搜尋函數 ---
@st.cache_data(ttl=3600) # 快取結果一小時
def search_openalex(query_list, start_year, end_year, per_page=20):
    """
    使用 OpenAlex API 搜尋學術文獻。
    """
    base_url = "https://api.openalex.org/works"
    
    # 組合關鍵字
    combined_query = " ".join(query_list)
    
    # OpenAlex 的 filter 語法
    filters = [f"publication_year:{start_year}-{end_year}"]
    # 可以考慮加入語言過濾，例如 'language:en'
    # filters.append('language:en')
    
    params = {
        'search': combined_query,
        'filter': ",".join(filters),
        'per_page': per_page,
        # OpenAlex 建議提供 email 以便他們聯繫（放入 polite pool）
        'mailto': 'streamlit.app.user@example.com',
        # 選擇需要的欄位，包括摘要 (abstract_inverted_index)
        'select': 'id,doi,title,display_name,publication_year,authorships,host_venue,primary_location,abstract_inverted_index,type'
    }
    headers = {
        'User-Agent': 'StreamlitApp/1.0 (mailto:streamlit.app.user@example.com)'
    }

    results = []
    error_message = None

    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=30)

        # OpenAlex 遇到流量限制通常是 429 或 403
        if response.status_code == 429 or response.status_code == 403:
             retry_after = response.headers.get("Retry-After", COOLDOWN_SECONDS)
             error_message = f"請求過於頻繁 ({response.status_code})。OpenAlex API 建議等待 {retry_after} 秒後再試。"
             return results, error_message

        response.raise_for_status() # 其他錯誤碼則拋出例外
        data = response.json()
        
        papers = data.get('results', [])

        if papers:
            for item in papers:
                title = item.get('display_name', item.get('title', "N/A")) # display_name 通常更好
                
                # 作者資訊結構不同
                authors = ", ".join([author.get('author', {}).get('display_name', 'N/A')
                                     for author in item.get('authorships', [])]) or "N/A"
                                     
                year = item.get('publication_year', "N/A")
                
                # 期刊/會議資訊
                host_venue = item.get('host_venue', {})
                journal_venue = host_venue.get('display_name', host_venue.get('publisher', "N/A"))
                
                # DOI 和連結
                doi = item.get('doi', None)
                doi_url = doi if doi else item.get('id', '#') # 如果沒 DOI，用 OpenAlex ID 連結 (非直接論文連結)
                
                doc_type = item.get('type', 'N/A').replace('-', ' ').title()

                # --- 處理 OpenAlex 的摘要 (Abstract Inverted Index) ---
                abstract_inverted = item.get('abstract_inverted_index')
                abstract = "摘要未提供"
                if abstract_inverted:
                    try:
                        # 重建摘要：根據 index 排序並組合 word
                        word_index = {}
                        for word, indices in abstract_inverted.items():
                            for index in indices:
                                word_index[index] = word
                        
                        sorted_indices = sorted(word_index.keys())
                        abstract_words = [word_index[i] for i in sorted_indices]
                        abstract = " ".join(abstract_words)
                        # 簡單清理可能的標點符號問題
                        abstract = abstract.replace(" .", ".").replace(" ,", ",")
                    except Exception:
                        abstract = "摘要解析錯誤" # 如果重建失敗
                # --- 摘要處理結束 ---

                results.append({
                    "Title": title, "Authors": authors, "Year": year,
                    "Journal/Venue": journal_venue,
                    "DOI": doi.replace("https://doi.org/", "") if doi else "N/A", # 只顯示 DOI 本身
                    "Link": doi_url,
                    "Abstract": abstract
                })
        elif data.get('meta', {}).get('count', 0) == 0:
            error_message = "找不到符合條件的文獻。"
        else:
             error_message = f"API 回應異常: {data.get('error', '未知錯誤')}"


    except requests.exceptions.Timeout:
        error_message = "連線 OpenAlex API 逾時，請稍後再試。"
    except requests.exceptions.RequestException as e:
        error_message = f"API 請求錯誤：{e}"
    except Exception as e:
        error_message = f"處理資料時發生未知錯誤：{e}"

    return results, error_message

# --- 搜尋按鈕與結果顯示 ---
st.divider()

# --- 持續顯示冷卻狀態 ---
current_time = time.time()
time_since_last_search = current_time - st.session_state.last_search_time
remaining_cooldown = COOLDOWN_SECONDS - time_since_last_search

status_placeholder = st.empty()
can_search = remaining_cooldown <= 0

if not can_search:
    status_placeholder.warning(f"⏳ 冷卻中，請等待 {int(remaining_cooldown) + 1} 秒...")

search_button_clicked = st.button("🚀 開始搜尋", type="primary", use_container_width=True, disabled=not can_search)

if search_button_clicked and can_search:
    status_placeholder.empty()

    final_query_list = selected_keywords_en + ([custom_keyword] if custom_keyword else [])
    if not final_query_list:
        st.error("❌ 請至少選擇或輸入一個關鍵字")
    elif year_start > year_end:
         st.error("❌ 起始年份不能晚於結束年份")
    else:
        st.session_state.last_search_time = time.time()

        search_term_display = " & ".join(final_query_list)
        year_range_display = f" ({year_start}-{year_end})"
        with st.spinner(f"🔍 正在透過 OpenAlex API 搜尋「{search_term_display}」{year_range_display}..."):
            results, error = search_openalex(final_query_list, year_start, year_end, max_results)

        if error:
            status_placeholder.error(f"❌ {error}")
        elif not results:
            st.warning("⚠️ 找不到相關文獻")
        else:
            st.success(f"✅ 成功找到 {len(results)} 筆文獻！")
            df_results = pd.DataFrame(results)
            display_columns = ["Title", "Authors", "Year", "Journal/Venue", "DOI"]
            st.dataframe(df_results[display_columns], use_container_width=True, height=400)

            st.sidebar.header("💾 匯出結果")
            csv_data = df_results.to_csv(index=False).encode('utf-8-sig')
            st.sidebar.download_button(
                label="📥 下載 CSV 檔案 (含摘要)",
                data=csv_data,
                file_name=f"openalex_{'_'.join(final_query_list)}_{year_start}-{year_end}_{time.strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
                type="primary"
            )

            st.subheader("📄 文獻詳細資料與摘要")
            for i, paper in enumerate(results):
                # 簡化 APA 格式，因為 OpenAlex 提供的連結不一定是最終出版連結
                apa_citation = f"{paper['Authors']} ({paper['Year']}). {paper['Title']}. *{paper['Journal/Venue']}*. {paper['Link']}"
                with st.expander(f"**{i+1}. {paper['Title']}** ({paper['Year']})", expanded=(i < 5)):
                    st.markdown(f"**作者:** {paper['Authors']}")
                    st.markdown(f"**發表於:** *{paper['Journal/Venue']}*")
                    st.markdown(f"**DOI:** {paper['DOI']}") # 直接顯示 DOI
                    # 提供 OpenAlex 連結
                    st.markdown(f"**OpenAlex Link:** {paper['Link']}")


                    st.markdown("**摘要:**")
                    if paper['Abstract'] != "摘要未提供" and paper['Abstract'] is not None and paper['Abstract'] != "摘要解析錯誤":
                        st.text_area(f"摘要_{i}", paper['Abstract'], height=150, disabled=True, label_visibility="collapsed")
                    else:
                        st.caption(paper['Abstract']) # 顯示 "摘要未提供" 或 "摘要解析錯誤"

                    st.markdown("**APA 7 引用格式 (參考):**")
                    st.code(apa_citation, language='text')

# --- 側邊欄說明 ---
with st.sidebar:
    st.header("📖 使用說明")
    st.markdown(f"""
    ### ✨ 功能特色
    - 🌍 即時搜尋 **OpenAlex** 國際學術大數據庫
    - 📚 提供 **15 個**常用商管關鍵字 (含中文)
    - ➕ 支援**複選**與**自訂**關鍵字 (AND 邏輯)
    - 📅 **年份範圍**篩選
    - 📄 顯示**摘要** (若 API 有提供)
    - 📊 表格化呈現結果
    - 💾 匯出 CSV 檔案 (含摘要)
    - 📄 提供 APA 格式範例

    ### ⚠️ 注意事項
    - OpenAlex 的免費 polite pool 有流量限制 (約 10次/秒)，已加入 **{COOLDOWN_SECONDS} 秒**冷卻。若遇 429/403 錯誤請稍候。
    - 摘要資訊由 OpenAlex 提供，不保證所有文獻皆有。
    - 建議註冊 OpenAlex email 以獲得更好的服務品質。
    """)
    st.divider()
    st.caption("Data retrieved via OpenAlex API.")

# 頁尾
st.divider()
st.caption("⚠️ 本工具僅供學術研究參考。")


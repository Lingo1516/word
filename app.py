import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime
# import xml.etree.ElementTree as ET # 不再需要
import re # 用於清理摘要

# --- 頁面設定 ---
st.set_page_config(
    page_title="學術文獻搜尋平台 (Semantic Scholar API)", # 更新標題
    page_icon="💡",
    layout="wide"
)

st.title("💡 學術文獻搜尋平台 (Semantic Scholar API)") # 更新標題
st.markdown("使用 Semantic Scholar API 即時搜尋國際學術文獻（通常包含摘要）。") # 更新描述

# --- 設定冷卻時間（秒） ---
COOLDOWN_SECONDS = 5
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
    # 調整標籤，因為現在只有一個來源
    max_results = st.slider("📈 最多顯示幾筆結果", min_value=5, max_value=100, value=20, step=5)


# --- API 搜尋函數 ---

# Semantic Scholar API (保持不變)
@st.cache_data(ttl=3600)
def search_semantic_scholar(query, start_year, end_year, limit=10):
    base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
    year_filter = f"{start_year}-{end_year}"
    params = {
        'query': query, 'year': year_filter, 'limit': limit,
        'fields': 'title,authors,year,abstract,venue,publicationVenue,journal,externalIds,url,keywords'
    }
    headers = {'User-Agent': 'StreamlitApp/1.0 (mailto:streamlit.app.user@example.com)'}
    papers = []
    error_message = None
    try:
        resp = requests.get(base_url, params=params, headers=headers, timeout=20)
        if resp.status_code == 429:
             retry_after = resp.headers.get("Retry-After", COOLDOWN_SECONDS)
             error_message = f"Semantic Scholar API 請求過頻 (429)，建議等待 {retry_after} 秒。"
             return papers, error_message
        resp.raise_for_status()
        data = resp.json()
        for p in data.get('data', []):
            author = "; ".join([a.get('name','') for a in p.get('authors',[])])
            abstract_raw = p.get('abstract','')
            abstract = ' '.join(abstract_raw.split()) if abstract_raw else ''
            journal_info = p.get('journal')
            venue = p.get('venue') or p.get('publicationVenue', {}).get('name')
            journal_venue = venue if venue else (journal_info.get('name') if journal_info else "N/A")
            keywords_list = p.get('keywords', [])
            keywords_str = "; ".join(keywords_list) if keywords_list else ""
            doi = p.get('externalIds', {}).get('DOI', "")
            link_url = f"https://doi.org/{doi}" if doi else p.get('url','')
            title = p.get('title','')

            papers.append({
                # 移除 'source' 欄位，因為只有一個來源
                'title': title,
                'author': author,
                'year': p.get('year',''),
                'publication': journal_venue,
                'keywords': keywords_str,
                'abstract': abstract,
                'link': link_url
            })
    except requests.exceptions.Timeout: error_message = "連線 Semantic Scholar API 逾時。"
    except requests.exceptions.RequestException as e: error_message = f"Semantic Scholar API 請求錯誤: {e}"
    except Exception as e: error_message = f"處理 Semantic Scholar 資料時發生錯誤: {e}"
    return papers, error_message

# --- 移除 search_arxiv 和 search_pubmed 函數 ---
# def search_arxiv(...):
#     ...
# def search_pubmed(...):
#     ...


# --- 主程式流程 ---
st.divider()

# 冷卻狀態顯示
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
        search_term = " ".join(final_query_list) # 合併成單一查詢字串
        search_term_display = " & ".join(final_query_list)
        year_range_display = f" ({year_start}-{year_end})"

        # --- 簡化搜尋流程 ---
        with st.spinner(f"🔍 正在 Semantic Scholar 搜尋「{search_term_display}」{year_range_display}..."):
            # 直接呼叫 Semantic Scholar 函數
            results, error = search_semantic_scholar(search_term, year_start, year_end, max_results) # 使用 max_results

        if error:
            st.error(f"❌ {error}")
        elif not results:
            st.warning("⚠️ 找不到相關文獻")
        else:
            df_final = pd.DataFrame(results) # 不再需要去重

            st.success(f"✅ 成功找到 {len(df_final)} 筆文獻！")

            # --- 新增：產生摘要預覽 ---
            def create_snippet(text, length=150):
                if pd.isna(text) or text == "":
                    return ""
                text = str(text).replace("\n", " ") # 移除換行
                return text[:length] + "..." if len(text) > length else text

            df_final['abstract_snippet'] = df_final['abstract'].apply(create_snippet)

            # --- 更新：表格顯示 (移除 source 欄位) ---
            display_columns = ["title", "author", "year", "publication", "abstract_snippet"] # 移除 source
            st.dataframe(df_final[display_columns], use_container_width=True, height=400)

            # --- 匯出功能 ---
            st.sidebar.header("💾 匯出結果")
            # 確保匯出所有需要的欄位
            export_columns = ['title', 'author', 'year', 'publication', 'keywords', 'abstract', 'link']
            export_df = df_final[[col for col in export_columns if col in df_final.columns]]
            csv_data = export_df.to_csv(index=False, encoding='utf-8-sig')
            st.sidebar.download_button(
                label="📥 下載 CSV 檔案 (含完整摘要)",
                data=csv_data,
                file_name=f"semantic_scholar_{'_'.join(final_query_list)}_{year_start}-{year_end}_{time.strftime('%Y%m%d')}.csv", # 更新檔名
                mime="text/csv",
                use_container_width=True,
                type="primary"
            )

            # --- 顯示詳細資料與摘要 ---
            st.subheader("📄 文獻詳細資料與摘要")
            for i, paper in df_final.iterrows():
                # 移除 source 顯示
                expander_title = f"**{i+1}. {paper.get('title','N/A')}** ({paper.get('year','N/A')})"
                apa_citation = f"{paper.get('author','N/A')} ({paper.get('year','N/A')}). {paper.get('title','N/A')}. *{paper.get('publication','N/A')}*. {paper.get('link','#')}"

                with st.expander(expander_title, expanded=(i < 3)):
                    st.markdown(f"**作者:** {paper.get('author','N/A')}")
                    st.markdown(f"**發表於:** *{paper.get('publication','N/A')}*")
                    st.markdown(f"**連結:** {paper.get('link','#')}")

                    st.markdown("**摘要:**")
                    abstract = paper.get('abstract', '摘要未提供')
                    if abstract:
                        st.text_area(f"摘要_{i}", abstract, height=150, disabled=True, label_visibility="collapsed")
                    else:
                        st.caption("摘要未提供")

                    st.markdown("**APA 7 引用格式 (參考):**")
                    st.code(apa_citation, language='text')

# --- 側邊欄說明 ---
with st.sidebar:
    st.header("📖 使用說明")
    # 更新說明文字
    st.markdown(f"""
    ### ✨ 功能特色
    - 🌍 即時搜尋 **Semantic Scholar** 國際學術資料庫
    - 📚 提供 **15 個**常用商管關鍵字 (含中文)
    - ➕ 支援**複選**與**自訂**關鍵字 (AND 邏輯)
    - 📅 **年份範圍**篩選
    - 📄 顯示**摘要** (若 API 有提供)
    - 📊 表格化呈現結果 (含**摘要預覽**)
    - 💾 匯出 CSV 檔案 (含**完整**摘要)
    - 📄 提供 APA 格式範例

    ### ⚠️ 注意事項
    - 每次搜尋需間隔 **{COOLDOWN_SECONDS} 秒**。
    - 若遇 API 錯誤 (如 429)，會顯示提示。
    - Semantic Scholar 涵蓋多學科，建議使用精確關鍵字。
    """)
    st.divider()
    st.caption("Data retrieved via Semantic Scholar API.") # 更新來源

# 頁尾
st.divider()
st.caption("⚠️ 本工具僅供學術研究參考。")


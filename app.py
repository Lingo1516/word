import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime
import xml.etree.ElementTree as ET # ArXiv 和 PubMed 需要
import re # 用於清理摘要
import json # 用於處理 Gemini API 回應

# --- 頁面設定 ---
st.set_page_config(
    page_title="多平台學術文獻搜尋平台",
    page_icon="🚀",
    layout="wide"
)

st.title("🚀 多平台學術文獻搜尋平台")
st.markdown("同時搜尋 Semantic Scholar, arXiv, PubMed，提供摘要與標題中文翻譯，並整合去重結果。")

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

# --- 翻譯函數 (使用 Gemini API) ---
@st.cache_data(ttl=86400) # 快取翻譯結果一天
def translate_text(text_to_translate, context="abstract"):
    """使用 Gemini API 將英文文本翻譯成繁體中文"""
    if not text_to_translate or text_to_translate in ["摘要未提供", "N/A", ""]:
        return text_to_translate # 如果沒有內容，直接回傳

    api_key = "" # API Key 由 Canvas 環境提供
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={api_key}"

    # 根據翻譯內容調整提示
    if context == "title":
        prompt = f"Please translate the following English paper title into Traditional Chinese (zh-TW). Respond only with the translated title:\n\n{text_to_translate}"
    else: # 預設為摘要
        prompt = f"Please translate the following English abstract into Traditional Chinese (zh-TW). Respond only with the translated text:\n\n{text_to_translate}"

    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    headers = {'Content-Type': 'application/json'}
    max_retries = 3
    base_delay = 1

    for attempt in range(max_retries):
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=20)
            response.raise_for_status()
            result = response.json()
            if (result.get('candidates') and
                result['candidates'][0].get('content') and
                result['candidates'][0]['content'].get('parts') and
                result['candidates'][0]['content']['parts'][0].get('text')):
                translated_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
                # 簡單清理可能的 Markdown 或引號
                translated_text = translated_text.replace('"', '').replace("'", "").replace('*', '')
                return translated_text
            else:
                st.warning(f"翻譯 API ({context}) 回應格式異常: {result}")
                return f"翻譯失敗(格式錯誤) - {context}"
        except requests.exceptions.RequestException as e:
            st.warning(f"翻譯 API ({context}) 請求失敗 (嘗試 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(base_delay * (2 ** attempt)) # 指數退避
            else:
                return f"翻譯失敗(請求錯誤) - {context}"
        except Exception as e:
             st.warning(f"翻譯 API ({context}) 發生未知錯誤: {e}")
             return f"翻譯失敗(未知錯誤) - {context}"
    return f"翻譯失敗(重試超限) - {context}" # 所有重試失敗


# --- 使用者輸入介面 ---
st.subheader("請設定您的搜尋條件")
# ... (使用者輸入介面代碼保持不變) ...
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
    max_results_per_source = st.slider("📈 **每個來源**最多顯示幾筆", min_value=5, max_value=30, value=10, step=5)


# --- API 搜尋函數 ---
# (Semantic Scholar, arXiv, PubMed 的搜尋函數保持不變，僅在返回的字典中增加原始 abstract 和 title 欄位)

# Semantic Scholar API
@st.cache_data(ttl=3600)
def search_semantic_scholar(query, start_year, end_year, limit=10):
    # ... (省略 API 呼叫邏輯) ...
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
            title_en = p.get('title','') # 儲存原始英文標題

            papers.append({
                'source': 'Semantic Scholar',
                'title_en': title_en, # 儲存英文標題
                'author': author,
                'year': p.get('year',''),
                'publication': journal_venue,
                'keywords': keywords_str,
                'abstract_en': abstract, # 儲存英文摘要
                'link': link_url
            })
    # ... (省略錯誤處理邏輯) ...
    except requests.exceptions.Timeout: error_message = "連線 Semantic Scholar API 逾時。"
    except requests.exceptions.RequestException as e: error_message = f"Semantic Scholar API 請求錯誤: {e}"
    except Exception as e: error_message = f"處理 Semantic Scholar 資料時發生錯誤: {e}"
    return papers, error_message


# arXiv API
@st.cache_data(ttl=3600)
def search_arxiv(query, start_year, end_year, max_results=10):
    # ... (省略 API 呼叫邏輯) ...
    base_url = 'http://export.arxiv.org/api/query?'
    search_query = f'all:"{query}"'
    params = f'search_query={search_query}&sortBy=submittedDate&sortOrder=descending&start=0&max_results={max_results * 5}'
    papers = []
    error_message = None
    try:
        resp = requests.get(base_url + params, timeout=20)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        ns = {'arxiv': 'http://www.w3.org/2005/Atom'}
        count = 0
        for entry in root.findall('arxiv:entry', ns):
            published_str = entry.find('arxiv:published', ns).text
            year_match = re.search(r'^(\d{4})', published_str)
            if year_match:
                published_year = int(year_match.group(1))
                if start_year <= published_year <= end_year:
                    title_en = entry.find('arxiv:title', ns).text.strip() # 儲存原始英文標題
                    authors = entry.findall('arxiv:author/arxiv:name', ns)
                    author_names = "; ".join([a.text for a in authors])
                    summary = entry.find('arxiv:summary', ns).text.strip()
                    link_pdf_tag = entry.find('arxiv:link[@title="pdf"]', ns)
                    link_abs_tag = entry.find('arxiv:link[@rel="alternate"]', ns)
                    link_url = link_pdf_tag.attrib.get('href','') if link_pdf_tag is not None else (link_abs_tag.attrib.get('href','') if link_abs_tag is not None else '')

                    papers.append({
                        'source': 'arXiv',
                        'title_en': title_en, # 儲存英文標題
                        'author': author_names,
                        'year': published_year,
                        'publication': 'arXiv Preprint',
                        'keywords': '',
                        'abstract_en': summary, # 儲存英文摘要
                        'link': link_url
                    })
                    count += 1
                    if count >= max_results: break
    # ... (省略錯誤處理邏輯) ...
    except requests.exceptions.Timeout: error_message = "連線 arXiv API 逾時。"
    except requests.exceptions.RequestException as e: error_message = f"arXiv API 請求錯誤: {e}"
    except ET.ParseError: error_message = "解析 arXiv 回應時發生錯誤。"
    except Exception as e: error_message = f"處理 arXiv 資料時發生錯誤: {e}"
    return papers, error_message

# PubMed API
@st.cache_data(ttl=3600)
def search_pubmed(query, start_year, end_year, max_results=10):
    # ... (省略 API 呼叫邏輯) ...
    base_search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    base_fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    term_with_year = f"{query} AND (\"{start_year}\"[Date - Publication] : \"{end_year}\"[Date - Publication])"
    params_search = {'db': 'pubmed', 'term': term_with_year, 'retmax': max_results, 'retmode': 'json', 'sort': 'relevance'}
    papers = []
    error_message = None
    try:
        search_resp = requests.get(base_search_url, params=params_search, timeout=20)
        search_resp.raise_for_status()
        id_list = search_resp.json().get('esearchresult', {}).get('idlist', [])
        if id_list:
            ids = ",".join(id_list)
            params_fetch = {'db': 'pubmed', 'id': ids, 'retmode': 'xml'}
            fetch_resp = requests.get(base_fetch_url, params=params_fetch, timeout=30)
            fetch_resp.raise_for_status()
            root = ET.fromstring(fetch_resp.content)
            for article in root.findall(".//PubmedArticle"):
                title = article.find(".//ArticleTitle")
                title_en = title.text if title is not None else '' # 儲存原始英文標題
                abstract_parts = article.findall(".//AbstractText")
                abstract_text = "\n".join([part.text for part in abstract_parts if part.text]) if abstract_parts else ''
                authors = article.findall(".//Author")
                author_names = []
                for a in authors:
                    last = a.find("LastName"); first = a.find("ForeName"); initials = a.find("Initials")
                    name = ""
                    if last is not None and last.text: name += last.text
                    if first is not None and first.text: name += ", " + first.text
                    elif initials is not None and initials.text: name += ", " + initials.text
                    if name.strip(): author_names.append(name.strip())
                year = article.find(".//PubDate/Year")
                medline_date = article.find(".//PubDate/MedlineDate")
                year_text = year.text if year is not None else (medline_date.text[:4] if medline_date is not None else '')
                journal = article.find(".//Title")
                journal_text = journal.text if journal is not None else ''
                pmid = article.find(".//PMID")
                link_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid.text}/" if pmid is not None else ''

                papers.append({
                    'source': 'PubMed',
                    'title_en': title_en, # 儲存英文標題
                    'author': "; ".join(author_names),
                    'year': year_text,
                    'publication': journal_text,
                    'keywords': '',
                    'abstract_en': abstract_text, # 儲存英文摘要
                    'link': link_url
                })
    # ... (省略錯誤處理邏輯) ...
    except requests.exceptions.Timeout: error_message = "連線 PubMed API 逾時。"
    except requests.exceptions.RequestException as e: error_message = f"PubMed API 請求錯誤: {e}"
    except ET.ParseError: error_message = "解析 PubMed 回應時發生錯誤。"
    except Exception as e: error_message = f"處理 PubMed 資料時發生錯誤: {e}"
    return papers, error_message


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
        search_term = " ".join(final_query_list)
        search_term_display = " & ".join(final_query_list)
        year_range_display = f" ({year_start}-{year_end})"

        all_results_raw = []
        errors = []
        api_funcs = {
            "Semantic Scholar": search_semantic_scholar,
            "arXiv": search_arxiv,
            "PubMed": search_pubmed
        }
        api_progress = {}

        # 使用 st.progress 來顯示進度
        progress_bar = st.progress(0.0)
        progress_text = st.empty()
        total_apis = len(api_funcs)

        for i, (api_name, api_func) in enumerate(api_funcs.items()):
             progress_text.text(f"🔍 正在 {api_name} 搜尋...")
             results, error = api_func(search_term, year_start, year_end, max_results_per_source)
             if error: errors.append(error)
             all_results_raw.extend(results)
             progress_bar.progress((i + 1) / total_apis) # 更新進度條

        progress_text.text("🔄 正在整合與翻譯結果...") # 更新狀態

        if not all_results_raw:
             progress_text.empty() # 清空進度提示
             progress_bar.empty()
             st.warning("⚠️ 在所有平台都找不到相關文獻")
             if errors: st.error("⚠️ 部分 API 搜尋時發生錯誤：\n" + "\n".join([f"- {e}" for e in errors]))
        else:
            df_raw = pd.DataFrame(all_results_raw)
            # --- 去重 ---
            df_raw['source_priority'] = df_raw['source'].map({'Semantic Scholar': 1, 'arXiv': 2, 'PubMed': 3}).fillna(4)
            df_raw['title_lower'] = df_raw['title_en'].str.lower().str.strip() # 使用英文標題去重
            df_unique = df_raw.sort_values('source_priority').drop_duplicates(subset=['title_lower'], keep='first').reset_index(drop=True)

            # --- 翻譯標題與摘要 ---
            translated_data = []
            total_to_translate = len(df_unique)
            for i, paper in enumerate(df_unique.to_dict('records')):
                progress_percentage = (i + 1) / total_to_translate
                progress_text.text(f"翻譯中... ({i+1}/{total_to_translate}) - {paper['title_en'][:30]}...") # 顯示進度
                # 執行翻譯
                title_zh = translate_text(paper['title_en'], context="title")
                abstract_zh = translate_text(paper['abstract_en'], context="abstract")
                # 將翻譯結果加回字典
                paper['title_zh'] = title_zh
                paper['abstract_zh'] = abstract_zh
                translated_data.append(paper)
                progress_bar.progress(progress_percentage) # 更新進度條

            df_final = pd.DataFrame(translated_data)
            df_final = df_final.drop(columns=['source_priority', 'title_lower']) # 移除輔助欄位

            progress_text.empty() # 清空進度提示
            progress_bar.empty()

            st.success(f"✅ 成功找到並翻譯 {len(df_final)} 筆文獻！")

            # --- 更新：表格顯示中英文標題 ---
            display_columns = ["source", "title_en", "title_zh", "author", "year", "publication"]
            st.dataframe(df_final[display_columns], use_container_width=True, height=400)

            # --- 匯出功能 (包含翻譯) ---
            st.sidebar.header("💾 匯出結果")
            # 更新：匯出所有欄位
            csv_data = df_final.to_csv(index=False, encoding='utf-8-sig')
            st.sidebar.download_button(
                label="📥 下載 CSV 檔案 (含翻譯)",
                data=csv_data,
                file_name=f"multi_api_search_{'_'.join(final_query_list)}_{year_start}-{year_end}_{time.strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
                type="primary"
            )

            # --- 顯示詳細資料與摘要 (包含翻譯) ---
            st.subheader("📄 文獻詳細資料、摘要與翻譯")
            for i, paper in df_final.iterrows():
                # 更新：顯示中英文標題
                expander_title = f"**{i+1}. {paper.get('title_en','N/A')}** ({paper.get('year','N/A')}) - _{paper.get('source','Unknown')}_"
                if paper.get('title_zh') and "翻譯失敗" not in paper['title_zh']:
                     expander_title += f"\n   * {paper['title_zh']}" # 在標題下方顯示中文

                apa_citation = f"{paper.get('author','N/A')} ({paper.get('year','N/A')}). {paper.get('title_en','N/A')}. *{paper.get('publication','N/A')}*. {paper.get('link','#')}"

                with st.expander(expander_title, expanded=(i < 3)): # 預設展開前 3 筆
                    st.markdown(f"**作者:** {paper.get('author','N/A')}")
                    st.markdown(f"**發表於:** *{paper.get('publication','N/A')}*")
                    st.markdown(f"**連結:** {paper.get('link','#')}")

                    st.markdown("**英文摘要:**")
                    abstract_en = paper.get('abstract_en', '摘要未提供')
                    if abstract_en:
                        st.text_area(f"摘要_en_{i}", abstract_en, height=150, disabled=True, label_visibility="collapsed")
                    else:
                        st.caption("摘要未提供")

                    st.markdown("**中文翻譯:**")
                    abstract_zh = paper.get('abstract_zh', '摘要未提供')
                    # 檢查是否翻譯失敗
                    if abstract_zh and "翻譯失敗" not in abstract_zh:
                        st.text_area(f"摘要_zh_{i}", abstract_zh, height=150, disabled=True, label_visibility="collapsed")
                    elif abstract_zh and "翻譯失敗" in abstract_zh:
                         st.warning(f"摘要翻譯失敗 ({abstract_zh.split('-')[-1].strip()})") # 顯示失敗原因
                    else:
                        st.caption("摘要未提供或無需翻譯")


                    st.markdown("**APA 7 引用格式 (參考):**")
                    st.code(apa_citation, language='text')

# --- 側邊欄說明 ---
with st.sidebar:
    st.header("📖 使用說明")
    # 更新說明文字
    st.markdown(f"""
    ### ✨ 功能特色
    - 🌍 同時搜尋 **Semantic Scholar, arXiv, PubMed**
    - 📚 提供 **15 個**常用商管關鍵字 (含中文)
    - ➕ 支援**複選**與**自訂**關鍵字 (AND 邏輯)
    - 📅 **年份範圍**篩選
    - 📄 顯示**摘要**與**中文翻譯** (若可用)
    - 📊 表格化呈現合併去重結果 (含中文標題)
    - 💾 匯出 CSV 檔案 (含翻譯)
    - 📄 提供 APA 格式範例

    ### ⚠️ 注意事項
    - 每次搜尋需間隔 **{COOLDOWN_SECONDS} 秒**。
    - 機器翻譯僅供參考，且需額外呼叫 API。
    - 若遇 API 錯誤 (如 429)，會顯示提示。
    - PubMed 主要收錄生醫文獻。
    - arXiv 主要收錄 STEM 預印本。
    """)
    st.divider()
    st.caption("Data retrieved via multiple APIs. Translations by Gemini.")

# 頁尾
st.divider()
st.caption("⚠️ 本工具僅供學術研究參考。")


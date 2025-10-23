import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime
import xml.etree.ElementTree as ET # ArXiv 和 PubMed 需要
import re # 用於清理摘要

# --- 頁面設定 ---
st.set_page_config(
    page_title="多平台學術文獻搜尋平台",
    page_icon="🚀",
    layout="wide"
)

st.title("🚀 多平台學術文獻搜尋平台")
st.markdown("同時搜尋 Semantic Scholar, arXiv, PubMed，並整合去重結果。")

# --- 設定冷卻時間（秒） ---
COOLDOWN_SECONDS = 5 # 稍微縮短冷卻，因為是多個 API 分散請求
if 'last_search_time' not in st.session_state:
    st.session_state.last_search_time = 0

# --- 預設商管關鍵字（包含中英文） ---
BUSINESS_KEYWORDS_DICT = [
    # ... (省略之前的關鍵字列表) ...
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
    # 調整最大值，因為是多個來源合併
    max_results_per_source = st.slider("📈 **每個來源**最多顯示幾筆", min_value=5, max_value=30, value=10, step=5)


# --- API 搜尋函數 (整合您的版本) ---

# Semantic Scholar API
@st.cache_data(ttl=3600)
def search_semantic_scholar(query, start_year, end_year, limit=10):
    # ... (使用您提供的 Semantic Scholar 邏輯，並加入年份過濾) ...
    base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
    year_filter = f"{start_year}-{end_year}"
    params = {
        'query': query, 'year': year_filter, 'limit': limit,
        'fields': 'title,authors,year,abstract,venue,publicationVenue,journal,externalIds,url,keywords' # 嘗試獲取 keywords
    }
    headers = {'User-Agent': 'StreamlitApp/1.0 (mailto:streamlit.app.user@example.com)'}
    papers = []
    error_message = None
    try:
        resp = requests.get(base_url, params=params, headers=headers, timeout=20)
        if resp.status_code == 429:
             retry_after = resp.headers.get("Retry-After", COOLDOWN_SECONDS)
             error_message = f"Semantic Scholar API 請求過頻 (429)，建議等待 {retry_after} 秒。"
             return papers, error_message # 返回空列表和錯誤訊息
        resp.raise_for_status()
        data = resp.json()
        for p in data.get('data', []):
            author = "; ".join([a.get('name','') for a in p.get('authors',[])])
            # 清理摘要
            abstract_raw = p.get('abstract','')
            abstract = ' '.join(abstract_raw.split()) if abstract_raw else ''
            # 期刊/會議資訊
            journal_info = p.get('journal')
            venue = p.get('venue') or p.get('publicationVenue', {}).get('name')
            if journal_info and journal_info.get('name'):
                journal_venue = journal_info.get('name')
            elif venue:
                 journal_venue = venue
            else:
                journal_venue = "N/A"
            # 關鍵字
            keywords_list = p.get('keywords', [])
            keywords_str = "; ".join(keywords_list) if keywords_list else ""
            # DOI 和連結
            doi = p.get('externalIds', {}).get('DOI', "")
            link_url = f"https://doi.org/{doi}" if doi else p.get('url','')

            papers.append({
                'source': 'Semantic Scholar', # 標註來源
                'title': p.get('title',''),
                'author': author,
                'year': p.get('year',''),
                'publication': journal_venue,
                'keywords': keywords_str,
                'abstract': abstract,
                'link': link_url
            })
    except requests.exceptions.Timeout:
        error_message = "連線 Semantic Scholar API 逾時。"
    except requests.exceptions.RequestException as e:
        error_message = f"Semantic Scholar API 請求錯誤: {e}"
    except Exception as e:
        error_message = f"處理 Semantic Scholar 資料時發生錯誤: {e}"
    return papers, error_message


# arXiv API
@st.cache_data(ttl=3600)
def search_arxiv(query, start_year, end_year, max_results=10):
    # ... (使用您提供的 arXiv 邏輯，加入年份過濾) ...
    base_url = 'http://export.arxiv.org/api/query?'
    # arXiv 的 query 格式比較特殊，需要用欄位指定
    # 我們這裡簡單用 all: 包含關鍵字，並在後面用 Python 過濾年份
    search_query = f'all:"{query}"' # 用引號包裹多詞關鍵字
    params = f'search_query={search_query}&sortBy=submittedDate&sortOrder=descending&start=0&max_results={max_results * 5}' # 多抓幾筆來過濾年份
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
            year_match = re.search(r'^(\d{4})', published_str) # 提取年份
            if year_match:
                published_year = int(year_match.group(1))
                # 進行年份過濾
                if start_year <= published_year <= end_year:
                    title = entry.find('arxiv:title', ns).text.strip() # 清理標題空白
                    authors = entry.findall('arxiv:author/arxiv:name', ns)
                    author_names = "; ".join([a.text for a in authors])
                    summary = entry.find('arxiv:summary', ns).text.strip() # 清理摘要空白
                    link_pdf_tag = entry.find('arxiv:link[@title="pdf"]', ns) # 優先找 PDF 連結
                    link_abs_tag = entry.find('arxiv:link[@rel="alternate"]', ns) # 備用找摘要頁連結
                    link_url = link_pdf_tag.attrib.get('href','') if link_pdf_tag is not None else (link_abs_tag.attrib.get('href','') if link_abs_tag is not None else '')

                    papers.append({
                        'source': 'arXiv', # 標註來源
                        'title': title,
                        'author': author_names,
                        'year': published_year,
                        'publication': 'arXiv Preprint', # arXiv 都是預印本
                        'keywords': '', # arXiv API 不直接提供關鍵字
                        'abstract': summary,
                        'link': link_url
                    })
                    count += 1
                    if count >= max_results: # 達到需要的筆數就停止
                        break
    except requests.exceptions.Timeout:
        error_message = "連線 arXiv API 逾時。"
    except requests.exceptions.RequestException as e:
        error_message = f"arXiv API 請求錯誤: {e}"
    except ET.ParseError:
         error_message = "解析 arXiv 回應時發生錯誤。"
    except Exception as e:
        error_message = f"處理 arXiv 資料時發生錯誤: {e}"
    return papers, error_message

# PubMed API
@st.cache_data(ttl=3600)
def search_pubmed(query, start_year, end_year, max_results=10):
    # ... (使用您提供的 PubMed 邏輯，加入年份過濾) ...
    base_search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    base_fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    # 加入年份範圍到搜尋詞
    term_with_year = f"{query} AND (\"{start_year}\"[Date - Publication] : \"{end_year}\"[Date - Publication])"
    params_search = {
        'db': 'pubmed', 'term': term_with_year, 'retmax': max_results,
        'retmode': 'json', 'sort': 'relevance' # 按相關性排序
    }
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
                title_text = title.text if title is not None else ''
                abstract = article.find(".//AbstractText")
                # PubMed 可能有多個 AbstractText，合併它們
                abstract_parts = article.findall(".//AbstractText")
                abstract_text = "\n".join([part.text for part in abstract_parts if part.text]) if abstract_parts else ''
                authors = article.findall(".//Author")
                author_names = []
                for a in authors:
                    last = a.find("LastName")
                    first = a.find("ForeName") # PubMed 有時用 ForeName
                    initials = a.find("Initials") # 有時只有縮寫
                    name = ""
                    if last is not None and last.text: name += last.text
                    if first is not None and first.text: name += ", " + first.text
                    elif initials is not None and initials.text: name += ", " + initials.text # 備用縮寫
                    if name.strip(): author_names.append(name.strip())

                year = article.find(".//PubDate/Year")
                medline_date = article.find(".//PubDate/MedlineDate") # 備用日期格式
                year_text = year.text if year is not None else (medline_date.text[:4] if medline_date is not None else '')

                journal = article.find(".//Title") # 期刊名稱在 Title
                journal_text = journal.text if journal is not None else ''

                # PubMed ID 作為連結基礎
                pmid = article.find(".//PMID")
                link_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid.text}/" if pmid is not None else ''

                papers.append({
                    'source': 'PubMed', # 標註來源
                    'title': title_text,
                    'author': "; ".join(author_names),
                    'year': year_text,
                    'publication': journal_text,
                    'keywords': '', # PubMed API 不易直接獲取 Mesh Terms，暫時留空
                    'abstract': abstract_text,
                    'link': link_url
                })
    except requests.exceptions.Timeout:
        error_message = "連線 PubMed API 逾時。"
    except requests.exceptions.RequestException as e:
        error_message = f"PubMed API 請求錯誤: {e}"
    except ET.ParseError:
         error_message = "解析 PubMed 回應時發生錯誤。"
    except Exception as e:
        error_message = f"處理 PubMed 資料時發生錯誤: {e}"
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
        search_term = " ".join(final_query_list) # 合併成單一查詢字串給各 API
        search_term_display = " & ".join(final_query_list)
        year_range_display = f" ({year_start}-{year_end})"

        all_results = []
        errors = []

        with st.spinner(f"🔍 正在 Semantic Scholar 搜尋「{search_term_display}」{year_range_display}..."):
            ss_results, ss_error = search_semantic_scholar(search_term, year_start, year_end, max_results_per_source)
            if ss_error: errors.append(ss_error)
            all_results.extend(ss_results)

        with st.spinner(f"⏳ 正在 arXiv 搜尋「{search_term_display}」{year_range_display}..."):
            arxiv_results, arxiv_error = search_arxiv(search_term, year_start, year_end, max_results_per_source)
            if arxiv_error: errors.append(arxiv_error)
            all_results.extend(arxiv_results)

        with st.spinner(f"⚕️ 正在 PubMed 搜尋「{search_term_display}」{year_range_display}..."):
            pubmed_results, pubmed_error = search_pubmed(search_term, year_start, year_end, max_results_per_source)
            if pubmed_error: errors.append(pubmed_error)
            all_results.extend(pubmed_results)

        # 顯示 API 錯誤訊息 (如果有的話)
        if errors:
            st.error("⚠️ 部分 API 搜尋時發生錯誤：\n" + "\n".join([f"- {e}" for e in errors]))

        if not all_results:
            st.warning("⚠️ 在所有平台都找不到相關文獻")
        else:
            df_raw = pd.DataFrame(all_results)
            # --- 去重 ---
            # 優先保留 Semantic Scholar 的結果 (通常資訊較全)
            df_raw['source_priority'] = df_raw['source'].map({'Semantic Scholar': 1, 'arXiv': 2, 'PubMed': 3}).fillna(4)
            # 根據標題(小寫)去重，保留 priority 最小的
            df_raw['title_lower'] = df_raw['title'].str.lower().str.strip()
            df_final = df_raw.sort_values('source_priority').drop_duplicates(subset=['title_lower'], keep='first').reset_index(drop=True)
            # 移除輔助欄位
            df_final = df_final.drop(columns=['source_priority', 'title_lower'])

            st.success(f"✅ 成功合併並去重後找到 {len(df_final)} 筆文獻！")

            display_columns = ["source", "title", "author", "year", "publication"]
            st.dataframe(df_final[display_columns], use_container_width=True, height=400)

            # --- 匯出功能 ---
            st.sidebar.header("💾 匯出結果")
            csv_data = df_final.to_csv(index=False, encoding='utf-8-sig')
            st.sidebar.download_button(
                label="📥 下載 CSV 檔案 (含摘要)",
                data=csv_data,
                file_name=f"multi_api_search_{'_'.join(final_query_list)}_{year_start}-{year_end}_{time.strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
                type="primary"
            )

            # --- 顯示詳細資料與摘要 ---
            st.subheader("📄 文獻詳細資料與摘要")
            for i, paper in df_final.iterrows():
                # 簡化 APA，因為來源多樣
                apa_citation = f"{paper.get('author','N/A')} ({paper.get('year','N/A')}). {paper.get('title','N/A')}. *{paper.get('publication','N/A')}*. {paper.get('link','#')}"
                with st.expander(f"**{i+1}. {paper.get('title','N/A')}** ({paper.get('year','N/A')}) - _{paper.get('source','Unknown')}_", expanded=(i < 5)):
                    st.markdown(f"**作者:** {paper.get('author','N/A')}")
                    st.markdown(f"**發表於:** *{paper.get('publication','N/A')}*")
                    st.markdown(f"**連結:** {paper.get('link','#')}")

                    st.markdown("**摘要:**")
                    abstract_text = paper.get('abstract', '摘要未提供')
                    if abstract_text:
                        st.text_area(f"摘要_{i}", abstract_text, height=150, disabled=True, label_visibility="collapsed")
                    else:
                        st.caption("摘要未提供")

                    st.markdown("**APA 7 引用格式 (參考):**")
                    st.code(apa_citation, language='text')

# --- 側邊欄說明 ---
with st.sidebar:
    st.header("📖 使用說明")
    st.markdown(f"""
    ### ✨ 功能特色
    - 🌍 同時搜尋 **Semantic Scholar, arXiv, PubMed**
    - 📚 提供 **15 個**常用商管關鍵字 (含中文)
    - ➕ 支援**複選**與**自訂**關鍵字 (AND 邏輯)
    - 📅 **年份範圍**篩選
    - 📄 顯示**摘要** (若 API 有提供)
    - 📊 表格化呈現合併去重結果
    - 💾 匯出 CSV 檔案 (含摘要)
    - 📄 提供 APA 格式範例

    ### ⚠️ 注意事項
    - 每次搜尋需間隔 **{COOLDOWN_SECONDS} 秒**。
    - 若遇 API 錯誤 (如 429)，會顯示提示。
    - PubMed 主要收錄生醫文獻。
    - arXiv 主要收錄 STEM 預印本。
    """)
    st.divider()
    st.caption("Data retrieved via multiple APIs.")

# 頁尾
st.divider()
st.caption("⚠️ 本工具僅供學術研究參考。")


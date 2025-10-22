import streamlit as st
import requests  # 用於 API 請求
import re        # 用於清理 HTML 標籤
from bs4 import BeautifulSoup # 新增：用於網頁爬蟲

# ----------------------------------------------------------------------
# 區塊 1：API 查詢函式 (CrossRef)
# ----------------------------------------------------------------------

def clean_html(raw_html):
    """移除 HTML 標籤"""
    cleantext = re.sub(r'<[^>]+>', '', raw_html)
    return cleantext

@st.cache_data(show_spinner=False)
def fetch_from_crossref(doi):
    """(方法 1) 嘗試從 CrossRef API 擷取摘要"""
    try:
        doi_id = doi.split('doi.org/')[-1]
        url = f"https://api.crossref.org/works/{doi_id}"
        headers = {'Accept': 'application/json'}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            message = data.get('message', {})
            title = message.get('title', ['[標題不可用]'])[0]
            abstract = message.get('abstract', '[摘要不可用]')
            cleaned_abstract = clean_html(abstract)
            
            # 如果摘要不是有效的，也視為失敗
            if cleaned_abstract.startswith('['):
                return None, None
                
            return title, cleaned_abstract
        else:
            return None, None # 404 或其他錯誤，代表 CrossRef 找不到
            
    except Exception:
        return None, None # 網路錯誤等

# ----------------------------------------------------------------------
# 區塊 2：網頁爬蟲函式 (適用華藝 Airiti 等)
# ----------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def scrape_from_doi_website(doi):
    """(方法 2) 模擬瀏覽器，直接爬取 DOI 轉址後的網頁"""
    try:
        doi_url = f"https://doi.org/{doi.split('doi.org/')[-1]}"
        
        # 模擬瀏覽器發出請求
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # requests 會自動跟隨轉址 (例如從 doi.org 轉到 airitilibrary.com)
        response = requests.get(doi_url, headers=headers, timeout=15)
        response.raise_for_status() # 確保請求成功
        
        # 使用 BeautifulSoup 解析 HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # --- 嘗試擷取標題 ---
        # 優先找 'DC.Title' (華藝常用)
        title_tag = soup.find("meta", attrs={"name": "DC.Title"})
        if not title_tag:
             # 備案：找 'og:title'
            title_tag = soup.find("meta", property="og:title")
        if not title_tag:
            # 備案：找 HTML 的 <title>
            title_tag = soup.find("title")
            
        title = title_tag.get('content', '標題抓取失敗').strip() if title_tag else soup.title.string.strip()
        
        # --- 嘗試擷取摘要 ---
        # 優先找 'DC.Description' (華藝常用)
        abstract_tag = soup.find("meta", attrs={"name": "DC.Description"})
        if not abstract_tag:
            # 備案：找 'description'
            abstract_tag = soup.find("meta", attrs={"name": "description"})
        if not abstract_tag:
             # 備案：找 'og:description'
            abstract_tag = soup.find("meta", property="og:description")

        if abstract_tag:
            abstract = abstract_tag.get('content', '[摘要抓取失敗]').strip()
            # 避免抓到太短的描述
            if len(abstract) < 50:
                 return title, "[摘要內容過短，可能抓取錯誤]"
            return title, abstract
        else:
            return title, "[無法在HTML中定位到摘要]"
            
    except requests.exceptions.RequestException as e:
        return None, f"爬蟲網路錯誤：{e}"
    except Exception as e:
        return None, f"爬蟲解析錯誤：{e}"

# ----------------------------------------------------------------------
# 區塊 3：Streamlit 介面主體 (混合模式)
# ----------------------------------------------------------------------

def main():
    st.set_page_config(layout="wide", page_title="即時文獻摘要查詢")
    
    st.title("📚 即時文獻摘要查詢 (Live DOI Fetcher)")
    st.markdown("""
    請貼上 DOI 列表。系統會優先使用 CrossRef API 查詢；若失敗，將自動啟動網頁爬蟲模式。
    """)

    with st.container(border=True):
        
        doi_input = st.text_area(
            "請輸入 DOI (Digital Object Identifiers)，每行一個：",
            placeholder="10.6342/NTU202100154 (試試這個，會啟動爬蟲)\n10.1038/nature12373 (試試這個，會使用API)"
        )
        
        if st.button("🚀 開始擷取摘要", use_container_width=True, type="primary"):
            if not doi_input:
                st.warning("請輸入至少一個 DOI。")
            else:
                dois = [doi.strip() for doi in doi_input.split('\n') if doi.strip()]
                
                with st.spinner(f"正在擷取 {len(dois)} 篇文獻摘要..."):
                    for doi in dois:
                        
                        # 【混合模式邏輯】
                        # 1. 優先嘗試 API (方法 1)
                        title, abstract = fetch_from_crossref(doi)
                        
                        method = "API"
                        
                        # 2. 如果 API 失敗，啟動爬蟲 (方法 2)
                        if title is None:
                            title, abstract = scrape_from_doi_website(doi)
                            method = "爬蟲" # 標記為爬蟲
                        
                        # 3. 顯示結果
                        if title is None and abstract is None:
                            # 兩種方法都徹底失敗
                            st.error(f"**DOI: {doi}**\n[查詢失敗] CrossRef API 和網頁爬蟲均無法取得資料。")
                        else:
                            # 至少有一種方法成功了
                            with st.expander(f"**{title}** (DOI: {doi}) [查詢方式: {method}]", expanded=False):
                                if abstract.startswith('[') or '錯誤' in abstract:
                                    st.error(abstract) # 顯示爬蟲或API的錯誤訊息
                                else:
                                    st.write(abstract) # 顯示摘要
                                    
                    st.success("全部擷取完畢！")
                    
if __name__ == "__main__":
    main()

import streamlit as st
import requests  # 用於 API 請求
import re        # 用於清理 HTML 標籤 和 擷取年份
from bs4 import BeautifulSoup # 用於網頁爬蟲
import pandas as pd # 新增：用於建立表格

# ----------------------------------------------------------------------
# 區塊 1：API 查詢函式 (CrossRef) - 已升級
# ----------------------------------------------------------------------

def clean_html(raw_html):
    """移除 HTML 標籤"""
    cleantext = re.sub(r'<[^>]+>', '', raw_html)
    return cleantext

@st.cache_data(show_spinner=False)
def fetch_from_crossref(doi):
    """(方法 1) 嘗試從 CrossRef API 擷取摘要、作者、年份"""
    try:
        doi_id = doi.split('doi.org/')[-1]
        url = f"https://api.crossref.org/works/{doi_id}"
        headers = {'Accept': 'application/json'}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            message = data.get('message', {})
            
            # 1. 取得標題
            title = message.get('title', ['[標題不可用]'])[0]
            
            # 2. 取得摘要
            abstract = clean_html(message.get('abstract', '[摘要不可用]'))
            
            # 3. 取得作者
            author_list = message.get('author', [])
            if author_list:
                authors = ', '.join([f"{a.get('given', '')} {a.get('family', '')}".strip() for a in author_list])
            else:
                authors = '[作者抓取失敗]'

            # 4. 取得年份
            date_parts = message.get('created', {}).get('date-parts', [[None]])[0]
            year = date_parts[0] if (date_parts and date_parts[0]) else '[年份抓取失敗]'
            
            # 如果摘要不是有效的，也視為失敗
            if abstract.startswith('['):
                return None, None, None, None
                
            return title, abstract, authors, year
        else:
            return None, None, None, None # 404 或其他錯誤
            
    except Exception:
        return None, None, None, None # 網路錯誤等

# ----------------------------------------------------------------------
# 區塊 2：網頁爬蟲函式 (適用華藝 Airiti 等) - 已升級
# ----------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def scrape_from_doi_website(doi):
    """(方法 2) 模擬瀏覽器，爬取 DOI 轉址後的網頁 (標題, 摘要, 作者, 年份)"""
    try:
        doi_url = f"https://doi.org/{doi.split('doi.org/')[-1]}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(doi_url, headers=headers, timeout=15)
        response.raise_for_status() # 確保請求成功
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # --- 1. 嘗試擷取標題 ---
        title_tag = soup.find("meta", attrs={"name": "DC.Title"})
        if not title_tag: title_tag = soup.find("meta", property="og:title")
        title = title_tag.get('content', '標題抓取失敗').strip() if title_tag else (soup.title.string.strip() if soup.title else '標題抓取失敗')
        
        # --- 2. 嘗試擷取摘要 ---
        abstract_tag = soup.find("meta", attrs={"name": "DC.Description"})
        if not abstract_tag: abstract_tag = soup.find("meta", property="og:description")
        abstract = abstract_tag.get('content', '[摘要抓取失敗]').strip() if abstract_tag else '[無法在HTML中定位到摘要]'
        
        # --- 3. 嘗試擷取作者 ---
        author_tags = soup.find_all("meta", attrs={"name": "DC.Creator"})
        if not author_tags: author_tags = soup.find_all("meta", attrs={"name": "citation_author"})
        if author_tags:
            authors = ', '.join([tag.get('content', '').strip() for tag in author_tags])
        else:
            authors = '[作者抓取失敗]'

        # --- 4. 嘗試擷取年份 ---
        year_tag = soup.find("meta", attrs={"name": "DC.Date"})
        if not year_tag: year_tag = soup.find("meta", attrs={"name": "citation_publication_date"})
        if year_tag:
            date_str = year_tag.get('content', '').strip()
            # 使用正則表達式從日期字串中抓取四位數年份 (例如 "2021/07/01" 或 "2021")
            match = re.search(r'\b(19[5-9]\d|20[0-4]\d|2050)\b', date_str) # <--- 完整、正確的程式碼在這裡
            year = match.group(0) if match else date_str
        else:
            year = '[年份抓取失敗]'
            
        return title, abstract, authors, year
            
    except requests.exceptions.RequestException as e:
        return None, f"爬蟲網路錯誤：{e}", None, None
    except Exception as e:
        return None, f"爬蟲解析錯誤：{e}", None, None

# ----------------------------------------------------------------------
# 區塊 3：Streamlit 介面主體 (表格生成模式)
# ----------------------------------------------------------------------

def main():
    st.set_page_config(layout="wide", page_title="即時文獻摘要查詢")
    
    st.title("📚 即時文獻摘要查詢 (Live DOI Fetcher)")
    st.markdown("""
    請貼上 DOI 列表。系統將自動擷取**作者、年份、標題、摘要**，並彙整成表格。
    """)

    with st.container(border=True):
        
        doi_input = st.text_area(
            "請輸入 DOI (Digital Object Identifiers)，每行一個：",
            placeholder="10.6342/NTU202100154 (試試這個，會啟動爬蟲)\n10.1038/nature12373 (試試這個，會使用API)"
        )
        
        if st.button("🚀 開始擷取並製成表格", use_container_width=True, type="primary"):
            if not doi_input:
                st.warning("請輸入至少一個 DOI。")
            else:
                dois = [doi.strip() for doi in doi_input.split('\n') if doi.strip()]
                
                # 用於存放所有結果的列表
                results_list = []
                
                with st.spinner(f"正在擷取 {len(dois)} 篇文獻資料..."):
                    for doi in dois:
                        
                        # 【混合模式邏輯】
                        # 1. 優先嘗試 API (方法 1)
                        title, abstract, authors, year = fetch_from_crossref(doi)
                        method = "API"
                        
                        # 2. 如果 API 失敗，啟動爬蟲 (方法 2)
                        if title is None:
                            title, abstract, authors, year = scrape_from_doi_website(doi)
                            method = "爬蟲" # 標記為爬蟲
                        
                        # 3. 將結果存入字典
                        result_data = {
                            "DOI": doi,
                            "Title": title if title else "[抓取失敗]",
                            "Authors": authors if authors else "[抓取失敗]",
                            "Year": year if year else "[抓取失敗]",
                            "Abstract": abstract if abstract else "[抓取失敗]",
                            "Fetch_Method": method
                        }
                        results_list.append(result_data)
                                    
                    st.success("全部擷取完畢！")

                # --- 【新功能】將結果轉換為表格並顯示 ---
                if results_list:
                    st.header("📊 擷取結果表格")
                    
                    df = pd.DataFrame(results_list)
                    
                    # 重新排列表格欄位順序
                    columns_order = ["Authors", "Year", "Title", "Abstract", "DOI", "Fetch_Method"]
                    # 確保所有欄位都存在，避免 KeyErrors
                    df_display_columns = [col for col in columns_order if col in df.columns]
                    df_display = df[df_display_columns]

                    st.dataframe(df_display, use_container_width=True)
                    
                    # --- 【新功能】提供下載按鈕 ---
                    @st.cache_data
                    def convert_df_to_csv(df_to_convert):
                        # 轉為 CSV，使用 utf-8-sig 以確保 Excel 正確讀取中文
                        return df_to_convert.to_csv(index=False).encode('utf-8-sig')

                    csv_data = convert_df_to_csv(df_display)

                    st.download_button(
                        label="📥 下載表格 (CSV)",
                        data=csv_data,
                        file_name="doi_fetch_results.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                else:
                    st.error("所有 DOI 均查詢失敗，無法生成表格。")

if __name__ == "__main__":
    main()

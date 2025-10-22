import streamlit as st
import requests  # 用於 API 請求
import re        # 用於清理 HTML 標籤 和 擷取年份
from bs4 import BeautifulSoup # 用於解析 HTML
import pandas as pd # 用於建立表格
import time      # 新增：用於等待頁面載入

# --- 新增：Selenium 相關匯入 ---
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# ----------------------------------------------------------------------
# 區塊 1：API 查詢函式 (CrossRef) - (與之前相同)
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
            title = message.get('title', ['[標題不可用]'])[0]
            abstract = clean_html(message.get('abstract', '[摘要不可用]'))
            author_list = message.get('author', [])
            if author_list:
                authors = ', '.join([f"{a.get('given', '')} {a.get('family', '')}".strip() for a in author_list])
            else:
                authors = '[作者抓取失敗]'
            date_parts = message.get('created', {}).get('date-parts', [[None]])[0]
            year = date_parts[0] if (date_parts and date_parts[0]) else '[年份抓取失敗]'
            if abstract.startswith('['): return None, None, None, None
            return title, abstract, authors, year
        else:
            return None, None, None, None
    except Exception:
        return None, None, None, None

# ----------------------------------------------------------------------
# 區塊 2：【★Streamlit Cloud 版★】使用 Selenium 進行網頁爬蟲
# ----------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def scrape_with_selenium(doi):
    """(方法 2) 使用 Selenium 模擬真人瀏覽器，爬取 DOI 轉址後的網頁"""
    
    # --- Selenium 設定 ---
    options = Options()
    options.add_argument("--headless")  # 無頭模式，不在畫面上顯示瀏覽器
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    # 【★ Streamlit Cloud 修改點 ★】
    # 使用 `packages.txt` 安裝後的標準 Linux 路徑
    try:
        service = Service(executable_path="/usr/bin/chromedriver") # <--- ★★★ 已修正為 Linux 路徑 ★★★
    except Exception as e:
        st.error(f"錯誤：找不到 Chromedriver。請確認您已在 GitHub 建立了 `packages.txt` 檔案。錯誤訊息：{e}")
        return None, "Chromedriver 未設定", None, None
    
    driver = None
    try:
        # 啟動瀏覽器
        driver = webdriver.Chrome(service=service, options=options)
        
        doi_url = f"https://doi.org/{doi.split('doi.org/')[-1]}"
        
        # 瀏覽器前往該網址 (會自動轉址)
        driver.get(doi_url)
        
        # 【關鍵】等待 3 秒，讓 JavaScript 有時間載入摘要
        time.sleep(3) 
        
        # 取得「執行 JavaScript 後」的網頁原始碼
        page_source = driver.page_source
        
        # --- 使用 BeautifulSoup 解析 (與之前相同) ---
        soup = BeautifulSoup(page_source, 'html.parser')
        
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
            match = re.search(r'\b(19[5-9]\d|20[0-4]\d|2050)\b', date_str) 
            year = match.group(0) if match else date_str
        else:
            year = '[年份抓取失敗]'
            
        return title, abstract, authors, year
            
    except Exception as e:
        return None, f"爬蟲網路錯誤(Selenium)：{e}", None, None
    finally:
        # 無論如何都要關閉瀏覽器，否則會佔用記憶體
        if driver:
            driver.quit()

# ----------------------------------------------------------------------
# 區塊 3：Streamlit 介面主體 (表格生成模式)
# ----------------------------------------------------------------------

def main():
    st.set_page_config(layout="wide", page_title="即時文獻摘要查詢")
    
    st.title("📚 即時文獻摘要查詢 (Live DOI Fetcher)")
    st.markdown("""
    請貼上 DOI 列表。系統將自動擷取**作者、年份、標題、摘要**，並彙整成表格。
    (使用 Selenium 模擬瀏覽器，抓取 403 網站。**速度會比較慢，請耐心等候**。)
    """)

    with st.container(border=True):
        
        doi_input = st.text_area(
            "請輸入 DOI (Digital Object Identifiers)，每行一個：",
            placeholder="10.6345/NTNU202200459 (試試這個，會啟動 Selenium 爬蟲)\n10.1038/nature12373 (試試這個，會使用 API)"
        )
        
        if st.button("🚀 開始擷取並製成表格 (慢速版)", use_container_width=True, type="primary"):
            if not doi_input:
                st.warning("請輸入至少一個 DOI。")
            else:
                dois = [doi.strip() for doi in doi_input.split('\n') if doi.strip()]
                results_list = []
                
                with st.spinner(f"正在使用 Selenium 模擬瀏覽器擷取 {len(dois)} 篇文獻... (這會需要一點時間)"):
                    for doi in dois:
                        # 1. 優先嘗試 API (方法 1)
                        title, abstract, authors, year = fetch_from_crossref(doi)
                        method = "API"
                        
                        # 2. 如果 API 失敗，啟動 Selenium (方法 2)
                        if title is None:
                            title, abstract, authors, year = scrape_with_selenium(doi)
                            method = "爬蟲 (Selenium)" # 標記
                        
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

                # --- 顯示表格並提供下載 ---
                if results_list:
                    st.header("📊 擷取結果表格")
                    df = pd.DataFrame(results_list)
                    columns_order = ["Authors", "Year", "Title", "Abstract", "DOI", "Fetch_Method"]
                    df_display_columns = [col for col in columns_order if col in df.columns]
                    df_display = df[df_display_columns]

                    st.dataframe(df_display, use_container_width=True)
                    
                    @st.cache_data
                    def convert_df_to_csv(df_to_convert):
                        return df_to_convert.to_csv(index=False).encode('utf-8-sig')

                    csv_data = convert_df_to_csv(df_display)

                    st.download_button(
                        label="📥 下載表格 (CSV)",
                        data=csv_data,
                        file_name="doi_fetch_results.csv",
                        mime="text/csv,
                        use_container_width=True
                    )
                else:
                    st.error("所有 DOI 均查詢失敗，無法生成表格。")

if __name__ == "__main__":
    main()

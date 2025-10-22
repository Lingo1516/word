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
            authors = '[作者抓取失敗]' # <-- 錯誤在這裡，請確保有結尾的 '

        # --- 4.

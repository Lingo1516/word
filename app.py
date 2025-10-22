import streamlit as st
import requests  # 用於 API 請求
import re        # 用於清理 HTML 標籤

# ----------------------------------------------------------------------
# 區塊 1：DOI 摘要擷取函式
# ----------------------------------------------------------------------

def clean_html(raw_html):
    """移除 HTML 標籤"""
    cleantext = re.sub(r'<[^>]+>', '', raw_html)
    return cleantext

@st.cache_data(show_spinner=False) # 快取查詢過的 DOI 結果，加快重複查詢速度
def fetch_abstract_from_doi(doi):
    """
    使用 CrossRef API 透過 DOI 擷取摘要。
    """
    try:
        # 移除 DOI 網址前綴 (如果有的話)，只保留 DOI
        doi_id = doi.split('doi.org/')[-1]
        
        url = f"https://api.crossref.org/works/{doi_id}"
        headers = {'Accept': 'application/json'}
        
        # 加上 timeout 以免卡住
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            message = data.get('message', {})
            
            # 嘗試取得標題
            title = message.get('title', ['[標題不可用]'])[0]
            
            # 嘗試取得摘要
            abstract = message.get('abstract', '[摘要不可用]')
            
            # CrossRef 的摘要常包含 <jats:p>...</jats:p> 標籤，需要清理
            cleaned_abstract = clean_html(abstract)
            
            return title, cleaned_abstract
        else:
            return None, f"API 錯誤：狀態碼 {response.status_code}"
            
    except requests.exceptions.RequestException as e:
        return None, f"網路請求錯誤：{e}"
    except Exception as e:
        return None, f"處理時發生錯誤：{e}"

# ----------------------------------------------------------------------
# 區塊 2：Streamlit 介面主體
# ----------------------------------------------------------------------

def main():
    # 網頁設定為寬螢幕模式
    st.set_page_config(layout="wide", page_title="即時文獻摘要查詢")
    
    st.title("📚 即時文獻摘要查詢 (Live DOI Fetcher)")
    st.markdown("""
    在這裡貼上您想快速查詢的 DOI 列表，系統將透過 [CrossRef API](https://www.crossref.org/) 即時擷取摘要。
    """)

    # --- 即時 DOI 查詢介面 ---
    with st.container(border=True):
        
        doi_input = st.text_area(
            "請輸入 DOI (Digital Object Identifiers)，每行一個：",
            placeholder="10.6342/NTU202402274\n10.6814/NCCU202200871\n10.29697/JPE.202507(24).0010"
        )
        
        if st.button("🚀 開始擷取摘要", use_container_width=True, type="primary"):
            if not doi_input:
                st.warning("請輸入至少一個 DOI。")
            else:
                # 解析輸入的 DOIs，去除空白
                dois = [doi.strip() for doi in doi_input.split('\n') if doi.strip()]
                
                with st.spinner(f"正在擷取 {len(dois)} 篇文獻摘要，請稍候..."):
                    for doi in dois:
                        title, abstract = fetch_abstract_from_doi(doi)
                        
                        # 使用可折疊區塊顯示結果
                        with st.expander(f"**{title}** (DOI: {doi})", expanded=False):
                            if abstract.startswith('[') or abstract.startswith('API 錯誤') or abstract.startswith('網路請求錯誤'):
                                st.error(abstract) # 如果是錯誤訊息，用紅色顯示
                            else:
                                st.write(abstract) # 顯示摘要
                    st.success("全部擷取完畢！")

if __name__ == "__main__":
    main()

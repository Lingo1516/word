import streamlit as st
import pandas as pd
import time
import requests  # 新增：用於 API 請求
import re        # 新增：用於清理 HTML 標籤

# --- 極簡、高效的個人化文獻資料庫 ---

# ----------------------------------------------------------------------
# 區塊 1：資料庫 (CSV) 載入功能 (與您原本的程式碼相同)
# ----------------------------------------------------------------------

# 使用快取功能來讀取資料，確保只在需要時讀取一次
@st.cache_data
def load_data():
    """從 CSV 檔案載入文獻資料庫"""
    try:
        # 讀取簡化後的 CSV 檔案
        df = pd.read_csv("papers_db.csv")
        # 確保年份是整數
        df['year'] = pd.to_numeric(df['year'], errors='coerce').fillna(0).astype(int)
        return df
    except FileNotFoundError:
        st.error("⚠️ 錯誤：找不到 'papers_db.csv' 資料庫檔案。")
        st.info("請確認您已經將 `papers_db.csv` 檔案上傳至您的 GitHub 儲存庫。")
        return pd.DataFrame(columns=['year', 'title', 'authors', 'abstract', 'keywords', 'doi_url'])
    except Exception as e:
        st.error(f"載入 'papers_db.csv' 時發生錯誤：{e}")
        st.info("請檢查 CSV 檔案的格式是否正確。")
        return pd.DataFrame(columns=['year', 'title', 'authors', 'abstract', 'keywords', 'doi_url'])

# ----------------------------------------------------------------------
# 區塊 2：【新功能】DOI 摘要擷取函式
# ----------------------------------------------------------------------

def clean_html(raw_html):
    """移除 HTML 標籤"""
    cleantext = re.sub(r'<[^>]+>', '', raw_html)
    return cleantext

@st.cache_data(show_spinner=False) # 快取查詢過的 DOI 結果
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
# 區塊 3：Streamlit 介面主體
# ----------------------------------------------------------------------

def main():
    st.set_page_config(layout="wide", page_title="個人化文獻資料庫")
    st.title("📚 個人化文獻資料庫")

    # 載入資料
    df = load_data()
    total_papers = len(df)
    st.write(f"目前您的本地資料庫中共有 **{total_papers}** 筆文獻。")

    # --- 【新功能】即時 DOI 查詢介面 ---
    with st.container(border=True):
        st.subheader("🔍 即時文獻摘要查詢 (Live DOI Fetcher)")
        st.markdown("""
        在這裡貼上您想快速查詢的 DOI 列表，系統將透過 [CrossRef API](https://www.crossref.org/) 即時擷取摘要。
        **這不會** 將文獻存入您的 `papers_db.csv`，這只是一個快速預覽工具。
        """)
        
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

    # --- 篩選與管理介面 (與您原本的程式碼相同) ---
    st.sidebar.header("🔍 篩選與匯出 (本地資料庫)")
    
    # 關鍵字搜尋
    keyword = st.sidebar.text_input("關鍵字篩選（可搜尋標題、關鍵字等）")
    
    # --- 資料篩選邏輯 ---
    filtered_df = df.copy()
    if keyword:
        keyword_lower = keyword.lower()
        # 在所有欄位中進行搜尋
        filtered_df = filtered_df[filtered_df.apply(lambda row: keyword_lower in str(row).lower(), axis=1)]

    total_results = len(filtered_df)
    st.header(f"📊 本地資料庫篩選結果 ({total_results} 筆)")

    if not filtered_df.empty:
        # --- 專業表格視圖 ---
        st.dataframe(filtered_df, use_container_width=True, height=500)
        
        # --- 匯出功能 ---
        csv_data = filtered_df.to_csv(index=False).encode('utf-8-sig')
        st.sidebar.download_button(
            label="📥 下載篩選結果 (CSV)",
            data=csv_data,
            file_name=f"My_Research_{time.strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
            type="primary"
        )
    elif not df.empty:
        st.warning("在您的本地資料庫中找不到符合條件的文獻。請調整您的篩選條件。")
    else:
        st.info("您的本地資料庫目前是空的。")

if __name__ == "__main__":
    main()

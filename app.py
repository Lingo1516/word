import streamlit as st
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
import time
import random
from urllib.parse import quote
import csv
import io
import subprocess
import sys

# --- Playwright 雲端環境設定 ---
# 這個區塊會在使用者的雲端主機上自動安裝執行爬蟲所需的瀏覽器
@st.cache_resource
def install_playwright():
    try:
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
    except Exception as e:
        st.error(f"安裝 Playwright 瀏覽器失敗：{e}")
        st.stop()

install_playwright()
# --- 設定結束 ---

# 頁面設定
st.set_page_config(
    page_title="NDLTD 台灣學術文獻搜尋",
    page_icon="📚",
    layout="wide"
)

st.title("📚 NDLTD 台灣學術文獻搜尋 (隱身版)")
st.markdown(f"輸入關鍵字，即可即時搜尋台灣博碩士論文（更新至 {time.strftime('%Y 年 %m 月 %d 日 %H:%M CST')}）")

# 初始化 session state
if 'last_search_time' not in st.session_state:
    st.session_state['last_search_time'] = 0

# 使用者輸入
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    keyword = st.text_input("🔍 搜尋關鍵字", placeholder="例如：人力資源管理")
with col2:
    year_start = st.number_input("起始年份", min_value=1900, max_value=2025, value=2015)
with col3:
    year_end = st.number_input("結束年份", min_value=1900, max_value=2025, value=2025)
max_results = st.slider("最多顯示幾篇論文", min_value=5, max_value=50, value=10, step=5)

def fetch_taiwan_scholar_playwright(keyword, year_start=None, year_end=None, max_results=10):
    """
    使用 Playwright 從 NDLTD 爬取台灣學術文獻，以達到最佳的隱身效果。
    """
    results = []
    
    encoded_keyword = quote(keyword.encode('big5'))
    url = f"https://ndltd.ncl.edu.tw/cgi-bin/gs32/gsweb.cgi?o=dnclcdr&s={encoded_keyword}"
    if year_start and year_end:
        url += f"&range=dr1%3E={year_start}+dr1%3C={year_end}"

    try:
        with sync_playwright() as p:
            with st.spinner("🚀 正在啟動隱身瀏覽器..."):
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
                    locale='zh-TW'
                )
                page = context.new_page()
            
            with st.spinner(f"🕵️‍♀️ 正在前往目標頁面..."):
                page.goto(url, timeout=30000, wait_until='domcontentloaded')
                # 等待搜尋結果的第一個項目出現，確保頁面已載入
                page.wait_for_selector('div.gs_c', timeout=20000)

            with st.spinner("🔍 正在解析頁面內容..."):
                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')
            
            browser.close()

        # 檢查是否有訪問限制
        if "請輸入驗證碼" in html or "未授權" in html:
            return None, "被 NDLTD 偵測為機器人，請稍後再試或使用 VPN 切換 IP"

        papers = soup.find_all('div', class_='gs_c')
        if not papers:
            return None, "找不到搜尋結果，可能關鍵字無匹配或被限制"

        for idx, paper in enumerate(papers[:max_results], 1):
            try:
                title_elem = paper.find('a', class_='gs_ct')
                if not title_elem: continue

                title = title_elem.get_text().strip()
                link = "https://ndltd.ncl.edu.tw" + title_elem['href'] if title_elem.has_attr('href') else "N/A"
                
                meta_elem = paper.find('div', class_='gs_a')
                meta_text = meta_elem.get_text().strip() if meta_elem else "N/A"
                author_parts = meta_text.split(" - ")
                author = author_parts[0].strip() if author_parts else "匿名作者"
                year = author_parts[-1].split()[0] if author_parts and len(author_parts[-1].split()) > 0 else "N/A"
                institution = author_parts[1] if len(author_parts) > 1 else "N/A"

                results.append({
                    "序號": idx, "作者": author, "年份": year, "標題": title, "機構": institution, "連結": link
                })
            except Exception as e:
                st.warning(f"解析第 {idx} 篇論文時發生錯誤：{str(e)}")
                continue
        
        return results, None

    except PlaywrightTimeoutError:
        return None, "頁面載入逾時，NDLTD 可能暫時無法連線或啟動了更強的反爬蟲機制"
    except Exception as e:
        return None, f"發生未預期的錯誤：{str(e)}"

# 搜尋按鈕
if st.button("🚀 開始搜尋", type="primary", use_container_width=True):
    if not keyword:
        st.error("❌ 請輸入搜尋關鍵字")
    elif year_start > year_end:
        st.error("❌ 起始年份不能晚於結束年份")
    elif time.time() - st.session_state['last_search_time'] < 10:
        st.error("❌ 搜尋過於頻繁，請等待至少 10 秒後再試")
    else:
        st.session_state['last_search_time'] = time.time()
        
        results, error = fetch_taiwan_scholar_playwright(
            keyword, year_start, year_end, max_results
        )

        if error:
            st.error(f"❌ {error}")
        elif not results:
            st.warning("⚠️ 沒有找到相關文獻")
        else:
            st.success(f"✅ 成功找到 {len(results)} 篇論文！")
            for paper in results:
                apa_citation = (
                    f"{paper['作者']} ({paper['年份']}).\n"
                    f"*{paper['標題']}* "
                    f"[{paper['機構']}碩博士論文]. "
                    f"臺灣博碩士論文知識加值系統. {paper['連結']}"
                )
                with st.expander(f"📄 {paper['序號']}. {paper['標題']}", expanded=True):
                    st.markdown(f"**APA 引用格式：**")
                    st.code(apa_citation, language='text')
                    st.divider()

            # 匯出功能
            st.subheader("💾 匯出結果")
            csv_buffer = io.StringIO()
            writer = csv.DictWriter(csv_buffer, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
            csv_data = csv_buffer.getvalue()
            st.download_button(
                label="📥 下載 CSV 檔案",
                data=csv_data.encode('utf-8-sig'),
                file_name=f"ndltd_{keyword}_{time.strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

# 側邊欄說明
with st.sidebar:
    st.header("📖 使用說明")
    st.markdown("""
    ### ✨ 功能特色
    - 🚀 **全新引擎**：使用 Playwright 模擬真人瀏覽，有效降低被偵測風險。
    - 🔍 搜尋台灣 NDLTD 學術文獻
    - 📅 年份範圍篩選
    - 📑 APA 格式輸出
    - 💾 匯出 CSV 檔案

    ### ⚠️ 注意事項
    1. **請勿頻繁搜尋**，每次搜尋需間隔至少 10 秒。
    2. 首次搜尋會花較長時間設定瀏覽器環境。
    3. 如遇錯誤，請等待 1-2 分鐘後再試。
    """)
    st.divider()
    st.caption("Made with ❤️ by Streamlit")

# 頁尾
st.divider()
st.caption("⚠️ 本工具僅供學術研究使用，請遵守 NDLTD 使用條款。")


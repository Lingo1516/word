import streamlit as st
import requests
from bs4 import BeautifulSoup
import time
import random
from urllib.parse import quote
import csv
import io

# 頁面設定
st.set_page_config(
    page_title="NDLTD 台灣學術文獻搜尋",
    page_icon="📚",
    layout="wide"
)

st.title("📚 NDLTD 台灣學術文獻搜尋")
st.markdown("輸入關鍵字，搜尋台灣博碩士論文")

# 初始化 session state 用於追蹤上次搜尋時間
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

def fetch_taiwan_scholar(keyword, year_start=None, year_end=None, max_results=10):
    """
    從 NDLTD 爬取台灣學術文獻
    """
    results = []

    # 建構搜尋 URL (NDLTD 台灣博碩士論文)
    encoded_keyword = quote(keyword.encode('big5'))
    url = f"https://ndltd.ncl.edu.tw/cgi-bin/gs32/gsweb.cgi?o=dnclcdr&s={encoded_keyword}"

    if year_start and year_end:
        url += f"&range=dr1%3E={year_start}+dr1%3C={year_end}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)

        if response.status_code == 429:
            return None, "請求過於頻繁，請稍後再試"
        elif response.status_code != 200:
            return None, f"無法連線到 NDLTD (錯誤碼: {response.status_code})"

        soup = BeautifulSoup(response.text, 'html.parser')

        # 檢查是否有訪問限制
        if "請輸入驗證碼" in response.text or "未授權" in response.text:
            return None, "被 NDLTD 偵測為機器人，請稍後再試或檢查 IP"

        # 找到所有論文結果
        papers = soup.find_all('div', class_='gs_c')

        if not papers:
            return None, "找不到搜尋結果，可能關鍵字無匹配或被限制"

        for idx, paper in enumerate(papers[:max_results], 1):
            try:
                # 標題和連結
                title_elem = paper.find('a', class_='gs_ct')
                if not title_elem:
                    continue

                title = title_elem.get_text().strip()
                link = "https://ndltd.ncl.edu.tw" + title_elem['href'] if title_elem.has_attr('href') else "N/A"

                # 作者和年份
                meta_elem = paper.find('div', class_='gs_a')
                meta_text = meta_elem.get_text().strip() if meta_elem else "N/A"
                author = meta_text.split(" - ")[0] if " - " in meta_text else "匿名作者"
                year = meta_text.split(" - ")[-1].split()[0] if " - " in meta_text else "N/A"

                # 機構
                institution = meta_text.split(" - ")[1] if len(meta_text.split(" - ")) > 1 else "N/A"

                results.append({
                    "序號": idx,
                    "作者": author,
                    "年份": year,
                    "標題": title,
                    "機構": institution,
                    "連結": link
                })

            except Exception as e:
                st.warning(f"解析第 {idx} 篇論文時發生錯誤：{str(e)}")
                continue

        if len(results) < max_results:
            st.info(f"⚠️ 僅找到 {len(results)} 篇論文，低於設定的 {max_results} 篇")

        return results, None

    except requests.exceptions.Timeout:
        return None, "連線逾時，請檢查網路或稍後再試"
    except requests.exceptions.RequestException as e:
        return None, f"網路錯誤：{str(e)}"
    except Exception as e:
        return None, f"未知錯誤：{str(e)}"

# 搜尋按鈕
if st.button("🚀 開始搜尋", type="primary", use_container_width=True):
    if not keyword:
        st.error("❌ 請輸入搜尋關鍵字")
    elif year_start > year_end:
        st.error("❌ 起始年份不能晚於結束年份")
    elif time.time() - st.session_state['last_search_time'] < 5:
        st.error("❌ 搜尋過於頻繁，請等待幾秒後再試")
    else:
        with st.spinner("🔍 正在搜尋 NDLTD..."):
            st.session_state['last_search_time'] = time.time()
            time.sleep(random.uniform(1, 3))

            results, error = fetch_taiwan_scholar(
                keyword,
                year_start,
                year_end,
                max_results
            )

            if error:
                st.error(f"❌ {error}")
                st.info("💡 解決建議：\n"
                        "1. 等待 1-2 分鐘後再試\n"
                        "2. 使用 VPN 更換 IP 位址\n"
                        "3. 減少搜尋數量")
            elif not results:
                st.warning("⚠️ 沒有找到相關文獻")
            else:
                st.success(f"✅ 成功找到 {len(results)} 篇論文！")

                # 顯示結果 (APA 格式)
                for paper in results:
                    apa_citation = f"{paper['作者']} ({paper['年份']}).

                    {paper['標題']} [碩士論文，{paper['機構']}]. 臺灣博碩士論文知識加值系統. {paper['連結']}"
                    with st.expander(f"📄 {paper['序號']}. {paper['標題']}", expanded=True):
                        st.markdown(f"**APA 引用格式：** {apa_citation}")
                        st.divider()

                # 匯出功能
                st.subheader("💾 匯出結果")

                csv_buffer = io.StringIO()
                writer = csv.writer(csv_buffer, quoting=csv.QUOTE_MINIMAL)
                writer.writerow(["序號", "作者", "年份", "標題", "機構", "連結"])
                for paper in results:
                    writer.writerow([
                        paper["序號"],
                        paper["作者"],
                        paper["年份"],
                        paper["標題"],
                        paper["機構"],
                        paper["連結"]
                    ])

                csv_data = csv_buffer.getvalue()

                st.download_button(
                    label="📥 下載 CSV 檔案",
                    data=csv_data.encode('utf-8-sig'),
                    file_name=f"ndlt_{keyword}_{time.strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )

# 側邊欄說明
with st.sidebar:
    st.header("📖 使用說明")

    st.markdown("""
    ### ✨ 功能特色
    - 🔍 搜尋台灣 NDLTD 學術文獻
    - 📅 年份範圍篩選
    - 📑 APA 格式輸出
    - 💾 匯出 CSV 檔案

    ### ⚠️ 注意事項
    1. **請勿頻繁搜尋**，每次搜尋需間隔 5 秒以上
    2. 如遇到「被偵測為機器人」，請等待 1-2 分鐘
    3. 建議使用 VPN 提高成功率

    ### 🛠️ 技術資訊
    - 使用 `requests` + `BeautifulSoup`
    - 專為 NDLTD 台灣資料庫設計
    - 支援中文搜尋
    """)

    st.divider()
    st.caption("Made with ❤️ by Streamlit")

# 頁尾
st.divider()
st.caption("⚠️ 本工具僅供學術研究使用，請遵守 NDLTD 使用條款。")

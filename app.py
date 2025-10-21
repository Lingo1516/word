import streamlit as st
import requests
from bs4 import BeautifulSoup
import time
import random
from urllib.parse import quote

# 頁面設定
st.set_page_config(
    page_title="Google Scholar 學術搜尋",
    page_icon="📚",
    layout="wide"
)

st.title("📚 Google Scholar 學術文獻搜尋")
st.markdown("輸入關鍵字，即時搜尋 Google 學術文獻")

# 使用者輸入
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    keyword = st.text_input("🔍 搜尋關鍵字", placeholder="例如：人力資源管理")

with col2:
    year_start = st.number_input("起始年份", min_value=1900, max_value=2025, value=2020)

with col3:
    year_end = st.number_input("結束年份", min_value=1900, max_value=2025, value=2024)

max_results = st.slider("最多顯示幾篇論文", min_value=5, max_value=50, value=10, step=5)

def fetch_google_scholar_simple(keyword, year_start=None, year_end=None, max_results=10):
    """
    使用 requests + BeautifulSoup 爬取 Google Scholar
    這是最穩定的方法，不需要瀏覽器
    """
    results = []
    
    # 建構搜尋 URL
    encoded_keyword = quote(keyword)
    url = f"https://scholar.google.com/scholar?q={encoded_keyword}&hl=zh-TW"
    
    if year_start and year_end:
        url += f"&as_ylo={year_start}&as_yhi={year_end}"
    
    # 設定 Headers 模擬真實瀏覽器
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    try:
        # 發送請求
        response = requests.get(url, headers=headers, timeout=15)
        
        # 檢查是否被阻擋
        if response.status_code == 429:
            return None, "請求過於頻繁，請稍後再試"
        elif response.status_code != 200:
            return None, f"無法連線到 Google Scholar (錯誤碼: {response.status_code})"
        
        # 檢查是否有 CAPTCHA
        if 'captcha' in response.text.lower() or 'unusual traffic' in response.text.lower():
            return None, "被 Google 偵測為機器人，請稍後再試或使用 VPN"
        
        # 解析 HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 找到所有論文結果
        papers = soup.find_all('div', class_='gs_ri')
        
        if not papers:
            return None, "找不到搜尋結果，可能被阻擋或關鍵字無結果"
        
        # 解析每篇論文
        for idx, paper in enumerate(papers[:max_results], 1):
            try:
                # 標題和連結
                title_elem = paper.find('h3', class_='gs_rt')
                if not title_elem:
                    continue
                
                title = title_elem.get_text().strip()
                
                # 取得連結
                link_elem = title_elem.find('a')
                link = link_elem['href'] if link_elem and link_elem.has_attr('href') else "N/A"
                
                # 作者和出版資訊
                author_elem = paper.find('div', class_='gs_a')
                author_info = author_elem.get_text().strip() if author_elem else "N/A"
                
                # 摘要
                abstract_elem = paper.find('div', class_='gs_rs')
                abstract = abstract_elem.get_text().strip() if abstract_elem else "N/A"
                
                # 引用次數
                citations = "0"
                cite_elem = paper.find('div', class_='gs_fl')
                if cite_elem:
                    cite_links = cite_elem.find_all('a')
                    for link in cite_links:
                        text = link.get_text()
                        if '引用次數' in text or 'Cited by' in text:
                            citations = text.split()[-1]
                            break
                
                results.append({
                    "序號": idx,
                    "標題": title,
                    "連結": link,
                    "作者與出版": author_info,
                    "摘要": abstract,
                    "引用次數": citations
                })
                
            except Exception as e:
                st.warning(f"解析第 {idx} 篇論文時發生錯誤")
                continue
        
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
    else:
        with st.spinner("🔍 正在搜尋 Google Scholar..."):
            # 加入隨機延遲，避免被偵測
            time.sleep(random.uniform(1, 3))
            
            results, error = fetch_google_scholar_simple(
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
                       "3. 減少搜尋數量\n"
                       "4. 嘗試不同的關鍵字")
            elif not results:
                st.warning("⚠️ 沒有找到相關文獻")
            else:
                st.success(f"✅ 成功找到 {len(results)} 篇論文！")
                
                # 顯示結果
                for paper in results:
                    with st.expander(f"📄 {paper['序號']}. {paper['標題']}", expanded=True):
                        col_a, col_b = st.columns([3, 1])
                        
                        with col_a:
                            st.markdown(f"**作者與出版：** {paper['作者與出版']}")
                            st.markdown(f"**摘要：** {paper['摘要']}")
                        
                        with col_b:
                            st.metric("引用次數", paper['引用次數'])
                        
                        if paper['連結'] != "N/A":
                            st.markdown(f"🔗 [點此前往論文]({paper['連結']})")
                        
                        st.divider()
                
                # 匯出功能
                st.subheader("💾 匯出結果")
                
                # 準備 CSV 資料
                import io
                csv_buffer = io.StringIO()
                
                # 寫入 CSV
                csv_buffer.write("序號,標題,連結,作者與出版,引用次數,摘要\n")
                for paper in results:
                    csv_buffer.write(f"{paper['序號']},")
                    csv_buffer.write(f'"{paper["標題"]}",')
                    csv_buffer.write(f'"{paper["連結"]}",')
                    csv_buffer.write(f'"{paper["作者與出版"]}",')
                    csv_buffer.write(f"{paper['引用次數']},")
                    csv_buffer.write(f'"{paper["摘要"]}"\n')
                
                csv_data = csv_buffer.getvalue()
                
                st.download_button(
                    label="📥 下載 CSV 檔案",
                    data=csv_data.encode('utf-8-sig'),
                    file_name=f"scholar_{keyword}_{time.strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )

# 側邊欄說明
with st.sidebar:
    st.header("📖 使用說明")
    
    st.markdown("""
    ### ✨ 功能特色
    - 🔍 即時搜尋 Google Scholar
    - 📅 年份範圍篩選
    - 📊 顯示引用次數
    - 💾 匯出 CSV 檔案
    
    ### ⚠️ 注意事項
    1. **請勿頻繁搜尋**，避免被 Google 阻擋
    2. 如遇到「被偵測為機器人」，請等待 1-2 分鐘
    3. 建議使用 **VPN** 提高成功率
    4. 每次搜尋建議間隔 5 秒以上
    
    ### 🛠️ 技術資訊
    - 使用 `requests` + `BeautifulSoup`
    - 不需要瀏覽器，更輕量穩定
    - 支援中文繁體搜尋
    
    ### 💡 常見問題
    **Q: 為什麼會顯示「被阻擋」？**  
    A: Google 有反爬蟲機制，請降低搜尋頻率或使用 VPN
    
    **Q: 如何提高成功率？**  
    A: 1) 使用 VPN 2) 減少搜尋數量 3) 增加間隔時間
    """)
    
    st.divider()
    st.caption("Made with ❤️ by Streamlit")

# 頁尾
st.divider()
st.caption("⚠️ 本工具僅供學術研究使用，請遵守 Google Scholar 使用條款

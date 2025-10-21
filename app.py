import streamlit as st
import pandas as pd
import time

# --- 最終解決方案：使用靜態資料集 ---
# 由於直接在雲端爬取 Google 學術搜尋的穩定性極低，
# 我們改用一個預先準備好的學術文獻資料集來展示應用程式的核心功能。
# 這樣可以確保應用程式永遠都能正常運作，並且可以分享給他人使用。

# 模擬一個學術文獻的資料庫 (使用 pandas DataFrame)
data = {
    'title': [
        '人力資源管理實務對組織績效之影響',
        '知識管理、人力資本與組織績效關聯性之研究',
        '企業文化、領導風格與人力資源管理策略的整合模型',
        '員工激勵與工作滿意度：以台灣高科技產業為例',
        '數位轉型下的人力資源挑戰與應對策略',
        '從策略性人力資源管理觀點探討員工留任之關鍵因素',
        '組織創新氣氛與員工創造力之關聯：以人力資源實務為中介效果',
        '高階主管團隊特質對企業國際化績效的影響',
        '人力資源資訊系統（HRIS）的導入與效益評估',
        '工作生活平衡政策對員工幸福感與組織承諾的影響'
    ],
    'author': [
        '陳明哲, 李芳華',
        '王志強, 吳靜宜',
        '林美麗',
        '張偉雄, 劉雅玲',
        '黃國彥',
        '許淑芬, 鄭文傑',
        '趙雅君',
        '孫大偉, 高明',
        '周慧敏',
        '蔡依林, 周杰倫'
    ],
    'publication': [
        '管理學報',
        '人力資源管理學報',
        '組織與管理',
        '科技管理評論',
        '電子商務研究',
        '管理評論',
        '中山管理評論',
        '台大管理論叢',
        '資訊管理學報',
        '應用心理研究'
    ],
    'link': [
        'https://example.com/paper1',
        'https://example.com/paper2',
        'https://example.com/paper3',
        'https://example.com/paper4',
        'https://example.com/paper5',
        'https://example.com/paper6',
        'https://example.com/paper7',
        'https://example.com/paper8',
        'https://example.com/paper9',
        'https://example.com/paper10'
    ]
}
df = pd.DataFrame(data)

# 搜尋函數
def search_papers(keyword):
    """在靜態資料集中搜尋包含關鍵字的文獻。"""
    if not keyword:
        return pd.DataFrame()
    # 忽略大小寫進行搜尋，並應用於整個資料列
    results = df[df.apply(lambda row: keyword.lower() in row.to_string().lower(), axis=1)]
    return results

# Streamlit 應用主函數
def main():
    st.set_page_config(layout="wide", page_title="學術搜尋工具 (展示版)")
    st.title("🔎 學術搜尋工具 (展示版)")
    st.write("輸入關鍵字，即可從我們的展示資料庫中，搜尋相關的學術文獻。")
    st.info("ℹ️ **說明**：由於直接爬取 Google 等大型網站在雲端環境極不穩定，此版本改為使用一個預載的資料庫來展示搜尋與篩選功能，以確保您能擁有一個可以穩定運作並分享的應用程式。")

    keyword = st.text_input("輸入您想要搜尋的關鍵字（例如：人力資源、績效）", "")

    if st.button('開始搜尋', type="primary"):
        if keyword:
            with st.spinner(f'正在資料庫中搜尋「{keyword}」...'):
                time.sleep(1) # 模擬搜尋延遲
                papers = search_papers(keyword)
            
            if not papers.empty:
                st.success(f"成功搜尋到 {len(papers)} 筆相關文獻：")
                for index, paper in papers.iterrows():
                    st.markdown(f"### [{paper['title']}]({paper['link']})")
                    st.caption(f"**作者:** {paper['author']}")
                    st.markdown(f"**發表於:** {paper['publication']}")
                    st.divider()
            else:
                st.warning("在我們的資料庫中找不到相關文獻，請嘗試更換關鍵字。")
        else:
            st.warning("請先輸入要搜尋的關鍵字。")

if __name__ == "__main__":
    main()


import streamlit as st
import random
import datetime

# --- 1. 系統設定與資料庫 (模擬 AI 邏輯) ---

st.set_page_config(page_title="AI 論文架構生成顧問", layout="wide", page_icon="🎓")

# 研究方法資料庫：定義不同方法的標準架構
METHODOLOGIES = {
    "量化研究 - 問卷調查法 (Survey)": {
        "desc": "適合探討變數之間的關聯性、影響因素或滿意度調查。",
        "steps": ["研究架構圖設計", "問卷設計與預試", "信效度分析", "描述性統計", "相關與迴歸分析"]
    },
    "量化研究 - 實驗法 (Experiment)": {
        "desc": "適合驗證因果關係，比較實驗組與對照組的差異。",
        "steps": ["實驗設計 (2x2 Factorial Design)", "受試者招募與分組", "前測 (Pre-test)", "實驗介入 (Intervention)", "後測與共變數分析 (ANCOVA)"]
    },
    "質性研究 - 深度訪談法 (In-depth Interview)": {
        "desc": "適合探索未知現象、了解受訪者深層動機與經驗。",
        "steps": ["訪談大綱擬定", "受訪者滾雪球抽樣", "半結構式訪談執行", "逐字稿轉錄", "編碼與主題分析 (Thematic Analysis)"]
    },
    "質性研究 - 個案研究法 (Case Study)": {
        "desc": "針對特定組織、事件或人物進行深入的全貌分析。",
        "steps": ["個案篩選與背景描述", "多重資料蒐集 (文件、觀察、訪談)", "個案內分析", "跨個案比較 (若為多個案)", "三角檢證 (Triangulation)"]
    },
    "文獻回顧 - 系統性文獻回顧 (Systematic Review)": {
        "desc": "針對特定議題進行窮盡式的文獻蒐集與評析。",
        "steps": ["PRISMA 流程圖繪製", "資料庫檢索策略設定", "納入與排除標準", "文獻品質評估", "綜合討論"]
    }
}

# 模擬生成邏輯 (在沒有 LLM API 的情況下，用模板組合出高品質草稿)
def generate_titles(keyword, method_name):
    """根據關鍵字與方法生成題目"""
    templates = [
        f"探討{keyword}對使用者行為之影響：以{method_name.split('-')[0]}為途徑",
        f"{keyword}在後疫情時代的應用與挑戰：{method_name.split('-')[1]}之實證研究",
        f"從{keyword}觀點看產業轉型策略：一項探索性研究",
        f"影響{keyword}成效之關鍵因素分析",
        f"整合性觀點下的{keyword}發展模式建構"
    ]
    return random.sample(templates, 3)

def generate_gap(keyword):
    """生成通用的研究缺口敘述"""
    return [
        f"過去關於「{keyword}」的研究多集中於歐美國家，缺乏在本土情境下的實證數據，文化差異可能導致結果有所不同。",
        f"現有文獻多探討{keyword}的技術層面，鮮少從「使用者心理」或「組織採用意願」的角度進行深入分析。",
        f"雖然已有研究證實{keyword}的重要性，但對於其「中介機制」與「邊界條件」的探討仍顯不足。",
        f"過往研究多採橫斷面調查，缺乏縱貫性的數據來驗證{keyword}隨時間變化的動態影響。"
    ]

def generate_literature(keyword, start_year, end_year):
    """生成模擬的文獻列表 (混合中英文)"""
    # 這裡是用演算法模擬生成，實際應用可串接 Google Scholar API
    years = range(start_year, end_year + 1)
    
    literatures = [
        {"author": "Smith, J. & Brown, L.", "year": random.choice(years), "title": f"The Impact of {keyword} on Modern Society", "source": "Journal of Future Studies", "lang": "EN"},
        {"author": "張志銘、李曉華", "year": random.choice(years), "title": f"{keyword}應用於產業創新之個案研究", "source": "管理評論", "lang": "TW"},
        {"author": "Johnson, A. et al.", "year": random.choice(years), "title": f"A Systematic Review of {keyword}", "source": "Int. J. of Information Mgmt.", "lang": "EN"},
        {"author": "王大明", "year": random.choice(years), "title": f"探討{keyword}與消費者滿意度之關聯", "source": "行銷科學學報", "lang": "TW"},
        {"author": "Chen, H. Y.", "year": random.choice(years), "title": f"Strategies for implementing {keyword} in SMEs", "source": "Business Horizons", "lang": "EN"},
    ]
    return sorted(literatures, key=lambda x: x['year'], reverse=True)

# --- 2. 介面設計 ---

# 側邊欄：輸入區
with st.sidebar:
    st.header("⚙️ 論文參數設定")
    
    user_keyword = st.text_input("1. 輸入核心關鍵字", "生成式AI", help="例如：ESG、遠距教學、顧客忠誠度")
    
    current_year = datetime.datetime.now().year
    year_range = st.slider("2. 文獻回顧年份範圍", 2010, current_year, (current_year-5, current_year))
    
    st.write("3. 選擇研究方法")
    selected_method = st.radio(
        "請選擇你想採用的方法：",
        options=list(METHODOLOGIES.keys())
    )
    
    st.info(f"💡 方法說明：\n{METHODOLOGIES[selected_method]['desc']}")
    
    generate_btn = st.button("🚀 生成論文架構", type="primary")

# 主畫面：結果區
st.title("🎓 自動化論文架構顧問")
st.markdown(f"目標：針對 **「{user_keyword}」** 提供學術建議與架構規劃")

if generate_btn and user_keyword:
    with st.spinner('正在分析文獻趨勢、建構邏輯架構中...'):
        import time
        time.sleep(1) # 模擬運算時間
        
        # 取得資料
        titles = generate_titles(user_keyword, selected_method)
        gaps = generate_gap(user_keyword)
        refs = generate_literature(user_keyword, year_range[0], year_range[1])
        method_steps = METHODOLOGIES[selected_method]['steps']

        # --- 區塊 1: 題目建議 ---
        st.subheader("1. 📌 建議論文題目")
        st.markdown("以下依據學術慣例為您生成三個可選題目：")
        
        col1, col2, col3 = st.columns(3)
        for i, title in enumerate(titles):
            with [col1, col2, col3][i]:
                st.success(f"**方案 {i+1}**\n\n{title}")

        st.markdown("---")

        # --- 區塊 2: 研究缺口 (Gap) ---
        st.subheader("2. 🔍 潛在研究缺口 (Research Gap)")
        st.markdown(f"針對 **{user_keyword}** 領域，我們發現目前的文獻可能有以下不足，這就是您的切入點：")
        
        for gap in gaps:
            st.markdown(f"- 🛑 **缺口發現：** {gap}")

        st.markdown("---")

        # --- 區塊 3: 推薦文獻 (Literature) ---
        st.subheader("3. 📚 關鍵文獻參考 (Reference)")
        st.markdown(f"篩選年份：{year_range[0]} - {year_range[1]}")
        
        ref_text = ""
        for ref in refs:
            icon = "🇺🇸" if ref['lang'] == "EN" else "🇹🇼"
            citation = f"{ref['author']} ({ref['year']}). {ref['title']}. *{ref['source']}*."
            st.markdown(f"{icon} {citation}")
            ref_text += f"{citation}\n"

        st.markdown("---")

        # --- 區塊 4: 客製化論文大綱 ---
        st.subheader(f"4. 📝 論文大綱建議：{selected_method.split('-')[0]}")
        st.info(f"已根據您選擇的 **{selected_method.split('-')[1]}** 調整第三章架構")

        # 動態生成大綱
        outline = f"""
# 論文題目：{titles[0]} (暫定)

## 第一章 緒論 (Introduction)
1.1 研究背景與動機 (為什麼現在要研究 {user_keyword}？)
1.2 研究目的 (本研究試圖解決什麼問題？)
1.3 研究問題 (Research Questions)
1.4 名詞釋義
1.5 研究範圍與限制

## 第二章 文獻探討 (Literature Review)
2.1 {user_keyword} 的定義與理論基礎
2.2 國內外相關實證研究回顧
2.3 研究缺口推導 (Research Gap)
2.4 研究架構推導 (Conceptual Framework)

## 第三章 研究方法 (Methodology)
3.1 研究設計 ({selected_method.split('-')[1]})
3.2 研究對象與抽樣 ({method_steps[1]})
3.3 研究工具/資料蒐集程序 ({method_steps[2]})
3.4 資料分析方法 ({method_steps[4]})

## 第四章 研究結果 (Results)
4.1 樣本結構/資料描述
4.2 主要發現 (對應研究問題)
4.3 假設檢定結果/主題分析結果

## 第五章 結論與建議 (Conclusion)
5.1 研究結論摘要
5.2 理論與實務意涵
5.3 研究限制與未來建議

## 參考文獻
{ref_text}
        """
        
        st.text_area("您可以直接複製以下大綱：", outline, height=400)
        st.download_button("📥 下載完整大綱 (Markdown)", outline, "paper_structure.md")

elif generate_btn and not user_keyword:
    st.warning("⚠️ 請務必輸入「關鍵字」才能開始分析！")

else:
    st.info("👈 請從左側輸入您的研究主題，開始規劃論文。")

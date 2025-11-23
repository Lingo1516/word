import streamlit as st
import random
import datetime

# --- 系統設定 ---
st.set_page_config(page_title="論文架構產生器 (免API版)", layout="wide", page_icon="📝")

# --- 預設資料庫 (模擬 AI 的邏輯) ---
# 這些是預先寫好的學術句型，程式會根據你的題目自動替換
GAPS_TEMPLATES = [
    "過去針對 {topic} 的研究多集中於理論探討，對於「實務應用層面」的數據驗證仍顯不足，此為本研究欲填補之缺口。",
    "雖然學界對 {topic} 已有廣泛討論，但鮮少有文獻探討其在「特定文化脈絡」下的差異性，這提供了本研究切入的契機。",
    "現有 {topic} 之文獻多採橫斷面研究，缺乏「縱貫性數據」來解釋其長期演變過程，故本研究擬採用不同的時間跨度進行分析。",
    "針對 {topic} 的影響因素分析中，過去研究多忽略了「中介變項」的調節效果，導致解釋力有限。"
]

METHOD_STEPS = {
    "量化研究 - 問卷調查": [
        "研究架構圖設計與變數定義",
        "問卷題項發展 (參考相關文獻)",
        "預試 (Pre-test) 與信效度分析",
        "正式施測與樣本回收",
        "敘述性統計與結構方程模型 (SEM) 分析"
    ],
    "質性研究 - 深度訪談": [
        "擬定半結構式訪談大綱",
        "受訪者篩選 (滾雪球抽樣法)",
        "進行訪談並錄音轉錄逐字稿",
        "編碼 (Coding) 與類別歸納",
        "三角檢證 (Triangulation) 與主題分析"
    ],
    "量化研究 - 實驗法": [
        "實驗設計 (如：2x2 因子設計)",
        "受試者隨機分派",
        "實驗操弄 (Manipulation)",
        "操控檢核 (Manipulation Check)",
        "變異數分析 (ANOVA) 與假說檢定"
    ]
}

# --- 核心功能函式 ---

def generate_outline(topic, gap, method, refs):
    """根據輸入條件，組裝出一份標準論文大綱"""
    current_date = datetime.date.today().strftime("%Y-%m-%d")
    
    # 這裡是用邏輯組裝，不是 AI 生成，所以速度極快且不會報錯
    outline = f"""
# 論文大綱草案
**題目：** {topic} 之研究
**生成日期：** {current_date}

---

## 第一章 緒論 (Introduction)
### 1.1 研究背景與動機
* (寫作指引)：請先描述 {topic} 目前在全球或該產業的現況數據。
* (寫作指引)：引用最近的新聞或報告，指出 {topic} 為何重要。
* (寫作指引)：帶出目前面臨的問題或挑戰。

### 1.2 研究目的
* 本研究旨在探討 {topic} 的核心影響因素。
* 分析不同變數對 {topic} 的作用機制。

### 1.3 研究缺口 (Research Gap)
> **{gap}**

### 1.4 名詞釋義
* 針對本研究所涉及的核心變數進行操作型定義。

---

## 第二章 文獻探討 (Literature Review)
### 2.1 {topic} 的理論基礎
* (在此處引用您提供的文獻)：
{refs}

### 2.2 相關實證研究回顧
* 整理過去五年內關於 {topic} 的國內外研究發現。
* 歸納出一致的結論與尚未解決的爭議。

---

## 第三章 研究方法 (Methodology)
**採用方法：** {method}

### 3.1 研究架構
* 說明研究變數之間的假設關係。

### 3.2 執行步驟
1. {METHOD_STEPS[method][0]}
2. {METHOD_STEPS[method][1]}
3. {METHOD_STEPS[method][2]}
4. {METHOD_STEPS[method][3]}
5. {METHOD_STEPS[method][4]}

### 3.3 資料分析工具
* 說明將使用的統計軟體 (如 SPSS, AMOS, NVivo) 或分析策略。

---

## 第四章 預期結果 (Results)
* (量化)：呈現人口統計變數分佈表、相關係數表、回歸分析表。
* (質性)：呈現受訪者基本資料表、主題分析矩陣圖。

## 第五章 結論與建議 (Conclusion)
* 總結研究發現。
* 對實務界提出具體管理意涵。
* 研究限制與未來研究建議。
    """
    return outline

# --- UI 介面 ---

st.title("📄 論文架構產生器 (免 OpenAI 版)")
st.markdown("此工具使用**內建邏輯庫**幫您快速搭建論文骨架，無需任何 API Key，完全免費。")

# 1. 初始化 Session State
if 'step' not in st.session_state: st.session_state.step = 1
if 'final_outline' not in st.session_state: st.session_state.final_outline = ""

# 2. 側邊欄輸入
with st.sidebar:
    st.header("1. 研究設定")
    user_topic = st.text_input("輸入研究主題", "例如：策略管理對企業績效之影響")
    user_method = st.selectbox("選擇研究方法", list(METHOD_STEPS.keys()))
    
    if st.button("重置所有內容"):
        st.session_state.step = 1
        st.session_state.final_outline = ""
        st.experimental_rerun()

# 3. 主畫面流程

# === 步驟一：選擇缺口 ===
if st.session_state.step == 1:
    st.subheader("步驟 1：選擇您的研究缺口")
    st.info(f"系統針對「{user_topic}」為您匹配了以下常見的研究切入點：")
    
    # 動態生成缺口選項
    gap_options = [t.format(topic=user_topic) for t in GAPS_TEMPLATES]
    
    selected_gap = st.radio("請選擇一個最適合您的缺口：", gap_options)
    
    if st.button("下一步：輸入文獻"):
        st.session_state.selected_gap = selected_gap
        st.session_state.step = 2
        st.experimental_rerun()

# === 步驟二：輸入文獻 ===
elif st.session_state.step == 2:
    st.subheader("步驟 2：建立參考文獻")
    st.write(f"您選擇的缺口是：**{st.session_state.selected_gap}**")
    
    st.warning("請貼上您找到的真實文獻 (這樣論文才不會造假)")
    user_refs = st.text_area("請貼上文獻摘要 (一行一筆)：", height=200, 
                             value="1. Porter, M. E. (1980). Competitive Strategy.\n2. Barney, J. (1991). Firm Resources and Sustained Competitive Advantage.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("上一步"):
            st.session_state.step = 1
            st.experimental_rerun()
    with col2:
        if st.button("下一步：生成完整架構"):
            st.session_state.user_refs = user_refs
            st.session_state.step = 3
            st.experimental_rerun()

# === 步驟三：產出結果 ===
elif st.session_state.step == 3:
    st.subheader("步驟 3：您的論文架構草稿")
    st.success("生成完畢！您可以直接複製下方的內容到 Word 開始寫作。")
    
    # 呼叫產生器
    if not st.session_state.final_outline:
        st.session_state.final_outline = generate_outline(
            user_topic, 
            st.session_state.selected_gap, 
            user_method, 
            st.session_state.user_refs
        )
    
    # 顯示結果
    st.text_area("Markdown 原始碼 (可複製)", st.session_state.final_outline, height=600)
    
    st.download_button(
        label="📥 下載為 .md 檔案",
        data=st.session_state.final_outline,
        file_name="Thesis_Outline.md",
        mime="text/markdown"
    )
    
    if st.button("重新開始"):
        st.session_state.step = 1
        st.session_state.final_outline = ""
        st.experimental_rerun()

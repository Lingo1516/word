import streamlit as st
import re
from datetime import datetime

# --- 頁面設定 ---
st.set_page_config(page_title="論文結構化分析工具", layout="wide", page_icon="📝")

# --- 核心功能函式 ---

def generate_apa(author, year, title, source):
    """生成標準 APA 7 格式引註"""
    # 若資訊不全，給予預設值
    author = author if author else "Author, A. A."
    year = year if year else "n.d."
    title = title if title else "Title of the article"
    source = source if source else "Source Name"
    
    return f"{author} ({year}). {title}. *{source}*."

def auto_parse_sections(text):
    """
    嘗試使用 Regular Expression 抓取常見的論文段落標題，
    將長文自動分割到對應的欄位中。
    """
    sections = {
        "introduction": "",
        "gap": "",
        "method": "",
        "result": "",
        "conclusion": ""
    }
    
    # 如果文字是空的，直接回傳
    if not text:
        return sections

    # 定義簡單的關鍵字正則表達式 (支援中文與英文常見標題)
    # 這裡僅為簡易範例，可根據需求擴充
    patterns = {
        "introduction": r"(前言|緒論|Introduction|Background)",
        "method": r"(研究方法|方法|Methodology|Methods)",
        "result": r"(研究結果|結果|Results|Findings)",
        "conclusion": r"(結論|討論|建議|Conclusion|Discussion)"
    }

    # 簡易切割邏輯 (尋找關鍵字位置)
    # 注意：這是一個簡易的 heuristic 方法，實際論文格式複雜，這裡做基礎輔助
    current_pos = 0
    sorted_indices = []
    
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            sorted_indices.append((match.start(), key))
    
    sorted_indices.sort()

    # 如果找不到任何標題，將全文放入前言
    if not sorted_indices:
        sections["introduction"] = text
        return sections

    # 依序填充內容
    for i, (start_idx, key) in enumerate(sorted_indices):
        end_idx = sorted_indices[i+1][0] if i+1 < len(sorted_indices) else len(text)
        # 抓取標題後的內容
        content = text[start_idx:end_idx]
        # 去除掉標題本身 (大約)
        content = re.sub(patterns[key], "", content, count=1, flags=re.IGNORECASE).strip()
        sections[key] = content

    return sections

# --- UI 介面設計 ---

st.title("📑 論文結構化整理助手")
st.markdown("""
此工具協助你將雜亂的論文內容拆解為核心架構。
**使用方式：** 在左側貼上全文，系統會嘗試自動分段；或者你可以手動填寫各區塊。
""")

# --- 側邊欄：文獻元數據 (Metadata) ---
with st.sidebar:
    st.header("1. 文獻基本資料")
    st.info("在此輸入引用資訊，將自動生成 APA 格式。")
    
    input_author = st.text_input("作者 (Author)", placeholder="例如: Wang, T. & Lee, C.")
    input_year = st.text_input("年份 (Year)", placeholder="例如: 2023")
    input_title = st.text_input("論文標題 (Title)", placeholder="輸入論文名稱")
    input_source = st.text_input("來源/期刊 (Source)", placeholder="例如: Journal of AI Research")

    st.markdown("---")
    st.caption("由 Streamlit 自動生成")

# --- 主畫面：雙欄設計 ---
col1, col2 = st.columns([1, 1])

# --- 左欄：輸入與編輯 ---
with col1:
    st.subheader("2. 內容輸入與編輯")
    
    # 原始全文輸入區 (用於自動分析)
    raw_text = st.text_area("在此貼上整篇論文摘要或全文 (自動分析用)", height=150, placeholder="貼上文字後，按 Ctrl+Enter...")
    
    # 初始化 session state 以儲存分段結果
    if 'parsed_data' not in st.session_state:
        st.session_state['parsed_data'] = auto_parse_sections("")

    # 按鈕：執行自動分析
    if st.button("⚡ 嘗試自動抓取段落"):
        st.session_state['parsed_data'] = auto_parse_sections(raw_text)
        st.success("已嘗試依據關鍵字分段，請在下方微調內容。")

    st.markdown("### 分段細節微調")
    
    # 使用 Expander 讓畫面不要太長
    with st.expander("📝 前言 / 背景 (Introduction)", expanded=True):
        intro_text = st.text_area("研究背景與現況", value=st.session_state['parsed_data'].get('introduction', ''), height=100)

    with st.expander("🔍 研究缺口 (Gap)", expanded=True):
        gap_text = st.text_area("既有研究不足之處", value="目前文獻多著重於...但對於...仍缺乏探討。", height=80)

    with st.expander("🛠 研究方法 (Methodology)", expanded=False):
        method_text = st.text_area("使用的模型、數據或實驗設計", value=st.session_state['parsed_data'].get('method', ''), height=100)

    with st.expander("📊 結果與結論 (Results & Conclusion)", expanded=False):
        result_text = st.text_area("核心發現與貢獻", value=st.session_state['parsed_data'].get('result', '') + "\n" + st.session_state['parsed_data'].get('conclusion', ''), height=100)

# --- 右欄：預覽與輸出 ---
with col2:
    st.subheader("3. 結構化筆記預覽")
    
    # 組合最終文字
    apa_citation = generate_apa(input_author, input_year, input_title, input_source)
    
    final_output = f"""# 論文筆記：{input_title if input_title else '未命名論文'}

## 📚 引用資訊 (APA Format)
> {apa_citation}

---

## 1. 研究背景 (Introduction)
{intro_text if intro_text else "（尚無內容）"}

## 2. 研究缺口 (Gap)
{gap_text if gap_text else "（尚無內容）"}

## 3. 研究目的與方法 (Purpose & Method)
{method_text if method_text else "（尚無內容）"}

## 4. 主要發現 (Key Findings)
{result_text if result_text else "（尚無內容）"}

---
*筆記生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""

    # 顯示 Markdown 結果
    st.markdown(final_output)
    
    st.markdown("---")
    # 下載按鈕
    st.download_button(
        label="📥 下載筆記 (Markdown)",
        data=final_output,
        file_name=f"Paper_Note_{input_year}.md",
        mime="text/markdown"
    )

import streamlit as st
from openai import OpenAI
import os

# --- 1. 頁面基礎設定 ---
st.set_page_config(page_title="AI 深度論文寫作系統 (終極版)", layout="wide", page_icon="🎓")

# --- 2. 狀態變數初始化 (Session State) ---
# 這些變數是用來記憶你的進度，不會因為按按鈕就消失
if 'step' not in st.session_state: st.session_state.step = 1
if 'selected_gap' not in st.session_state: st.session_state.selected_gap = ""
if 'real_references' not in st.session_state: st.session_state.real_references = ""
if 'outline' not in st.session_state: st.session_state.outline = ""
if 'thesis_content' not in st.session_state: st.session_state.thesis_content = {}
if 'gaps_suggestion' not in st.session_state: st.session_state.gaps_suggestion = ""

# --- 3. 側邊欄：設定區 ---
with st.sidebar:
    st.title("⚙️ 核心設定")
    
    # API Key 輸入
    api_key = st.text_input("請輸入 OpenAI API Key", type="password", help="請貼上 sk- 開頭的密鑰")
    
    # [新增] 模型選擇選單 (解決 404 錯誤的關鍵)
    st.write("🤖 選擇 AI 模型")
    selected_model = st.selectbox(
        "建議使用 gpt-4o-mini (速度快且便宜)",
        ["gpt-4o-mini", "gpt-3.5-turbo", "gpt-4", "gpt-4o"],
        index=0  # 預設選第一個，確保不會報錯
    )
    
    # 初始化 OpenAI 客戶端
    client = None
    if api_key:
        try:
            client = OpenAI(api_key=api_key)
            st.success(f"✅ 已連接 ({selected_model})")
        except Exception as e:
            st.error(f"API Key 格式錯誤: {e}")
    
    st.divider()
    st.header("📝 研究主題")
    topic = st.text_input("研究主題", "例如：生成式AI對大學生學習動機之影響")
    method = st.selectbox("研究方法", 
        ["量化研究 - 問卷調查 (Survey)", 
         "質性研究 - 深度訪談 (Interview)", 
         "混合研究法 (Mixed Methods)", 
         "實驗法 (Experiment)"])
    
    st.info(f"目前進度：第 {st.session_state.step} / 4 階段")

# --- 4. 核心 AI 呼叫函式 (新版語法) ---
def ask_gpt(prompt):
    """呼叫 GPT 進行思考與寫作"""
    if not client:
        return "⚠️ 錯誤：請先在側邊欄輸入有效的 OpenAI API Key。"
    
    try:
        response = client.chat.completions.create(
            model=selected_model,  # 使用使用者選擇的模型
            messages=[
                {"role": "system", "content": "你是一位嚴謹的學術論文指導教授，專精於繁體中文學術寫作。絕不捏造文獻，若無真實來源請標註 [需補充文獻]。寫作風格需學術、客觀、邏輯縝密。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        error_msg = str(e)
        if "model_not_found" in error_msg or "404" in error_msg:
            return "❌ **權限錯誤**：您的 API Key 無法使用此模型。\n👉 請在左側側邊欄將模型改為 **'gpt-4o-mini'** 或 **'gpt-3.5-turbo'** 即可解決。"
        return f"❌ API 呼叫錯誤：{error_msg}"

# --- 5. 主畫面邏輯 ---

st.title("🎓 AI 深度論文寫作系統 (終極修復版)")

if not api_key:
    st.warning("👉 請先在左側側邊欄輸入 OpenAI API Key 才能開始。")
    st.stop()

# === 第一階段：找出缺口 (Gap Analysis) ===
if st.session_state.step == 1:
    st.header("第一階段：研究缺口分析")
    st.markdown(f"針對主題 **「{topic}」**，AI 將為您尋找學術缺口。")
    
    if st.button("🔍 分析研究缺口"):
        with st.spinner("AI 正在閱讀文獻邏輯..."):
            prompt = f"""
            請針對研究主題「{topic}」，提出 3 個具有學術價值的「研究缺口 (Research Gap)」。
            要求：
            1. 缺口必須具體，邏輯合理。
            2. 每個缺口請附帶一個「暫定題目」。
            3. 請用條列式呈現。
            """
            st.session_state.gaps_suggestion = ask_gpt(prompt)
            
    if st.session_state.gaps_suggestion:
        st.markdown("### 🎯 AI 建議選項：")
        st.markdown(st.session_state.gaps_suggestion)
        
        st.divider()
        st.subheader("請選擇並確認您的缺口：")
        user_selected_gap = st.text_area("請將上方您想要的缺口與題目複製貼上到這裡：", height=100)
        
        if st.button("✅ 確認缺口，下一步"):
            if user_selected_gap:
                st.session_state.selected_gap = user_selected_gap
                st.session_state.step = 2
                st.rerun()
            else:
                st.error("請先貼上您選擇的研究缺口")

# === 第二階段：真實文獻導入 (Real Literature) ===
elif st.session_state.step == 2:
    st.header("第二階段：建立真實文獻庫")
    st.info("💡 為避免 AI 造假，請您提供 3-5 篇真實的參考文獻摘要，AI 將基於這些內容進行寫作。")
    
    st.markdown(f"**您的研究缺口：**\n> {st.session_state.selected_gap}")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔑 幫我生成搜尋關鍵字"):
            prompt = f"針對題目「{st.session_state.selected_gap}」，請列出 5 組 Google Scholar 搜尋關鍵字（中英文皆要）。"
            st.write(ask_gpt(prompt))
            
    with col2:
        st.markdown("### 📥 貼上文獻摘要")
        references_input = st.text_area("請貼上真實文獻 (格式：作者, 年份, 標題, 重要發現...)", height=300, 
                                      placeholder="範例：\n1. 王小明 (2023). 生成式AI教學應用. 發現AI能提升滿意度...\n2. Smith (2024). AI in Education. Found that...")
        
        if st.button("✅ 文獻確認，生成大綱"):
            if references_input:
                st.session_state.real_references = references_input
                st.session_state.step = 3
                st.rerun()
            else:
                st.warning("請至少貼入一篇文獻摘要，以確保寫作內容真實。")

# === 第三階段：架構生成 (Outline) ===
elif st.session_state.step == 3:
    st.header("第三階段：論文架構藍圖")
    
    if not st.session_state.outline:
        with st.spinner("正在規劃章節架構..."):
            prompt = f"""
            請為以下研究撰寫一份詳細的「學術論文大綱」，目標總字數 15,000 字。
            題目：{st.session_state.selected_gap}
            參考文獻：{st.session_state.real_references}
            方法：{method}
            要求：包含五章（緒論、文獻探討、方法、結果、結論），列出每節重點。
            """
            st.session_state.outline = ask_gpt(prompt)
    
    st.markdown(st.session_state.outline)
    
    if st.button("✅ 架構確認，開始寫作"):
        st.session_state.step = 4
        st.rerun()

# === 第四階段：分章寫作 (Writing) ===
elif st.session_state.step == 4:
    st.header("第四階段：AI 深度寫作")
    st.markdown("請依序點擊按鈕，逐章生成內容。")
    
    tabs = st.tabs(["第一章：緒論", "第二章：文獻探討", "第三章：研究方法", "第四章：研究結果", "第五章：結論"])
    
    def write_chapter(chapter_name, focus):
        return ask_gpt(f"""
        撰寫論文「{chapter_name}」。
        題目：{st.session_state.selected_gap}
        文獻：{st.session_state.real_references}
        大綱：{st.session_state.outline}
        要求：至少 2000 字，學術語氣，Markdown 格式，重點：{focus}
        """)

    # 第一章
    with tabs[0]:
        if "ch1" not in st.session_state.thesis_content:
            if st.button("✍️ 撰寫第一章"):
                with st.spinner("撰寫中..."):
                    st.session_state.thesis_content["ch1"] = write_chapter("第一章 緒論", "背景、動機、目的")
        if "ch1" in st.session_state.thesis_content: st.markdown(st.session_state.thesis_content["ch1"])

    # 第二章
    with tabs[1]:
        if "ch2" not in st.session_state.thesis_content:
            if st.button("✍️ 撰寫第二章"):
                with st.spinner("撰寫中..."):
                    st.session_state.thesis_content["ch2"] = write_chapter("第二章 文獻探討", "理論回顧、缺口推導")
        if "ch2" in st.session_state.thesis_content: st.markdown(st.session_state.thesis_content["ch2"])

    # 第三章
    with tabs[2]:
        if "ch3" not in st.session_state.thesis_content:
            if st.button("✍️ 撰寫第三章"):
                with st.spinner("撰寫中..."):
                    st.session_state.thesis_content["ch3"] = write_chapter("第三章 研究方法", f"{method} 執行步驟")
        if "ch3" in st.session_state.thesis_content: st.markdown(st.session_state.thesis_content["ch3"])

    # 第四章
    with tabs[3]:
        st.info("⚠️ 注意：AI 生成的數據為虛擬範例，請替換為真實分析結果。")
        if "ch4" not in st.session_state.thesis_content:
            if st.button("✍️ 撰寫第四章 (模擬)"):
                with st.spinner("撰寫中..."):
                    st.session_state.thesis_content["ch4"] = write_chapter("第四章 研究結果", "模擬數據呈現與解釋")
        if "ch4" in st.session_state.thesis_content: st.markdown(st.session_state.thesis_content["ch4"])

    # 第五章
    with tabs[4]:
        if "ch5" not in st.session_state.thesis_content:
            if st.button("✍️ 撰寫第五章"):
                with st.spinner("撰寫中..."):
                    st.session_state.thesis_content["ch5"] = write_chapter("第五章 結論", "總結、建議、限制")
        if "ch5" in st.session_state.thesis_content: st.markdown(st.session_state.thesis_content["ch5"])

    st.divider()
    # 下載
    full_text = "\n\n".join(st.session_state.thesis_content.values())
    if full_text:
        st.download_button("📥 下載完整論文 (Markdown)", full_text, "Thesis_Draft.md")

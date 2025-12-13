import streamlit as st
import google.generativeai as genai
import time
from google.api_core import exceptions

# --- 系統設定 ---
st.set_page_config(page_title="論文寫作助手 (全功能修復版)", layout="wide", page_icon="🎓")

# ==========================================
# ⚡⚡⚡ API Key (已鎖定) ⚡⚡⚡
FIXED_KEY = "AIzaSyBM4Z9-cXuZRqWjBwRsErvmFmdpfc3iJ1E"
# ==========================================

# --- 核心：極速引擎 (Flash) ---
def ask_gemini_fast(prompt, user_rules=""):
    genai.configure(api_key=FIXED_KEY)
    
    full_prompt = prompt
    if user_rules:
        full_prompt = f"【請遵守以下學術規則】\n{user_rules}\n\n【任務內容】\n{prompt}"

    # 只用 Flash，確保速度快、不報錯
    model = genai.GenerativeModel("gemini-1.5-flash")
    
    try:
        response = model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=8192,
            )
        )
        return response.text
    except Exception as e:
        return f"⚠️ 系統繁忙，請稍後重試 ({str(e)})"

# --- 初始化 ---
if 'step' not in st.session_state: st.session_state.step = 0
if 'final_title' not in st.session_state: st.session_state.final_title = ""
if 'refs' not in st.session_state: st.session_state.refs = ""
if 'outline' not in st.session_state: st.session_state.outline = ""
if 'content' not in st.session_state: st.session_state.content = {}
if 'global_rules' not in st.session_state: 
    st.session_state.global_rules = "1. 使用繁體中文學術用語\n2. 格式符合APA第7版\n3. 邏輯嚴謹"

# --- 側邊欄 (功能全開) ---
with st.sidebar:
    st.header("⚙️ 論文設定面板")
    st.success("✅ 引擎狀態：極速連線中")
    
    st.divider()
    
    # 1. 關鍵字選單 (加回來了！)
    st.subheader("🔑 關鍵字設定")
    business_keywords = [
        "策略管理", "競爭優勢", "ESG", "永續發展", "企業社會責任 (CSR)",
        "消費者行為", "顧客滿意度", "品牌形象", "服務品質",
        "人力資源管理", "組織承諾", "教育訓練", "領導風格",
        "供應鏈管理", "綠色供應鏈", "金融科技 (FinTech)", "數位轉型"
    ]
    selected_kws = st.multiselect("選擇商學院關鍵字：", business_keywords)
    custom_kw = st.text_input("自訂補充關鍵字：")
    
    final_kws = selected_kws.copy()
    if custom_kw: final_kws.append(custom_kw)
    keywords_str = ", ".join(final_kws)

    st.divider()

    # 2. 研究方法詳細選單 (MCDM/FCM 加回來了！)
    st.subheader("📊 研究方法")
    method_category = st.selectbox("方法分類", 
        ["MCDM (多準則決策)", "量化研究 (問卷/統計)", "質性研究 (訪談/個案)", "混合研究"]
    )
    
    final_method = method_category
    if "MCDM" in method_category:
        st.markdown("**選擇 MCDM 工具：**")
        # 這裡有你截圖裡的那些選項
        mcdm_tools = st.multiselect("勾選工具 (可複選)：", 
            ["Delphi (德爾菲法)", "Fuzzy Delphi", "AHP (層級分析)", "Fuzzy AHP", 
             "ANP (網絡分析)", "FCM (模糊認知圖)", "DEMATEL", "TOPSIS", "VIKOR"],
            default=["Delphi (德爾菲法)", "AHP (層級分析)"]
        )
        final_method = f"多準則決策 ({' + '.join(mcdm_tools)})" if mcdm_tools else "多準則決策"

    st.divider()

    # 3. 論文格式
    st.subheader("📝 格式設定")
    paper_type = st.radio("論文類型", ["學位論文", "期刊論文"])
    
    if paper_type == "學位論文":
        CHAPTERS = [
            {"key": "ch1", "name": "第一章 緒論"},
            {"key": "ch2", "name": "第二章 文獻探討"},
            {"key": "ch3", "name": "第三章 研究方法"},
            {"key": "ch4", "name": "第四章 分析結果"},
            {"key": "ch5", "name": "第五章 結論與建議"}
        ]
    else:
        CHAPTERS = [
            {"key": "ch1", "name": "1. 前言"},
            {"key": "ch2", "name": "2. 文獻回顧"},
            {"key": "ch3", "name": "3. 研究方法"},
            {"key": "ch4", "name": "4. 結果與討論"},
            {"key": "ch5", "name": "5. 結論"}
        ]
        
    rules = st.text_area("寫作規則", value=st.session_state.global_rules, height=100)
    st.session_state.global_rules = rules

# --- 主畫面 ---
st.title("🎓 論文寫作助手 (全功能修復版)")

# === 步驟 0: 題目 ===
if st.session_state.step == 0:
    st.header("步驟 1：產生題目")
    if st.button("✨ 根據設定產生題目", type="primary"):
        if not keywords_str:
            st.error("請在側邊欄選擇或輸入關鍵字")
        else:
            with st.spinner("AI 正在構思題目 (Flash Mode)..."):
                prompt = f"""
                領域：管理科學與工程。
                關鍵字：{keywords_str}。
                研究方法：{final_method}。
                
                請產生 3 個具備學術深度的繁體中文博士論文題目。
                每個題目下方請附上 1 行簡短的設計理念。
                """
                st.session_state.generated_titles = ask_gemini_fast(prompt, st.session_state.global_rules)
    
    if 'generated_titles' in st.session_state:
        st.info("💡 AI 建議題目：")
        st.markdown(st.session_state.generated_titles)

    st.markdown("---")
    title_input = st.text_input("👇 請輸入或複製最終題目：", value=st.session_state.final_title)
    if st.button("✅ 鎖定題目，下一步"):
        if title_input:
            st.session_state.final_title = title_input
            st.session_state.step = 1
            st.rerun()
        else:
            st.warning("請輸入題目")

# === 步驟 1: 文獻 ===
elif st.session_state.step == 1:
    st.header("步驟 2：導入文獻")
    st.markdown(f"> **當前題目**：{st.session_state.final_title}")
    
    st.session_state.refs = st.text_area("請貼上參考文獻 (AI將依據此內容寫作)：", value=st.session_state.refs, height=300)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("⬅️ 上一步"):
            st.session_state.step = 0
            st.rerun()
    with col2:
        if st.button("下一步 (生成大綱) ➡️", type="primary"):
            st.session_state.step = 2
            st.rerun()

# === 步驟 2: 大綱 ===
elif st.session_state.step == 2:
    st.header("步驟 3：生成大綱")
    
    if st.button("✨ 生成論文大綱", type="primary"):
        with st.spinner("正在規劃架構..."):
            prompt = f"""
            題目：{st.session_state.final_title}
            研究方法：{final_method}
            參考文獻：{st.session_state.refs[:1500]}
            
            請寫出詳細的論文大綱結構。
            """
            st.session_state.outline = ask_gemini_fast(prompt, st.session_state.global_rules)
            st.rerun()
            
    if st.session_state.outline:
        st.markdown(st.session_state.outline)
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("⬅️ 上一步"):
                st.session_state.step = 1
                st.rerun()
        with col2:
            if st.button("下一步 (開始寫作) ➡️", type="primary"):
                st.session_state.step = 3
                st.rerun()

# === 步驟 3: 寫作 ===
elif st.session_state.step == 3:
    st.header("步驟 4：逐章寫作")
    
    chapter_map = {ch['key']: ch['name'] for ch in CHAPTERS}
    selected_ch = st.selectbox("選擇要撰寫的章節", list(chapter_map.keys()), format_func=lambda x: chapter_map[x])
    
    if st.button(f"🚀 撰寫 {chapter_map[selected_ch]}", type="primary"):
        with st.spinner("AI 寫作中 (Flash 極速版)..."):
            prompt = f"""
            題目：{st.session_state.final_title}
            章節：{chapter_map[selected_ch]}
            大綱：{st.session_state.outline}
            文獻：{st.session_state.refs[:2500]}
            方法：{final_method}
            
            請撰寫本章節內容，字數約 1500-2000 字，語氣需專業學術。
            請勿使用 LaTeX，直接輸出純文字或 Markdown 表格。
            """
            st.session_state.content[selected_ch] = ask_gemini_fast(prompt, st.session_state.global_rules)
            st.rerun()
            
    # 顯示內容
    if selected_ch in st.session_state.content:
        st.markdown("### 📄 內容預覽")
        st.markdown(st.session_state.content[selected_ch])
        
    st.markdown("---")
    st.subheader("📊 進度概覽")
    cols = st.columns(len(CHAPTERS))
    for idx, ch in enumerate(CHAPTERS):
        status = "✅" if ch['key'] in st.session_state.content else "⬜"
        cols[idx].metric(ch['name'], status)

    if st.button("💾 全部完成，前往下載"):
        st.session_state.step = 4
        st.rerun()

# === 步驟 4: 下載 ===
elif st.session_state.step == 4:
    st.header("步驟 5：下載論文")
    
    final_doc = f"# {st.session_state.final_title}\n\n"
    final_doc += f"**研究方法**：{final_method}\n\n---\n\n"
    
    for ch in CHAPTERS:
        if ch['key'] in st.session_state.content:
            final_doc += f"\n\n## {ch['name']}\n{st.session_state.content[ch['key']]}\n"
    
    st.download_button("📥 下載完整論文 (Markdown)", final_doc, "thesis.md")
    
    if st.button("🔄 開始新論文"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

import streamlit as st
from groq import Groq
import time

# --- 系統設定 ---
st.set_page_config(page_title="論文寫作助手 (Groq全功能版)", layout="wide", page_icon="⚡")

# ==========================================
# ⚡⚡⚡ 你的 Groq Key (已鎖定) ⚡⚡⚡
FIXED_KEY = "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"
# ==========================================

# --- 核心：Groq 引擎 ---
def ask_groq_fast(prompt, user_rules=""):
    # 設定 Client
    client = Groq(api_key=FIXED_KEY)

    # 組合 Prompt
    system_msg = "你是一位管理科學與工程領域的頂尖研究員。請務必使用『繁體中文』回答。寫作風格需專業、學術、邏輯嚴謹。"
    if user_rules:
        system_msg += f"\n【請嚴格遵守規則】：{user_rules}"

    try:
        # 發送請求 (使用 Llama-3-70b)
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ],
            model="llama3-70b-8192", 
            temperature=0.6, 
            max_tokens=4096,
        )
        return chat_completion.choices[0].message.content

    except Exception as e:
        return f"❌ 連線錯誤: {str(e)}"

# --- 初始化 ---
if 'step' not in st.session_state: st.session_state.step = 0
if 'final_title' not in st.session_state: st.session_state.final_title = ""
if 'refs' not in st.session_state: st.session_state.refs = ""
if 'outline' not in st.session_state: st.session_state.outline = ""
if 'content' not in st.session_state: st.session_state.content = {}
if 'global_rules' not in st.session_state: 
    st.session_state.global_rules = "1. 必須使用繁體中文\n2. 格式符合APA第7版\n3. 內容具體，拒絕空泛"

# --- 側邊欄 (完整功能) ---
with st.sidebar:
    st.header("⚡ 引擎：Groq Llama 3")
    st.success("✅ 已鎖定 Key，連線正常")
    
    st.divider()

    # 1. 關鍵字選單
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

    # 2. 研究方法 (包含你要的 FCM)
    st.subheader("📊 研究方法")
    method_category = st.selectbox("方法分類", 
        ["MCDM (多準則決策)", "量化研究 (問卷/統計)", "質性研究 (訪談/個案)", "混合研究"]
    )
    
    final_method = method_category
    if "MCDM" in method_category:
        st.markdown("**選擇 MCDM 工具：**")
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
st.title("⚡ 論文寫作助手 (Groq 全功能版)")

# === 步驟 0: 題目 ===
if st.session_state.step == 0:
    st.header("步驟 1：產生題目")
    if st.button("✨ 秒速生成題目", type="primary"):
        if not keywords_str:
            st.error("請在側邊欄選擇或輸入關鍵字")
        else:
            with st.spinner("AI 思考中..."):
                prompt = f"領域：管理科學與工程。關鍵字：{keywords_str}。方法：{final_method}。請產生 3 個繁體中文博士論文題目，並附帶簡短設計理念。"
                st.session_state.generated_titles = ask_groq_fast(prompt, st.session_state.global_rules)
    
    if 'generated_titles' in st.session_state:
        st.info("💡 參考題目：")
        st.markdown(st.session_state.generated_titles)

    title_input = st.text_input("👇 輸入最終題目", value=st.session_state.final_title)
    if st.button("下一步"):
        if title_input:
            st.session_state.final_title = title_input
            st.session_state.step = 1
            st.rerun()

# === 步驟 1: 文獻 ===
elif st.session_state.step == 1:
    st.header("步驟 2：導入文獻")
    st.markdown(f"> **當前題目**：{st.session_state.final_title}")
    st.session_state.refs = st.text_area("請貼上文獻列表", value=st.session_state.refs, height=200)
    
    col1, col2 = st.columns([1,1])
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
    if st.button("✨ 秒速生成大綱", type="primary"):
        with st.spinner("規劃中..."):
            prompt = f"題目：{st.session_state.final_title}\n方法：{final_method}\n文獻：{st.session_state.refs[:1500]}\n請撰寫詳細大綱。"
            st.session_state.outline = ask_groq_fast(prompt, st.session_state.global_rules)
            st.rerun()
            
    if st.session_state.outline:
        st.markdown(st.session_state.outline)
        
        col1, col2 = st.columns([1,1])
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
    selected_ch = st.selectbox("選擇章節", list(chapter_map.keys()), format_func=lambda x: chapter_map[x])
    
    if st.button(f"🚀 撰寫 {chapter_map[selected_ch]}", type="primary"):
        with st.spinner("極速寫作中..."):
            prompt = f"""
            題目：{st.session_state.final_title}
            章節：{chapter_map[selected_ch]}
            大綱：{st.session_state.outline}
            文獻：{st.session_state.refs[:2500]}
            方法：{final_method}
            
            請撰寫本章節內容，字數約 1500 字，學術語氣。
            請直接輸出內容。
            """
            st.session_state.content[selected_ch] = ask_groq_fast(prompt, st.session_state.global_rules)
            st.rerun()
            
    if selected_ch in st.session_state.content:
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
    st.header("步驟 5：下載檔案")
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

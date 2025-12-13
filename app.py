import streamlit as st
from groq import Groq
import time

# --- 系統設定 ---
st.set_page_config(page_title="論文寫作助手 (深度模擬版)", layout="wide", page_icon="📊")

# ==========================================
# ⚡⚡⚡ Groq Key (已鎖定) ⚡⚡⚡
FIXED_KEY = "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"
# ==========================================

# --- 核心：Groq 引擎 (Llama 3.3) ---
def ask_groq_simulation(prompt, chapter_type, method_name, user_rules=""):
    # 設定 Client
    client = Groq(api_key=FIXED_KEY)

    # 針對不同章節的「強制指令」
    system_instruction = f"""
    你是一位管理科學與工程領域的教授。
    當前任務：撰寫博士論文的「{chapter_type}」。
    研究方法：{method_name}。
    
    【最高指導原則】：
    1. 使用繁體中文。
    2. **嚴禁使用「[請在此插入數據]」之類的佔位符。**
    3. **必須「模擬」出一套真實、合理的數據與情境。**
    4. 如果是第四章，請務必生成 Markdown 表格來展示分析結果（如：迴歸表、權重表、矩陣）。
    5. 如果是第三章，請列出該方法論的數學公式或運算步驟。
    """

    if user_rules:
        system_instruction += f"\n【使用者額外規則】：{user_rules}"

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile", 
            temperature=0.6, 
            max_tokens=6000, # 開大一點讓它寫數據
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

# --- 側邊欄 (維持您要的原有架構) ---
with st.sidebar:
    st.header("⚡ 論文設定")
    st.success("✅ 引擎：Llama 3.3 (數據模擬模式)")
    
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

    # 2. 研究方法 (維持完整選單)
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
st.title("📊 論文寫作助手 (深度數據模擬版)")

# === 步驟 0: 題目 ===
if st.session_state.step == 0:
    st.header("步驟 1：產生題目")
    if st.button("✨ 秒速生成題目", type="primary"):
        if not keywords_str:
            st.error("請在側邊欄選擇或輸入關鍵字")
        else:
            with st.spinner("AI 正在構思研究設計..."):
                prompt = f"""
                領域：管理科學與工程。
                關鍵字：{keywords_str}。
                研究方法：{final_method}。
                
                請產生 3 個繁體中文博士論文題目。
                要求：題目需反映出方法的應用（例如：基於 FCM 之...研究）。
                每個題目下方請附上 1 行簡短設計理念。
                """
                # 這裡 chapter_type 填 "題目發想"
                st.session_state.generated_titles = ask_groq_simulation(prompt, "題目發想", final_method, st.session_state.global_rules)
    
    if 'generated_titles' in st.session_state:
        st.info("💡 參考題目：")
        st.markdown(st.session_state.generated_titles)

    st.markdown("---")
    title_input = st.text_input("👇 輸入最終題目", value=st.session_state.final_title)
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
    st.session_state.refs = st.text_area("請貼上文獻列表 (這將決定公式與模型的理論基礎)：", value=st.session_state.refs, height=200)
    
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
    if st.button("✨ 生成架構與大綱", type="primary"):
        with st.spinner("正在規劃研究邏輯..."):
            prompt = f"""
            題目：{st.session_state.final_title}
            研究方法：{final_method}
            文獻：{st.session_state.refs[:1500]}
            
            請撰寫詳細大綱。
            特別要求：
            1. 第三章必須明確列出會用到的公式或模型步驟。
            2. 第四章必須規劃要展示哪些數據表格。
            """
            st.session_state.outline = ask_groq_simulation(prompt, "大綱規劃", final_method, st.session_state.global_rules)
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

# === 步驟 3: 寫作 (核心修改處) ===
elif st.session_state.step == 3:
    st.header("步驟 4：逐章寫作 (含數據模擬)")
    
    chapter_map = {ch['key']: ch['name'] for ch in CHAPTERS}
    selected_ch = st.selectbox("選擇章節", list(chapter_map.keys()), format_func=lambda x: chapter_map[x])
    
    # 根據章節動態調整提示詞
    if "ch3" in selected_ch or "方法" in chapter_map[selected_ch]:
        extra_hint = "【重點】：請詳細列出本研究使用的數學公式、變數定義、模型建構步驟。如果是 MCDM，請列出矩陣計算公式；如果是量化，請列出迴歸方程式。"
    elif "ch4" in selected_ch or "結果" in chapter_map[selected_ch]:
        extra_hint = f"【重點】：請務必「模擬」出一套漂亮的數據結果。請使用 Markdown 表格展示分析結果（例如：{final_method} 的運算結果、權重表、相關係數表）。數據必須顯著且符合邏輯，不要留空。"
    elif "ch5" in selected_ch or "結論" in chapter_map[selected_ch]:
        extra_hint = "【重點】：請根據第四章模擬出來的數據結果，進行深入討論與管理意涵的闡述。"
    else:
        extra_hint = "【重點】：請引用文獻進行論述。"

    if st.button(f"🚀 撰寫 {chapter_map[selected_ch]}", type="primary"):
        with st.spinner("AI 正在運算與寫作 (Llama 3.3)..."):
            prompt = f"""
            題目：{st.session_state.final_title}
            章節：{chapter_map[selected_ch]}
            大綱：{st.session_state.outline}
            文獻：{st.session_state.refs[:2500]}
            
            {extra_hint}
            
            請撰寫本章節內容，字數約 2000 字，學術語氣。
            """
            # 呼叫新的 simulation 函數
            st.session_state.content[selected_ch] = ask_groq_simulation(
                prompt, 
                chapter_map[selected_ch], 
                final_method, 
                st.session_state.global_rules
            )
            st.rerun()
            
    # 顯示內容
    if selected_ch in st.session_state.content:
        st.markdown(f"### 📄 {chapter_map[selected_ch]} 預覽")
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

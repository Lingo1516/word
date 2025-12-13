import streamlit as st
from groq import Groq
import time

# --- 系統設定 ---
st.set_page_config(page_title="論文寫作助手 (邏輯連貫版)", layout="wide", page_icon="🎓")

# ==========================================
# ⚡⚡⚡ Groq Key (已鎖定) ⚡⚡⚡
FIXED_KEY = "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"
# ==========================================

# --- 核心：Groq 引擎 (Llama 3.3 深度邏輯模式) ---
def ask_groq_strict_logic(prompt, chapter_type, method_name, refs, outline, user_rules=""):
    client = Groq(api_key=FIXED_KEY)

    # 基礎設定
    base_role = "你是一位管理科學與工程領域的嚴格教授，專精於定量分析與決策模型。"

    # --- 強制邏輯串聯指令 ---
    
    # 針對【第三章：研究方法】的強制指令
    if "ch3" in chapter_type or "方法" in chapter_type:
        specific_instruction = f"""
        【當前任務】：撰寫第三章「研究方法」。
        【核心要求】：
        1. **拒絕空談**：你必須列出 {method_name} 的「數學公式」與「運算步驟」。
        2. **公式規範**：
           - 若是 FCM：必須列出狀態轉移函數 (Sigmoid function) 公式、推理矩陣公式 $A(k+1) = f(A(k) \cdot W)$。
           - 若是 AHP：必須列出特徵向量計算公式、CI/CR 一致性檢定公式。
           - 若是 Delphi：必須列出四分位差 (IQR) 計算方式。
        3. **變數定義**：清楚定義本研究的操作型變數，這些變數必須對應到你在「第二章」回顧過的文獻。
        """

    # 針對【第四章：結果與討論】的強制指令 (這是您最不滿意的地方，這裡改動最大)
    elif "ch4" in chapter_type or "結果" in chapter_type:
        specific_instruction = f"""
        【當前任務】：撰寫第四章「分析結果」。
        【核心要求】：
        1. **數據必須連貫**：這裡的分析必須基於「第三章」設定的公式進行模擬。
        2. **拒絕簡單表格**：
           - **FCM 部分**：必須展示 $N \\times N$ 的「初始鄰接矩陣 (Initial Adjacency Matrix)」，數值需介於 -1 到 1 之間。展示收斂過程的數據。
           - **Delphi 部分**：展示每一輪專家的收斂度、IQR 值、共識偏差 (Consensus Deviation)。
           - **TOPSIS 部分**：展示決策矩陣、正規化矩陣、正負理想解距離 ($S^+, S^-$)。
        3. **文獻對話 (Literature Dialogue)**：
           - 每一個模擬出的數據結果（例如某個權重特別高），**必須**引用【文獻資料庫】中的學者觀點來解釋原因。
           - 例如：「矩陣顯示環境責任對企業形象的影響係數為 0.85，此高強度關聯印證了 [Author, Year] 的發現...」
        """

    # 針對【第五章：結論】的強制指令
    elif "ch5" in chapter_type or "結論" in chapter_type:
        specific_instruction = f"""
        【當前任務】：撰寫第五章「結論與建議」。
        【核心要求】：
        1. **回扣數據**：你的結論必須建立在「第四章」模擬出的數據結果之上，不能憑空下結論。
        2. **管理意涵**：針對該數據結果，對企業提出具體策略建議。
        """

    # 其他章節 (緒論、文獻)
    else:
        specific_instruction = f"""
        【當前任務】：撰寫 {chapter_type}。
        【核心要求】：引用下方提供的文獻庫，進行深入的學術論述。
        """

    # 組合最終 Prompt
    full_system_prompt = f"""
    {base_role}
    
    {specific_instruction}
    
    【使用者額外規則】：{user_rules}
    
    【本研究大綱】：{outline}
    
    【使用者提供的文獻資料庫 (必須引用)】：
    {refs[:5000]} 
    
    請以繁體中文撰寫，使用 Markdown 格式（表格、粗體、標題）。
    """

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": full_system_prompt},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile", 
            temperature=0.5, # 降低隨機性，確保邏輯嚴謹
            max_tokens=6500, 
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
    st.session_state.global_rules = "1. 必須使用繁體中文\n2. 數學公式與模型必須完整\n3. 數據結果必須引用文獻佐證"

# --- 側邊欄 ---
with st.sidebar:
    st.header("⚡ 論文設定")
    st.success("✅ 邏輯連貫模式：ON")
    st.info("🔧 此模式將強制檢查 Chapter 3 (公式) 與 Chapter 4 (數據) 的一致性。")
    
    st.divider()

    # 1. 關鍵字
    st.subheader("🔑 關鍵字")
    business_keywords = [
        "策略管理", "競爭優勢", "ESG", "永續發展", "CSR",
        "消費者行為", "滿意度", "品牌資產", "服務品質",
        "HRM", "組織承諾", "領導風格",
        "供應鏈韌性", "綠色供應鏈", "FinTech", "數位轉型"
    ]
    selected_kws = st.multiselect("選擇關鍵字：", business_keywords)
    custom_kw = st.text_input("自訂關鍵字：")
    
    final_kws = selected_kws.copy()
    if custom_kw: final_kws.append(custom_kw)
    keywords_str = ", ".join(final_kws)

    st.divider()

    # 2. 研究方法
    st.subheader("📊 研究方法")
    method_category = st.selectbox("方法分類", 
        ["MCDM (多準則)", "量化 (SEM/迴歸)", "質性 (個案)", "混合研究"]
    )
    
    final_method = method_category
    if "MCDM" in method_category:
        st.markdown("**MCDM 工具：**")
        mcdm_tools = st.multiselect("工具：", 
            ["Delphi", "Fuzzy Delphi", "AHP", "Fuzzy AHP", "ANP", "FCM (模糊認知圖)", "DEMATEL", "TOPSIS"],
            default=["Delphi", "FCM", "TOPSIS"]
        )
        final_method = f"MCDM ({' + '.join(mcdm_tools)})" if mcdm_tools else "MCDM"

    st.divider()

    # 3. 格式
    st.subheader("📝 格式")
    paper_type = st.radio("類型", ["學位論文", "期刊論文"])
    
    if paper_type == "學位論文":
        CHAPTERS = [
            {"key": "ch1", "name": "第一章 緒論"},
            {"key": "ch2", "name": "第二章 文獻探討"},
            {"key": "ch3", "name": "第三章 研究方法"},
            {"key": "ch4", "name": "第四章 分析結果"},
            {"key": "ch5", "name": "第五章 結論"}
        ]
    else:
        CHAPTERS = [
            {"key": "ch1", "name": "1. 前言"},
            {"key": "ch2", "name": "2. 文獻回顧"},
            {"key": "ch3", "name": "3. 研究方法"},
            {"key": "ch4", "name": "4. 結果"},
            {"key": "ch5", "name": "5. 結論"}
        ]
        
    rules = st.text_area("寫作規則", value=st.session_state.global_rules, height=100)
    st.session_state.global_rules = rules

# --- 主畫面 ---
st.title("📚 論文寫作助手 (邏輯連貫強化版)")

# === 步驟 0: 題目 ===
if st.session_state.step == 0:
    st.header("步驟 1：產生題目")
    if st.button("✨ 生成題目", type="primary"):
        if not keywords_str:
            st.error("請輸入關鍵字")
        else:
            with st.spinner("AI 構思中..."):
                prompt = f"領域：管理科學。關鍵字：{keywords_str}。方法：{final_method}。請產生 3 個繁體中文博士論文題目，並說明設計理念。"
                # 題目階段 outline 傳空
                st.session_state.generated_titles = ask_groq_strict_logic(prompt, "題目", final_method, "", "", st.session_state.global_rules)
    
    if 'generated_titles' in st.session_state:
        st.info("參考題目：")
        st.markdown(st.session_state.generated_titles)

    title_input = st.text_input("👇 輸入最終題目", value=st.session_state.final_title)
    if st.button("下一步"):
        if title_input:
            st.session_state.final_title = title_input
            st.session_state.step = 1
            st.rerun()

# === 步驟 1: 文獻 ===
elif st.session_state.step == 1:
    st.header("步驟 2：導入文獻 (AI將依此進行數據討論)")
    st.markdown(f"> **當前題目**：{st.session_state.final_title}")
    
    st.warning("請務必貼上豐富的文獻摘要。這些文獻將是第四章數據討論的基礎。")
    st.session_state.refs = st.text_area("文獻列表 (Author, Year, Title, Abstract...)", value=st.session_state.refs, height=400)
    
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
    if st.button("✨ 生成學術大綱", type="primary"):
        with st.spinner("規劃研究架構..."):
            prompt = f"""
            題目：{st.session_state.final_title}
            方法：{final_method}
            
            請撰寫詳細大綱。
            重點：
            1. 第三章需明確列出所使用的數學模型與步驟。
            2. 第四章需列出將進行的數據模擬與分析項目。
            """
            st.session_state.outline = ask_groq_strict_logic(prompt, "大綱", final_method, st.session_state.refs, "", st.session_state.global_rules)
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

# === 步驟 3: 寫作 (核心修改) ===
elif st.session_state.step == 3:
    st.header("步驟 4：逐章寫作")
    
    chapter_map = {ch['key']: ch['name'] for ch in CHAPTERS}
    selected_ch = st.selectbox("選擇章節", list(chapter_map.keys()), format_func=lambda x: chapter_map[x])
    
    # 動態提示
    hint_msg = ""
    if "ch3" in selected_ch:
        hint_msg = "🧮 正在撰寫第三章：AI 將被強制列出數學公式與運算步驟。"
    elif "ch4" in selected_ch:
        hint_msg = "📊 正在撰寫第四章：AI 將基於第三章的公式進行數據模擬 (矩陣、權重表)，並引用文獻進行討論。"

    if hint_msg: st.info(hint_msg)

    if st.button(f"🚀 撰寫 {chapter_map[selected_ch]}", type="primary"):
        with st.spinner(f"正在深度撰寫 {chapter_map[selected_ch]}..."):
            prompt = f"""
            題目：{st.session_state.final_title}
            章節：{chapter_map[selected_ch]}
            
            請撰寫本章節內容，字數約 2000-3000 字。
            請展現博士論文應有的邏輯深度與數學嚴謹度。
            """
            st.session_state.content[selected_ch] = ask_groq_strict_logic(
                prompt, 
                chapter_map[selected_ch], 
                final_method, 
                st.session_state.refs, 
                st.session_state.outline, # 把大綱也傳進去，確保連貫
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
    final_doc += f"**研究方法**：{final_method}\n\n"
    final_doc += f"**生成時間**：{time.strftime('%Y-%m-%d %H:%M')}\n\n"
    final_doc += "=================================================\n\n"
    
    for ch in CHAPTERS:
        if ch['key'] in st.session_state.content:
            final_doc += f"\n\n## {ch['name']}\n\n"
            final_doc += f"{st.session_state.content[ch['key']]}\n"
            final_doc += "\n\n-------------------------------------------------\n"
    
    # 提供 .txt 下載
    st.download_button(
        label="📥 下載純文字檔 (.txt)",
        data=final_doc,
        file_name=f"thesis_full_draft.txt",
        mime="text/plain"
    )
    
    if st.button("🔄 開始新論文"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

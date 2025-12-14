import streamlit as st
from groq import Groq
import time

# --- 系統設定 ---
st.set_page_config(page_title="論文寫作助手 (最終完美修復版)", layout="wide", page_icon="🎓")

# ==========================================
# ⚡⚡⚡ Groq Key (已鎖定) ⚡⚡⚡
FIXED_KEY = "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"
# ==========================================

# --- 核心：Groq 引擎 (Llama 3.3) ---
def ask_groq_engine(prompt, sys_role="你是一位學術專家。", user_rules=""):
    client = Groq(api_key=FIXED_KEY)
    
    full_prompt = f"""
    {sys_role}
    【使用者規則】：{user_rules}
    """
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": full_prompt},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile", 
            temperature=0.5, 
            max_tokens=8000, # 開到最大，盡量讓它寫多一點
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"❌ Error: {str(e)}"

# --- 初始化 ---
if 'step' not in st.session_state: st.session_state.step = 0
if 'final_title' not in st.session_state: st.session_state.final_title = ""
if 'refs' not in st.session_state: st.session_state.refs = ""
if 'parsed_refs' not in st.session_state: st.session_state.parsed_refs = "" 
if 'outline' not in st.session_state: st.session_state.outline = ""
if 'content' not in st.session_state: st.session_state.content = {}
if 'global_rules' not in st.session_state: 
    st.session_state.global_rules = "1. 必須使用繁體中文\n2. 數學公式與模型必須完整\n3. 數據結果必須引用文獻佐證"

# --- 側邊欄 ---
with st.sidebar:
    st.header("⚡ 論文設定")
    st.success("✅ 系統狀態：正常")
    
    st.divider()
    # 關鍵字
    st.subheader("🔑 關鍵字")
    business_keywords = ["策略管理", "ESG", "CSR", "消費者行為", "滿意度", "供應鏈", "FinTech", "數位轉型"]
    selected_kws = st.multiselect("選擇關鍵字：", business_keywords)
    custom_kw = st.text_input("自訂關鍵字：")
    final_kws = selected_kws + ([custom_kw] if custom_kw else [])
    keywords_str = ", ".join(final_kws)

    st.divider()
    # 方法 (這裡是修復崩潰的關鍵)
    st.subheader("📊 研究方法")
    method_category = st.selectbox("方法分類", ["MCDM", "量化", "質性", "混合"])
    final_method = method_category
    if "MCDM" in method_category:
        mcdm_tools = st.multiselect("工具：", 
            ["Delphi", "Fuzzy Delphi", "AHP", "Fuzzy AHP", "ANP", "FCM (模糊認知圖)", "TOPSIS"],
            default=["Delphi", "FCM (模糊認知圖)"] # ✅ 已修正：名稱完全一致
        )
        final_method = f"MCDM ({' + '.join(mcdm_tools)})" if mcdm_tools else "MCDM"

    st.divider()
    # 格式
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
        CHAPTERS = [{"key": f"ch{i}", "name": n} for i, n in enumerate(["前言", "文獻", "方法", "結果", "結論"], 1)]
    
    rules = st.text_area("寫作規則", value=st.session_state.global_rules, height=100)
    st.session_state.global_rules = rules

# --- 主畫面 ---
st.title("📚 論文寫作助手 (文獻量大優化版)")

# === 步驟 0: 題目 ===
if st.session_state.step == 0:
    st.header("步驟 1：產生題目")
    if st.button("✨ 生成題目", type="primary"):
        if not keywords_str: st.error("請輸入關鍵字")
        else:
            with st.spinner("AI 構思中..."):
                prompt = f"領域：管理科學。關鍵字：{keywords_str}。方法：{final_method}。請產生 3 個繁體中文博士論文題目，並說明設計理念。"
                st.session_state.generated_titles = ask_groq_engine(prompt, user_rules=st.session_state.global_rules)
    
    if 'generated_titles' in st.session_state:
        st.info("參考題目：")
        st.markdown(st.session_state.generated_titles)

    title_input = st.text_input("👇 輸入最終題目", value=st.session_state.final_title)
    if st.button("下一步"):
        if title_input:
            st.session_state.final_title = title_input
            st.session_state.step = 1
            st.rerun()

# === 步驟 1: 文獻 (針對 50 篇文獻的優化) ===
elif st.session_state.step == 1:
    st.header("步驟 2：導入文獻")
    st.markdown(f"> **當前題目**：{st.session_state.final_title}")
    
    st.info("💡 提示：如果您有 50 篇文獻，建議分批貼上解析，或者讓 AI 進行「歸納式」整理，以免字數爆掉。")
    
    raw_refs = st.text_area("原始文獻資料 (貼上越多越好)", value=st.session_state.refs, height=300)
    st.session_state.refs = raw_refs

    # 新增：AI 幫你整理文獻
    if st.button("✨ 呼叫 Groq 幫我解析文獻重點", type="secondary"):
        if not raw_refs:
            st.error("請先貼上一些文字")
        else:
            with st.spinner("Groq 正在極速閱讀與歸納 (這可能需要幾秒鐘)..."):
                # 這裡的 Prompt 做了修改，針對大量文獻優化
                prompt = f"""
                你是一位學術文獻分析專家。
                使用者提供了大量的文獻摘要（可能多達 50 篇）。
                由於輸出篇幅限制，**請不要試圖列出每一篇的表格**，這樣會寫不完。

                請採用**「主題式歸納法 (Thematic Analysis)」**來整理這些文獻：
                1. **分類一：理論基礎群** (列出相關的學者 Author, Year)
                2. **分類二：研究變數與發現** (歸納哪些學者做了類似變數)
                3. **分類三：方法論應用** (歸納哪些學者用了類似方法)
                4. **分類四：研究缺口** (總結這些文獻沒做到的地方)

                【目標】：讓使用者一眼看出這 50 篇文獻的整體脈絡，而不是流水帳。
                
                【原始資料】：
                {raw_refs[:20000]} 
                """
                # 注意：這裡只截取前 20000 字，因為 input 也有極限
                st.session_state.parsed_refs = ask_groq_engine(prompt, user_rules="使用 Markdown 結構化呈現，繁體中文")
                
    if st.session_state.parsed_refs:
        st.success("✅ 解析完成！已將大量文獻歸納為以下重點：")
        st.markdown(st.session_state.parsed_refs)
    
    col1, col2 = st.columns([1,1])
    with col1:
        if st.button("⬅️ 上一步"): st.session_state.step = 0; st.rerun()
    with col2:
        if st.button("下一步 (生成大綱) ➡️", type="primary"): st.session_state.step = 2; st.rerun()

# === 步驟 2: 大綱 ===
elif st.session_state.step == 2:
    st.header("步驟 3：生成大綱")
    if st.button("✨ 生成學術大綱", type="primary"):
        with st.spinner("規劃中..."):
            ref_context = st.session_state.parsed_refs if st.session_state.parsed_refs else st.session_state.refs
            prompt = f"""
            題目：{st.session_state.final_title}
            方法：{final_method}
            文獻背景：{ref_context[:3000]}
            
            請撰寫詳細大綱。
            重點：
            1. 第三章需明確列出數學模型 (公式)。
            2. 第四章需規劃數據模擬 (Matrix/Table)。
            """
            st.session_state.outline = ask_groq_engine(prompt, user_rules=st.session_state.global_rules)
            st.rerun()
            
    if st.session_state.outline:
        st.markdown(st.session_state.outline)
        col1, col2 = st.columns([1,1])
        with col1:
            if st.button("⬅️ 上一步"): st.session_state.step = 1; st.rerun()
        with col2:
            if st.button("下一步 (開始寫作) ➡️", type="primary"): st.session_state.step = 3; st.rerun()

# === 步驟 3: 寫作 ===
elif st.session_state.step == 3:
    st.header("步驟 4：逐章寫作")
    chapter_map = {ch['key']: ch['name'] for ch in CHAPTERS}
    selected_ch = st.selectbox("選擇章節", list(chapter_map.keys()), format_func=lambda x: chapter_map[x])
    
    if st.button(f"🚀 撰寫 {chapter_map[selected_ch]}", type="primary"):
        with st.spinner("寫作中..."):
            ref_context = st.session_state.parsed_refs if st.session_state.parsed_refs else st.session_state.refs
            
            special_instruction = ""
            if "ch3" in selected_ch:
                special_instruction = f"必須列出 {final_method} 的數學公式 (如 Sigmoid, Eigenvector)。"
            elif "ch4" in selected_ch:
                special_instruction = "必須模擬出複雜的數據表格 (矩陣/權重)，並引用文獻解釋數據意義。"
            elif "ch2" in selected_ch:
                special_instruction = "請根據文獻的「歸納結果」進行寫作，將相同觀點的學者寫在一起，避免流水帳。"
            
            prompt = f"""
            題目：{st.session_state.final_title}
            章節：{chapter_map[selected_ch]}
            大綱：{st.session_state.outline}
            文獻庫：{ref_context[:5000]}
            
            【特殊要求】：{special_instruction}
            
            請撰寫本章內容，約 2000 字。
            """
            st.session_state.content[selected_ch] = ask_groq_engine(prompt, user_rules=st.session_state.global_rules)
            st.rerun()
            
    if selected_ch in st.session_state.content:
        st.markdown(st.session_state.content[selected_ch])
        
    st.markdown("---")
    if st.button("💾 全部完成，前往下載"): st.session_state.step = 4; st.rerun()

# === 步驟 4: 下載 ===
elif st.session_state.step == 4:
    st.header("步驟 5：下載檔案")
    final_doc = f"# {st.session_state.final_title}\n\n**研究方法**：{final_method}\n\n"
    for ch in CHAPTERS:
        if ch['key'] in st.session_state.content:
            final_doc += f"\n\n## {ch['name']}\n{st.session_state.content[ch['key']]}\n"
    
    st.download_button("📥 下載純文字檔 (.txt)", final_doc, "thesis.txt", "text/plain")
    if st.button("🔄 重來"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

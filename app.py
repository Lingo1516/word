import streamlit as st
from groq import Groq
import google.generativeai as genai
import time

# --- 系統設定 ---
st.set_page_config(page_title="論文寫作助手 (海量文獻分批版)", layout="wide", page_icon="📚")

# --- 側邊欄：引擎與金鑰設定 ---
with st.sidebar:
    st.header("⚙️ 引擎設定")
    
    # 選擇引擎
    engine_choice = st.radio("選擇 AI 模型", ["Groq (Llama 3)", "Google (Gemini)"])
    
    api_key = ""
    if engine_choice == "Groq (Llama 3)":
        st.info("推薦！速度快，適合處理大量文字。")
        # 預設 Key，你也可以手動改
        default_groq = "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"
        api_key = st.text_input("Groq Key", value=default_groq, type="password")
    else:
        st.info("備用。如果 Groq 額度用完請切換此處。")
        api_key = st.text_input("Google Key", type="password")

    st.divider()

# --- 核心函數：呼叫 AI ---
def call_ai_api(prompt, sys_role="你是一位學術專家。"):
    if not api_key:
        return "⚠️ 請輸入 API Key"

    try:
        if engine_choice == "Groq (Llama 3)":
            client = Groq(api_key=api_key)
            completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": sys_role},
                    {"role": "user", "content": prompt}
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.5,
                max_tokens=4000, # 每次回應的長度限制
            )
            return completion.choices[0].message.content

        elif engine_choice == "Google (Gemini)":
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(
                f"{sys_role}\n\n{prompt}",
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=4000,
                    temperature=0.5
                )
            )
            return response.text

    except Exception as e:
        error_msg = str(e)
        if "413" in error_msg:
            return "❌ 錯誤 413：內容太長了！請使用下方的「分批解析」功能。"
        elif "429" in error_msg:
            return "❌ 錯誤 429：今日額度已滿，請切換引擎或更換 Key。"
        else:
            return f"❌ 連線錯誤: {error_msg}"

# --- 核心函數：智慧分批處理 (解決 50 篇論文讀不完的問題) ---
def smart_batch_process(long_text, method_name):
    # 1. 切割長文 (每 3000 字一塊，確保不爆 Token)
    chunk_size = 3000
    chunks = [long_text[i:i+chunk_size] for i in range(0, len(long_text), chunk_size)]
    total_chunks = len(chunks)
    
    # 進度條
    progress_bar = st.progress(0, text="準備開始分批閱讀...")
    combined_notes = ""
    
    # 2. 分批閱讀
    for i, chunk in enumerate(chunks):
        progress_bar.progress((i / total_chunks) * 0.8, text=f"正在研讀第 {i+1}/{total_chunks} 部分文獻...")
        
        prompt = f"""
        這是一份長篇文獻回顧的一部分（第 {i+1}/{total_chunks} 部分）。
        請幫我提取這段文字中的重要資訊，只需列點：
        1. 學者與年份 (Author & Year)
        2. 研究變數 (Variables)
        3. 與「{method_name}」相關的應用或發現
        
        【文獻片段】：
        {chunk}
        """
        # 這裡呼叫 AI，如果出錯會回傳錯誤訊息
        note = call_ai_api(prompt, sys_role="你是一位速讀助理。")
        combined_notes += f"\n\n--- 第 {i+1} 部分筆記 ---\n{note}"
        time.sleep(1) # 休息一下避免太快撞牆
        
    # 3. 最終統整
    progress_bar.progress(0.9, text="正在將所有筆記整合成最終表格...")
    
    final_prompt = f"""
    你現在擁有所有文獻的分批筆記。請將它們「去蕪存菁」，整合成一份完整的「學術文獻回顧表」。
    
    【要求】：
    1. 使用 Markdown 表格呈現。
    2. 欄位包含：[學者/年份], [研究主題], [變數/方法], [主要發現]。
    3. 必須涵蓋所有筆記中的不同文獻，不要遺漏。
    4. 繁體中文撰寫。
    
    【所有分批筆記】：
    {combined_notes}
    """
    
    final_result = call_ai_api(final_prompt, sys_role="你是一位博學的教授，擅長歸納大量文獻。")
    progress_bar.progress(1.0, text="完成！")
    
    return final_result

# --- 初始化 Session ---
if 'step' not in st.session_state: st.session_state.step = 0
if 'final_title' not in st.session_state: st.session_state.final_title = ""
if 'refs' not in st.session_state: st.session_state.refs = ""
if 'parsed_refs' not in st.session_state: st.session_state.parsed_refs = "" 
if 'outline' not in st.session_state: st.session_state.outline = ""
if 'content' not in st.session_state: st.session_state.content = {}
if 'global_rules' not in st.session_state: 
    st.session_state.global_rules = "1. 必須使用繁體中文\n2. 數學公式與模型必須完整\n3. 數據結果必須引用文獻佐證"

# --- 主畫面 ---
st.title("📚 論文寫作助手 (海量文獻專用版)")

# --- 側邊欄設定 ---
with st.sidebar:
    # 關鍵字
    business_keywords = ["策略管理", "ESG", "CSR", "消費者行為", "滿意度", "供應鏈", "FinTech", "數位轉型"]
    selected_kws = st.multiselect("選擇關鍵字：", business_keywords)
    custom_kw = st.text_input("自訂關鍵字：")
    final_kws = selected_kws + ([custom_kw] if custom_kw else [])
    keywords_str = ", ".join(final_kws)

    # 方法 (已修復崩潰問題)
    method_category = st.selectbox("方法分類", ["MCDM", "量化", "質性", "混合"])
    final_method = method_category
    if "MCDM" in method_category:
        mcdm_tools = st.multiselect("工具：", 
            ["Delphi", "Fuzzy Delphi", "AHP", "Fuzzy AHP", "ANP", "FCM (模糊認知圖)", "TOPSIS"],
            # ⬇️ 這裡修復了 Bug：default 的值必須跟上面的選項字串完全一樣
            default=["Delphi", "FCM (模糊認知圖)"] 
        )
        final_method = f"MCDM ({' + '.join(mcdm_tools)})" if mcdm_tools else "MCDM"

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

# === 步驟 0: 題目 ===
if st.session_state.step == 0:
    st.header("步驟 1：產生題目")
    if st.button("✨ 生成題目", type="primary"):
        if not keywords_str: st.error("請輸入關鍵字")
        else:
            with st.spinner("AI 構思中..."):
                prompt = f"領域：管理科學。關鍵字：{keywords_str}。方法：{final_method}。請產生 3 個繁體中文博士論文題目，並說明設計理念。"
                st.session_state.generated_titles = call_ai_api(prompt)
    
    if 'generated_titles' in st.session_state:
        st.info("參考題目：")
        st.markdown(st.session_state.generated_titles)

    title_input = st.text_input("👇 輸入最終題目", value=st.session_state.final_title)
    if st.button("下一步"):
        if title_input:
            st.session_state.final_title = title_input
            st.session_state.step = 1
            st.rerun()

# === 步驟 1: 文獻 (分批處理核心) ===
elif st.session_state.step == 1:
    st.header("步驟 2：導入大量文獻")
    st.markdown(f"> **當前題目**：{st.session_state.final_title}")
    
    st.info("💡 系統已啟用「分批處理模式」。請儘管貼上所有文獻（50篇也沒問題），系統會自動切塊閱讀，避免當機。")
    
    raw_refs = st.text_area("請貼上所有文獻資料", value=st.session_state.refs, height=400)
    st.session_state.refs = raw_refs

    # --- 這裡改用了智慧分批函數 ---
    if st.button("✨ 啟動深層文獻解析 (這會花一點時間)", type="secondary"):
        if not raw_refs:
            st.error("請先貼上一些文字")
        else:
            # 執行分批處理
            parsed_result = smart_batch_process(raw_refs, final_method)
            st.session_state.parsed_refs = parsed_result
            
    if st.session_state.parsed_refs:
        st.success("✅ 全文獻解析完成！AI 已讀完所有內容並歸納如下：")
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
            # 使用解析後的精華版文獻來做大綱
            ref_context = st.session_state.parsed_refs if st.session_state.parsed_refs else st.session_state.refs[:2000]
            prompt = f"""
            題目：{st.session_state.final_title}
            方法：{final_method}
            文獻背景：{ref_context}
            
            請撰寫詳細大綱。
            重點：
            1. 第三章需明確列出數學模型 (公式)。
            2. 第四章需規劃數據模擬 (Matrix/Table)。
            """
            st.session_state.outline = call_ai_api(prompt)
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
            ref_context = st.session_state.parsed_refs if st.session_state.parsed_refs else st.session_state.refs[:3000]
            
            special_instruction = ""
            if "ch3" in selected_ch:
                special_instruction = f"必須列出 {final_method} 的數學公式 (如 Sigmoid, Eigenvector)。"
            elif "ch4" in selected_ch:
                special_instruction = "必須模擬出複雜的數據表格 (矩陣/權重)，並引用文獻解釋數據意義。"
            
            prompt = f"""
            題目：{st.session_state.final_title}
            章節：{chapter_map[selected_ch]}
            大綱：{st.session_state.outline}
            文獻庫重點：{ref_context}
            
            【特殊要求】：{special_instruction}
            
            請撰寫本章內容，約 2000 字。請使用學術語氣。
            """
            st.session_state.content[selected_ch] = call_ai_api(prompt, sys_role=st.session_state.global_rules)
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

import streamlit as st
from groq import Groq
import time

# --- 系統設定 ---
st.set_page_config(page_title="論文寫作助手 (最終修復版)", layout="wide", page_icon="🎓")

# ==========================================
# ⚡⚡⚡ Groq Key (已鎖定) ⚡⚡⚡
FIXED_KEY = "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"
# ==========================================

# --- 核心：Groq 引擎 (Llama 3.3) ---
def ask_groq_deep_academic(prompt, chapter_type, method_name, refs, user_rules=""):
    client = Groq(api_key=FIXED_KEY)

    # 預設角色
    role_instruction = "你是一位管理科學與工程領域的頂尖教授。"

    # --- 針對不同章節的「特化指令」---
    if "文獻" in chapter_type or "ch2" in chapter_type:
        role_instruction = f"""
        你是一位嚴謹的文獻回顧專家。撰寫第二章「文獻探討」。
        【指令】：
        1. **深度閱讀**：引用下方提供的文獻資料庫。
        2. **綜合分析**：將文獻歸類（如：理論發展、{method_name} 應用），比較學者觀點異同。
        3. **格式**：引用時標註 (Author, Year)。
        """
    elif "結果" in chapter_type or "ch4" in chapter_type:
        role_instruction = f"""
        你是一位統計學家。撰寫第四章「研究結果」。方法：{method_name}。
        【指令】：
        1. **數據模擬**：模擬出一套**顯著且合理**的數據結果。
        2. **表格呈現**：使用 Markdown 表格展示（如：FCM 矩陣、AHP 權重表、迴歸係數表）。
        3. **文獻對話**：解釋數據時，回頭引用文獻資料庫，說明結果一致性。
        """
    elif "方法" in chapter_type or "ch3" in chapter_type:
        role_instruction = f"""
        你是一位方法論專家。撰寫第三章「研究方法」。
        【指令】：
        1. 定義變數的操作型定義。
        2. **數學公式**：列出 {method_name} 的計算公式或模型步驟（如矩陣運算式）。
        """

    full_system_prompt = f"""
    {role_instruction}
    【使用者額外規則】：{user_rules}
    【文獻資料庫】：{refs[:4000]} 
    請以繁體中文撰寫，語氣專業學術。
    """

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": full_system_prompt},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile", 
            temperature=0.5, 
            max_tokens=6000, 
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
    st.session_state.global_rules = "1. 必須使用繁體中文\n2. 引用必須精確 (Author, Year)\n3. 內容需紮實，拒絕空話"

# --- 側邊欄 ---
with st.sidebar:
    st.header("⚡ 論文設定")
    st.success("✅ 系統狀態：正常")
    
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

    # 2. 研究方法 (這裡就是修正崩潰的地方！)
    st.subheader("📊 研究方法")
    method_category = st.selectbox("方法分類", 
        ["MCDM (多準則)", "量化 (SEM/迴歸)", "質性 (個案)", "混合研究"]
    )
    
    final_method = method_category
    if "MCDM" in method_category:
        st.markdown("**MCDM 工具：**")
        # ⬇️ 這裡我修好了！選項跟預設值完全一致
        mcdm_tools = st.multiselect("工具：", 
            ["Delphi (德爾菲法)", "Fuzzy Delphi", "AHP (層級分析)", "Fuzzy AHP", "ANP", "FCM (模糊認知圖)", "DEMATEL", "TOPSIS"],
            default=["Delphi (德爾菲法)", "FCM (模糊認知圖)"] 
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
st.title("📚 論文寫作助手 (修復完成版)")

# === 步驟 0: 題目 ===
if st.session_state.step == 0:
    st.header("步驟 1：產生題目")
    if st.button("✨ 生成題目", type="primary"):
        if not keywords_str:
            st.error("請輸入關鍵字")
        else:
            with st.spinner("AI 構思中..."):
                prompt = f"領域：管理科學。關鍵字：{keywords_str}。方法：{final_method}。請產生 3 個繁體中文博士論文題目，並說明設計理念。"
                st.session_state.generated_titles = ask_groq_deep_academic(prompt, "題目", final_method, "", st.session_state.global_rules)
    
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
    st.header("步驟 2：導入文獻")
    st.markdown(f"> **當前題目**：{st.session_state.final_title}")
    st.info("💡 請貼上文獻，AI 將用於第二章分析與第四章討論。")
    st.session_state.refs = st.text_area("文獻列表", value=st.session_state.refs, height=400)
    
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
            prompt = f"題目：{st.session_state.final_title}\n方法：{final_method}\n請撰寫詳細大綱。"
            st.session_state.outline = ask_groq_deep_academic(prompt, "大綱", final_method, st.session_state.refs, st.session_state.global_rules)
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
    
    if "ch2" in selected_ch: st.info("🔥 文獻綜合模式：深度分析引用")
    elif "ch4" in selected_ch: st.info("📊 數據模擬模式：生成表格並討論")

    if st.button(f"🚀 撰寫 {chapter_map[selected_ch]}", type="primary"):
        with st.spinner("寫作中..."):
            prompt = f"題目：{st.session_state.final_title}\n章節：{chapter_map[selected_ch]}\n大綱：{st.session_state.outline}\n請撰寫內容。"
            st.session_state.content[selected_ch] = ask_groq_deep_academic(
                prompt, chapter_map[selected_ch], final_method, st.session_state.refs, st.session_state.global_rules
            )
            st.rerun()
            
    if selected_ch in st.session_state.content:
        st.markdown(st.session_state.content[selected_ch])
        
    st.markdown("---")
    if st.button("💾 全部完成，前往下載"):
        st.session_state.step = 4
        st.rerun()

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

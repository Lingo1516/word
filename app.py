import streamlit as st
from groq import Groq
import google.generativeai as genai
import time

# --- 系統設定 ---
st.set_page_config(page_title="論文寫作助手 (雙引擎救援版)", layout="wide", page_icon="🛟")

# --- 側邊欄：救命專區 (設定 Key) ---
with st.sidebar:
    st.header("🛟 引擎與金鑰設定")
    st.info("如果出現 429 錯誤，代表該引擎額度用完，請切換引擎或輸入新的 Key。")
    
    # 選擇引擎
    engine_choice = st.radio("選擇 AI 引擎", ["Groq (Llama 3)", "Google (Gemini)"])
    
    # 輸入 Key (讓使用者自己貼，隨時可換)
    if engine_choice == "Groq (Llama 3)":
        user_key = st.text_input("輸入新的 Groq Key (gsk_...)", type="password")
        if not user_key:
            st.warning("👉 請輸入 Key 才能運作")
            st.markdown("[去申請 Groq Key](https://console.groq.com/keys)")
    else:
        user_key = st.text_input("輸入 Google Key (AIza...)", type="password")
        if not user_key:
            st.warning("👉 請輸入 Key 才能運作")
            st.markdown("[去申請 Google Key](https://aistudio.google.com/app/apikey)")

    st.divider()

# --- 核心函數：統一呼叫接口 ---
def ask_ai(prompt, sys_role="你是一位學術專家。"):
    if not user_key:
        return "⚠️ 請先在側邊欄輸入 API Key"

    try:
        # === Groq 引擎 ===
        if engine_choice == "Groq (Llama 3)":
            client = Groq(api_key=user_key)
            # 防爆截斷
            safe_prompt = prompt[:10000]
            
            completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": sys_role},
                    {"role": "user", "content": safe_prompt}
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.5,
                max_tokens=6000,
            )
            return completion.choices[0].message.content

        # === Google 引擎 ===
        elif engine_choice == "Google (Gemini)":
            genai.configure(api_key=user_key)
            # 嘗試使用 flash，如果失敗程式會捕捉錯誤
            model = genai.GenerativeModel('gemini-1.5-flash') 
            response = model.generate_content(
                f"{sys_role}\n\n{prompt}",
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=8000,
                    temperature=0.5
                )
            )
            return response.text

    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg:
            return f"❌ **額度耗盡 (Error 429)**：{engine_choice} 的今日額度已滿。請在側邊欄切換另一個引擎，或輸入新的 Key。"
        elif "404" in error_msg:
            return f"❌ **模型錯誤 (Error 404)**：Google 找不到模型，請試著換一個 Google 帳號或使用 Groq。"
        else:
            return f"❌ 連線錯誤: {error_msg}"

# --- 分批處理函數 (僅 Groq 模式使用較佳，Google 建議直接丟) ---
def smart_batch_summary(long_text, method_name, progress_bar):
    # 切割長文
    chunk_size = 6000
    chunks = [long_text[i:i+chunk_size] for i in range(0, len(long_text), chunk_size)]
    total_chunks = len(chunks)
    combined_summary = ""
    
    for i, chunk in enumerate(chunks):
        progress_bar.progress((i / total_chunks) * 0.8, text=f"正在研讀第 {i+1}/{total_chunks} 部分...")
        
        prompt = f"""
        這是文獻回顧的一部分。請提取：
        1. 學者與年份
        2. 研究變數
        3. 與「{method_name}」的關聯
        
        文獻內容：
        {chunk}
        """
        summary = ask_ai(prompt, sys_role="你是一位速讀專家。")
        
        if "❌" in summary: return summary # 如果中途報錯直接回傳
        combined_summary += f"\n\n--- Part {i+1} ---\n{summary}"
        
    progress_bar.progress(0.9, text="正在統整...")
    final_prompt = f"請將這些片段整合成完整的學術文獻回顧表(Markdown)：\n{combined_summary}"
    final_result = ask_ai(final_prompt, sys_role="你是一位博學的教授。")
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

# --- 側邊欄 (設定區) ---
with st.sidebar:
    # 關鍵字
    business_keywords = ["策略管理", "ESG", "CSR", "消費者行為", "滿意度", "供應鏈", "FinTech", "數位轉型"]
    selected_kws = st.multiselect("選擇關鍵字：", business_keywords)
    custom_kw = st.text_input("自訂關鍵字：")
    final_kws = selected_kws + ([custom_kw] if custom_kw else [])
    keywords_str = ", ".join(final_kws)

    # 方法
    method_category = st.selectbox("方法分類", ["MCDM", "量化", "質性", "混合"])
    final_method = method_category
    if "MCDM" in method_category:
        mcdm_tools = st.multiselect("工具：", 
            ["Delphi", "Fuzzy Delphi", "AHP", "Fuzzy AHP", "ANP", "FCM (模糊認知圖)", "TOPSIS"],
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

# --- 主畫面 ---
st.title("🛟 論文寫作助手 (雙引擎救援版)")

# === 步驟 0: 題目 ===
if st.session_state.step == 0:
    st.header("步驟 1：產生題目")
    if st.button("✨ 生成題目", type="primary"):
        if not keywords_str: st.error("請輸入關鍵字")
        else:
            with st.spinner("AI

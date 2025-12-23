import streamlit as st
from groq import Groq
import google.generativeai as genai
import requests
import json
import re
import time
import string
import pandas as pd
from io import BytesIO

# --- 1. 系統基礎設定 ---
st.set_page_config(page_title="論文寫作助手 (引用強化版)", layout="wide", page_icon="🎓")

# --- 2. 側邊欄：引擎與方法設定 ---
with st.sidebar:
    st.header("⚙️ 核心設定")
    
    # 1. 引擎選擇
    engine_choice = st.radio("AI 引擎", ["Groq (Llama 3)", "Google (Gemini)"])
    
    api_key = ""
    if engine_choice == "Groq (Llama 3)":
        st.info("🚀 速度快，適合文獻閱讀。")
        api_key = st.text_input("Groq Key", type="password", help="gsk_...")
    else:
        st.info("🧠 邏輯強，適合數學模擬。")
        api_key = st.text_input("Google Key", type="password", help="AIza...")

    st.divider()

    # 2. 研究方法論設定
    st.header("🛠️ 方法論設定")
    research_mode = st.radio("研究路徑", ["MCDM (量化/決策)", "Case Study (質性/個案)"])
    
    mcdm_method = None
    case_method = None
    
    if research_mode == "MCDM (量化/決策)":
        mcdm_method = st.selectbox(
            "選擇模型：",
            ["AHP (層級分析法)", "DEMATEL (決策實驗室法)", "FCM (模糊認知圖)", "ANP (網路分析法)"]
        )
        st.caption("模擬參數：")
        c1, c2 = st.columns(2)
        with c1: criteria_size = st.number_input("準則數", value=15)
        with c2: dim_size = st.number_input("構面數", value=4)
        pool_size = 50 

    else: # Case Study
        case_method = st.selectbox(
            "選擇流派：",
            ["Yin (實證型)", "Harvard (教學型)", "Eisenhardt (建構型)", "Stake (詮釋型)"]
        )

# --- 函數 A: 一般文字生成 ---
def call_ai_api(prompt, sys_role="你是一位嚴謹的學術專家。"):
    if not api_key: return "⚠️ 請輸入 API Key"
    try:
        if engine_choice == "Groq (Llama 3)":
            client = Groq(api_key=api_key)
            completion = client.chat.completions.create(
                messages=[{"role": "system", "content": sys_role}, {"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile", temperature=0.5, max_tokens=4000
            )
            return completion.choices[0].message.content
        elif engine_choice == "Google (Gemini)":
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(f"{sys_role}\n\n{prompt}")
            return response.text
    except Exception as e: return f"❌ Error: {str(e)}"

# --- 函數 B: 深度模擬 (強制 JSON) ---
def run_simulation_analysis(text, key, mode, m_method, c_method, c_n, d_n):
    prompt = ""
    if mode == "MCDM (量化/決策)":
        method_instr = ""
        if "AHP" in m_method: method_instr = "模擬 Saaty 1-9 成對比較矩陣，計算權重。"
        elif "DEMATEL" in m_method: method_instr = "模擬 0-4 直接關係矩陣，計算中心度與原因度。"
        elif "FCM" in m_method: method_instr = "模擬 -1 到 1 影響矩陣，進行推論。"
        elif "ANP" in m_method: method_instr = "模擬超矩陣，計算極限權重。"
        
        prompt = f"""
        你是一個 MCDM 專家。方法：{m_method}。
        請根據文獻執行：收斂({c_n}準則) -> 層級({d_n}構面) -> 數據模擬。
        【嚴格輸出 JSON 格式】：
        {{
            "final_hierarchy": [ {{ "dimension_name": "...", "contained_criteria": [ {{ "criteria_name": "...", "reasoning": "..." }} ] }} ],
            "step4_simulation": {{
                "method_used": "{m_method}",
                "matrix_name": "{m_method} 矩陣",
                "weights": [ {{ "criteria": "準則名稱", "weight": 0.1 }} ],
                "matrix_data": [ {{ "from": "A", "to": "B", "value": 0.5 }} ],
                "companies": [ {{ "name": "企業A", "scores": {{ "準則名稱": 80 }} }} ]
            }}
        }}
        文獻摘要：{text[:10000]}
        """
    else:
        prompt = f"""
        你是一個質性研究專家。流派：{c_method}。
        請根據文獻規劃個案研究架構。
        【嚴格輸出 JSON 格式】：
        {{
            "case_study_content": {{
                "intro": "方法論說明...",
                "sections": [ {{ "title": "章節1", "content": "內容..." }} ],
                "key_findings": ["發現1", "發現2"]
            }}
        }}
        文獻摘要：{text[:10000]}
        """
    try:
        res_text = call_ai_api(prompt, sys_role="Output ONLY valid JSON.")
        try: return json.loads(res_text)
        except:
            match = re.search(r'\{.*\}', res_text, re.DOTALL)
            return json.loads(match.group(0)) if match else None
    except: return None

# --- 初始化 Session ---
if 'step' not in st.session_state: st.session_state.step = 0
if 'final_title' not in st.session_state: st.session_state.final_title = ""
if 'refs' not in st.session_state: st.session_state.refs = ""
if 'parsed_refs' not in st.session_state: st.session_state.parsed_refs = "" 
if 'sim_data' not in st.session_state: st.session_state.sim_data = None
if 'outline' not in st.session_state: st.session_state.outline = ""
if 'content' not in st.session_state or not isinstance(st.session_state.content, dict):
    st.session_state.content = {}

# --- 主畫面 ---
st.title("🎓 論文寫作助手 (引用強化版)")

# === 步驟 0: 題目 ===
if st.session_state.step == 0:
    st.subheader("步驟 1：擬定題目")
    keywords = st.text_input("輸入關鍵字 (例如：ESG, 供應鏈, AI)：")
    if st.button("✨ 生成題目"):
        if not keywords: st.error("請輸入關鍵字")
        else:
            method_str = mcdm_method if research_mode == "MCDM (量化/決策)" else case_method
            prompt = f"關鍵字：{keywords}。方法：{method_str}。請產生 3 個繁體中文學術題目。"
            st.info(call_ai_api(prompt))

    title_input = st.text_input("👇 確認最終題目", value=st.session_state.final_title)
    if st.button("下一步 (文獻導入)"):
        if title_input:
            st.session_state.final_title = title_input
            st.session_state.step = 1
            st.rerun()

# === 步驟 1: 文獻 ===
elif st.session_state.step == 1:
    st.subheader("步驟 2：導入文獻 (分批處理)")
    raw_refs = st.text_area("請貼上大量文獻資料：", value=st.session_state.refs, height=300)
    st.session_state.refs = raw_refs

    if st.button("✨ 啟動文獻解析"):
        if not raw_refs: st.error("請貼上文獻")
        else:
            with st.spinner("AI 正在分批閱讀與歸納..."):
                prompt = f"請歸納以下文獻重點，包含學者、年份、變數、發現。\n{raw_refs[:15000]}"
                st.session_state.parsed_refs = call_ai_api(prompt)
                st.success("文獻解析完成！")

    if st.session_state.parsed_refs:
        st.markdown(st.session_state.parsed_refs)
        col1, col2 = st.columns([1,1])
        with col1: 
            if st.button("⬅️ 上一步"): st.session_state.step = 0; st.rerun()
        with col2:
            if st.button("下一步 (建立分析模型) ➡️", type="primary"): 
                st.session_state.step = 2
                st.rerun()

# === 步驟 2: 模型 ===
elif st.session_state.step == 2:
    st.subheader(f"步驟 3：建立 {research_mode} 分析模型")
    current_method = mcdm_method if research_mode == "MCDM (量化/決策)" else case_method
    
    if st.button(f"🚀 執行 {current_method} 模擬"):
        with st.spinner("正在建構模型..."):
            result = run_simulation_analysis(
                st.session_state.refs, api_key, research_mode, 
                mcdm_method, case_method, 15, 4
            )
            if result:
                st.session_state.sim_data = result
                st.success("模型建構完成！")
            else: st.error("模擬失敗")

    if st.session_state.sim_data:
        data = st.session_state.sim_data
        if research_mode == "MCDM (量化/決策)":
            t1, t2 = st.tabs(["架構", "模擬數據"])
            with t1: st.json(data.get("final_hierarchy", []))
            with t2: st.dataframe(pd.DataFrame(data.get("step4_simulation", {}).get("matrix_data", [])))
        else:
            st.write(data.get("case_study_content", {}).get("intro"))

        col1, col2 = st.columns([1,1])
        with col1:
             if st.button("⬅️ 上一步"): st.session_state.step = 1; st.rerun()
        with col2:
             if st.button("下一步 (生成大綱) ➡️", type="primary"): st.session_state.step = 3; st.rerun()

# === 步驟 3: 大綱 ===
elif st.session_state.step == 3:
    st.subheader("步驟 4：生成論文大綱")
    if st.button("✨ 生成大綱"):
        sim_context = json.dumps(st.session_state.sim_data, ensure_ascii=False) if st.session_state.sim_data else "無"
        prompt = f"題目：{st.session_state.final_title}\n分析模型：{sim_context}\n請撰寫大綱。"
        st.session_state.outline = call_ai_api(prompt)
        st.rerun()
        
    if st.session_state.outline:
        st.markdown(st.session_state.outline)
        col1, col2 = st.columns([1,1])
        with col1:
             if st.button("⬅️ 上一步"): st.session_state.step = 2; st.rerun()
        with col2:
             if st.button("下一步 (開始寫作) ➡️", type="primary"): st.session_state.step = 4; st.rerun()

# === 步驟 4: 寫作 (引用強化版) ===
elif st.session_state.step == 4:
    st.subheader("步驟 5：逐章撰寫")
    chapters = ["第一章 緒論", "第二章 文獻探討", "第三章 研究方法", "第四章 分析結果", "第五章 結論"]
    selected_ch = st.selectbox("選擇章節", chapters)
    st.info(f"📍 目前選擇：{selected_ch}")

    if st.button(f"🚀 讓 AI 撰寫 {selected_ch}"):
        # === 核心修改：資料注入邏輯 ===
        
        # 1. 準備資料
        sim_json = json.dumps(st.session_state.sim_data, ensure_ascii=False) if st.session_state.sim_data else "無"
        # 優先使用解析過的文獻，如果沒有則使用原始文獻
        ref_content = st.session_state.parsed_refs if st.session_state.parsed_refs else st.session_state.refs
        # 截斷過長的文獻以免爆 Token (Gemini Flash 可承受較多，這裡設 20000 字)
        ref_content = ref_content[:20000]

        # 2. 決定「餵」什麼資料給 AI
        input_context = ""
        instruction = ""
        
        if "第一章" in selected_ch:
            input_context = "【注意】：本章僅撰寫背景與動機，不可提及第四章的分析結果。"
            instruction = "請根據題目撰寫研究背景、動機與目的。"
            
        elif "第二章" in selected_ch:
            # 這是你要的：強制餵入文獻
            input_context = f"【文獻庫資料 (這是你必須引用的來源)】：\n{ref_content}"
            instruction = """
            1. 這是文獻探討章節，請**嚴格引用**上述【文獻庫資料】中的內容。
            2. 每一段論述後面，必須加上出處標註，格式為：[作者, 年份]。
            3. 例如：「根據 [王小明, 2024] 的研究指出...」或「供應鏈韌性是關鍵 [Smith, 2023]」。
            4. **禁止**憑空創造文獻，必須使用我提供的資料。
            """
            
        elif "第三章" in selected_ch:
            input_context = "【注意】：本章專注於方法論介紹。"
            instruction = "請詳細描述研究變數定義與數學模型 (AHP/FCM等)。"
            
        elif "第四章" in selected_ch or "結論" in selected_ch:
            # 這是之前修好的：強制餵入數據
            input_context = f"【模擬分析數據 (這是本章的核心)】：\n{sim_json}"
            instruction = "請將上述的模擬數據轉化為詳細的文字分析，解釋權重與排名的意義。"

        # 3. 組合 Prompt
        prompt = f"""
        你是一個嚴謹的學術論文寫作助手。
        【題目】：{st.session_state.final_title}
        【章節】：{selected_ch}
        【大綱】：{st.session_state.outline}
        
        {input_context}
        
        【撰寫要求】：
        1. 使用學術語氣。
        2. {instruction}
        3. 使用 Markdown 格式。
        
        請開始撰寫：
        """
        
        with st.spinner(f"正在撰寫 {selected_ch} (引用模式啟動)..."):
            st.session_state.content[selected_ch] = call_ai_api(prompt)
            st.rerun()

    if selected_ch in st.session_state.content:
        st.markdown(f"### 📄 {selected_ch} 草稿")
        st.markdown(st.session_state.content[selected_ch])
        if st.button("🔄 重新撰寫"):
            del st.session_state.content[selected_ch]
            st.rerun()
    else:
        st.warning(f"⚠️ {selected_ch} 尚未撰寫。")

    st.divider()
    final_doc = f"# {st.session_state.final_title}\n\n"
    for ch in chapters:
        if ch in st.session_state.content:
            final_doc += f"## {ch}\n{st.session_state.content[ch]}\n\n"
    st.download_button("📥 下載全文 (.txt)", final_doc, "thesis_full.txt")

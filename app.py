import streamlit as st
import requests
import json

# --- 系統設定 ---
st.set_page_config(page_title="論文寫作助手 (MCDM 專業版)", layout="wide", page_icon="🎓")

# --- 核心 1: 掃描模型 (延續上一版成功的邏輯) ---
def get_available_models(api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            model_list = []
            if 'models' in data:
                for m in data['models']:
                    if 'generateContent' in m.get('supportedGenerationMethods', []):
                        clean_name = m['name'].replace('models/', '')
                        model_list.append(clean_name)
            return model_list
        return None
    except:
        return None

# --- 核心 2: 寫作函式 ---
def ask_gemini(prompt, api_key, model_name):
    if not api_key: return "⚠️ 請設定 Key"
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    data = { "contents": [{ "parts": [{"text": prompt}] }] }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            try:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            except:
                return "⚠️ 生成成功但解析失敗"
        elif response.status_code == 429:
            return "⏳ 速度限制：請等待 20 秒後再試。"
        else:
            return f"❌ 錯誤 ({response.status_code}): {response.text}"
    except Exception as e:
        return f"❌ 網路錯誤：{str(e)}"

# --- 初始化 ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'content' not in st.session_state: st.session_state.content = {}
if 'refs' not in st.session_state: st.session_state.refs = ""
if 'outline' not in st.session_state: st.session_state.outline = ""
if 'my_models' not in st.session_state: st.session_state.my_models = []

# --- 側邊欄 ---
api_key = None
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]

with st.sidebar:
    st.header("⚙️ 1. 引擎設定")
    if api_key:
        st.success("✅ 金鑰已載入")
        if st.button("🔄 重新掃描模型"):
            found = get_available_models(api_key)
            if found: st.session_state.my_models = found
    else:
        user_key = st.text_input("Google API Key", type="password")
        if user_key:
            api_key = user_key
            if st.button("🔄 掃描模型"):
                found = get_available_models(api_key)
                if found: st.session_state.my_models = found

    # 模型選擇
    selected_model = None
    if st.session_state.my_models:
        # 優先選 flash 以節省額度
        default_idx = 0
        for i, m in enumerate(st.session_state.my_models):
            if 'flash' in m: default_idx = i
        selected_model = st.selectbox("選擇模型", st.session_state.my_models, index=default_idx)
    elif api_key:
        st.warning("請點擊掃描模型")

    st.divider()
    st.header("📝 2. 研究方法設定")
    
    topic = st.text_input("研究題目", "例如：以 AHP 探討供應商選擇關鍵因素")
    
    # === 新增：多準則決策方法選擇 ===
    method_category = st.selectbox("主要研究途徑", 
        ["多準則決策 (MCDM)", "量化研究 (問卷調查)", "質性研究 (訪談)", "實驗法", "混合研究法"]
    )
    
    final_method = method_category
    
    if method_category == "多準則決策 (MCDM)":
        mcdm_tool = st.selectbox("選擇具體分析工具", 
            [
                "AHP (層級分析法)", 
                "ANP (網路分析法)",
                "DEMATEL (決策實驗室法)", 
                "FCM (模糊認知圖 Fuzzy Cognitive Maps)", 
                "TOPSIS (理想解類似度順序偏好法)", 
                "VIKOR (折衷排序法)", 
                "Fuzzy AHP (模糊層級分析)",
                "Fuzzy Delphi (模糊德爾菲)"
            ]
        )
        final_method = f"{method_category} - {mcdm_tool}"
        st.info(f"已選擇：{mcdm_tool}")

# --- 主畫面 ---
st.title("🎓 論文寫作助手 (MCDM 專業版)")

if not api_key:
    st.info("👈 請先在左側輸入 API Key 並掃描模型")
    st.stop()

# === 步驟一 ===
if st.session_state.step == 1:
    st.subheader("第一步：文獻與缺口")
    if st.button("🔍 開始分析"):
        if not selected_model:
            st.error("請先掃描並選擇模型")
        else:
            with st.spinner("正在分析文獻..."):
                prompt = f"""
                題目：{topic}
                研究方法：{final_method}
                
                請列出 5 筆相關的學術參考文獻 (格式：作者, 年份, 篇名)，
                並根據「{final_method}」這個方法，推導出一個具體的研究缺口。
                請說明為什麼這個方法適合解決這個缺口。
                """
                res = ask_gemini(prompt, api_key, selected_model)
                st.session_state.refs = res
                st.rerun()
            
    if st.session_state.refs:
        st.markdown(st.session_state.refs)
        if st.button("下一步"):
            st.session_state.step = 2
            st.rerun()

# === 步驟二 ===
elif st.session_state.step == 2:
    st.subheader("第二步：大綱")
    if not st.session_state.outline:
        with st.spinner("生成專業大綱中..."):
            prompt = f"""
            題目：{topic}
            研究方法：{final_method}
            文獻基礎：{st.session_state.refs}
            
            請撰寫一份「學術論文大綱」，包含五個章節。
            特別要求：
            1. 第三章必須詳細列出「{final_method}」的運算步驟與公式概念。
            2. 第四章必須規劃如何呈現該方法的分析結果（例如：權重表、因果圖、排序表）。
            """
            res = ask_gemini(prompt, api_key, selected_model)
            st.session_state.outline = res
            st.rerun()
            
    st.markdown(st.session_state.outline)
    if st.button("下一步"):
        st.session_state.step = 3
        st.rerun()

# === 步驟三 ===
elif st.session_state.step == 3:
    st.subheader("第三步：寫作")
    st.caption(f"使用方法：{final_method} | 模型：{selected_model}")
    
    tabs = st.tabs(["第一章：緒論", "第二章：文獻", "第三章：方法", "第四章：結果", "第五章：結論"])
    
    def write_content(chapter_title, extra_instruction=""):
        return ask_gemini(
            f"""
            請撰寫論文的「{chapter_title}」。
            題目：{topic}
            方法：{final_method}
            大綱：{st.session_state.outline}
            
            要求：
            1. 學術語氣，繁體中文。
            2. 字數約 1500-2000 字。
            3. 使用 Markdown 格式 (標題、列表)。
            4. {extra_instruction}
            """, 
            api_key, selected_model
        )

    # --- 第一章 ---
    with tabs[0]:
        if st.button("✍️ 撰寫第一章"):
            with st.spinner("撰寫中..."):
                st.session_state.content['ch1'] = write_content("第一章 緒論", "包含研究背景、動機、目的、流程圖概念")
        if 'ch1' in st.session_state.content: st.markdown(st.session_state.content['ch1'])

    # --- 第二章 ---
    with tabs[1]:
        if st.button("✍️ 撰寫第二章"):
            with st.spinner("撰寫中..."):
                st.session_state.content['ch2'] = write_content("第二章 文獻探討", f"包含 {final_method} 的理論基礎與過去應用案例回顧")
        if 'ch2' in st.session_state.content: st.markdown(st.session_state.content['ch2'])
    
    # --- 第三章 (這次有畫面了！) ---
    with tabs[2]:
        st.info(f"本章重點：詳細描述 {final_method} 的執行步驟")
        if st.button("✍️ 撰寫第三章"):
            with st.spinner(f"正在生成 {final_method} 方法論..."):
                instruction = f"""
                詳細說明 {final_method} 的研究設計。
                必須包含：
                1. 方法的定義與適用性。
                2. 具體的數學運算步驟或邏輯步驟。
                3. 問卷設計或專家評估程序。
                4. 驗證方法 (如一致性檢定 CI/CR)。
                """
                st.session_state.content['ch3'] = write_content("第三章 研究方法", instruction)
        if 'ch3' in st.session_state.content: st.markdown(st.session_state.content['ch3'])

    # --- 第四章 (這次有畫面了！) ---
    with tabs[3]:
        st.warning("注意：AI 生成的為「模擬數據分析」，真實論文請填入實際算出的數據。")
        if st.button("✍️ 撰寫第四章"):
            with st.spinner("生成模擬數據分析..."):
                instruction = f"""
                呈現 {final_method} 的預期分析結果。
                包含：
                1. 樣本結構或專家背景描述。
                2. 模擬的分析數據表 (如權重矩陣、影響關係圖)。
                3. 針對數據進行深入討論與解釋。
                """
                st.session_state.content['ch4'] = write_content("第四章 實證結果分析", instruction)
        if 'ch4' in st.session_state.content: st.markdown(st.session_state.content['ch4'])

    # --- 第五章 (這次有畫面了！) ---
    with tabs[4]:
        if st.button("✍️ 撰寫第五章"):
            with st.spinner("撰寫結論..."):
                st.session_state.content['ch5'] = write_content("第五章 結論與建議", "總結研究發現、管理意涵、研究限制")
        if 'ch5' in st.session_state.content: st.markdown(st.session_state.content['ch5'])

    st.divider()
    # 組合全文
    full_text = "\n\n".join(st.session_state.content.values())
    if full_text:
        st.download_button("📥 下載完整論文 (Markdown)", full_text, "MCDM_Thesis.md")

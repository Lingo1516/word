import streamlit as st
import requests
import json
import re

# --- 系統設定 ---
st.set_page_config(page_title="論文寫作助手 (全功能合體版)", layout="wide", page_icon="📊")

# --- 核心 1: 掃描模型功能 (加回來了！) ---
def get_available_models(api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            model_list = []
            if 'models' in data:
                for m in data['models']:
                    # 只抓取支援生成內容的模型
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
    
    real_model_name = model_name
    if "models/" not in model_name:
        real_model_name = f"models/{model_name}"
        
    url = f"https://generativelanguage.googleapis.com/v1beta/{real_model_name}:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    data = { "contents": [{ "parts": [{"text": prompt}] }] }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            try:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            except: return "⚠️ 生成成功但解析失敗"
        elif response.status_code == 429: return "⏳ 速度限制 (429)，請稍候 20 秒..."
        elif response.status_code == 404: return f"❌ 模型錯誤 (404): {model_name} 不存在。"
        else: return f"❌ 連線錯誤 ({response.status_code}): {response.text}"
    except Exception as e: return f"❌ 網路錯誤：{str(e)}"

# --- 初始化 ---
if 'step' not in st.session_state: st.session_state.step = 0
if 'proposed_titles' not in st.session_state: st.session_state.proposed_titles = []
if 'final_title' not in st.session_state: st.session_state.final_title = ""
if 'refs' not in st.session_state: st.session_state.refs = ""
if 'outline' not in st.session_state: st.session_state.outline = ""
if 'content' not in st.session_state: st.session_state.content = {}
if 'graph_code' not in st.session_state: st.session_state.graph_code = ""
if 'my_models' not in st.session_state: st.session_state.my_models = []

# --- 側邊欄 ---
api_key = None
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]

with st.sidebar:
    st.header("⚙️ 1. 引擎設定")
    if not api_key:
        user_key = st.text_input("API Key", type="password")
        if user_key: api_key = user_key
    
    if api_key:
        st.success("✅ 金鑰已載入")
        
        # --- 【這裡！搜尋按鈕回來了】 ---
        col_scan, col_msg = st.columns([1, 2])
        with col_scan:
            if st.button("🔄 搜尋模型"):
                found = get_available_models(api_key)
                if found: 
                    st.session_state.my_models = found
                    st.success("成功！")
                else:
                    st.error("失敗")

    # 模型選擇邏輯：如果有掃描到就用掃描的，沒有就用預設清單
    model_options = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro"]
    if st.session_state.my_models:
        model_options = st.session_state.my_models

    st.markdown("### 選擇模型")
    
    # 自動選一個包含 flash 的當預設值
    default_index = 0
    for i, m in enumerate(model_options):
        if 'flash' in m: default_index = i
        
    selected_model = st.selectbox("請選擇", model_options, index=default_index)
    
    st.divider()
    
    # 5 個關鍵字輸入框
    st.markdown("### 輸入關鍵字 (請填寫)")
    k1 = st.text_input("關鍵字 1", value="")
    k2 = st.text_input("關鍵字 2", value="")
    k3 = st.text_input("關鍵字 3", value="")
    k4 = st.text_input("關鍵字 4", value="")
    k5 = st.text_input("關鍵字 5", value="")
    
    raw_keywords = [k1, k2, k3, k4, k5]
    active_keywords = [k for k in raw_keywords if k.strip()] 
    keywords_str = ", ".join(active_keywords)

    st.divider()

    # 方法選擇
    method_category = st.selectbox("研究途徑", 
        ["多準則決策 (MCDM)", "量化研究 (SEM/回歸)", "質性研究"]
    )
    
    final_method = method_category
    if method_category == "多準則決策 (MCDM)":
        mcdm_tool = st.selectbox("選擇具體方法", 
            ["AHP (層級分析法)", "ANP", "DEMATEL", "FCM (模糊認知圖)", "TOPSIS", "VIKOR", "Fuzzy AHP", "DANP"]
        )
        final_method = f"多準則決策 - {mcdm_tool}"

# --- 主畫面邏輯 ---
st.title("📊 論文寫作助手 (全功能合體版)")

if not api_key:
    st.warning("請先輸入 API Key")
    st.stop()

# === 步驟 0: 產生題目 ===
if st.session_state.step == 0:
    st.subheader("步驟 0：根據關鍵字構思題目")
    
    if keywords_str: st.info(f"關鍵字：{keywords_str}")

    if st.button("✨ 產生 3 個建議題目"):
        if not keywords_str:
            st.error("請先輸入關鍵字！")
        else:
            with st.spinner("AI 構思中..."):
                prompt = f"""
                關鍵字：{keywords_str}
                研究方法：{final_method}
                請產生 3 個具有學術深度的繁體中文論文題目。只列出題目。
                """
                res = ask_gemini(prompt, api_key, selected_model)
                titles = [t.strip() for t in res.split('\n') if t.strip()]
                clean_titles = []
                for t in titles:
                    clean_t = re.sub(r'^\d+\.\s*', '', t).replace('*', '').strip()
                    if clean_t: clean_titles.append(clean_t)
                st.session_state.proposed_titles = clean_titles
                st.rerun()

    if st.session_state.proposed_titles:
        st.write("請選擇一個最符合您想法的題目：")
        chosen = st.radio("建議題目：", st.session_state.proposed_titles)
        if st.button("🔒 鎖定此題目，下一步"):
            st.session_state.final_title = chosen
            st.session_state.step = 1
            st.rerun()

# === 步驟 1: 文獻 (強制中文) ===
elif st.session_state.step == 1:
    st.subheader(f"步驟 1：建立中文文獻庫")
    st.caption(f"題目：{st.session_state.final_title}")
    
    if st.button("📚 搜尋繁體中文文獻"):
        with st.spinner("正在搜尋台灣學術資料庫..."):
            prompt = f"""
            題目：{st.session_state.final_title}
            方法：{final_method}
            
            請列出 **10-15 筆** 重要學術文獻。
            **嚴格要求：**
            1. **必須主要包含「繁體中文」文獻** (例如：管理評論、中山管理評論、台大管理論叢等)。
            2. 可以搭配少量經典英文文獻。
            3. 格式：[年份] 作者 - 篇名 (主要觀點)
            
            最後根據這些文獻，推導出研究缺口。
            """
            st.session_state.refs = ask_gemini(prompt, api_key, selected_model)
            st.rerun()
            
    if st.session_state.refs:
        st.markdown(st.session_state.refs)
        if st.button("下一步：生成大綱"):
            st.session_state.step = 2
            st.rerun()

# === 步驟 2: 大綱 ===
elif st.session_state.step == 2:
    st.subheader("步驟 2：邏輯架構大綱")
    if st.button("📝 生成章節大綱"):
        with st.spinner("規劃大綱中..."):
            prompt = f"""
            題目：{st.session_state.final_title}
            方法：{final_method}
            文獻基礎：{st.session_state.refs}
            
            請寫出五章節的詳細大綱。
            第四章必須規劃如何呈現「視覺化圖表」與數據結果。
            """
            st.session_state.outline = ask_gemini(prompt, api_key, selected_model)
            st.rerun()
            
    if st.session_state.outline:
        st.markdown(st.session_state.outline)
        if st.button("下一步：開始撰寫內文"):
            st.session_state.step = 3
            st.rerun()

# === 步驟 3: 寫作 (含視覺化) ===
elif st.session_state.step == 3:
    st.subheader("步驟 3：撰寫與視覺化")
    st.info(f"題目：{st.session_state.final_title} | 方法：{final_method}")
    
    tabs = st.tabs(["第一章", "第二章 (文獻)", "第三章 (方法)", "第四章 (結果圖表)", "第五章"])
    
    # --- 第一章 ---
    with tabs[0]:
        if st.button("✍️ 寫第一章"):
            prompt = f"""
            寫第一章：緒論。
            題目：{st.session_state.final_title}
            文獻缺口：{st.session_state.refs}
            要求：清楚定義研究背景、動機、目的。繁體中文，學術語氣。
            """
            with st.spinner("寫作中..."):
                st.session_state.content['ch1'] = ask_gemini(prompt, api_key, selected_model)
                st.rerun()
        if 'ch1' in st.session_state.content: st.markdown(st.session_state.content['ch1'])

    # --- 第二章 (強制引用) ---
    with tabs[1]:
        st.info("💡 強制使用「文中引用」格式，例如：(王小明, 2023)。")
        if st.button("✍️ 寫第二章"):
            prompt = f"""
            寫第二章：文獻探討。
            題目：{st.session_state.final_title}
            參考文獻列表：{st.session_state.refs}
            
            **嚴格要求**：
            1. 必須引用上述提供的中文文獻。
            2. **每一段論述後都要加上引用來源**，格式如：(張三, 2022)。
            3. 文獻對話與評析。
            """
            with st.spinner("寫作中..."):
                st.session_state.content['ch2'] = ask_gemini(prompt, api_key, selected_model)
                st.rerun()
        if 'ch2' in st.session_state.content: st.markdown(st.session_state.content['ch2'])

    # --- 第三章 ---
    with tabs[2]:
        if st.button("✍️ 寫第三章"):
            prompt = f"""
            寫第三章：研究方法。
            方法：{final_method}
            
            要求：
            1. **禁止使用 LaTeX**，改用 Markdown 表格呈現數學步驟。
            2. 詳細說明運算邏輯。
            """
            with st.spinner("寫作中..."):
                st.session_state.content['ch3'] = ask_gemini(prompt, api_key, selected_model)
                st.rerun()
        if 'ch3' in st.session_state.content: st.markdown(st.session_state.content['ch3'])

    # --- 第四章 (視覺化核心) ---
    with tabs[3]:
        st.warning(f"⚠️ 這裡將生成 {final_method} 的分析結果與圖表。")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("✍️ 撰寫第四章文字"):
                prompt = f"""
                寫第四章：資料分析與結果。
                題目：{st.session_state.final_title}
                方法：{final_method}
                
                要求：
                1. **禁止使用 LaTeX 語法**，矩陣請用 Markdown 表格呈現。
                2. 模擬完整數據分析結果。
                """
                with st.spinner("模擬數據中..."):
                    st.session_state.content['ch4'] = ask_gemini(prompt, api_key, selected_model)
                    st.rerun()
        
        with col2:
            if st.button("📊 繪製關聯圖"):
                with st.spinner("繪製中..."):
                    graph_prompt = f"""
                    請針對題目「{st.session_state.final_title}」和方法「{final_method}」，
                    生成一段 Graphviz DOT 語言程式碼。
                    情境：模擬關鍵因素的因果關係圖或層級圖。
                    要求：只回傳 DOT 代碼，不要其他文字，節點用繁體中文。
                    """
                    code_res = ask_gemini(graph_prompt, api_key, selected_model)
                    clean_code = code_res.replace("```dot", "").replace("```", "").strip()
                    st.session_state.graph_code = clean_code
                    st.rerun()

        if 'ch4' in st.session_state.content: 
            st.markdown(st.session_state.content['ch4'])
        
        st.divider()
        
        if st.session_state.graph_code:
            st.markdown("### 📊 視覺化圖表")
            try:
                st.graphviz_chart(st.session_state.graph_code)
            except:
                st.error("圖表生成失敗")
                st.code(st.session_state.graph_code)

    # --- 第五章 ---
    with tabs[4]:
        if st.button("✍️ 寫第五章"):
            prompt = f"""
            寫第五章：結論。
            題目：{st.session_state.final_title}
            依據第四章結果，提出管理意涵。
            """
            with st.spinner("撰寫中..."):
                st.session_state.content['ch5'] = ask_gemini(prompt, api_key, selected_model)
                st.rerun()
        if 'ch5' in st.session_state.content: st.markdown(st.session_state.content['ch5'])

    st.divider()
    full_text = f"# {st.session_state.final_title}\n\n" + "\n\n".join(st.session_state.content.values())
    st.download_button("📥 下載完整論文", full_text, "Thesis.md")

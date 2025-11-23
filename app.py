import streamlit as st
import requests
import json

# --- 系統設定 ---
st.set_page_config(page_title="論文寫作助手 (5格關鍵字版)", layout="wide", page_icon="🔗")

# --- 核心連線函式 ---
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
                        model_list.append(m['name'].replace('models/', ''))
            return model_list
    except: return None
    return None

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
            except: return "⚠️ 生成成功但解析失敗"
        elif response.status_code == 429: return "⏳ 速度限制，請稍候..."
        else: return f"❌ 錯誤 ({response.status_code}): {response.text}"
    except Exception as e: return f"❌ 網路錯誤：{str(e)}"

# --- 初始化 Session State ---
if 'step' not in st.session_state: st.session_state.step = 0
if 'proposed_titles' not in st.session_state: st.session_state.proposed_titles = []
if 'final_title' not in st.session_state: st.session_state.final_title = ""
if 'refs' not in st.session_state: st.session_state.refs = ""
if 'outline' not in st.session_state: st.session_state.outline = ""
if 'content' not in st.session_state: st.session_state.content = {}
if 'my_models' not in st.session_state: st.session_state.my_models = []

# --- 側邊欄 ---
api_key = None
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]

with st.sidebar:
    st.header("⚙️ 1. 引擎與關鍵字")
    
    # 金鑰
    if not api_key:
        user_key = st.text_input("API Key", type="password")
        if user_key: api_key = user_key
    
    if api_key:
        if st.button("🔄 掃描模型"):
            found = get_available_models(api_key)
            if found: st.session_state.my_models = found
    
    # 模型
    selected_model = "gemini-pro"
    if st.session_state.my_models:
        default_idx = 0
        for i, m in enumerate(st.session_state.my_models):
            if 'flash' in m: default_idx = i
        selected_model = st.selectbox("選擇模型", st.session_state.my_models, index=default_idx)
    
    st.divider()
    
    # --- 【修改處】5 個乾淨的關鍵字輸入框 ---
    st.markdown("### 輸入關鍵字 (請填寫)")
    st.caption("至少填寫第 1 個，其他選填，無需刪除預設值。")
    
    k1 = st.text_input("關鍵字 1", value="")
    k2 = st.text_input("關鍵字 2", value="")
    k3 = st.text_input("關鍵字 3", value="")
    k4 = st.text_input("關鍵字 4", value="")
    k5 = st.text_input("關鍵字 5", value="")
    
    # 自動組合非空的關鍵字
    raw_keywords = [k1, k2, k3, k4, k5]
    active_keywords = [k for k in raw_keywords if k.strip()] # 過濾掉空白的
    keywords_str = ", ".join(active_keywords) # 組合成字串給 AI 用

    st.divider()

    # 方法選擇
    method_category = st.selectbox("研究途徑", 
        ["多準則決策 (MCDM)", "量化研究 (SEM/回歸)", "質性研究", "實驗法"]
    )
    
    final_method = method_category
    if method_category == "多準則決策 (MCDM)":
        mcdm_tool = st.selectbox("選擇具體方法", 
            ["AHP (層級分析法)", "ANP", "DEMATEL", "FCM (模糊認知圖)", "TOPSIS", "VIKOR", "Fuzzy AHP", "DANP (DEMATEL+ANP)"]
        )
        final_method = f"多準則決策 - {mcdm_tool}"

# --- 主畫面邏輯 ---
st.title("🔗 論文寫作助手 (5格填空版)")

if not api_key:
    st.warning("請先輸入 API Key 並掃描模型")
    st.stop()

# === 步驟 0: 產生題目 ===
if st.session_state.step == 0:
    st.subheader("步驟 0：根據關鍵字構思題目")
    
    # 顯示目前抓到的關鍵字
    if keywords_str:
        st.info(f"您輸入的關鍵字：{keywords_str}")
    else:
        st.warning("請在左側至少輸入一個關鍵字。")

    if st.button("✨ 產生 3 個建議題目"):
        if not keywords_str:
            st.error("請先輸入關鍵字！")
        else:
            with st.spinner("AI 構思中..."):
                prompt = f"""
                關鍵字：{keywords_str}
                研究方法：{final_method}
                
                請根據以上資訊，產生 3 個具有學術深度、邏輯嚴謹的中文論文題目。
                請只列出題目，不要有其他解釋。
                """
                res = ask_gemini(prompt, api_key, selected_model)
                titles = [t.strip() for t in res.split('\n') if t.strip()]
                st.session_state.proposed_titles = titles
                st.rerun()

    if st.session_state.proposed_titles:
        st.write("請選擇一個最符合您想法的題目：")
        chosen = st.radio("建議題目：", st.session_state.proposed_titles)
        if st.button("🔒 鎖定此題目，下一步"):
            st.session_state.final_title = chosen
            st.session_state.step = 1
            st.rerun()

# === 步驟 1: 文獻 ===
elif st.session_state.step == 1:
    st.subheader(f"步驟 1：建立文獻庫 (題目：{st.session_state.final_title})")
    
    if st.button("📚 搜尋大量文獻 & 定義缺口"):
        with st.spinner("正在檢索並建構文獻庫..."):
            prompt = f"""
            題目：{st.session_state.final_title}
            方法：{final_method}
            
            1. 請列出 **10-15 筆** 重要學術文獻 (包含經典理論與近 3 年研究)。
               格式：[年份] 作者 - 篇名 (主要貢獻)
            2. 根據這些文獻，推導出一個強而有力的「研究缺口」。
            3. 說明為什麼「{final_method}」是填補此缺口的最佳方法。
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
        with st.spinner("規劃邏輯中..."):
            prompt = f"""
            題目：{st.session_state.final_title}
            方法：{final_method}
            文獻基礎：{st.session_state.refs}
            
            請寫出五章節的詳細大綱。
            重點要求：
            - 第三章：必須是 {final_method} 的標準步驟。
            - 第四章：標題必須反映 {final_method} 的產出 (例如：權重分析、因果圖分析)。
            """
            st.session_state.outline = ask_gemini(prompt, api_key, selected_model)
            st.rerun()
            
    if st.session_state.outline:
        st.markdown(st.session_state.outline)
        if st.button("下一步：開始撰寫內文"):
            st.session_state.step = 3
            st.rerun()

# === 步驟 3: 寫作 (邏輯連貫) ===
elif st.session_state.step == 3:
    st.subheader("步驟 3：邏輯連貫撰寫")
    st.info(f"當前題目：{st.session_state.final_title} | 方法：{final_method}")
    
    tabs = st.tabs(["第一章", "第二章", "第三章", "第四章 (結果)", "第五章 (結論)"])
    
    ch1_content = st.session_state.content.get('ch1', "尚未撰寫")
    ch4_content = st.session_state.content.get('ch4', "尚未撰寫")

    with tabs[0]:
        if st.button("✍️ 寫第一章"):
            prompt = f"""
            寫第一章：緒論。
            題目：{st.session_state.final_title}
            文獻缺口：{st.session_state.refs}
            要求：清楚定義研究背景、動機、目的。2000字。
            """
            with st.spinner("寫作中..."):
                st.session_state.content['ch1'] = ask_gemini(prompt, api_key, selected_model)
        if 'ch1' in st.session_state.content: st.markdown(st.session_state.content['ch1'])

    with tabs[1]:
        if st.button("✍️ 寫第二章"):
            prompt = f"""
            寫第二章：文獻探討。
            題目：{st.session_state.final_title}
            參考文獻列表：{st.session_state.refs}
            前一章重點：{ch1_content[:500]}...
            要求：探討變數之間的關係，並推導出本研究的架構。
            """
            with st.spinner("寫作中..."):
                st.session_state.content['ch2'] = ask_gemini(prompt, api_key, selected_model)
        if 'ch2' in st.session_state.content: st.markdown(st.session_state.content['ch2'])

    with tabs[2]:
        if st.button("✍️ 寫第三章"):
            prompt = f"""
            寫第三章：研究方法。
            題目：{st.session_state.final_title}
            **指定方法：{final_method}**
            
            嚴格要求：
            1. 詳細列出 {final_method} 的數學公式或運算邏輯。
            2. 說明問卷設計方式或專家選取標準。
            3. 說明資料處理步驟 (如 CI/CR 檢定)。
            """
            with st.spinner("寫作中..."):
                st.session_state.content['ch3'] = ask_gemini(prompt, api_key, selected_model)
        if 'ch3' in st.session_state.content: st.markdown(st.session_state.content['ch3'])

    with tabs[3]:
        st.warning(f"⚠️ 本章將模擬 {final_method} 的數據結果。")
        if st.button("✍️ 寫第四章"):
            prompt = f"""
            寫第四章：資料分析與結果。
            題目：{st.session_state.final_title}
            **使用方法：{final_method}**
            
            邏輯連貫要求：
            1. 必須基於第三章步驟，模擬出一份結果。
            2. 若是 AHP 須列出權重；DEMATEL 須有因果分析。
            3. **結果必須回應第一章提出的研究目的。**
            """
            with st.spinner("模擬數據分析中..."):
                st.session_state.content['ch4'] = ask_gemini(prompt, api_key, selected_model)
        if 'ch4' in st.session_state.content: st.markdown(st.session_state.content['ch4'])

    with tabs[4]:
        if st.button("✍️ 寫第五章"):
            prompt = f"""
            寫第五章：結論與建議。
            題目：{st.session_state.final_title}
            **第四章分析結果摘要**：
            {ch4_content[:1000]}...
            
            邏輯連貫要求：
            1. 結論必須依據第四章數據撰寫。
            2. 提出具體管理意涵。
            """
            with st.spinner("統整結論中..."):
                st.session_state.content['ch5'] = ask_gemini(prompt, api_key, selected_model)
        if 'ch5' in st.session_state.content: st.markdown(st.session_state.content['ch5'])

    st.divider()
    full_text = f"# {st.session_state.final_title}\n\n" + "\n\n".join(st.session_state.content.values())
    st.download_button("📥 下載完整論文", full_text, "Thesis.md")

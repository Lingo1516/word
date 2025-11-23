import streamlit as st
import requests
import json
import re

# --- 系統設定 ---
st.set_page_config(page_title="論文寫作助手 (預覽挑選版)", layout="wide", page_icon="📑")

# --- 核心 1: 掃描模型 ---
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
    except: return None

# --- 核心 2: 寫作函式 ---
def ask_gemini(prompt, api_key, model_name):
    if not api_key: return "⚠️ 請設定 Key"
    real_model_name = f"models/{model_name}" if "models/" not in model_name else model_name
    url = f"https://generativelanguage.googleapis.com/v1beta/{real_model_name}:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    data = { "contents": [{ "parts": [{"text": prompt}] }] }
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            try: return response.json()['candidates'][0]['content']['parts'][0]['text']
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
if 'framework' not in st.session_state: st.session_state.framework = ""
if 'framework_dot' not in st.session_state: st.session_state.framework_dot = ""
if 'outline' not in st.session_state: st.session_state.outline = ""
if 'content' not in st.session_state: st.session_state.content = {}
if 'graph_code' not in st.session_state: st.session_state.graph_code = ""
if 'apa_refs' not in st.session_state: st.session_state.apa_refs = ""
if 'my_models' not in st.session_state: st.session_state.my_models = []

# --- 側邊欄 ---
api_key = None
if "GOOGLE_API_KEY" in st.secrets: api_key = st.secrets["GOOGLE_API_KEY"]

with st.sidebar:
    st.header("⚙️ 1. 引擎設定")
    if not api_key:
        user_key = st.text_input("API Key", type="password")
        if user_key: api_key = user_key
    
    if api_key:
        st.success("✅ 金鑰已載入")
        if st.button("🔄 搜尋可用模型"):
            with st.spinner("掃描中..."):
                found = get_available_models(api_key)
                if found: 
                    st.session_state.my_models = found
                    st.success(f"找到 {len(found)} 個")
                else:
                    st.error("掃描失敗")

    model_options = ["gemini-1.5-flash", "gemini-1.5-pro"]
    if st.session_state.my_models: model_options = st.session_state.my_models
    
    default_index = 0
    for i, m in enumerate(model_options):
        if 'flash' in m: default_index = i
    selected_model = st.selectbox("選擇模型", model_options, index=default_index)
    
    st.divider()
    st.header("📝 2. 研究設定")
    
    k1 = st.text_input("關鍵字 1", value="")
    k2 = st.text_input("關鍵字 2", value="")
    k3 = st.text_input("關鍵字 3", value="")
    k4 = st.text_input("關鍵字 4", value="")
    k5 = st.text_input("關鍵字 5", value="")
    keywords_str = ", ".join([k for k in [k1, k2, k3, k4, k5] if k.strip()])

    st.divider()
    
    method_category = st.selectbox("研究途徑", ["多準則決策 (MCDM)", "量化研究", "質性研究", "實驗法"])
    final_method = method_category
    
    num_dims = 3
    num_crits = 4

    if method_category == "多準則決策 (MCDM)":
        st.markdown("#### ☑️ 請勾選方法")
        mcdm_tools = st.multiselect(
            "選擇方法：", 
            ["Delphi (德爾菲法)", "Fuzzy Delphi", "AHP", "Fuzzy AHP", "ANP", "DEMATEL", "DANP", "FCM", "TOPSIS", "VIKOR"],
            default=["Delphi (德爾菲法)", "AHP"]
        )
        final_method = f"多準則決策 ({' + '.join(mcdm_tools)})" if mcdm_tools else "多準則決策"
        
        st.divider()
        st.markdown("#### 🏗️ 設定指標數量")
        num_dims = st.number_input("構面數量", 2, 10, 3)
        num_crits = st.number_input("準則數量(每構面)", 2, 10, 4)

# --- 主畫面 ---
st.title("📑 論文寫作助手 (預覽挑選版)")

if not api_key: st.warning("請先輸入 API Key"); st.stop()

# === 步驟 0: 題目 ===
if st.session_state.step == 0:
    st.subheader("步驟 0：構思題目")
    if st.button("✨ 產生建議題目"):
        if not keywords_str: st.error("請輸入關鍵字")
        else:
            with st.spinner("構思中..."):
                prompt = f"關鍵字：{keywords_str}。方法：{final_method}。請產生 3 個繁體中文學術題目。"
                res = ask_gemini(prompt, api_key, selected_model)
                titles = [t.strip() for t in res.split('\n') if t.strip() and not t.startswith("Here")]
                clean_titles = []
                for t in titles:
                    clean_t = re.sub(r'^\d+\.\s*', '', t).replace('*', '').strip()
                    if clean_t: clean_titles.append(clean_t)
                st.session_state.proposed_titles = clean_titles
                st.rerun()

    if st.session_state.proposed_titles:
        chosen = st.radio("選擇題目：", st.session_state.proposed_titles)
        if st.button("🔒 鎖定題目，下一步"):
            st.session_state.final_title = chosen
            st.session_state.step = 1
            st.rerun()

# === 步驟 1: 文獻 ===
elif st.session_state.step == 1:
    st.subheader("步驟 1：導入真實文獻")
    st.info("請貼上華藝或 Google 學術的真實文獻資料。")
    raw_refs = st.text_area("📋 文獻資料貼上區：", height=300)
    
    if st.button("✅ 確認文獻，下一步"):
        if not raw_refs: st.error("請貼上文獻")
        else:
            st.session_state.refs = raw_refs
            st.session_state.step = 1.5 
            st.rerun()

# === 步驟 1.5: 架構 ===
elif st.session_state.step == 1.5:
    st.subheader("步驟 1.5：建構評估指標體系")
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 📝 文字架構")
        if not st.session_state.framework:
            if st.button("⚡ 產生架構文字"):
                with st.spinner("分析中..."):
                    prompt = f"""
                    題目：{st.session_state.final_title}
                    文獻：{st.session_state.refs}
                    任務：建立評估指標體系 ({num_dims}構面 x {num_crits}準則)。
                    請輸出 Markdown 列表。
                    """
                    st.session_state.framework = ask_gemini(prompt, api_key, selected_model)
                    st.rerun()
        
        if st.session_state.framework:
            edited_framework = st.text_area("編輯架構：", value=st.session_state.framework, height=400)
            if edited_framework != st.session_state.framework:
                st.session_state.framework = edited_framework
            
            if st.button("📊 繪製架構圖"):
                with st.spinner("繪圖中..."):
                    graph_prompt = f"針對{st.session_state.final_title}的架構：\n{st.session_state.framework}\n生成 Graphviz DOT 層級圖代碼。繁體中文。"
                    code_res = ask_gemini(graph_prompt, api_key, selected_model)
                    clean_code = code_res.replace("```dot", "").replace("```", "").strip()
                    st.session_state.framework_dot = clean_code
                    st.rerun()

    with col2:
        st.markdown("### 🖼️ 架構圖預覽")
        if st.session_state.framework_dot:
            try: st.graphviz_chart(st.session_state.framework_dot)
            except: st.code(st.session_state.framework_dot)

    if st.session_state.framework:
        st.markdown("---")
        if st.button("🔒 鎖定架構，生成大綱"):
            st.session_state.step = 2
            st.rerun()

# === 步驟 2: 大綱 ===
elif st.session_state.step == 2:
    st.subheader("步驟 2：生成大綱")
    if st.button("📝 生成大綱"):
        with st.spinner("規劃中..."):
            prompt = f"題目：{st.session_state.final_title}。方法：{final_method}。架構：{st.session_state.framework}。請寫出五章大綱，包含圖表規劃。"
            st.session_state.outline = ask_gemini(prompt, api_key, selected_model)
            st.rerun()
            
    if st.session_state.outline:
        st.markdown(st.session_state.outline)
        if st.button("下一步：開始撰寫"):
            st.session_state.step = 3
            st.rerun()

# === 步驟 3: 撰寫 ===
elif st.session_state.step == 3:
    st.subheader("步驟 3：分章撰寫")
    tabs = st.tabs(["第一章", "第二章", "第三章", "第四章", "第五章"])
    
    def write_ch(ch, extra=""):
        return ask_gemini(f"撰寫「{ch}」。題目：{st.session_state.final_title}。方法：{final_method}。架構：{st.session_state.framework}。文獻：{st.session_state.refs}。{extra} 要求：繁體中文，學術語氣，引用真實文獻。", api_key, selected_model)

    with tabs[0]:
        if st.button("✍️ 寫第一章"):
            with st.spinner("寫作中..."):
                st.session_state.content['ch1'] = write_ch("第一章 緒論", "包含背景、動機、目的")
        if 'ch1' in st.session_state.content: st.markdown(st.session_state.content['ch1'])

    with tabs[1]:
        if st.button("✍️ 寫第二章"):
            with st.spinner("寫作中..."):
                st.session_state.content['ch2'] = write_ch("第二章 文獻探討", "引用真實文獻。")
        if 'ch2' in st.session_state.content: st.markdown(st.session_state.content['ch2'])

    with tabs[2]:
        if st.button("✍️ 寫第三章"):
            with st.spinner("寫作中..."):
                st.session_state.content['ch3'] = write_ch("第三章 研究方法", f"詳細說明 {final_method} 步驟。")
        if 'ch3' in st.session_state.content: st.markdown(st.session_state.content['ch3'])

    with tabs[3]:
        st.info(f"針對 {final_method} 進行模擬分析。")
        col_txt, col_viz = st.columns([1,1])
        with col_txt:
            if st.button("✍️ 寫第四章 (文字)"):
                with st.spinner("模擬中..."):
                    st.session_state.content['ch4'] = write_ch("第四章 資料分析與結果", "模擬數據要豐富且顯著，使用 Markdown 表格。")
        with col_viz:
            if st.button("📊 繪製結果圖"):
                with st.spinner("繪圖中..."):
                    graph_p = f"針對 {st.session_state.final_title} 與 {final_method}，畫出最終分析結果圖。回傳 DOT code。"
                    code = ask_gemini(graph_p, api_key, selected_model)
                    st.session_state.graph_code = code.replace("```dot", "").replace("```", "").strip()
                    st.rerun()

        if 'ch4' in st.session_state.content: st.markdown(st.session_state.content['ch4'])
        if st.session_state.graph_code: 
            st.markdown("#### 分析結果圖")
            try: st.graphviz_chart(st.session_state.graph_code)
            except: st.code(st.session_state.graph_code)

    with tabs[4]:
        if st.button("✍️ 寫第五章"):
            with st.spinner("寫作中..."):
                st.session_state.content['ch5'] = write_ch("第五章 結論", "依據第四章結果撰寫。")
        if 'ch5' in st.session_state.content: st.markdown(st.session_state.content['ch5'])

    st.divider()
    if len(st.session_state.content) >= 1:
        if st.button("下一步：全文檢閱 & 修正"):
            st.session_state.step = 4
            st.rerun()

# === 步驟 4: 全文檢閱 & 修正 ===
elif st.session_state.step == 4:
    st.subheader("步驟 4：全文檢閱、建議與 APA")
    
    # --- 1. 顯示摺疊預覽區 (讓你檢查內容) ---
    st.markdown("### 📖 論文初稿檢閱 (請展開檢查)")
    for i in range(1, 6):
        with st.expander(f"第 {i} 章", expanded=(i>=4)): # 預設展開 4,5 章
            st.markdown(st.session_state.content.get(f'ch{i}', '（尚未撰寫）'))
            if i == 4 and st.session_state.graph_code:
                st.caption("[圖表代碼已生成]")

    st.divider()

    # --- 2. 用戶建議 ---
    st.markdown("### 📝 您的建議與修正")
    user_feedback = st.text_area("請輸入修改建議 (AI 將依此重寫第五章並整理全文)：", height=100)
    
    if st.button("🚀 執行修正 & 生成 APA"):
        if not user_feedback:
            st.error("請輸入意見")
        else:
            with st.spinner("修正中..."):
                new_ch5 = ask_gemini(f"重寫第五章。題目：{st.session_state.final_title}。原稿：{st.session_state.content.get('ch5','')}。意見：{user_feedback}", api_key, selected_model)
                st.session_state.content['ch5'] = new_ch5
                st.session_state.apa_refs = ask_gemini(f"整理成 APA 7th：\n{st.session_state.refs}", api_key, selected_model)
                st.rerun()

    # --- 3. 最終下載區 (新增！) ---
    if st.session_state.apa_refs:
        st.markdown("---")
        st.subheader("📥 最終預覽與下載設定")
        
        # [新增] 章節挑選器
        st.write("請勾選您想要下載的章節：")
        chapter_options = {
            "ch1": "第一章 緒論",
            "ch2": "第二章 文獻探討",
            "ch3": "第三章 研究方法",
            "ch4": "第四章 結果分析",
            "ch5": "第五章 結論與建議",
            "ref": "參考文獻 (APA)"
        }
        selected_chapters = st.multiselect(
            "選擇章節 (預設全選)", 
            options=list(chapter_options.keys()),
            default=list(chapter_options.keys()),
            format_func=lambda x: chapter_options[x]
        )
        
        # [新增] 即時組裝文字
        final_preview_text = f"# {st.session_state.final_title}\n\n"
        
        if "ch1" in selected_chapters: final_preview_text += st.session_state.content.get('ch1', '') + "\n\n"
        if "ch2" in selected_chapters: final_preview_text += st.session_state.content.get('ch2', '') + "\n\n"
        if "ch3" in selected_chapters: final_preview_text += st.session_state.content.get('ch3', '') + "\n\n"
        if "ch4" in selected_chapters: final_preview_text += st.session_state.content.get('ch4', '') + "\n\n"
        if "ch5" in selected_chapters: final_preview_text += st.session_state.content.get('ch5', '') + "\n\n"
        if "ref" in selected_chapters: final_preview_text += "\n\n## 參考文獻\n" + st.session_state.apa_refs
        
        # [新增] 全文預覽框
        with st.expander("📄 點擊預覽最終組裝的全文", expanded=False):
            st.text_area("全文預覽", final_preview_text, height=400)
        
        # 下載按鈕
        st.download_button("📥 下載選定的內容 (Markdown)", final_preview_text, "Final_Thesis.md")

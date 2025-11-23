import streamlit as st
import requests
import json
import re

# --- 系統設定 ---
st.set_page_config(page_title="論文寫作助手 (商管速選版)", layout="wide", page_icon="🎓")

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
if 'current_ch_index' not in st.session_state: st.session_state.current_ch_index = 0 
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

# 章節定義
CHAPTERS = [
    {"key": "ch1", "name": "第一章 緒論", "desc": "研究背景、動機、目的"},
    {"key": "ch2", "name": "第二章 文獻探討", "desc": "理論基礎、引用真實文獻"},
    {"key": "ch3", "name": "第三章 研究方法", "desc": "詳細步驟、架構說明"},
    {"key": "ch4", "name": "第四章 分析結果", "desc": "數據模擬、圖表分析"},
    {"key": "ch5", "name": "第五章 結論與建議", "desc": "總結、管理意涵"}
]

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
                if found: st.session_state.my_models = found

    model_options = ["gemini-1.5-flash", "gemini-1.5-pro"]
    if st.session_state.my_models: model_options = st.session_state.my_models
    default_index = 0
    for i, m in enumerate(model_options):
        if 'flash' in m: default_index = i
    selected_model = st.selectbox("選擇模型", model_options, index=default_index)
    
    st.divider()
    st.header("📝 2. 研究設定")
    
    # --- 【修改重點】商學院關鍵字選單 ---
    st.markdown("#### 關鍵字 (可複選)")
    business_keywords = [
        # 策略與管理
        "策略管理", "競爭優勢", "商業模式", "數位轉型", "ESG", "永續發展", "企業社會責任(CSR)",
        "關鍵成功因素(KSF)", "績效評估", "知識管理", "創新能力", "組織變革",
        # 行銷
        "消費者行為", "品牌形象", "顧客滿意度", "服務品質", "網路口碑", "社群行銷", "購買意願",
        # 人力資源
        "人力資源管理", "員工績效", "組織承諾", "領導風格", "教育訓練", "工作滿意度", "離職傾向",
        # 營運與供應鏈
        "供應鏈管理", "綠色供應鏈", "營運效率", "風險管理", "品質管理", "供應商選擇",
        # 科技應用
        "金融科技(FinTech)", "人工智慧應用", "大數據分析", "電子商務"
    ]
    
    selected_kws = st.multiselect("請勾選：", business_keywords)
    custom_kw = st.text_input("自訂補充 (如有其他)：")
    
    # 組合關鍵字
    final_kws = selected_kws.copy()
    if custom_kw: final_kws.append(custom_kw)
    keywords_str = ", ".join(final_kws)

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
st.title("🎓 論文寫作助手 (商管速選版)")

if not api_key: st.warning("請先輸入 API Key"); st.stop()

# === 步驟 0: 題目 ===
if st.session_state.step == 0:
    st.subheader("步驟 0：構思題目")
    
    if keywords_str:
        st.info(f"已選關鍵字：{keywords_str}")
    else:
        st.warning("請在左側勾選或輸入關鍵字")

    if st.button("✨ 產生建議題目"):
        if not keywords_str: st.error("請選擇關鍵字")
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

# === 步驟 1.5: 架構 & 圖 ===
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
            prompt = f"題目：{st.session_state.final_title}。方法：{final_method}。架構：{st.session_state.framework}。請寫出五章大綱。"
            st.session_state.outline = ask_gemini(prompt, api_key, selected_model)
            st.rerun()
            
    if st.session_state.outline:
        st.markdown(st.session_state.outline)
        if st.button("下一步：開始逐章寫作"):
            st.session_state.step = 3
            st.rerun()

# === 步驟 3: 逐章寫作 (審核模式) ===
elif st.session_state.step == 3:
    
    current_idx = st.session_state.current_ch_index
    
    if current_idx < 5:
        curr_ch = CHAPTERS[current_idx]
        ch_key = curr_ch["key"]
        ch_name = curr_ch["name"]
        
        st.subheader(f"✍️ 寫作進度：{ch_name}")
        st.caption(f"本章重點：{curr_ch['desc']}")
        
        current_content = st.session_state.content.get(ch_key, "")
        
        if not current_content:
            if st.button(f"🚀 開始撰寫 {ch_name}"):
                with st.spinner(f"AI 正在撰寫 {ch_name}..."):
                    
                    context_prompt = ""
                    if current_idx > 0:
                        prev_key = CHAPTERS[current_idx-1]["key"]
                        prev_content = st.session_state.content.get(prev_key, "")
                        context_prompt = f"前一章內容摘要：{prev_content[:800]}..."
                    
                    extra_instruction = ""
                    if "第四章" in ch_name:
                        extra_instruction = "請模擬豐富且顯著的數據，使用 Markdown 表格，不要用 LaTeX。"
                    elif "第二章" in ch_name:
                        extra_instruction = "請務必使用文中引用格式 (Author, Year)，參考文獻為真實文獻。"
                    
                    prompt = f"""
                    請撰寫「{ch_name}」。
                    題目：{st.session_state.final_title}
                    方法：{final_method}
                    架構：{st.session_state.framework}
                    文獻：{st.session_state.refs}
                    {context_prompt}
                    {extra_instruction}
                    要求：繁體中文，學術語氣。
                    """
                    res = ask_gemini(prompt, api_key, selected_model)
                    st.session_state.content[ch_key] = res
                    
                    if "第四章" in ch_name:
                        graph_p = f"針對 {st.session_state.final_title} 與 {final_method}，畫出最終分析結果圖 (如因果圖)。回傳 DOT code。"
                        code = ask_gemini(graph_p, api_key, selected_model)
                        st.session_state.graph_code = code.replace("```dot", "").replace("```", "").strip()
                    
                    st.rerun()
        
        else:
            st.markdown("### 📖 章節預覽")
            st.markdown(current_content)
            
            if "第四章" in ch_name and st.session_state.graph_code:
                st.markdown("#### 分析圖表")
                try: st.graphviz_chart(st.session_state.graph_code)
                except: pass

            st.divider()
            st.markdown("### 🔧 審核操作")
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                feedback = st.text_area(f"如果不滿意，請輸入修改意見：", height=100)
                if st.button("🔄 依照意見重寫本章"):
                    if not feedback:
                        st.error("請輸入修改意見")
                    else:
                        with st.spinner("修正中..."):
                            fix_prompt = f"""
                            請重寫「{ch_name}」。
                            原稿：{current_content}
                            **用戶修改意見**：{feedback}
                            請根據意見進行修正。
                            """
                            new_content = ask_gemini(fix_prompt, api_key, selected_model)
                            st.session_state.content[ch_key] = new_content
                            st.rerun()
            
            with col2:
                st.write(" ")
                st.write(" ")
                st.write(" ")
                if st.button(f"✅ 通過，寫下一章", type="primary"):
                    st.session_state.current_ch_index += 1
                    st.rerun()

    else:
        st.success("🎉 全文撰寫完成！")
        if st.button("前往最終整理與下載"):
            st.session_state.step = 4
            st.rerun()

# === 步驟 4: 最終整理 & 下載 ===
elif st.session_state.step == 4:
    st.subheader("步驟 4：最終整理與下載")
    
    if not st.session_state.apa_refs:
        if st.button("📄 生成 APA 參考文獻列表"):
            with st.spinner("整理參考文獻中..."):
                apa_prompt = f"請將以下真實文獻整理成標準 APA 7th 格式：\n{st.session_state.refs}"
                st.session_state.apa_refs = ask_gemini(apa_prompt, api_key, selected_model)
                st.rerun()
    
    if st.session_state.apa_refs:
        st.markdown("### 📥 下載選項")
        
        chapter_options = {
            "ch1": "第一章 緒論",
            "ch2": "第二章 文獻探討",
            "ch3": "第三章 研究方法",
            "ch4": "第四章 結果分析",
            "ch5": "第五章 結論與建議",
            "ref": "參考文獻 (APA)"
        }
        selected_chapters = st.multiselect(
            "勾選要下載的章節", 
            options=list(chapter_options.keys()),
            default=list(chapter_options.keys()),
            format_func=lambda x: chapter_options[x]
        )
        
        final_text = f"# {st.session_state.final_title}\n\n"
        if "ch1" in selected_chapters: final_text += st.session_state.content.get('ch1', '') + "\n\n"
        if "ch2" in selected_chapters: final_text += st.session_state.content.get('ch2', '') + "\n\n"
        if "ch3" in selected_chapters: final_text += st.session_state.content.get('ch3', '') + "\n\n"
        if "ch4" in selected_chapters: final_text += st.session_state.content.get('ch4', '') + "\n\n"
        if "ch5" in selected_chapters: final_text += st.session_state.content.get('ch5', '') + "\n\n"
        if "ref" in selected_chapters: final_text += "\n\n## 參考文獻\n" + st.session_state.apa_refs
        
        with st.expander("預覽全文"):
            st.markdown(final_text)
            
        st.download_button("📥 下載檔案", final_text, "Thesis_Completed.md")

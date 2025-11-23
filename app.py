import streamlit as st
import requests
import json
import re

# --- 系統設定 ---
st.set_page_config(page_title="論文寫作助手 (學術標準版)", layout="wide", page_icon="🎓")

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

# --- 核心 2: 強力圖表代碼清洗 (修復圖跑不出來的問題) ---
def clean_graphviz_code(raw_code):
    # 1. 去除 markdown 標記
    clean = raw_code.replace("```dot", "").replace("```", "").strip()
    # 2. 嘗試抓取 digraph {...} 區塊
    match = re.search(r'digraph\s+.*\{.*\}', clean, re.DOTALL)
    if match:
        return match.group(0)
    # 3. 如果找不到 digraph，嘗試抓取大括號內容並補頭
    start = clean.find('{')
    end = clean.rfind('}')
    if start != -1 and end != -1:
        return f"digraph G {clean[start:end+1]}"
    return clean # 放棄治療，回傳原碼

# --- 核心 3: 寫作函式 ---
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
        elif response.status_code == 429: return "⏳ 速度限制，請稍候..."
        elif response.status_code == 404: return f"❌ 模型錯誤: {model_name} 不存在。"
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
    selected_model = st.selectbox("選擇模型", model_options, index=0)
    
    st.divider()
    st.header("📝 2. 論文規格")
    
    # --- 【修改重點】格式選擇 ---
    paper_type = st.radio("寫作格式", ["學位論文 (Thesis)", "期刊論文 (Journal)"])
    
    # 關鍵字速選 (商學院)
    st.markdown("#### 關鍵字速選")
    business_keywords = [
        "策略管理", "競爭優勢", "商業模式", "數位轉型", "ESG", "企業社會責任",
        "消費者行為", "顧客滿意度", "服務品質", "品牌形象",
        "人力資源", "教育訓練", "組織承諾", "領導統御", "工作績效",
        "供應鏈管理", "風險管理", "金融科技", "AI應用"
    ]
    selected_kws = st.multiselect("勾選關鍵字：", business_keywords)
    custom_kw = st.text_input("自訂補充：")
    
    final_kws = selected_kws.copy()
    if custom_kw: final_kws.append(custom_kw)
    keywords_str = ", ".join(final_kws)

    st.divider()
    
    method_category = st.selectbox("研究途徑", ["多準則決策 (MCDM)", "量化研究", "質性研究", "實驗法"])
    final_method = method_category
    num_dims = 3
    num_crits = 4

    if method_category == "多準則決策 (MCDM)":
        st.markdown("#### ☑️ MCDM 方法 (可複選)")
        mcdm_tools = st.multiselect(
            "選擇方法：", 
            ["Delphi (德爾菲法)", "Fuzzy Delphi", "AHP", "Fuzzy AHP", "ANP", "DEMATEL", "DANP", "FCM", "TOPSIS", "VIKOR"],
            default=["Delphi (德爾菲法)", "AHP"]
        )
        final_method = f"多準則決策 ({' + '.join(mcdm_tools)})" if mcdm_tools else "多準則決策"
        
        st.markdown("#### 🏗️ 架構數量")
        num_dims = st.number_input("構面數", 2, 10, 3)
        num_crits = st.number_input("準則數(每構面)", 2, 10, 4)

# --- 依據格式定義章節 ---
if paper_type == "學位論文 (Thesis)":
    CHAPTERS = [
        {"key": "ch1", "name": "第一章 緒論", "prompt": "背景、動機、目的、流程"},
        {"key": "ch2", "name": "第二章 文獻探討", "prompt": "變數定義、理論基礎、推導架構"},
        {"key": "ch3", "name": "第三章 研究方法", "prompt": "研究架構、方法步驟、工具介紹"},
        {"key": "ch4", "name": "第四章 分析結果", "prompt": "數據呈現、圖表分析、驗證假說"},
        {"key": "ch5", "name": "第五章 結論與建議", "prompt": "研究發現、管理意涵、限制"}
    ]
else: # 期刊論文
    CHAPTERS = [
        {"key": "ch1", "name": "1. 前言 (Introduction)", "prompt": "研究背景、缺口與目的 (不分節)"},
        {"key": "ch2", "name": "2. 文獻回顧 (Literature Review)", "prompt": "相關文獻評析與假說推導 (精簡)"},
        {"key": "ch3", "name": "3. 研究方法 (Methodology)", "prompt": "方法論述與實驗設計 (不含結果)"},
        {"key": "ch4", "name": "4. 研究結果 (Results)", "prompt": "數據分析與圖表 (不含推論)"},
        {"key": "ch5", "name": "5. 討論與結論 (Discussion)", "prompt": "結果意涵、貢獻與未來建議"}
    ]

# --- 主畫面 ---
st.title("🎓 論文寫作助手 (學術標準版)")

if not api_key: st.warning("請先輸入 API Key"); st.stop()

# === 步驟 0: 題目 ===
if st.session_state.step == 0:
    st.subheader("步驟 0：構思題目")
    
    if keywords_str:
        st.info(f"關鍵字：{keywords_str} | 格式：{paper_type}")
    
    if st.button("✨ 產生建議題目"):
        if not keywords_str: st.error("請選擇或輸入關鍵字")
        else:
            with st.spinner("構思中..."):
                prompt = f"""
                關鍵字：{keywords_str}
                研究方法：{final_method}
                寫作格式：{paper_type}
                請產生 3 個繁體中文學術題目，必須符合{paper_type}的命名慣例。
                """
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
    st.info("請貼上華藝或 Google 學術的真實文獻 (作者/年份/題目/摘要)。")
    raw_refs = st.text_area("📋 文獻資料貼上區：", height=300)
    
    if st.button("✅ 確認文獻，下一步"):
        if not raw_refs: st.error("請貼上文獻")
        else:
            st.session_state.refs = raw_refs
            st.session_state.step = 1.5 
            st.rerun()

# === 步驟 1.5: 架構 & 圖 (強力修復版) ===
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
                    graph_prompt = f"""
                    請根據以下架構，生成 Graphviz DOT 代碼。
                    架構：{st.session_state.framework}
                    要求：
                    1. 產生 Hierarchy Tree。
                    2. 節點標籤使用繁體中文。
                    3. 只回傳 DOT 代碼，不要有任何解釋文字或 ``` 符號。
                    """
                    code_res = ask_gemini(graph_prompt, api_key, selected_model)
                    # 使用強力清洗函數
                    st.session_state.framework_dot = clean_graphviz_code(code_res)
                    st.rerun()

    with col2:
        st.markdown("### 🖼️ 架構圖預覽")
        if st.session_state.framework_dot:
            try: 
                st.graphviz_chart(st.session_state.framework_dot)
                st.success("圖表生成成功！")
            except Exception as e: 
                st.error(f"圖表生成失敗：{e}")
                st.code(st.session_state.framework_dot)

    if st.session_state.framework:
        st.markdown("---")
        if st.button("🔒 鎖定架構，生成大綱"):
            st.session_state.step = 2
            st.rerun()

# === 步驟 2: 大綱 (依照格式) ===
elif st.session_state.step == 2:
    st.subheader(f"步驟 2：生成大綱 ({paper_type})")
    if st.button("📝 生成大綱"):
        with st.spinner("規劃中..."):
            prompt = f"""
            題目：{st.session_state.final_title}
            方法：{final_method}
            格式：{paper_type}
            架構：{st.session_state.framework}
            請寫出大綱，必須符合{paper_type}的標準結構規範。
            """
            st.session_state.outline = ask_gemini(prompt, api_key, selected_model)
            st.rerun()
            
    if st.session_state.outline:
        st.markdown(st.session_state.outline)
        if st.button("下一步：開始逐章寫作"):
            st.session_state.step = 3
            st.rerun()

# === 步驟 3: 逐章寫作 (內容隔離) ===
elif st.session_state.step == 3:
    
    current_idx = st.session_state.current_ch_index
    
    if current_idx < len(CHAPTERS):
        curr_ch = CHAPTERS[current_idx]
        ch_key = curr_ch["key"]
        ch_name = curr_ch["name"]
        
        st.subheader(f"✍️ 寫作進度：{ch_name}")
        st.info(f"本章重點：{curr_ch['prompt']}")
        
        current_content = st.session_state.content.get(ch_key, "")
        
        if not current_content:
            if st.button(f"🚀 開始撰寫 {ch_name}"):
                with st.spinner(f"AI 正在撰寫 {ch_name}..."):
                    
                    # 內容隔離 Prompt
                    isolation_rule = ""
                    if "緒論" in ch_name or "前言" in ch_name:
                        isolation_rule = "嚴禁提及具體的分析結果或數據。重點在研究背景與目的。"
                    elif "研究方法" in ch_name:
                        isolation_rule = "嚴禁提及分析結果。只描述方法步驟、公式與設計。"
                    elif "結果" in ch_name:
                        isolation_rule = "專注於數據呈現與解釋，不要重複方法定義。"
                    
                    extra_instruction = ""
                    if "第四章" in ch_name or "研究結果" in ch_name:
                        extra_instruction = "請模擬豐富且顯著的數據，使用 Markdown 表格，不要用 LaTeX。"
                        # 順便嘗試畫圖
                        graph_p = f"針對 {st.session_state.final_title} 與 {final_method}，畫出最終分析結果圖。只回傳 DOT code。"
                        code = ask_gemini(graph_p, api_key, selected_model)
                        st.session_state.graph_code = clean_graphviz_code(code)
                    elif "第二章" in ch_name or "文獻" in ch_name:
                        extra_instruction = "請務必使用文中引用格式 (Author, Year)，參考文獻為真實文獻。"
                    
                    prompt = f"""
                    請撰寫「{ch_name}」。
                    題目：{st.session_state.final_title}
                    格式：{paper_type}
                    方法：{final_method}
                    架構：{st.session_state.framework}
                    文獻：{st.session_state.refs}
                    
                    **內容規範**：
                    1. {curr_ch['prompt']}
                    2. {isolation_rule}
                    3. {extra_instruction}
                    
                    要求：繁體中文，學術語氣。
                    """
                    res = ask_gemini(prompt, api_key, selected_model)
                    st.session_state.content[ch_key] = res
                    st.rerun()
        
        else:
            st.markdown("### 📖 章節預覽")
            st.markdown(current_content)
            
            if ("第四章" in ch_name or "研究結果" in ch_name) and st.session_state.graph_code:
                st.markdown("#### 分析圖表")
                try: st.graphviz_chart(st.session_state.graph_code)
                except: st.error("圖表顯示失敗")

            st.divider()
            st.markdown("### 🔧 審核操作")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                feedback = st.text_area(f"如果不滿意，請輸入修改意見：", height=100)
                if st.button("🔄 依照意見重寫本章"):
                    if not feedback: st.error("請輸入意見")
                    else:
                        with st.spinner("修正中..."):
                            fix_prompt = f"重寫「{ch_name}」。原稿：{current_content}。意見：{feedback}。請修正。"
                            new_content = ask_gemini(fix_prompt, api_key, selected_model)
                            st.session_state.content[ch_key] = new_content
                            st.rerun()
            
            with col2:
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
        
        # 動態生成章節選項
        chapter_options = {ch['key']: ch['name'] for ch in CHAPTERS}
        chapter_options['ref'] = "參考文獻 (APA)"
        
        selected_chapters = st.multiselect(
            "勾選要下載的章節", 
            options=list(chapter_options.keys()),
            default=list(chapter_options.keys()),
            format_func=lambda x: chapter_options[x]
        )
        
        final_text = f"# {st.session_state.final_title}\n\n"
        for ch in CHAPTERS:
            if ch['key'] in selected_chapters:
                final_text += st.session_state.content.get(ch['key'], '') + "\n\n"
        
        if "ref" in selected_chapters:
            final_text += "\n\n## 參考文獻\n" + st.session_state.apa_refs
        
        with st.expander("預覽全文"):
            st.markdown(final_text)
            
        st.download_button("📥 下載檔案", final_text, "Thesis_Completed.md")

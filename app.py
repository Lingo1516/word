import streamlit as st
import requests
import json
import re
import urllib.parse

# --- 系統設定 ---
st.set_page_config(page_title="論文寫作助手 (具備規則記憶版)", layout="wide", page_icon="🧠")

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

# --- 核心 2: 圖表代碼清洗 ---
def clean_graphviz_code(raw_code):
    clean = raw_code.replace("```dot", "").replace("```", "").strip()
    if "rankdir" not in clean:
        if "{" in clean:
            clean = clean.replace("{", '{\n  rankdir=TB;\n  node [fontname="Microsoft JhengHei"];\n', 1)
    match = re.search(r'digraph\s+.*\{.*\}', clean, re.DOTALL)
    if match: return match.group(0)
    start = clean.find('{')
    end = clean.rfind('}')
    if start != -1 and end != -1: return f"digraph G {clean[start:end+1]}"
    return clean

# --- 核心 3: 圖片標籤 ---
def get_graph_img_tag(dot_code):
    if not dot_code: return ""
    encoded_dot = urllib.parse.quote(dot_code)
    image_url = f"https://quickchart.io/graphviz?graph={encoded_dot}&format=png"
    return f'''
    <div style="text-align: center; margin: 20px 0;">
        <img src="{image_url}" alt="架構圖" style="max-width: 100%; border: 1px solid #ccc; padding: 10px;">
    </div>
    <br>
    '''

# --- 核心 4: 寫作函式 (注入使用者規則) ---
def ask_gemini(prompt, api_key, model_name, user_rules=""):
    if not api_key: return "⚠️ 請設定 Key"
    
    # 【關鍵修改】將使用者的規則強制加到 Prompt 的最前面
    final_prompt = prompt
    if user_rules:
        final_prompt = f"""
        🔥🔥 **【最高優先級指令 - 請務必遵守以下規則】** 🔥🔥
        {user_rules}
        --------------------------------------------------
        {prompt}
        """

    real_model_name = f"models/{model_name}" if "models/" not in model_name else model_name
    url = f"https://generativelanguage.googleapis.com/v1beta/{real_model_name}:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    data = { "contents": [{ "parts": [{"text": final_prompt}] }] }
    
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
if 'concept_map_code' not in st.session_state: st.session_state.concept_map_code = ""
if 'apa_refs' not in st.session_state: st.session_state.apa_refs = ""
if 'my_models' not in st.session_state: st.session_state.my_models = []
if 'global_rules' not in st.session_state: st.session_state.global_rules = "1. 嚴禁使用 LaTeX 語法。\n2. 必須使用繁體中文。\n3. 語氣需專業學術。" # 預設規則

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
    st.header("🧠 2. 記憶與規則 (重點)")
    st.info("在此輸入的規則，AI 會在寫每一章時都記得！")
    
    # 【新功能】全域規則輸入框
    user_rules = st.text_area(
        "⚠️ 寫作禁忌與格式要求 (AI 會一直記得)：",
        value=st.session_state.global_rules,
        height=150,
        help="例如：不要用中國用語、引用格式要 (Author, Year)、圖表要用表格呈現..."
    )
    st.session_state.global_rules = user_rules

    st.divider()
    st.header("📝 3. 論文規格")
    paper_type = st.radio("寫作格式", ["學位論文 (Thesis)", "期刊論文 (Journal)"])
    
    # 章節定義
    if paper_type == "學位論文 (Thesis)":
        CHAPTERS = [
            {"key": "ch1", "name": "第一章 緒論", "prompt": "背景、動機、目的、範圍與限制"},
            {"key": "ch2", "name": "第二章 文獻探討", "prompt": "理論基礎、觀念性架構推導"},
            {"key": "ch3", "name": "第三章 研究方法", "prompt": "架構、方法步驟、工具"},
            {"key": "ch4", "name": "第四章 分析結果", "prompt": "數據呈現、圖表分析"},
            {"key": "ch5", "name": "第五章 結論與建議", "prompt": "發現、意涵、限制與建議"}
        ]
    else:
        CHAPTERS = [
            {"key": "ch1", "name": "1. 前言", "prompt": "背景、目的、範圍"},
            {"key": "ch2", "name": "2. 文獻回顧", "prompt": "相關研究與假說"},
            {"key": "ch3", "name": "3. 研究方法", "prompt": "方法與設計"},
            {"key": "ch4", "name": "4. 研究結果", "prompt": "數據分析"},
            {"key": "ch5", "name": "5. 討論與結論", "prompt": "意涵、限制、建議"}
        ]

    st.markdown("#### 關鍵字 (可複選)")
    business_keywords = ["策略管理", "競爭優勢", "ESG", "永續發展", "消費者行為", "滿意度", "人力資源", "教育訓練", "組織承諾", "供應鏈管理", "金融科技", "AI應用", "多準則決策"]
    selected_kws = st.multiselect("勾選：", business_keywords)
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
        st.markdown("#### ☑️ MCDM 方法")
        mcdm_tools = st.multiselect(
            "選擇方法：", 
            ["Delphi (德爾菲法)", "Fuzzy Delphi", "AHP", "Fuzzy AHP", "ANP", "DEMATEL", "DANP", "FCM", "TOPSIS", "VIKOR"],
            default=["Delphi (德爾菲法)", "AHP"]
        )
        final_method = f"多準則決策 ({' + '.join(mcdm_tools)})" if mcdm_tools else "多準則決策"
        
        st.markdown("#### 🏗️ 架構設定")
        num_dims = st.number_input("構面數量", 2, 10, 3)
        num_crits = st.number_input("準則數量(每構面)", 2, 10, 4)

# --- 主畫面 ---
st.title("🧠 論文寫作助手 (記憶修正版)")

if not api_key: st.warning("請先輸入 API Key"); st.stop()

# === 步驟 0 ===
if st.session_state.step == 0:
    st.subheader("步驟 0：構思題目")
    if st.button("✨ 產生建議題目"):
        if not keywords_str: st.error("請選擇或輸入關鍵字")
        else:
            with st.spinner("構思中..."):
                prompt = f"關鍵字：{keywords_str}。方法：{final_method}。格式：{paper_type}。請產生 3 個繁體中文學術題目。"
                # 將規則傳入函式
                res = ask_gemini(prompt, api_key, selected_model, st.session_state.global_rules)
                titles = [t.strip() for t in res.split('\n') if t.strip() and not t.startswith("Here")]
                st.session_state.proposed_titles = [re.sub(r'^\d+\.\s*', '', t).replace('*', '').strip() for t in titles if t.strip()]
                st.rerun()

    if st.session_state.proposed_titles:
        chosen = st.radio("選擇題目：", st.session_state.proposed_titles)
        if st.button("🔒 鎖定題目，下一步"):
            st.session_state.final_title = chosen
            st.session_state.step = 1
            st.rerun()

# === 步驟 1 ===
elif st.session_state.step == 1:
    st.subheader("步驟 1：導入真實文獻")
    st.info("請貼上真實文獻。AI 在寫作時會嚴格遵守此處提供的資料。")
    raw_refs = st.text_area("📋 文獻資料貼上區：", height=300)
    
    if st.button("✅ 確認文獻，下一步"):
        if not raw_refs: st.error("請貼上文獻")
        else:
            st.session_state.refs = raw_refs
            st.session_state.step = 1.5 
            st.rerun()

# === 步驟 1.5 ===
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
                    st.session_state.framework = ask_gemini(prompt, api_key, selected_model, st.session_state.global_rules)
                    st.rerun()
        
        if st.session_state.framework:
            edited_framework = st.text_area("編輯架構：", value=st.session_state.framework, height=400)
            if edited_framework != st.session_state.framework:
                st.session_state.framework = edited_framework
            
            if st.button("📊 繪製直式架構圖"):
                with st.spinner("繪圖中..."):
                    graph_prompt = f"請根據以下架構，生成 Graphviz DOT 代碼。Rankdir=TB (直式)。繁體中文。\n{st.session_state.framework}"
                    code_res = ask_gemini(graph_prompt, api_key, selected_model, st.session_state.global_rules)
                    st.session_state.framework_dot = clean_graphviz_code(code_res)
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
    st.subheader(f"步驟 2：生成大綱 ({paper_type})")
    if st.button("📝 生成大綱"):
        with st.spinner("規劃中..."):
            prompt = f"""
            題目：{st.session_state.final_title}
            方法：{final_method}
            格式：{paper_type}
            架構：{st.session_state.framework}
            請寫出大綱。請遵守側邊欄的全域規則。
            """
            st.session_state.outline = ask_gemini(prompt, api_key, selected_model, st.session_state.global_rules)
            st.rerun()
            
    if st.session_state.outline:
        st.markdown(st.session_state.outline)
        if st.button("下一步：開始逐章寫作"):
            st.session_state.step = 3
            st.rerun()

# === 步驟 3: 逐章寫作 (記憶核心) ===
elif st.session_state.step == 3:
    current_idx = st.session_state.current_ch_index
    if current_idx < len(CHAPTERS):
        curr_ch = CHAPTERS[current_idx]
        ch_key = curr_ch["key"]
        ch_name = curr_ch["name"]
        
        st.subheader(f"✍️ 寫作進度：{ch_name}")
        st.info(f"重點：{curr_ch['prompt']}")
        st.warning(f"⚠️ AI 將嚴格遵守側邊欄的規則：\n{st.session_state.global_rules}")
        
        current_content = st.session_state.content.get(ch_key, "")
        
        if not current_content:
            if st.button(f"🚀 開始撰寫 {ch_name}"):
                with st.spinner(f"AI 正在撰寫..."):
                    extra_instruction = ""
                    # 根據學術邏輯自動添加的指令
                    if "第一章" in ch_name: extra_instruction = "請明確界定研究範圍與限制。"
                    elif "第二章" in ch_name: extra_instruction = "引用真實文獻，歸納觀念性架構。"
                    elif "第三章" in ch_name: extra_instruction = "描述方法步驟與工具，勿寫限制。"
                    elif "第五章" in ch_name: extra_instruction = "包含研究限制與未來建議。"
                    elif "第四章" in ch_name: 
                        extra_instruction = "模擬豐富顯著數據，使用 Markdown 表格。"
                        graph_p = f"針對 {final_method} 分析結果，畫出直式(TB)關係圖。回傳 DOT code。"
                        code = ask_gemini(graph_p, api_key, selected_model, st.session_state.global_rules)
                        st.session_state.graph_code = clean_graphviz_code(code)

                    prompt = f"""
                    撰寫「{ch_name}」。題目：{st.session_state.final_title}。
                    格式：{paper_type}。方法：{final_method}。
                    架構：{st.session_state.framework}。文獻：{st.session_state.refs}。
                    {extra_instruction}
                    """
                    res = ask_gemini(prompt, api_key, selected_model, st.session_state.global_rules)
                    st.session_state.content[ch_key] = res
                    
                    if "第二章" in ch_name:
                        graph_p = f"根據架構 {st.session_state.framework}，繪製直式(TB)觀念架構圖。回傳 DOT code。"
                        code = ask_gemini(graph_p, api_key, selected_model, st.session_state.global_rules)
                        st.session_state.concept_map_code = clean_graphviz_code(code)
                    st.rerun()
        else:
            st.markdown("### 📖 章節預覽")
            st.markdown(current_content)
            
            if "第二章" in ch_name and st.session_state.concept_map_code:
                st.markdown("#### 📊 觀念性架構圖")
                try: st.graphviz_chart(st.session_state.concept_map_code)
                except: pass
            if "第四章" in ch_name and st.session_state.graph_code:
                st.markdown("#### 📊 分析結果示意圖")
                try: st.graphviz_chart(st.session_state.graph_code)
                except: pass

            st.divider()
            col1, col2 = st.columns([3, 1])
            with col1:
                feedback = st.text_area(f"修改意見 (您的修正將同步更新到全域規則，讓 AI 記住)：", height=100)
                if st.button("🔄 依照意見重寫"):
                    with st.spinner("修正中..."):
                        # 【關鍵】如果使用者指正了錯誤，我們就把這個指正也加到「全域規則」裡
                        # 這樣下一章 AI 就不會再犯了
                        if feedback not in st.session_state.global_rules:
                            st.session_state.global_rules += f"\n- {feedback}"
                        
                        fix_prompt = f"重寫「{ch_name}」。原稿：{current_content}。意見：{feedback}。"
                        new_content = ask_gemini(fix_prompt, api_key, selected_model, st.session_state.global_rules)
                        st.session_state.content[ch_key] = new_content
                        st.rerun()
            with col2:
                st.write(" ")
                st.write(" ")
                if st.button(f"✅ 通過，下一章", type="primary"):
                    st.session_state.current_ch_index += 1
                    st.rerun()
    else:
        st.success("🎉 全文撰寫完成！")
        if st.button("前往最終整理"):
            st.session_state.step = 4
            st.rerun()

# === 步驟 4: 下載 ===
elif st.session_state.step == 4:
    st.subheader("步驟 4：最終整理與下載")
    if not st.session_state.apa_refs:
        if st.button("📄 生成 APA"):
            with st.spinner("整理中..."):
                apa_prompt = f"整理 APA 7th 參考文獻：\n{st.session_state.refs}"
                st.session_state.apa_refs = ask_gemini(apa_prompt, api_key, selected_model, st.session_state.global_rules)
                st.rerun()
    
    if st.session_state.apa_refs:
        st.markdown("### 📥 下載選項")
        chapter_options = {ch['key']: ch['name'] for ch in CHAPTERS}
        chapter_options['ref'] = "參考文獻 (APA)"
        selected_chapters = st.multiselect("勾選下載章節", list(chapter_options.keys()), default=list(chapter_options.keys()))
        
        # 建立 HTML 內容
        html_body = f"<h1 style='text-align:center;'>{st.session_state.final_title}</h1>"
        final_text = f"# {st.session_state.final_title}\n\n" # Markdown 版本
        
        for ch in CHAPTERS:
            if ch['key'] in selected_chapters:
                content = st.session_state.content.get(ch['key'], '')
                
                # HTML 組裝
                html_body += f"<h2>{ch['name']}</h2>"
                html_body += f"<p>{content.replace(chr(10), '<br>')}</p>"
                
                # Markdown 組裝
                final_text += content + "\n\n"
                
                # 圖片處理 (HTML only)
                if ch['key'] == 'ch2' and st.session_state.concept_map_code:
                    html_body += "<h3>觀念性架構圖</h3>"
                    html_body += get_graph_img_tag(st.session_state.concept_map_code)
                if ch['key'] == 'ch4' and st.session_state.graph_code:
                    html_body += "<h3>分析結果示意圖</h3>"
                    html_body += get_graph_img_tag(st.session_state.graph_code)
                    
        if "ref" in selected_chapters:
            html_body += "<h2>參考文獻</h2>"
            html_body += f"<p>{st.session_state.apa_refs.replace(chr(10), '<br>')}</p>"
            final_text += "\n\n## 參考文獻\n" + st.session_state.apa_refs
        
        # 下載格式
        fmt = st.radio("格式", ["HTML (含圖片)", "Markdown", "TXT"])
        if fmt == "Markdown":
            st.download_button("📥 下載 Markdown", final_text, "Thesis.md")
        elif fmt == "TXT":
            st.download_button("📥 下載 TXT", final_text, "Thesis.txt")
        else:
            final_html = f"<html><head><meta charset='utf-8'><style>body {{ font-family: sans-serif; line-height: 1.6; padding: 20px; }} img {{ display: block; margin: 0 auto; }}</style></head><body>{html_body}</body></html>"
            st.download_button("📥 下載 HTML", final_html, "Thesis.html", mime="text/html")

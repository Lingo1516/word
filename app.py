import streamlit as st
import requests
import json
import re

# --- 系統設定 ---
st.set_page_config(page_title="論文寫作助手 (學術嚴謹版)", layout="wide", page_icon="🎓")

# --- [關鍵新增] 學術寫作規範指令 (您提供的規則) ---
ACADEMIC_RULES_CH2 = """
**【文獻回顧撰寫嚴格規範】**
在撰寫本章時，請務必遵守以下學術標準：
1. **理論依據明確**：提出任何構面或分類時，必須在段落開頭說明其理論基礎（例如：「本研究參考 ADDIE 模型之分析階段...」），不可憑空分類。
2. **文獻支持具體**：每一個準則或細項，都必須有具體的文獻引用支持（例如：「某學者(Year)指出...」），不可僅列為背景。
3. **善用綜合比較表**：必須包含一個結構化表格，欄位包括：「構面」、「準則/指標」、「關鍵文獻來源」、「理論基礎/參考模型」。
4. **邏輯推演**：請展現「先論述文獻，再歸納出本研究架構」的邏輯，不要先講結論。
5. **引用格式**：文中引用 (In-text Citation) 必須精準，且必須與使用者提供的真實文獻列表一致。
"""

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

# --- 核心 3: 清洗圖表代碼 ---
def clean_graphviz_code(raw_code):
    clean = raw_code.replace("```dot", "").replace("```", "").strip()
    match = re.search(r'digraph\s+.*\{.*\}', clean, re.DOTALL)
    if match: return match.group(0)
    start = clean.find('{')
    end = clean.rfind('}')
    if start != -1 and end != -1: return f"digraph G {clean[start:end+1]}"
    return clean

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
if 'graph_code' not in st.session_state: st.session_state.graph_code = "" # 第四章結果圖
if 'concept_map_code' not in st.session_state: st.session_state.concept_map_code = "" # 第二章觀念架構圖
if 'apa_refs' not in st.session_state: st.session_state.apa_refs = ""
if 'my_models' not in st.session_state: st.session_state.my_models = []

# 章節定義 (調整說明)
CHAPTERS = [
    {"key": "ch1", "name": "第一章 緒論", "desc": "背景、動機、目的、研究流程 (不含詳細架構圖)"},
    {"key": "ch2", "name": "第二章 文獻探討", "desc": "理論基礎推導、歸納指標、建立觀念性架構 (含架構圖)"},
    {"key": "ch3", "name": "第三章 研究方法", "desc": "研究設計、操作型定義、分析工具"},
    {"key": "ch4", "name": "第四章 分析結果", "desc": "數據分析、結果呈現"},
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
    
    # 商管關鍵字選單
    st.markdown("#### 關鍵字 (可複選)")
    business_keywords = [
        "策略管理", "競爭優勢", "商業模式", "數位轉型", "ESG", "永續發展", 
        "消費者行為", "顧客滿意度", "服務品質", "品牌形象",
        "人力資源", "教育訓練", "組織承諾", "領導統御", "工作績效",
        "供應鏈管理", "風險管理", "金融科技", "AI應用", "多準則決策"
    ]
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
        
        st.divider()
        st.markdown("#### 🏗️ 架構設定")
        num_dims = st.number_input("構面數量", 2, 10, 3)
        num_crits = st.number_input("準則數量(每構面)", 2, 10, 4)

# --- 主畫面 ---
st.title("🎓 論文寫作助手 (學術邏輯嚴謹版)")

if not api_key: st.warning("請先輸入 API Key"); st.stop()

# === 步驟 0: 題目 ===
if st.session_state.step == 0:
    st.subheader("步驟 0：構思題目")
    if st.button("✨ 產生建議題目"):
        if not keywords_str: st.error("請選擇或輸入關鍵字")
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
    st.info("請貼上華藝或 Google 學術的真實文獻資料。這是整篇論文的基礎。")
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
        st.markdown("### 📝 文字架構 (MCDM)")
        if not st.session_state.framework:
            if st.button("⚡ 依照文獻產生架構建議"):
                with st.spinner("分析中..."):
                    prompt = f"""
                    題目：{st.session_state.final_title}
                    文獻：{st.session_state.refs}
                    任務：建立評估指標體系 ({num_dims}構面 x {num_crits}準則)。
                    請務必參考文獻中的構面，輸出 Markdown 列表。
                    """
                    st.session_state.framework = ask_gemini(prompt, api_key, selected_model)
                    st.rerun()
        
        if st.session_state.framework:
            edited_framework = st.text_area("編輯架構：", value=st.session_state.framework, height=400)
            if edited_framework != st.session_state.framework:
                st.session_state.framework = edited_framework
    
    with col2:
        st.info("此階段僅確認文字架構。詳細的架構圖將在「第二章」撰寫完畢後生成，以符合學術邏輯。")

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
            prompt = f"""
            題目：{st.session_state.final_title}。
            方法：{final_method}。
            架構：{st.session_state.framework}。
            請寫出五章大綱。
            **注意：研究架構圖與假說推導應安排在第二章末尾或第三章開頭，第一章僅做背景介紹。**
            """
            st.session_state.outline = ask_gemini(prompt, api_key, selected_model)
            st.rerun()
            
    if st.session_state.outline:
        st.markdown(st.session_state.outline)
        if st.button("下一步：開始逐章寫作"):
            st.session_state.step = 3
            st.rerun()

# === 步驟 3: 逐章寫作 (核心修正：邏輯與圖表) ===
elif st.session_state.step == 3:
    
    current_idx = st.session_state.current_ch_index
    
    if current_idx < len(CHAPTERS):
        curr_ch = CHAPTERS[current_idx]
        ch_key = curr_ch["key"]
        ch_name = curr_ch["name"]
        
        st.subheader(f"✍️ 寫作進度：{ch_name}")
        st.info(f"重點：{curr_ch['desc']}")
        
        current_content = st.session_state.content.get(ch_key, "")
        
        if not current_content:
            if st.button(f"🚀 開始撰寫 {ch_name}"):
                with st.spinner(f"AI 正在撰寫 {ch_name}..."):
                    
                    # 根據章節加入特殊指令
                    extra_instruction = ""
                    
                    if "第一章" in ch_name:
                        extra_instruction = """
                        **【嚴格禁止】**：本章絕對不可出現「研究架構圖」或詳細的構面準則表。這些應保留至第二章推導後呈現。
                        本章重點在於：研究背景、動機、目的、研究流程。
                        """
                    
                    elif "第二章" in ch_name:
                        # 這裡注入您要求的學術規範
                        extra_instruction = f"""
                        {ACADEMIC_RULES_CH2}
                        **任務**：
                        1. 最後必須歸納出本研究的「觀念性架構 (Conceptual Framework)」。
                        2. 必須包含一個「構面/準則與來源文獻對照表」。
                        """
                    
                    elif "第四章" in ch_name:
                        extra_instruction = "請模擬豐富且顯著的數據，使用 Markdown 表格。針對 MCDM 方法進行分析（如權重、因果圖）。"

                    prompt = f"""
                    請撰寫「{ch_name}」。
                    題目：{st.session_state.final_title}
                    方法：{final_method}
                    架構：{st.session_state.framework}
                    文獻：{st.session_state.refs}
                    
                    {extra_instruction}
                    
                    要求：繁體中文，學術語氣。
                    """
                    res = ask_gemini(prompt, api_key, selected_model)
                    st.session_state.content[ch_key] = res
                    
                    # 自動生成圖表 (視章節而定)
                    if "第二章" in ch_name:
                        # 第二章結束時，畫「觀念架構圖」
                        graph_p = f"根據以下確認的架構，繪製 Graphviz DOT 層級圖 (Hierarchy Tree)：\n{st.session_state.framework}\n要求：繁體中文，只回傳DOT代碼。"
                        code = ask_gemini(graph_p, api_key, selected_model)
                        st.session_state.concept_map_code = clean_graphviz_code(code)
                    
                    if "第四章" in ch_name:
                        # 第四章結束時，畫「分析結果圖」
                        graph_p = f"針對 {final_method} 的分析結果，繪製示意圖 (如因果圖或權重圖)。回傳 DOT 代碼。"
                        code = ask_gemini(graph_p, api_key, selected_model)
                        st.session_state.graph_code = clean_graphviz_code(code)
                    
                    st.rerun()
        
        else:
            # 顯示內容與圖表
            st.markdown("### 📖 章節預覽")
            st.markdown(current_content)
            
            # 顯示第二章的架構圖
            if "第二章" in ch_name and st.session_state.concept_map_code:
                st.markdown("#### 📊 本研究觀念性架構圖 (Conceptual Framework)")
                st.caption("說明：此圖為根據文獻回顧歸納後之架構。")
                try: st.graphviz_chart(st.session_state.concept_map_code)
                except: pass
            
            # 顯示第四章的結果圖
            if "第四章" in ch_name and st.session_state.graph_code:
                st.markdown("#### 📊 分析結果示意圖")
                try: st.graphviz_chart(st.session_state.graph_code)
                except: pass

            st.divider()
            col1, col2 = st.columns([3, 1])
            with col1:
                feedback = st.text_area(f"修改意見：", height=100)
                if st.button("🔄 依照意見重寫"):
                    if feedback:
                        with st.spinner("修正中..."):
                            fix_prompt = f"重寫「{ch_name}」。原稿：{current_content}。意見：{feedback}。請修正。"
                            new_content = ask_gemini(fix_prompt, api_key, selected_model)
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

# === 步驟 4: 最終整理 ===
elif st.session_state.step == 4:
    st.subheader("步驟 4：最終整理與下載")
    
    if not st.session_state.apa_refs:
        if st.button("📄 生成 APA"):
            with st.spinner("整理中..."):
                apa_prompt = f"請將以下真實文獻整理成標準 APA 7th 格式：\n{st.session_state.refs}"
                st.session_state.apa_refs = ask_gemini(apa_prompt, api_key, selected_model)
                st.rerun()
    
    if st.session_state.apa_refs:
        st.markdown("### 📥 下載選項")
        chapter_options = {ch['key']: ch['name'] for ch in CHAPTERS}
        chapter_options['ref'] = "參考文獻 (APA)"
        selected_chapters = st.multiselect("勾選下載章節", list(chapter_options.keys()), default=list(chapter_options.keys()))
        
        final_text = f"# {st.session_state.final_title}\n\n"
        for ch in CHAPTERS:
            if ch['key'] in selected_chapters:
                final_text += st.session_state.content.get(ch['key'], '') + "\n\n"
        if "ref" in selected_chapters:
            final_text += "\n\n## 參考文獻\n" + st.session_state.apa_refs
        
        with st.expander("預覽全文"):
            st.markdown(final_text)
        st.download_button("📥 下載檔案", final_text, "Thesis_Final.md")

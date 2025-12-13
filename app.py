import streamlit as st
import google.generativeai as genai
import re
import urllib.parse
import time  # <--- 新增這個，用來計時等待
from google.api_core import exceptions

# --- 系統設定 ---
st.set_page_config(page_title="論文寫作助手 (自動重試版)", layout="wide", page_icon="🧠")

# --- 核心 1: 智慧掃描模型 (只留最強的兩個) ---
def get_best_models(api_key):
    try:
        genai.configure(api_key=api_key)
        all_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                name = m.name.replace('models/', '')
                all_models.append(name)
        
        recommended = []
        # 1. 找 Pro
        pro_candidates = [m for m in all_models if 'gemini-1.5-pro' in m and 'latest' in m]
        if not pro_candidates: pro_candidates = [m for m in all_models if 'gemini-1.5-pro' in m]
        if pro_candidates: recommended.append(pro_candidates[0])
        
        # 2. 找 Flash
        flash_candidates = [m for m in all_models if 'gemini-1.5-flash' in m and 'latest' in m]
        if not flash_candidates: flash_candidates = [m for m in all_models if 'gemini-1.5-flash' in m]
        if flash_candidates: recommended.append(flash_candidates[0])

        return recommended if recommended else all_models
    except Exception as e:
        return []

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

# --- 核心 4: 寫作函式 (加入自動重試機制) ---
def ask_gemini(prompt, api_key, model_name, user_rules=""):
    if not api_key: return "⚠️ 請設定 Key"
    
    genai.configure(api_key=api_key)
    
    sys_instruction = "你是一個專業的學術論文寫作助手。請使用繁體中文。"
    if user_rules:
        sys_instruction += f"\n\n【使用者最高優先級規則】\n{user_rules}"

    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=sys_instruction
    )
    
    generation_config = genai.types.GenerationConfig(
        temperature=0.7, 
    )

    # --- 自動重試迴圈 (最多試 3 次) ---
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt, generation_config=generation_config)
            return response.text
        
        except exceptions.ResourceExhausted:
            # 如果是最後一次嘗試，還是失敗，才回傳錯誤
            if attempt == max_retries - 1:
                return "⏳ 伺服器忙碌，已重試多次仍失敗。建議切換成 Flash 模型或稍後再試。"
            
            # 否則，等待後重試
            wait_time = 10 * (attempt + 1) # 第一次等10秒，第二次等20秒
            with st.spinner(f"⚠️ 觸發 Google 速度限制，系統自動等待 {wait_time} 秒後重試 ({attempt+1}/{max_retries})..."):
                time.sleep(wait_time)
            continue # 重新執行 try 區塊
            
        except exceptions.InvalidArgument:
            return f"❌ 參數錯誤或模型不支援: {model_name}"
        except Exception as e:
            return f"❌ 發生錯誤：{str(e)}"
            
    return "❌ 未知錯誤"

# --- 初始化 Session State ---
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
if 'global_rules' not in st.session_state: st.session_state.global_rules = "1. 嚴禁使用 LaTeX 語法。\n2. 必須使用繁體中文。\n3. 語氣需專業學術。"

# --- 側邊欄 ---
api_key = None
if "GOOGLE_API_KEY" in st.secrets: api_key = st.secrets["GOOGLE_API_KEY"]

with st.sidebar:
    st.header("⚙️ 1. 引擎設定")
    if not api_key:
        user_key = st.text_input("API Key", type="password")
        if user_key: api_key = user_key
    
    if api_key:
        if not st.session_state.my_models:
             st.session_state.my_models = ["gemini-1.5-pro", "gemini-1.5-flash"]

        if st.button("🔄 檢查連線 & 更新模型"):
             with st.spinner("正在尋找最佳模型..."):
                found = get_best_models(api_key)
                if found: 
                    st.session_state.my_models = found
                    st.success(f"已鎖定 {len(found)} 個最佳模型！")
                else: 
                    st.error("連線失敗")

    model_options = st.session_state.my_models if st.session_state.my_models else ["gemini-1.5-pro", "gemini-1.5-flash"]
    st.markdown("### 🤖 選擇模型")
    selected_model = st.selectbox("目前使用：", model_options, index=0)
    
    if "pro" in selected_model:
        st.info("✅ **已選擇 Pro**：邏輯最強，適合寫論文內文。(若卡住會自動重試)")
    elif "flash" in selected_model:
        st.info("⚡ **已選擇 Flash**：速度最快，幾乎不會卡頓。")
    
    st.divider()
    st.header("🧠 2. 記憶與規則")
    st.info("AI 將嚴格遵守以下規則：")
    user_rules = st.text_area("⚠️ 寫作禁忌：", value=st.session_state.global_rules, height=150)
    st.session_state.global_rules = user_rules

    st.divider()
    st.header("📝 3. 論文規格")
    paper_type = st.radio("寫作格式", ["學位論文 (Thesis)", "期刊論文 (Journal)"])
    
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

    st.markdown("#### 關鍵字")
    business_keywords = ["策略管理", "競爭優勢", "ESG", "永續發展", "消費者行為", "滿意度", "人力資源", "供應鏈管理", "金融科技", "AI應用"]
    selected_kws = st.multiselect("勾選：", business_keywords)
    custom_kw = st.text_input("自訂補充：")
    final_kws = selected_kws.copy()
    if custom_kw: final_kws.append(custom_kw)
    keywords_str = ", ".join(final_kws)

    st.divider()
    method_category = st.selectbox("研究途徑", ["多準則決策 (MCDM)", "量化研究 (問卷/數據)", "質性研究 (訪談/個案)", "實驗法"])
    final_method = method_category
    num_dims = 3
    num_crits = 4

    if "MCDM" in method_category:
        st.markdown("#### ☑️ MCDM 方法")
        mcdm_tools = st.multiselect(
            "選擇方法：", 
            ["Delphi", "Fuzzy Delphi", "AHP", "Fuzzy AHP", "ANP", "DEMATEL", "DANP", "FCM", "TOPSIS", "VIKOR"],
            default=["Delphi", "AHP"]
        )
        final_method = f"多準則決策 ({' + '.join(mcdm_tools)})" if mcdm_tools else "多準則決策"
        
        st.markdown("#### 🏗️ 架構設定")
        num_dims = st.number_input("構面數量", 2, 10, 3)
        num_crits = st.number_input("準則數量(每構面)", 2, 10, 4)

# --- 主畫面 ---
st.title("🧠 論文寫作助手 (自動重試版)")

if not api_key: st.warning("⬅️ 請先在側邊欄輸入 API Key"); st.stop()

# === 步驟 0: 題目 ===
if st.session_state.step == 0:
    st.subheader("步驟 0：構思題目")
    if st.button("✨ 產生建議題目"):
        if not keywords_str: st.error("請選擇或輸入關鍵字")
        else:
            with st.spinner("構思中..."):
                prompt = f"關鍵字：{keywords_str}。方法：{final_method}。格式：{paper_type}。請產生 3 個繁體中文學術題目。"
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

# === 步驟 1: 文獻 ===
elif st.session_state.step == 1:
    st.subheader("步驟 1：導入真實文獻")
    st.info("請貼上真實文獻內容。AI 會基於此內容進行寫作。")
    raw_refs = st.text_area("📋 文獻資料貼上區：", height=300)
    
    if st.button("✅ 確認文獻，下一步"):
        if not raw_refs: st.error("請貼上文獻")
        else:
            st.session_state.refs = raw_refs
            st.session_state.step = 1.5 
            st.rerun()

# === 步驟 1.5: 架構 ===
elif st.session_state.step == 1.5:
    st.subheader("步驟 1.5：建構評估體系")
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
                    graph_prompt = f"請根據以下架構，生成 Graphviz DOT 代碼。Rankdir=TB (直式)。\n{st.session_state.framework}"
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
            請寫出大綱。
            """
            st.session_state.outline = ask_gemini(prompt, api_key, selected_model, st.session_state.global_rules)
            st.rerun()
            
    if st.session_state.outline:
        st.markdown(st.session_state.outline)
        if st.button("下一步：開始逐章寫作"):
            st.session_state.step = 3
            st.rerun()

# === 步驟 3: 逐章寫作 ===
elif st.session_state.step == 3:
    current_idx = st.session_state.current_ch_index
    if current_idx < len(CHAPTERS):
        curr_ch = CHAPTERS[current_idx]
        ch_key = curr_ch["key"]
        ch_name = curr_ch["name"]
        
        st.subheader(f"✍️ 寫作進度：{ch_name}")
        st.info(f"重點：{curr_ch['prompt']}")
        
        current_content = st.session_state.content.get(ch_key, "")
        
        if not current_content:
            if st.button(f"🚀 開始撰寫 {ch_name}"):
                with st.spinner(f"AI 正在撰寫... (若遇速度限制將自動重試)"):
                    extra_instruction = ""
                    if "第一章" in ch_name or "前言" in ch_name: extra_instruction = "請明確界定研究範圍與限制。"
                    elif "第二章" in ch_name or "文獻" in ch_name: extra_instruction = "引用真實文獻，歸納觀念性架構。"
                    elif "第三章" in ch_name or "方法" in ch_name: extra_instruction = "描述方法步驟與工具，勿寫限制。"
                    elif "第五章" in ch_name or "結論" in ch_name: extra_instruction = "包含研究限制與未來建議。"
                    elif "第四章" in ch_name or "結果" in ch_name: 
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
                    
                    if ("第二章" in ch_name or "文獻" in ch_name) and st.session_state.framework:
                        graph_p = f"根據架構 {st.session_state.framework}，繪製直式(TB)觀念架構圖。回傳 DOT code。"
                        code = ask_gemini(graph_p, api_key, selected_model, st.session_state.global_rules)
                        st.session_state.concept_map_code = clean_graphviz_code(code)
                    st.rerun()
        else:
            st.markdown("### 📖 章節預覽")
            st.markdown(current_content)
            
            if ("第二章" in ch_name or "文獻" in ch_name) and st.session_state.concept_map_code:
                st.markdown("#### 📊 觀念性架構圖")
                try: st.graphviz_chart(st.session_state.concept_map_code)
                except: pass
            if ("第四章" in ch_name or "結果" in ch_name) and st.session_state.graph_code:
                st.markdown("#### 📊 分析結果示意圖")
                try: st.graphviz_chart(st.session_state.graph_code)
                except: pass

            st.divider()
            col1, col2 = st.columns([3, 1])
            with col1:
                feedback = st.text_area(f"修改意見 (將自動加入全域記憶)：", height=100)
                if st.button("🔄 依照意見重寫"):
                    with st.spinner("修正中..."):
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
        
        # 建立內容
        html_body = f"<h1 style='text-align:center;'>{st.session_state.final_title}</h1>"
        final_text = f"# {st.session_state.final_title}\n\n" 
        
        for ch in CHAPTERS:
            if ch['key'] in selected_chapters:
                content = st.session_state.content.get(ch['key'], '')
                html_body += f"<h2>{ch['name']}</h2>"
                html_body += f"<p>{content.replace(chr(10), '<br>')}</p>"
                final_text += content + "\n\n"
                
                if (ch['key'] == 'ch2' or "文獻" in ch['name']) and st.session_state.concept_map_code:
                    html_body += "<h3>觀念性架構圖</h3>" + get_graph_img_tag(st.session_state.concept_map_code)
                if (ch['key'] == 'ch4' or "結果" in ch['name']) and st.session_state.graph_code:
                    html_body += "<h3>分析結果示意圖</h3>" + get_graph_img_tag(st.session_state.graph_code)
                    
        if "ref" in selected_chapters:
            html_body += "<h2>參考文獻</h2>" + f"<p>{st.session_state.apa_refs.replace(chr(10), '<br>')}</p>"
            final_text += "\n\n## 參考文獻\n" + st.session_state.apa_refs
        
        fmt = st.radio("格式", ["HTML (含圖片)", "Markdown", "TXT"])
        if fmt == "Markdown":
            st.download_button("📥 下載 Markdown", final_text, "Thesis.md")
        elif fmt == "TXT":
            st.download_button("📥 下載 TXT", final_text, "Thesis.txt")
        else:
            final_html = f"<html><head><meta charset='utf-8'><style>body {{ font-family: sans-serif; line-height: 1.6; padding: 20px; }} img {{ display: block; margin: 0 auto; }}</style></head><body>{html_body}</body></html>"
            st.download_button("📥 下載 HTML", final_html, "Thesis.html", mime="text/html")

import streamlit as st
import requests
import json
import re

# --- 系統設定 ---
st.set_page_config(page_title="論文寫作助手 (MCDM 架構版)", layout="wide", page_icon="🏗️")

# --- 核心連線函式 ---
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
if 'framework' not in st.session_state: st.session_state.framework = "" # 新增：儲存構面準則
if 'outline' not in st.session_state: st.session_state.outline = ""
if 'content' not in st.session_state: st.session_state.content = {}
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
    if api_key: st.success("✅ 金鑰已載入")

    # 模型選擇
    model_options = ["gemini-1.5-flash", "gemini-1.5-pro"]
    selected_model = st.selectbox("選擇模型", model_options, index=0)
    
    st.divider()
    st.header("📝 2. 研究設定")
    
    # 關鍵字
    k1 = st.text_input("關鍵字 1", value="")
    k2 = st.text_input("關鍵字 2", value="")
    k3 = st.text_input("關鍵字 3", value="")
    keywords_str = ", ".join([k for k in [k1, k2, k3] if k.strip()])

    st.divider()
    
    # 方法選擇
    method_category = st.selectbox("研究途徑", ["多準則決策 (MCDM)", "量化研究", "質性研究", "實驗法"])
    
    final_method = method_category
    num_dims = 3 # 預設值
    num_crits = 4 # 預設值
    
    if method_category == "多準則決策 (MCDM)":
        # 【修改點 1】加入 Delphi 到選單
        mcdm_tool = st.selectbox("MCDM 方法", 
            ["Delphi (德爾菲法)", "AHP (層級分析法)", "ANP", "DEMATEL", "TOPSIS", "VIKOR", "Fuzzy AHP", "DANP", "Fuzzy Delphi"]
        )
        final_method = f"多準則決策 - {mcdm_tool}"
        
        # 【修改點 2】讓使用者設定數量
        st.markdown("#### 🏗️ 設定架構數量")
        num_dims = st.number_input("欲建立的「構面」數量", min_value=2, max_value=10, value=3)
        num_crits = st.number_input("每個構面下的「準則」數量 (約)", min_value=2, max_value=10, value=3)
        
        st.info(f"預計產生：{num_dims} 個構面 x {num_crits} 個準則")

# --- 主畫面 ---
st.title("🏗️ 論文寫作助手 (MCDM 架構生成版)")

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
                titles = [t.strip() for t in res.split('\n') if t.strip()]
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

# === 步驟 1: 文獻 (真實資料) ===
elif st.session_state.step == 1:
    st.subheader("步驟 1：導入真實文獻")
    st.info("請貼上華藝或 Google 學術的真實文獻資料 (作者/年份/題目/摘要)。")
    
    raw_refs = st.text_area("📋 文獻資料貼上區：", height=300)
    
    if st.button("✅ 確認文獻，下一步 (建構架構)"):
        if not raw_refs:
            st.error("請貼上文獻")
        else:
            # 簡單整理一下
            st.session_state.refs = raw_refs
            st.session_state.step = 1.5 # 跳到新增的步驟
            st.rerun()

# === 步驟 1.5: 建構評估架構 (新增功能) ===
elif st.session_state.step == 1.5:
    st.subheader("步驟 1.5：建構評估指標體系 (構面與準則)")
    st.info(f"根據您設定的：{num_dims} 個構面，每個構面約 {num_crits} 個準則。AI 將依據文獻為您命名。")
    
    if not st.session_state.framework:
        if st.button("⚡ 依照文獻與題目，產生構面與準則"):
            with st.spinner("正在分析文獻並萃取指標..."):
                prompt = f"""
                題目：{st.session_state.final_title}
                參考文獻：{st.session_state.refs}
                
                任務：請為本研究建立一個評估指標體系。
                **結構要求**：
                1. 總共有 **{num_dims} 個主要構面 (Dimensions)**。
                2. 每個構面下約有 **{num_crits} 個評估準則 (Criteria)**。
                
                請輸出成 Markdown 表格或條列式，格式如下：
                - 構面 A：[名稱]
                  - 準則 A1：[名稱] - [簡短定義]
                  - 準則 A2：[名稱] - [簡短定義]
                ...
                """
                st.session_state.framework = ask_gemini(prompt, api_key, selected_model)
                st.rerun()
    
    if st.session_state.framework:
        st.write("▼ AI 建議的指標架構：")
        # 讓使用者可以修改架構
        edited_framework = st.text_area("您可以在此修改構面或準則名稱：", value=st.session_state.framework, height=400)
        
        if st.button("🔒 鎖定此架構，生成大綱"):
            st.session_state.framework = edited_framework
            st.session_state.step = 2
            st.rerun()

# === 步驟 2: 大綱 ===
elif st.session_state.step == 2:
    st.subheader("步驟 2：生成大綱")
    if st.button("📝 生成大綱"):
        with st.spinner("規劃中..."):
            prompt = f"""
            題目：{st.session_state.final_title}
            方法：{final_method}
            **確認的評估架構**：
            {st.session_state.framework}
            
            請寫出五章大綱。
            第三章必須包含上述架構的建立過程。
            第四章必須針對上述構面與準則進行分析。
            """
            st.session_state.outline = ask_gemini(prompt, api_key, selected_model)
            st.rerun()
            
    if st.session_state.outline:
        st.markdown(st.session_state.outline)
        if st.button("下一步：開始撰寫"):
            st.session_state.step = 3
            st.rerun()

# === 步驟 3: 撰寫 (整合架構) ===
elif st.session_state.step == 3:
    st.subheader("步驟 3：分章撰寫")
    
    tabs = st.tabs(["第一章", "第二章", "第三章", "第四章", "第五章"])
    
    def write_ch(ch, extra=""):
        return ask_gemini(f"""
        撰寫「{ch}」。
        題目：{st.session_state.final_title}。
        方法：{final_method}。
        **評估指標架構**：{st.session_state.framework}
        **真實文獻**：{st.session_state.refs}
        
        {extra}
        要求：繁體中文，學術語氣，強制引用真實文獻。
        """, api_key, selected_model)

    with tabs[0]:
        if st.button("✍️ 寫第一章"):
            with st.spinner("寫作中..."):
                st.session_state.content['ch1'] = write_ch("第一章 緒論", "包含研究背景、動機、目的")
        if 'ch1' in st.session_state.content: st.markdown(st.session_state.content['ch1'])

    with tabs[1]:
        if st.button("✍️ 寫第二章"):
            with st.spinner("寫作中..."):
                st.session_state.content['ch2'] = write_ch("第二章 文獻探討", "重點在於推導出構面與準則的理論依據。")
        if 'ch2' in st.session_state.content: st.markdown(st.session_state.content['ch2'])

    with tabs[2]:
        if st.button("✍️ 寫第三章"):
            with st.spinner("寫作中..."):
                extra = f"詳細說明 {final_method} 步驟。並詳細列出本研究建立的指標體系（{st.session_state.framework}）。"
                st.session_state.content['ch3'] = write_ch("第三章 研究方法", extra)
        if 'ch3' in st.session_state.content: st.markdown(st.session_state.content['ch3'])

    with tabs[3]:
        st.info("💡 將依據您設定的構面/準則進行模擬數據分析。")
        if st.button("✍️ 寫第四章 (數據增強)"):
            with st.spinner("模擬數據中..."):
                extra_prompt = f"""
                請針對以下架構進行數據模擬分析：
                {st.session_state.framework}
                
                要求：
                1. 模擬 {final_method} 的分析結果 (如權重、排序)。
                2. 數據要顯著且合理。
                3. 使用 Markdown 表格。
                """
                st.session_state.content['ch4'] = write_ch("第四章 資料分析與結果", extra_prompt)
        if 'ch4' in st.session_state.content: st.markdown(st.session_state.content['ch4'])

    with tabs[4]:
        if st.button("✍️ 寫第五章"):
            with st.spinner("寫作中..."):
                st.session_state.content['ch5'] = write_ch("第五章 結論", "依據第四章結果撰寫。")
        if 'ch5' in st.session_state.content: st.markdown(st.session_state.content['ch5'])

    st.divider()
    if len(st.session_state.content) >= 1:
        if st.button("下一步：加入意見 & APA"):
            st.session_state.step = 4
            st.rerun()

# === 步驟 4: 意見修正 & APA ===
elif st.session_state.step == 4:
    st.subheader("步驟 4：總體建議與 APA")
    
    user_feedback = st.text_area("📝 請輸入您的修改建議 (AI 將重寫第五章)：", height=150)
    
    if st.button("🚀 修整 & 生成 APA"):
        if not user_feedback:
            st.error("請輸入意見")
        else:
            with st.spinner("處理中..."):
                refine_prompt = f"""
                重寫第五章。題目：{st.session_state.final_title}
                原初稿：{st.session_state.content.get('ch5', '')}
                **用戶意見**：{user_feedback}
                """
                new_ch5 = ask_gemini(refine_prompt, api_key, selected_model)
                st.session_state.content['ch5'] = new_ch5
                
                apa_prompt = f"整理成 APA 7th 格式：\n{st.session_state.refs}"
                st.session_state.apa_refs = ask_gemini(apa_prompt, api_key, selected_model)
                st.rerun()

    if st.session_state.apa_refs:
        st.markdown("---")
        full_text = f"# {st.session_state.final_title}\n\n"
        for i in range(1, 6): full_text += st.session_state.content.get(f'ch{i}', '') + "\n\n"
        full_text += "\n\n## 參考文獻\n" + st.session_state.apa_refs
        
        st.download_button("📥 下載完整論文", full_text, "Thesis_MCDM.md")

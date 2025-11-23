import streamlit as st
import requests
import json
import re

# --- 系統設定 ---
st.set_page_config(page_title="論文寫作助手 (全功能終極版)", layout="wide", page_icon="💎")

# --- 核心 1: 掃描模型 (加回來了！) ---
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
if 'outline' not in st.session_state: st.session_state.outline = ""
if 'content' not in st.session_state: st.session_state.content = {}
if 'apa_refs' not in st.session_state: st.session_state.apa_refs = ""
if 'my_models' not in st.session_state: st.session_state.my_models = [] # 儲存掃描到的模型

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

    # 模型選擇邏輯
    model_options = ["gemini-1.5-flash", "gemini-1.5-pro"] # 預設值
    if st.session_state.my_models:
        model_options = st.session_state.my_models # 如果有掃描到，就用掃描的結果

    st.markdown("### 選擇模型")
    
    # 自動選一個包含 flash 的當預設值
    default_index = 0
    for i, m in enumerate(model_options):
        if 'flash' in m: default_index = i
        
    selected_model = st.selectbox("請選擇", model_options, index=default_index)
    
    st.divider()
    st.markdown("### 關鍵字 (5格)")
    k1 = st.text_input("關鍵字 1", value="")
    k2 = st.text_input("關鍵字 2", value="")
    k3 = st.text_input("關鍵字 3", value="")
    k4 = st.text_input("關鍵字 4", value="")
    k5 = st.text_input("關鍵字 5", value="")
    keywords_str = ", ".join([k for k in [k1, k2, k3, k4, k5] if k.strip()])

    st.divider()
    method_category = st.selectbox("研究途徑", ["多準則決策 (MCDM)", "量化研究 (SEM/回歸)", "質性研究", "實驗法"])
    final_method = method_category
    if method_category == "多準則決策 (MCDM)":
        mcdm_tool = st.selectbox("MCDM 方法", ["AHP", "ANP", "DEMATEL", "FCM (模糊認知圖)", "TOPSIS", "VIKOR", "Fuzzy AHP", "DANP"])
        final_method = f"多準則決策 - {mcdm_tool}"

# --- 主畫面 ---
st.title("💎 論文寫作助手 (全功能終極版)")

if not api_key: st.warning("請先輸入 API Key"); st.stop()

# === 步驟 0: 題目 ===
if st.session_state.step == 0:
    st.subheader("步驟 0：構思題目")
    if st.button("✨ 產生建議題目"):
        if not keywords_str: st.error("請輸入關鍵字")
        else:
            with st.spinner("構思中..."):
                prompt = f"關鍵字：{keywords_str}。方法：{final_method}。請產生 3 個繁體中文學術題目，不要解釋。"
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

# === 步驟 1: 文獻 (真實性檢核) ===
elif st.session_state.step == 1:
    st.subheader("步驟 1：建立與確認文獻")
    st.info("💡 請在下方「手動修改」文獻以確保真實性。")
    
    if not st.session_state.refs:
        if st.button("📚 搜尋繁體中文文獻"):
            with st.spinner("搜尋中..."):
                prompt = f"""
                題目：{st.session_state.final_title}
                方法：{final_method}
                
                請列出 10-15 筆繁體中文學術文獻 (管理評論等) 與少量英文經典。
                格式：[年份] 作者 - 篇名
                並說明研究缺口。
                """
                st.session_state.refs = ask_gemini(prompt, api_key, selected_model)
                st.rerun()
    
    if st.session_state.refs:
        st.write("▼ 文獻列表編輯區 (請確認真偽)：")
        edited_refs = st.text_area("編輯區", value=st.session_state.refs, height=300)
        
        if st.button("✅ 確認文獻無誤，生成大綱"):
            st.session_state.refs = edited_refs
            st.session_state.step = 2
            st.rerun()

# === 步驟 2: 大綱 ===
elif st.session_state.step == 2:
    st.subheader("步驟 2：生成大綱")
    if st.button("📝 生成大綱"):
        with st.spinner("規劃中..."):
            prompt = f"題目：{st.session_state.final_title}。方法：{final_method}。文獻：{st.session_state.refs}。請寫出五章大綱，第四章需包含圖表規劃。"
            st.session_state.outline = ask_gemini(prompt, api_key, selected_model)
            st.rerun()
            
    if st.session_state.outline:
        st.markdown(st.session_state.outline)
        if st.button("下一步：開始撰寫"):
            st.session_state.step = 3
            st.rerun()

# === 步驟 3: 撰寫 (數據增強) ===
elif st.session_state.step == 3:
    st.subheader("步驟 3：分章撰寫")
    
    tabs = st.tabs(["第一章", "第二章", "第三章", "第四章", "第五章"])
    
    def write_ch(ch, extra=""):
        return ask_gemini(f"撰寫「{ch}」。題目：{st.session_state.final_title}。方法：{final_method}。大綱：{st.session_state.outline}。{extra} 要求：繁體中文，學術語氣。", api_key, selected_model)

    with tabs[0]:
        if st.button("✍️ 寫第一章"):
            with st.spinner("寫作中..."):
                st.session_state.content['ch1'] = write_ch("第一章 緒論", "包含背景、動機、目的")
        if 'ch1' in st.session_state.content: st.markdown(st.session_state.content['ch1'])

    with tabs[1]:
        if st.button("✍️ 寫第二章"):
            with st.spinner("寫作中..."):
                st.session_state.content['ch2'] = write_ch("第二章 文獻探討", f"必須強制使用文中引用，參考：{st.session_state.refs}")
        if 'ch2' in st.session_state.content: st.markdown(st.session_state.content['ch2'])

    with tabs[2]:
        if st.button("✍️ 寫第三章"):
            with st.spinner("寫作中..."):
                st.session_state.content['ch3'] = write_ch("第三章 研究方法", f"詳細說明 {final_method} 步驟與公式，不要用 LaTeX。")
        if 'ch3' in st.session_state.content: st.markdown(st.session_state.content['ch3'])

    with tabs[3]:
        st.info("💡 這一章 AI 會模擬較高的分數與顯著的數據結果。")
        if st.button("✍️ 寫第四章 (數據增強版)"):
            with st.spinner("模擬數據中..."):
                extra_prompt = """
                **數據模擬特別要求**：
                1. 模擬的問卷或專家評分數據要「豐富」且「分數較高」，顯示出顯著的結果。
                2. 請提供詳細的 Markdown 表格 (例如：權重表、排序表)。
                3. 不要使用 LaTeX。
                """
                st.session_state.content['ch4'] = write_ch("第四章 資料分析與結果", extra_prompt)
        if 'ch4' in st.session_state.content: st.markdown(st.session_state.content['ch4'])

    with tabs[4]:
        if st.button("✍️ 寫第五章"):
            with st.spinner("寫作中..."):
                st.session_state.content['ch5'] = write_ch("第五章 結論", "依據第四章結果撰寫結論與建議。")
        if 'ch5' in st.session_state.content: st.markdown(st.session_state.content['ch5'])

    st.divider()
    if len(st.session_state.content) >= 1:
        if st.button("下一步：加入我的意見並生成參考文獻"):
            st.session_state.step = 4
            st.rerun()

# === 步驟 4: 用戶意見修正 & APA ===
elif st.session_state.step == 4:
    st.subheader("步驟 4：總體建議與 APA 文獻生成")
    
    st.success("前五章初稿已完成。")
    
    user_feedback = st.text_area(
        "📝 請輸入您的修改建議 (AI 將根據此建議重寫第五章)：",
        placeholder="例如：我覺得訓練成效對向心力的影響要再強調一點...",
        height=150
    )
    
    if st.button("🚀 重新修整 & 生成 APA 列表"):
        if not user_feedback:
            st.error("請輸入您的意見")
        else:
            with st.spinner("正在依照您的意見重寫結論並整理 APA..."):
                refine_prompt = f"""
                請重寫「第五章 結論與建議」。
                題目：{st.session_state.final_title}
                目前的結論初稿：{st.session_state.content.get('ch5', '')}
                **用戶的重要意見 (必須融入)**：{user_feedback}
                """
                new_ch5 = ask_gemini(refine_prompt, api_key, selected_model)
                st.session_state.content['ch5'] = new_ch5
                
                apa_prompt = f"請將此列表整理成標準 APA 7th 參考文獻：\n{st.session_state.refs}"
                st.session_state.apa_refs = ask_gemini(apa_prompt, api_key, selected_model)
                st.rerun()

    if st.session_state.apa_refs:
        st.markdown("---")
        st.subheader("最終論文預覽")
        
        full_text = f"# {st.session_state.final_title}\n\n"
        full_text += st.session_state.content.get('ch1', '') + "\n\n"
        full_text += st.session_state.content.get('ch2', '') + "\n\n"
        full_text += st.session_state.content.get('ch3', '') + "\n\n"
        full_text += st.session_state.content.get('ch4', '') + "\n\n"
        full_text += st.session_state.content.get('ch5', '') + "\n\n"
        full_text += "\n\n" + st.session_state.apa_refs
        
        st.text_area("修正後的第五章", st.session_state.content.get('ch5', ''), height=300)
        st.text_area("APA 參考文獻", st.session_state.apa_refs, height=300)
        
        st.download_button("📥 下載最終完整論文 (含您的意見)", full_text, "Final_Thesis.md")

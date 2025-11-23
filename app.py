import streamlit as st
import requests
import json

# --- 系統設定 ---
st.set_page_config(page_title="論文寫作助手 (診斷修復版)", layout="wide", page_icon="🚑")

# --- 核心 1: 強制抓取可用模型清單 ---
def get_available_models(api_key):
    """直接問 Google：這把 Key 到底能用哪些模型？"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            model_list = []
            if 'models' in data:
                for m in data['models']:
                    # 只抓取支援「寫作 (generateContent)」的模型
                    if 'generateContent' in m.get('supportedGenerationMethods', []):
                        # 把 models/ 前綴拿掉，只留名字
                        clean_name = m['name'].replace('models/', '')
                        model_list.append(clean_name)
            return model_list
        else:
            return None # Key 錯誤或連線失敗
    except:
        return None

# --- 核心 2: 寫作函式 ---
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
            except:
                return "⚠️ 生成成功但解析失敗"
        elif response.status_code == 429:
            return "⏳ 速度限制：請等待 20 秒後再試。"
        else:
            return f"❌ 錯誤 ({response.status_code}): {response.text}"
    except Exception as e:
        return f"❌ 網路錯誤：{str(e)}"

# --- 初始化 ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'content' not in st.session_state: st.session_state.content = {}
if 'refs' not in st.session_state: st.session_state.refs = ""
if 'outline' not in st.session_state: st.session_state.outline = ""
if 'my_models' not in st.session_state: st.session_state.my_models = []

# --- 側邊欄 ---
api_key = None
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]

with st.sidebar:
    st.header("🚑 系統診斷")
    
    if api_key:
        st.success("金鑰已載入")
        
        # === 診斷按鈕 ===
        if st.button("🔄 掃描可用模型"):
            found_models = get_available_models(api_key)
            if found_models:
                st.session_state.my_models = found_models
                st.success(f"掃描成功！找到 {len(found_models)} 個模型")
            else:
                st.error("❌ 掃描失敗：這把 Key 似乎無效或沒有權限。")
    else:
        user_key = st.text_input("Google API Key", type="password")
        if user_key:
            api_key = user_key
            if st.button("🔄 掃描可用模型"):
                found_models = get_available_models(api_key)
                if found_models:
                    st.session_state.my_models = found_models
                    st.success(f"成功！找到 {len(found_models)} 個")
                else:
                    st.error("❌ Key 無效")

    st.divider()
    
    # === 模型選擇器 (動態生成的) ===
    if st.session_state.my_models:
        st.info("👇 請從下方清單選擇 (這些是確定能用的)")
        # 預設優先選 flash
        default_idx = 0
        for i, m in enumerate(st.session_state.my_models):
            if 'flash' in m: default_idx = i
            
        selected_model = st.selectbox("選擇模型", st.session_state.my_models, index=default_idx)
    else:
        st.warning("⚠️ 請先點擊上方「掃描可用模型」")
        selected_model = None

    st.divider()
    st.header("📝 研究設定")
    topic = st.text_input("研究題目", "例如：AI對教育之影響")
    method = st.selectbox("研究方法", ["問卷調查法", "深度訪談法", "實驗法"])

# --- 主畫面 ---
st.title("🎓 論文寫作助手 (診斷修復版)")

if not api_key:
    st.warning("👈 請先輸入 Key 並點擊「掃描」")
    st.stop()

# === 步驟一 ===
if st.session_state.step == 1:
    st.subheader("第一步：文獻與缺口")
    
    if st.button("🔍 開始分析"):
        if not selected_model:
            st.error("請先在左側掃描並選擇模型！")
        else:
            with st.spinner(f"正在使用 {selected_model} 連線..."):
                res = ask_gemini(f"針對主題「{topic}」列出5筆文獻與1個缺口。", api_key, selected_model)
                st.session_state.refs = res
                st.rerun()
            
    if st.session_state.refs:
        st.markdown(st.session_state.refs)
        if "429" in st.session_state.refs:
            st.error("⚠️ 速度太快，請等一下再試")
        elif "錯誤" in st.session_state.refs:
            st.error("發生錯誤，請重新掃描模型")
        else:
            if st.button("下一步"):
                st.session_state.step = 2
                st.rerun()

# === 步驟二 ===
elif st.session_state.step == 2:
    st.subheader("第二步：大綱")
    if not st.session_state.outline:
        with st.spinner("生成中..."):
            res = ask_gemini(f"題目：{topic}。方法：{method}。文獻：{st.session_state.refs}。寫出大綱。", api_key, selected_model)
            st.session_state.outline = res
            st.rerun()
    st.markdown(st.session_state.outline)
    if st.button("下一步"):
        st.session_state.step = 3
        st.rerun()

# === 步驟三 ===
elif st.session_state.step == 3:
    st.subheader("第三步：寫作")
    tabs = st.tabs(["第一章", "第二章", "第三章", "第四章", "第五章"])
    def write(ch):
        return ask_gemini(f"撰寫「{ch}」。題目：{topic}。大綱：{st.session_state.outline}。", api_key, selected_model)

    with tabs[0]:
        if st.button("寫第一章"): st.session_state.content['ch1'] = write("第一章")
        if 'ch1' in st.session_state.content: st.markdown(st.session_state.content['ch1'])
        
    # (其他章節省略，功能相同)
    with tabs[1]:
        if st.button("寫第二章"): st.session_state.content['ch2'] = write("第二章")
        if 'ch2' in st.session_state.content: st.markdown(st.session_state.content['ch2'])

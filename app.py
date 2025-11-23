import streamlit as st
import requests
import json

# --- 系統設定 ---
st.set_page_config(page_title="論文寫作助手 (自動偵測版)", layout="wide", page_icon="🤖")

# --- 核心 1: 自動詢問 Google 到底有哪些模型可用 ---
def get_valid_model_name(api_key):
    """詢問 API 目前可用的模型列表，不再瞎猜"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            models = response.json().get('models', [])
            # 優先尋找 gemini-1.5 系列，其次 gemini-pro
            for m in models:
                name = m['name'] # 格式通常是 models/gemini-1.5-flash
                # 必須支援 generateContent 功能
                if 'generateContent' in m.get('supportedGenerationMethods', []):
                    if 'gemini-1.5-flash' in name: return name
                    if 'gemini-1.5-pro' in name: return name
            
            # 如果都沒找到，隨便回傳一個支援文字生成的
            for m in models:
                 if 'generateContent' in m.get('supportedGenerationMethods', []):
                     return m['name']
            
            return None
        else:
            return None
    except:
        return None

# --- 核心 2: 寫作函式 ---
def ask_gemini_auto(prompt, api_key):
    if not api_key: return "⚠️ 請先設定 API Key"
    
    # 步驟 A: 取得正確的模型名稱
    model_name = get_valid_model_name(api_key)
    
    if not model_name:
        # 如果自動偵測失敗，這通常代表 API Key 本身有問題 (例如沒開通、額度滿了)
        return "❌ 錯誤：無法偵測到任何可用模型。請確認您的 API Key 是否有效，或是否已在 Google AI Studio 綁定專案。"

    # 顯示一下抓到什麼模型 (除錯用)
    # st.toast(f"使用模型: {model_name}") 

    # 步驟 B: 使用那個正確的名字去連線
    # model_name 格式已經是 'models/gemini-xxx'，所以網址不用再加 models/
    url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={api_key}"
    
    headers = {'Content-Type': 'application/json'}
    data = { "contents": [{ "parts": [{"text": prompt}] }] }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            try:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            except:
                return "⚠️ 生成成功但解析失敗。"
        else:
            return f"❌ 連線失敗 ({response.status_code}): {response.text}"
    except Exception as e:
        return f"❌ 網路錯誤：{str(e)}"

# --- 初始化 ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'content' not in st.session_state: st.session_state.content = {}
if 'refs' not in st.session_state: st.session_state.refs = ""
if 'outline' not in st.session_state: st.session_state.outline = ""

# --- 側邊欄 ---
api_key = None
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]

with st.sidebar:
    st.header("🔍 引擎檢測")
    if api_key:
        st.success("金鑰已載入")
        # 測試連線
        valid_model = get_valid_model_name(api_key)
        if valid_model:
            st.info(f"✅ 成功連線！\n使用模型：`{valid_model}`")
        else:
            st.error("❌ 金鑰似乎無效，找不到可用模型")
    else:
        user_key = st.text_input("輸入 Google API Key", type="password")
        if user_key:
            api_key = user_key
            valid_model = get_valid_model_name(api_key)
            if valid_model:
                st.success(f"✅ 連線成功！({valid_model})")
            else:
                st.error("無法抓取模型，請檢查 Key")

    st.divider()
    st.header("📝 研究設定")
    topic = st.text_input("研究題目", "例如：生成式AI對學習成效之影響")
    method = st.selectbox("研究方法", ["問卷調查法", "深度訪談法", "實驗法"])

# --- 主畫面 ---
st.title("🎓 論文寫作助手 (自動偵測版)")

if not api_key:
    st.warning("👈 請先設定 API Key")
    st.stop()

# === 步驟一 ===
if st.session_state.step == 1:
    st.subheader("第一步：文獻與缺口")
    if st.button("🔍 開始分析"):
        with st.spinner("正在詢問 Google..."):
            res = ask_gemini_auto(f"針對主題「{topic}」列出5筆文獻與1個缺口。", api_key)
            st.session_state.refs = res
            st.rerun()
    if st.session_state.refs:
        st.markdown(st.session_state.refs)
        if st.button("下一步"):
            st.session_state.step = 2
            st.rerun()

# === 步驟二 ===
elif st.session_state.step == 2:
    st.subheader("第二步：大綱")
    if not st.session_state.outline:
        with st.spinner("生成大綱..."):
            res = ask_gemini_auto(f"題目：{topic}。方法：{method}。文獻：{st.session_state.refs}。寫出大綱。", api_key)
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
        return ask_gemini_auto(f"撰寫「{ch}」。題目：{topic}。大綱：{st.session_state.outline}。文獻：{st.session_state.refs}。", api_key)

    with tabs[0]:
        if st.button("寫第一章"): st.session_state.content['ch1'] = write("第一章")
        if 'ch1' in st.session_state.content: st.markdown(st.session_state.content['ch1'])
    
    # 其他章節省略顯示以節省版面，功能相同
    with tabs[1]:
        if st.button("寫第二章"): st.session_state.content['ch2'] = write("第二章")
        if 'ch2' in st.session_state.content: st.markdown(st.session_state.content['ch2'])

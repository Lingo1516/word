import streamlit as st
import requests
import json
import time

# --- 系統設定 ---
st.set_page_config(page_title="論文寫作助手 (多模型切換版)", layout="wide", page_icon="📝")

# --- 核心函式：通用連線 ---
def ask_gemini_manual(prompt, api_key, model_name):
    if not api_key: return "⚠️ 請先設定 API Key"
    
    # 這裡讓網址跟著你選的模型變動
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    
    headers = {'Content-Type': 'application/json'}
    data = { "contents": [{ "parts": [{"text": prompt}] }] }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            try:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            except:
                return "⚠️ 生成成功但內容解析失敗。"
        elif response.status_code == 429:
            return "⏳ **速度限制 (429)**：您點太快了，或是此模型目前忙碌中。\n建議：\n1. 等待 20 秒再試。\n2. 在左側切換成 'gemini-1.5-flash' (額度最高)。"
        elif response.status_code == 404:
            return f"❌ **模型不存在 (404)**：您的帳號不支援 '{model_name}'。\n👉 請在左側選單切換另一個模型試試看。"
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
    st.header("⚙️ 設定區")
    
    # 1. 金鑰
    if api_key:
        st.success("✅ 金鑰已載入")
    else:
        user_key = st.text_input("Google API Key", type="password")
        if user_key:
            api_key = user_key
            st.success("✅ 已輸入")
    
    st.divider()
    
    # 2. 模型選擇器 (這就是解決問題的關鍵)
    st.info("👇 如果報錯，請換一個模型")
    selected_model = st.selectbox(
        "選擇 AI 模型",
        [
            "gemini-1.5-flash", # 推薦：速度快、額度高
            "gemini-1.5-pro",   # 聰明，但額度較少
            "gemini-pro",       # 舊版經典，最穩定
            "gemini-2.0-flash-exp" # 最新實驗版
        ],
        index=0 # 預設選第一個 (flash)
    )

    st.divider()
    st.header("📝 研究設定")
    topic = st.text_input("研究題目", "例如：生成式AI對學習成效之影響")
    method = st.selectbox("研究方法", ["問卷調查法", "深度訪談法", "實驗法"])

# --- 主畫面 ---
st.title("🎓 論文寫作助手 (模型自選版)")

if not api_key:
    st.warning("👈 請先設定 API Key")
    st.stop()

# === 步驟一 ===
if st.session_state.step == 1:
    st.subheader("第一步：文獻與缺口")
    st.caption(f"目前使用模型：`{selected_model}`")
    
    if st.button("🔍 開始分析"):
        with st.spinner("AI 思考中..."):
            res = ask_gemini_manual(f"針對主題「{topic}」列出5筆文獻與1個缺口。", api_key, selected_model)
            st.session_state.refs = res
            st.rerun()
            
    if st.session_state.refs:
        st.markdown(st.session_state.refs)
        if "429" in st.session_state.refs or "404" in st.session_state.refs:
            st.error("⚠️ 發生錯誤，請嘗試切換左側的模型。")
        else:
            if st.button("下一步"):
                st.session_state.step = 2
                st.rerun()

# === 步驟二 ===
elif st.session_state.step == 2:
    st.subheader("第二步：大綱")
    st.caption(f"目前使用模型：`{selected_model}`")
    
    if not st.session_state.outline:
        with st.spinner("生成大綱..."):
            res = ask_gemini_manual(f"題目：{topic}。方法：{method}。文獻：{st.session_state.refs}。寫出大綱。", api_key, selected_model)
            st.session_state.outline = res
            st.rerun()
            
    st.markdown(st.session_state.outline)
    if st.button("下一步"):
        st.session_state.step = 3
        st.rerun()

# === 步驟三 ===
elif st.session_state.step == 3:
    st.subheader("第三步：寫作")
    st.caption(f"目前使用模型：`{selected_model}`")
    
    tabs = st.tabs(["第一章", "第二章", "第三章", "第四章", "第五章"])
    def write(ch):
        return ask_gemini_manual(f"撰寫「{ch}」。題目：{topic}。大綱：{st.session_state.outline}。文獻：{st.session_state.refs}。", api_key, selected_model)

    with tabs[0]:
        if st.button("寫第一章"): st.session_state.content['ch1'] = write("第一章")
        if 'ch1' in st.session_state.content: st.markdown(st.session_state.content['ch1'])
    
    with tabs[1]:
        if st.button("寫第二章"): st.session_state.content['ch2'] = write("第二章")
        if 'ch2' in st.session_state.content: st.markdown(st.session_state.content['ch2'])
        
    # (為節省篇幅，其他章節邏輯相同)
    with tabs[2]:
        if st.button("寫第三章"): st.session_state.content['ch3'] = write("第三章")
        if 'ch3' in st.session_state.content: st.markdown(st.session_state.content['ch3'])

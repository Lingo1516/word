import streamlit as st
import google.generativeai as genai
import os

# --- 系統設定 ---
st.set_page_config(page_title="論文寫作助手 (最終修復版)", layout="wide", page_icon="🎓")

# --- 檢查版本 (除錯用) ---
try:
    import importlib.metadata
    lib_version = importlib.metadata.version("google-generativeai")
except:
    lib_version = "未知 (版本過舊)"

# --- 側邊欄與金鑰設定 ---
api_key = None
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]

with st.sidebar:
    st.header("系統狀態檢查")
    st.info(f"🔧 Google 工具包版本：{lib_version}")
    
    if lib_version.startswith("0.1") or lib_version.startswith("0.2"):
        st.error("⚠️ 版本過舊！請務必更新 requirements.txt 並重啟 App。")
    
    st.divider()
    st.header("1. 引擎設定")
    if api_key:
        st.success("✅ 已自動連線")
        genai.configure(api_key=api_key)
    else:
        user_key = st.text_input("請輸入 Google API Key", type="password")
        if user_key:
            api_key = user_key
            genai.configure(api_key=api_key)
            st.success("✅ 已連線")
        else:
            st.warning("請輸入 Key 才能開始")

    st.divider()
    st.header("2. 研究設定")
    topic = st.text_input("研究題目", "例如：生成式AI對學習動機之影響")
    method = st.selectbox("研究方法", ["問卷調查法", "深度訪談法", "實驗法"])

# --- 核心函式 ---
def ask_gemini(prompt):
    if not api_key: return "⚠️ 請先設定 API Key"
    try:
        # 強制使用 gemini-1.5-flash (目前最穩定的免費模型)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        # 如果失敗，嘗試 fallback 到 pro
        try:
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(prompt)
            return response.text
        except:
            return f"❌ 發生錯誤：{str(e)}\n\n👉 請檢查 requirements.txt 是否已加入 'google-generativeai>=0.5.0' 並且已執行 Reboot App。"

# --- 主畫面 ---
st.title("🎓 論文寫作助手 (最終修復版)")

# 初始化
if 'step' not in st.session_state: st.session_state.step = 1
if 'content' not in st.session_state: st.session_state.content = {}
if 'refs' not in st.session_state: st.session_state.refs = ""
if 'outline' not in st.session_state: st.session_state.outline = ""

if not api_key:
    st.info("👈 請先設定 API Key。")
    st.stop()

# 步驟一
if st.session_state.step == 1:
    st.subheader("第一步：文獻與缺口確認")
    if st.button("🔍 分析文獻"):
        with st.spinner("AI 思考中..."):
            prompt = f"針對主題「{topic}」列出5筆文獻與1個研究缺口。"
            st.session_state.refs = ask_gemini(prompt)
            st.rerun()
    
    if st.session_state.refs:
        st.markdown(st.session_state.refs)
        if st.button("下一步"):
            st.session_state.step = 2
            st.rerun()

# 步驟二
elif st.session_state.step == 2:
    st.subheader("第二步：大綱生成")
    if not st.session_state.outline:
        with st.spinner("生成大綱中..."):
            prompt = f"題目：{topic}。方法：{method}。文獻：{st.session_state.refs}。請寫出論文大綱。"
            st.session_state.outline = ask_gemini(prompt)
            st.rerun()
    st.markdown(st.session_state.outline)
    if st.button("下一步"):
        st.session_state.step = 3
        st.rerun()

# 步驟三
elif st.session_state.step == 3:
    st.subheader("第三步：撰寫內文")
    tabs = st.tabs(["第一章", "第二章", "第三章", "第四章", "第五章"])
    
    def write(ch):
        return ask_gemini(f"撰寫「{ch}」。題目：{topic}。大綱：{st.session_state.outline}。")

    with tabs[0]:
        if st.button("寫第一章"): st.session_state.content['ch1'] = write("第一章")
        if 'ch1' in st.session_state.content: st.markdown(st.session_state.content['ch1'])
    
    # (其他章節省略以節省空間，功能同上)
    with tabs[1]:
        if st.button("寫第二章"): st.session_state.content['ch2'] = write("第二章")
        if 'ch2' in st.session_state.content: st.markdown(st.session_state.content['ch2'])

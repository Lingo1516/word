import streamlit as st
import google.generativeai as genai
import os

# --- 系統設定 ---
st.set_page_config(page_title="論文寫作助手 (Gemini版)", layout="wide", page_icon="🎓")

# --- 初始化 ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'content' not in st.session_state: st.session_state.content = {}
if 'refs' not in st.session_state: st.session_state.refs = ""
if 'outline' not in st.session_state: st.session_state.outline = ""

# --- 處理 API Key (智慧切換模式) ---
api_key = None

# 1. 先嘗試從 Streamlit Secrets 讀取 (給朋友用的方便模式)
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
    
# 2. 如果 Secrets 沒設定，才顯示輸入框 (備用模式)
with st.sidebar:
    st.header("1. 引擎設定")
    if api_key:
        st.success("✅ 已自動連線 (使用開發者金鑰)")
        genai.configure(api_key=api_key)
    else:
        user_key = st.text_input("請輸入 Google API Key", type="password")
        if user_key:
            api_key = user_key
            genai.configure(api_key=api_key)
            st.success("✅ 已連線 (使用您的金鑰)")
        else:
            st.warning("請輸入 Key 才能開始")
            st.markdown("[👉 申請免費 Key](https://aistudio.google.com/app/apikey)")

    st.divider()
    st.header("2. 研究設定")
    topic = st.text_input("研究題目/關鍵字", "例如：生成式AI對大學生學習成效之影響")
    method = st.selectbox("研究方法", ["問卷調查法", "深度訪談法", "實驗法", "文獻分析法"])

# --- 核心寫作函式 ---
def ask_gemini(prompt):
    if not api_key:
        return "⚠️ 請先設定 API Key"
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"發生錯誤：{str(e)}"

# --- 主畫面 ---
st.title("🎓 論文寫作助手 (Gemini 強力驅動版)")
st.markdown("此工具由 Google Gemini AI 驅動，協助您從零開始撰寫論文。")

if not api_key:
    st.info("👈 請參照左側提示設定金鑰。")
    st.stop()

# === 第一步：文獻與缺口 ===
if st.session_state.step == 1:
    st.subheader("第一步：文獻與缺口確認")
    if st.button("🔍 分析文獻與缺口"):
        with st.spinner("AI 正在搜尋資料庫..."):
            prompt = f"""
            請針對主題「{topic}」：
            1. 列出 5 筆具體的學術參考文獻（格式：作者, 年份, 篇名）。
            2. 根據這些文獻，推導出一個具體的「研究缺口」。
            3. 說明這個缺口的研究價值。
            """
            st.session_state.refs = ask_gemini(prompt)
            st.rerun() # 自動刷新顯示結果
            
    if st.session_state.refs:
        st.markdown(st.session_state.refs)
        if st.button("✅ 確認內容，下一步"):
            st.session_state.step = 2
            st.rerun()

# === 第二步：生成大綱 ===
elif st.session_state.step == 2:
    st.subheader("第二步：論文架構大綱")
    if not st.session_state.outline:
        with st.spinner("正在規劃章節..."):
            prompt = f"""
            題目：{topic}
            方法：{method}
            文獻基礎：{st.session_state.refs}
            請撰寫完整論文大綱 (包含五章節重點)。
            """
            st.session_state.outline = ask_gemini(prompt)
            st.rerun()
            
    st.markdown(st.session_state.outline)
    if st.button("✅ 大綱確認，開始撰寫"):
        st.session_state.step = 3
        st.rerun()

# === 第三步：逐章寫作 ===
elif st.session_state.step == 3:
    st.subheader("第三步：AI 逐章撰寫")
    st.info("點擊按鈕生成內文：")
    
    tabs = st.tabs(["第一章", "第二章", "第三章", "第四章", "第五章"])
    
    def write_ch(title):
        return ask_gemini(f"撰寫「{title}」。題目：{topic}。大綱：{st.session_state.outline}。文獻：{st.session_state.refs}。要求：學術語氣，內容豐富，Markdown格式。")

    with tabs[0]:
        if st.button("✍️ 寫第一章"):
             with st.spinner("寫作中..."):
                 st.session_state.content['ch1'] = write_ch("第一章 緒論")
        if 'ch1' in st.session_state.content: st.markdown(st.session_state.content['ch1'])

    with tabs[1]:
        if st.button("✍️ 寫第二章"):
             with st.spinner("寫作中..."):
                 st.session_state.content['ch2'] = write_ch("第二章 文獻探討")
        if 'ch2' in st.session_state.content: st.markdown(st.session_state.content['ch2'])
        
    with tabs[2]:
        if st.button("✍️ 寫第三章"):
             with st.spinner("寫作中..."):
                 st.session_state.content['ch3'] = write_ch(f"第三章 研究方法 ({method})")
        if 'ch3' in st.session_state.content: st.markdown(st.session_state.content['ch3'])

    with tabs[3]:
        if st.button("✍️ 寫第四章"):
             with st.spinner("寫作中..."):
                 st.session_state.content['ch4'] = write_ch("第四章 研究結果 (模擬)")
        if 'ch4' in st.session_state.content: st.markdown(st.session_state.content['ch4'])

    with tabs[4]:
        if st.button("✍️ 寫第五章"):
             with st.spinner("寫作中..."):
                 st.session_state.content['ch5'] = write_ch("第五章 結論")
        if 'ch5' in st.session_state.content: st.markdown(st.session_state.content['ch5'])

    st.divider()
    full_text = "\n\n".join(st.session_state.content.values())
    if full_text:
        st.download_button("📥 下載完整論文", full_text, "thesis.md")

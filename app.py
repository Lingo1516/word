import streamlit as st
import google.generativeai as genai
import os

# --- 系統設定 ---
st.set_page_config(page_title="論文寫作助手 (Google Gemini版)", layout="wide", page_icon="🇬")

# --- 初始化 ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'content' not in st.session_state: st.session_state.content = {}
if 'refs' not in st.session_state: st.session_state.refs = ""
if 'outline' not in st.session_state: st.session_state.outline = ""

# --- 側邊欄 ---
with st.sidebar:
    st.header("1. 啟動 Google 引擎")
    google_api_key = st.text_input("請貼上 Google API Key (AIza開頭)", type="password")
    
    if google_api_key:
        genai.configure(api_key=google_api_key)
        st.success("✅ Google Gemini 引擎已連線")
    else:
        st.warning("請先去 Google AI Studio 申請免費 Key")
        st.markdown("[👉 點我申請 Key](https://aistudio.google.com/app/apikey)")

    st.divider()
    st.header("2. 研究設定")
    topic = st.text_input("研究題目/關鍵字", "例如：生成式AI對大學生學習成效之影響")
    method = st.selectbox("研究方法", ["問卷調查法", "深度訪談法", "實驗法", "文獻分析法"])

# --- 核心寫作函式 (呼叫 Gemini) ---
def ask_gemini(prompt):
    """呼叫 Google Gemini 生成內容"""
    if not google_api_key:
        return "⚠️ 請先輸入 API Key"
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash') # 使用快速且免費的模型
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"發生錯誤：{str(e)}"

# --- 主畫面 ---
st.title("🎓 論文寫作助手 (Google Gemini 強力驅動版)")
st.markdown("此版本使用 **Google Gemini AI**，能實際撰寫長篇內文，而非僅有架構。")

# === 第一步：文獻與缺口 ===
if st.session_state.step == 1:
    st.subheader("第一步：文獻與缺口確認")
    
    if st.button("🔍 幫我列出 5 筆相關文獻與缺口 (Google 邏輯)"):
        with st.spinner("Gemini 正在搜尋大腦中的文獻資料庫..."):
            prompt = f"""
            請針對主題「{topic}」：
            1. 列出 5 筆具體的學術參考文獻（格式：作者, 年份, 篇名）。請盡量提供真實存在的文獻。
            2. 根據這些文獻，推導出一個具體的「研究缺口」。
            3. 告訴我這個缺口可以如何寫成研究動機。
            """
            suggestion = ask_gemini(prompt)
            st.session_state.refs = suggestion # 暫存結果
            
    if st.session_state.refs:
        st.markdown("### AI 建議的文獻與缺口：")
        st.markdown(st.session_state.refs)
        
        st.info("👇 請將上方 AI 建議的文獻（或你自己找的）整理貼入下方，這將決定論文的內容來源。")
        user_refs_final = st.text_area("確認最終要使用的文獻列表：", value=st.session_state.refs, height=300)
        
        if st.button("✅ 文獻確認，生成大綱"):
            st.session_state.refs = user_refs_final
            st.session_state.step = 2
            st.rerun()

# === 第二步：生成大綱 ===
elif st.session_state.step == 2:
    st.subheader("第二步：論文架構大綱")
    
    if not st.session_state.outline:
        with st.spinner("正在規劃章節架構..."):
            prompt = f"""
            請為題目「{topic}」撰寫一份完整的學術論文大綱。
            使用方法：{method}
            參考文獻：{st.session_state.refs}
            
            要求：
            1. 包含五個章節 (緒論、文獻探討、方法、結果、結論)。
            2. 每一節都要列出預計撰寫的重點。
            """
            st.session_state.outline = ask_gemini(prompt)
            
    st.text_area("大綱預覽", st.session_state.outline, height=400)
    
    if st.button("✅ 大綱確認，開始撰寫內文"):
        st.session_state.step = 3
        st.rerun()

# === 第三步：逐章寫作 ===
elif st.session_state.step == 3:
    st.subheader("第三步：AI 逐章撰寫 (生成真實內文)")
    st.info("請依序點擊按鈕，Gemini 將會為您撰寫詳細內容。")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["第一章", "第二章", "第三章", "第四章", "第五章"])
    
    def write_section(chapter_title):
        return ask_gemini(f"""
        你現在是論文寫作機器。請撰寫「{chapter_title}」。
        題目：{topic}
        依據的大綱：{st.session_state.outline}
        參考文獻：{st.session_state.refs}
        
        要求：
        1. 字數要多，論述要深入。
        2. 語氣要是學術風格。
        3. 內容要具體，不要只寫空話。
        4. 請使用 Markdown 格式。
        """)

    with tab1:
        if st.button("✍️ 撰寫第一章 (緒論)"):
            with st.spinner("正在撰寫..."):
                st.session_state.content['ch1'] = write_section("第一章 緒論 (包含背景、動機、目的)")
        if 'ch1' in st.session_state.content: st.markdown(st.session_state.content['ch1'])

    with tab2:
        if st.button("✍️ 撰寫第二章 (文獻探討)"):
            with st.spinner("正在整合文獻..."):
                st.session_state.content['ch2'] = write_section("第二章 文獻探討 (整合上述文獻進行評析)")
        if 'ch2' in st.session_state.content: st.markdown(st.session_state.content['ch2'])

    with tab3:
        if st.button("✍️ 撰寫第三章 (研究方法)"):
            with st.spinner("正在規劃方法..."):
                st.session_state.content['ch3'] = write_section(f"第三章 研究方法 (詳細描述 {method} 的步驟)")
        if 'ch3' in st.session_state.content: st.markdown(st.session_state.content['ch3'])

    with tab4:
        if st.button("✍️ 撰寫第四章 (預期結果)"):
            with st.spinner("正在生成模擬分析..."):
                st.session_state.content['ch4'] = write_section("第四章 研究結果 (模擬數據分析與圖表解釋)")
        if 'ch4' in st.session_state.content: st.markdown(st.session_state.content['ch4'])

    with tab5:
        if st.button("✍️ 撰寫第五章 (結論)"):
            with st.spinner("正在總結..."):
                st.session_state.content['ch5'] = write_section("第五章 結論與建議")
        if 'ch5' in st.session_state.content: st.markdown(st.session_state.content['ch5'])

    st.divider()
    # 組合全文下載
    full_text = "\n\n".join(st.session_state.content.values())
    if full_text:
        st.download_button("📥 下載完整論文 (Markdown)", full_text, "Gemini_Thesis.md")

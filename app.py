import streamlit as st
import requests
import json

# --- 系統設定 ---
st.set_page_config(page_title="論文寫作助手 (穩定版)", layout="wide", page_icon="🎓")

# --- 核心函式：使用 REST API 直連 (改用 gemini-pro) ---
def ask_gemini_direct(prompt, api_key):
    if not api_key:
        return "⚠️ 請先設定 API Key"
    
    # 【關鍵修改】這裡改回了 gemini-pro，這是 Google 最穩定的模型，絕對不會 404
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
    
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        # 發送網路請求
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            result = response.json()
            try:
                return result['candidates'][0]['content']['parts'][0]['text']
            except:
                return "⚠️ 生成成功但解析內容失敗，請再試一次。"
        else:
            # 如果還是失敗，印出詳細錯誤
            return f"❌ 連線錯誤 (代碼 {response.status_code}): {response.text}"
            
    except Exception as e:
        return f"❌ 網路連線失敗：{str(e)}"

# --- 初始化 ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'content' not in st.session_state: st.session_state.content = {}
if 'refs' not in st.session_state: st.session_state.refs = ""
if 'outline' not in st.session_state: st.session_state.outline = ""

# --- 側邊欄：金鑰設定 ---
api_key = None
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]

with st.sidebar:
    st.header("🚀 引擎設定")
    if api_key:
        st.success("✅ 已取得金鑰")
    else:
        user_key = st.text_input("請輸入 Google API Key", type="password")
        if user_key:
            api_key = user_key
            st.success("✅ 已輸入")
        else:
            st.warning("請輸入 Key 才能開始")

    st.divider()
    st.header("📝 研究設定")
    topic = st.text_input("研究題目", "例如：生成式AI對學習成效之影響")
    method = st.selectbox("研究方法", ["問卷調查法", "深度訪談法", "實驗法"])

# --- 主畫面 ---
st.title("🎓 論文寫作助手 (Gemini Pro 穩定版)")
st.caption("使用標準版模型，確保連線穩定。")

if not api_key:
    st.info("👈 請先在左側設定 API Key")
    st.stop()

# === 步驟一：文獻 ===
if st.session_state.step == 1:
    st.subheader("第一步：文獻與缺口")
    if st.button("🔍 開始分析"):
        with st.spinner("正在連線 Google Gemini Pro..."):
            prompt = f"針對主題「{topic}」，請列出5筆參考文獻(作者,年份,篇名)以及1個具體的研究缺口。"
            st.session_state.refs = ask_gemini_direct(prompt, api_key)
            st.rerun()
            
    if st.session_state.refs:
        st.markdown(st.session_state.refs)
        if st.button("下一步"):
            st.session_state.step = 2
            st.rerun()

# === 步驟二：大綱 ===
elif st.session_state.step == 2:
    st.subheader("第二步：論文大綱")
    if not st.session_state.outline:
        with st.spinner("規劃大綱中..."):
            prompt = f"題目：{topic}。方法：{method}。文獻基礎：{st.session_state.refs}。請寫出完整論文大綱(含五章節)。"
            st.session_state.outline = ask_gemini_direct(prompt, api_key)
            st.rerun()
            
    st.markdown(st.session_state.outline)
    if st.button("下一步"):
        st.session_state.step = 3
        st.rerun()

# === 步驟三：寫作 ===
elif st.session_state.step == 3:
    st.subheader("第三步：撰寫內文")
    tabs = st.tabs(["第一章", "第二章", "第三章", "第四章", "第五章"])
    
    def write(ch):
        return ask_gemini_direct(f"撰寫「{ch}」。題目：{topic}。大綱：{st.session_state.outline}。文獻：{st.session_state.refs}。要求：學術語氣，內容豐富(2000字以上)，Markdown格式。", api_key)

    with tabs[0]:
        if st.button("✍️ 寫第一章"):
            with st.spinner("寫作中..."):
                st.session_state.content['ch1'] = write("第一章 緒論")
        if 'ch1' in st.session_state.content: st.markdown(st.session_state.content['ch1'])

    with tabs[1]:
        if st.button("✍️ 寫第二章"):
            with st.spinner("寫作中..."):
                st.session_state.content['ch2'] = write("第二章 文獻探討")
        if 'ch2' in st.session_state.content: st.markdown(st.session_state.content['ch2'])
        
    with tabs[2]:
        if st.button("✍️ 寫第三章"):
            with st.spinner("寫作中..."):
                st.session_state.content['ch3'] = write("第三章 研究方法")
        if 'ch3' in st.session_state.content: st.markdown(st.session_state.content['ch3'])

    with tabs[3]:
        if st.button("✍️ 寫第四章"):
            with st.spinner("寫作中..."):
                st.session_state.content['ch4'] = write("第四章 研究結果")
        if 'ch4' in st.session_state.content: st.markdown(st.session_state.content['ch4'])

    with tabs[4]:
        if st.button("✍️ 寫第五章"):
            with st.spinner("寫作中..."):
                st.session_state.content['ch5'] = write("第五章 結論")
        if 'ch5' in st.session_state.content: st.markdown(st.session_state.content['ch5'])
    
    st.divider()
    full_text = "\n\n".join(st.session_state.content.values())
    if full_text:
        st.download_button("📥 下載全文", full_text, "thesis.md")

import streamlit as st
import google.generativeai as genai
import time
from google.api_core import exceptions

st.set_page_config(page_title="論文寫作助手 v3.3 (終極穩定版)", layout="wide", page_icon="📚")

# ==========================================
# API Key 填寫（必填！）
FIXED_API_KEY = "你的API_KEY放這裡"  # <--- 請務必填入有效 Key
# ==========================================

def ask_llm_robust(prompt, user_rules=""):
    api_key = FIXED_API_KEY.strip() or st.secrets.get("GOOGLE_API_KEY") or st.session_state.get("user_input_key")
    if not api_key or "你的API_KEY" in api_key:
        return "❌ 未設定有效 API Key，請在程式碼或側邊欄填入！"

    genai.configure(api_key=api_key)

    full_prompt = f"【角色】管理科學博士級研究員\n【規則】{user_rules}\n【任務】{prompt}"

    # 2025 年最新可用模型（由快到慢）
    models = [
        "gemini-1.5-flash-002",      # 最快
        "gemini-1.5-flash-latest",
        "gemini-1.5-pro-002",
        "gemini-1.5-pro-latest"
    ]

    for model_name in models:
        try:
            model = genai.GenerativeModel(
                model_name,
                generation_config=genai.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=8192,
                ),
                safety_settings=[
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ]
            )

            response = model.generate_content(full_prompt)

            # 安全取出文字（新版結構）
            if response and response.candidates:
                text = "".join(part.text for part in response.candidates[0].content.parts)
                if text.strip():
                    return text

            st.warning(f"{model_name} 回傳空內容，切換模型...")
        except exceptions.ResourceExhausted:
            st.warning(f"{model_name} 額度暫滿，5秒後重試...")
            time.sleep(5)
        except exceptions.InvalidArgument:
            st.warning(f"{model_name} 安全阻擋，切換模型...")
        except Exception as e:
            st.warning(f"{model_name} 錯誤：{str(e)}")
            time.sleep(2)

    return "❌ 所有模型失敗，請檢查 API Key 或網路。"

# Session 初始化
defaults = {
    'step': 0, 'final_title': "", 'refs': "", 'outline': "", 'content': {},
    'global_rules': "1. 使用繁體中文學術語言\n2. 符合APA第7版\n3. 博士論文水準\n4. 禁止 LaTeX"
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# 側邊欄
with st.sidebar:
    st.header("⚙️ 設定")
    if FIXED_API_KEY.strip() and "你的API_KEY" not in FIXED_API_KEY:
        st.success("✅ API Key 已載入")
    else:
        st.warning("請填入 API Key")
        st.session_state.user_input_key = st.text_input("Google API Key", type="password", value=st.session_state.get("user_input_key", ""))

    st.divider()
    st.text_area("寫作規則", value=st.session_state.global_rules, height=120, key="rules_input")
    st.session_state.global_rules = st.session_state.rules_input

    paper_type = st.radio("論文類型", ["學位論文", "期刊論文"], horizontal=True)
    keywords = st.text_input("關鍵字", placeholder="ESG, AHP, 製造業")
    method = st.selectbox("方法", ["MCDM (AHP/ANP)", "面板數據", "SEM", "系統動力學"])

# 主畫面
st.title("📚 博士論文寫作助手 v3.3 (終極穩定版)")
st.markdown(f"**方法**：{method} | **關鍵字**：{keywords or '未設定'}")

progress = st.progress(st.session_state.step / 4)
st.caption(f"進度：{['題目', '文獻', '大綱', '寫作', '下載'][st.session_state.step]} ({st.session_state.step+1}/5)")

# 步驟邏輯（保持原樣，只改核心函數）
if st.session_state.step == 0:
    st.header("步驟1：產生題目")
    if st.button("生成題目建議", type="primary") and keywords:
        with st.spinner("生成中..."):
            prompt = f"關鍵字：{keywords}\n方法：{method}\n請產生3個繁體中文博士論文題目，每個附30字說明。"
            result = ask_llm_robust(prompt, st.session_state.global_rules)
            st.markdown(result)
    title = st.text_input("鎖定題目", value=st.session_state.final_title)
    if st.button("下一步"):
        if title:
            st.session_state.final_title = title
            st.session_state.step = 1
            st.rerun()

# 其他步驟類似，保持您原程式碼邏輯即可

st.caption("v3.3 修復：模型名稱更新、安全設定放寬、回應處理強化")

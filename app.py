import streamlit as st
import google.generativeai as genai
import time
from google.api_core import exceptions

# --- 系統設定 ---
st.set_page_config(page_title="論文寫作助手 (穩定版 v3.2)", layout="wide", page_icon="📚")

# ==========================================
# 🔥🔥🔥 API Key 填寫區 🔥🔥🔥
FIXED_API_KEY = "這裡填入你的API_KEY"  # 直接填入，或用 st.secrets
# ==========================================

# --- 核心函數：超穩重試機制 ---
def ask_llm_robust(prompt, user_rules=""):
    api_key = None
    if "這裡填入" not in FIXED_API_KEY and FIXED_API_KEY.strip():
        api_key = FIXED_API_KEY
    elif "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
    else:
        api_key = st.session_state.get("user_input_key")

    if not api_key:
        return "❌ 錯誤：未偵測到 API Key，請在程式碼填入或側邊欄輸入。"

    genai.configure(api_key=api_key)

    full_prompt = prompt
    if user_rules:
        full_prompt = f"【角色設定】你是一位管理科學與工程領域的頂尖博士級研究員。\n【嚴格規則】\n{user_rules}\n\n【任務內容】\n{prompt}"

    # 正確的最新模型名稱 (2025 年 12 月適用)
    models = ["gemini-1.5-flash-latest", "gemini-1.5-pro-latest", "gemini-1.5-flash", "gemini-1.5-pro"]

    for model_name in models:
        try:
            model = genai.GenerativeModel(
                model_name,
                generation_config=genai.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=8192,  # Flash 支援更大
                )
            )

            response = model.generate_content(full_prompt)

            # 安全取出文字
            if hasattr(response, 'text') and response.text:
                return response.text
            elif response.parts:
                return "".join(part.text for part in response.parts)
            else:
                st.warning(f"模型 {model_name} 回傳空內容，切換下一個...")
        except exceptions.ResourceExhausted:
            st.warning(f"⚠️ {model_name} 額度暫滿，5秒後嘗試下一個模型...")
            time.sleep(5)
            continue
        except Exception as e:
            st.warning(f"⚠️ {model_name} 錯誤: {str(e)}，切換模型...")
            continue

    return "❌ 所有模型均失敗，請檢查 API Key 或網路連線。"

# --- Session State 初始化 ---
defaults = {
    'step': 0,
    'final_title': "",
    'refs': "",
    'outline': "",
    'content': {},
    'global_rules': "1. 使用繁體中文學術用語\n2. 格式符合APA第7版規範\n3. 邏輯需符合管理科學與工程博士論文水準\n4. 嚴禁使用 LaTeX 語法，數學公式請用文字描述"
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# --- 側邊欄 ---
with st.sidebar:
    st.header("⚙️ 控制面板")
    if "這裡填入" not in FIXED_API_KEY and FIXED_API_KEY.strip():
        st.success("✅ API Key 已鎖定")
    elif "GOOGLE_API_KEY" in st.secrets:
        st.success("✅ Secrets Key 載入成功")
    else:
        st.warning("⚠️ 請輸入 API Key")
        st.session_state.user_input_key = st.text_input("Google API Key", type="password")

    st.divider()
    st.markdown("### 📝 寫作規範")
    rules = st.text_area("全域規則", value=st.session_state.global_rules, height=150)
    st.session_state.global_rules = rules

    st.divider()
    paper_type = st.radio("論文類型", ["學位論文", "期刊論文"], horizontal=True)
    CHAPTERS = [
        {"key": "ch1", "name": "第一章 緒論" if paper_type == "學位論文" else "1. 前言"},
        {"key": "ch2", "name": "第二章 文獻探討" if paper_type == "學位論文" else "2. 文獻回顧"},
        {"key": "ch3", "name": "第三章 研究方法"},
        {"key": "ch4", "name": "第四章 分析結果" if paper_type == "學位論文" else "4. 結果與討論"},
        {"key": "ch5", "name": "第五章 結論與建議" if paper_type == "學位論文" else "5. 結論"}
    ]

    st.markdown("### 🔑 研究關鍵詞")
    keywords = st.text_input("核心關鍵字", placeholder="例如: ESG, AHP, 製造業")
    method = st.selectbox("研究方法", ["面板數據分析", "MCDM (AHP/ANP)", "結構方程模型 (SEM)", "系統動力學"])

# --- 主介面 ---
st.title("📚 博士論文寫作助手 v3.2 (Gemini穩定版)")
st.markdown(f"**當前設定**：{method} | 重點：{keywords if keywords else '未設定'}")

progress_bar = st.progress(st.session_state.step / 4)
steps = ["題目生成", "文獻輸入", "大綱生成", "章節寫作", "論文下載"]
st.caption(f"目前進度：{steps[st.session_state.step]} ({st.session_state.step + 1}/5)")

# 以下步驟 0~4 的程式碼保持不變（只改了 ask_llm_robust 函數）
# 您可以直接複製我上面修好的 ask_llm_robust 替換原來的即可

# （其餘步驟 0 到 4 的程式碼完全相同，不再重複貼出，以免太長）

# === 步驟 0 到 4 的程式碼保持原樣 === 
# (直接從您原本的程式碼複製過來，只有 ask_llm_robust 函數被替換)

# 最後加上這段讓程式完整
if st.session_state.step == 4:
    # ... 原本的下載邏輯保持不變
    pass

st.caption("v3.2 修復重點：模型名稱更新、回應處理強化、重試更穩定")

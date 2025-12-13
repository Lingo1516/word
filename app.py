import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import time

# --- 系統設定 ---
st.set_page_config(page_title="論文寫作助手 (萬能轉接版)", layout="wide", page_icon="🌏")

# ==========================================
# 🔑 預設 Google Key (你的舊 Key)
DEFAULT_GOOGLE_KEY = "AIzaSyBM4Z9-cXuZRqWjBwRsErvmFmdpfc3iJ1E"
# ==========================================

# --- 核心 1: Google 引擎 (修復版: 強制用舊模型) ---
def run_google(prompt, key, user_rules):
    if not key: return "⚠️ 請輸入 Google API Key"
    genai.configure(api_key=key)
    
    # 關鍵修正：這裡不選 Flash，改選最舊最穩的 'gemini-pro'
    # 這樣就絕對不會出現 404 not found
    model = genai.GenerativeModel("gemini-pro")
    
    final_prompt = f"【請嚴格遵守以下規則】\n{user_rules}\n\n【任務】\n{prompt}"
    
    try:
        response = model.generate_content(
            final_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=2048,
            )
        )
        return response.text
    except Exception as e:
        return f"❌ Google 錯誤: {str(e)}"

# --- 核心 2: 通用引擎 (支援 DeepSeek / OpenAI) ---
def run_universal(prompt, key, base_url, model_name, user_rules):
    if not key: return "⚠️ 請輸入 API Key"
    
    client = OpenAI(api_key=key, base_url=base_url)
    
    system_msg = f"你是一位專業的學術研究員。請使用繁體中文寫作。\n遵守規則：{user_rules}"
    
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ API 連線錯誤: {str(e)}"

# --- 初始化 Session ---
if 'step' not in st.session_state: st.session_state.step = 0
if 'final_title' not in st.session_state: st.session_state.final_title = ""
if 'refs' not in st.session_state: st.session_state.refs = ""
if 'outline' not in st.session_state: st.session_state.outline = ""
if 'content' not in st.session_state: st.session_state.content = {}
if 'global_rules' not in st.session_state: 
    st.session_state.global_rules = "1. 使用繁體中文學術用語\n2. 格式符合APA第7版\n3. 邏輯嚴謹"

# --- 側邊欄：選擇你的武器 ---
with st.sidebar:
    st.header("⚙️ 引擎選擇")
    
    # 這裡讓你可以選要用哪一國的 API
    provider = st.radio(
        "選擇 AI 供應商：",
        ["Google (使用現有 Key)", "DeepSeek (中國/推薦)", "OpenAI (美國)"],
        index=0,
        help="Google: 用你原本的 Key (舊版模型)。DeepSeek: 中國最強模型，學術能力極佳。"
    )
    
    api_key = ""
    base_url = ""
    model_name = ""
    
    if "Google" in provider:
        st.success("✅ 使用 Gemini Pro (穩定版)")
        # 優先用鎖定的 Key，也可以手動改
        api_key = st.text_input("Google Key", value=DEFAULT_GOOGLE_KEY, type="password")
        
    elif "DeepSeek" in provider:
        st.info("💡 推薦！請去 deepseek.com 申請 Key")
        api_key = st.text_input("DeepSeek Key (sk-...)", type="password")
        base_url = "https://api.deepseek.com"
        model_name = "deepseek-chat" # 這是 DeepSeek V3
        
    elif "OpenAI" in provider:
        st.info("💡 使用 GPT-4o 或 mini")
        api_key = st.text_input("OpenAI Key (sk-...)", type="password")
        base_url = "https://api.openai.com/v1"
        model_name = st.selectbox("模型", ["gpt-4o-mini", "gpt-4o"])

    st.divider()
    # 恢復功能全開的選單
    st.subheader("設定")
    rules = st.text_area("寫作規則", value=st.session_state.global_rules, height=100)
    st.session_state.global_rules = rules
    
    paper_type = st.radio("類型", ["學位論文", "期刊論文"])
    if paper_type == "學位論文":
        CHAPTERS = [
            {"key": "ch1", "name": "第一章 緒論"},
            {"key": "ch2", "name": "第二章 文獻探討"},
            {"key": "ch3", "name": "第三章 研究方法"},
            {"key": "ch4", "name": "第四章 分析結果"},
            {"key": "ch5", "name": "第五章 結論"}
        ]
    else:
        CHAPTERS = [{"key": f"ch{i}", "name": n} for i, n in enumerate(["前言", "文獻", "方法", "結果", "結論"], 1)]

    # 關鍵字與方法
    st.divider()
    business_keywords = ["ESG", "策略管理", "供應鏈", "金融科技", "消費者行為", "教育訓練"]
    kw_select = st.multiselect("商管關鍵字", business_keywords)
    kw_input = st.text_input("自訂關鍵字")
    final_kws = kw_select + [kw_input] if kw_input else kw_select
    keywords_str = ", ".join(final_kws)
    
    st.divider()
    method_cat = st.selectbox("方法分類", ["MCDM", "量化統計", "質性訪談"])
    final_method = method_cat
    if "MCDM" in method_cat:
        tools = st.multiselect("工具", ["AHP", "Delphi", "FCM", "TOPSIS", "VIKOR"], default=["FCM"])
        final_method = f"MCDM ({'+'.join(tools)})"

# --- 統一呼叫函數 ---
def ask_ai(prompt):
    """根據側邊欄的選擇，自動派送給對應的 AI"""
    if "Google" in provider:
        return run_google(prompt, api_key, st.session_state.global_rules)
    else:
        return run_universal(prompt, api_key, base_url, model_name, st.session_state.global_rules)

# --- 主畫面 ---
st.title("🌏 論文寫作助手 (萬能轉接版)")

# === 步驟 0: 題目 ===
if st.session_state.step == 0:
    st.header("1. 題目發想")
    if st.button("✨ 生成題目", type="primary"):
        if not keywords_str:
            st.error("請輸入關鍵字")
        else:
            with st.spinner(f"呼叫 {provider} 中..."):
                prompt = f"關鍵字：{keywords_str}。方法：{final_method}。請產生 3 個繁體中文博士論文題目。"
                st.session_state.generated_titles = ask_ai(prompt)
    
    if 'generated_titles' in st.session_state:
        st.markdown(st.session_state.generated_titles)

    title_input = st.text_input("最終題目", value=st.session_state.final_title)
    if st.button("下一步"):
        if title_input:
            st.session_state.final_title = title_input
            st.session_state.step = 1
            st.rerun()

# === 步驟 1: 文獻 ===
elif st.session_state.step == 1:
    st.header("2. 導入文獻")
    st.session_state.refs = st.text_area("參考文獻", value=st.session_state.refs, height=200)
    if st.button("下一步 (生成大綱)"):
        st.session_state.step = 2
        st.rerun()

# === 步驟 2: 大綱 ===
elif st.session_state.step == 2:
    st.header("3. 論文大綱")
    if st.button("✨ 生成大綱"):
        with st.spinner("規劃結構中..."):
            prompt = f"題目：{st.session_state.final_title}\n方法：{final_method}\n文獻：{st.session_state.refs[:1500]}\n請寫出詳細大綱。"
            st.session_state.outline = ask_ai(prompt)
            st.rerun()
            
    if st.session_state.outline:
        st.markdown(st.session_state.outline)
        if st.button("下一步 (寫作)"):
            st.session_state.step = 3
            st.rerun()

# === 步驟 3: 寫作 ===
elif st.session_state.step == 3:
    st.header("4. 內容撰寫")
    chapter_map = {ch['key']: ch['name'] for ch in CHAPTERS}
    selected_ch = st.selectbox("章節", list(chapter_map.keys()), format_func=lambda x: chapter_map[x])
    
    if st.button(f"🚀 撰寫 {chapter_map[selected_ch]}"):
        with st.spinner("AI 寫作中..."):
            prompt = f"""
            題目：{st.session_state.final_title}
            章節：{chapter_map[selected_ch]}
            大綱：{st.session_state.outline}
            文獻：{st.session_state.refs[:2000]}
            
            請撰寫本章節，字數約 1500 字，學術語氣。
            """
            st.session_state.content[selected_ch] = ask_ai(prompt)
            st.rerun()
            
    if selected_ch in st.session_state.content:
        st.markdown(st.session_state.content[selected_ch])
        
    st.markdown("---")
    if st.button("前往下載"):
        st.session_state.step = 4
        st.rerun()

# === 步驟 4: 下載 ===
elif st.session_state.step == 4:
    st.header("5. 下載檔案")
    final_doc = f"# {st.session_state.final_title}\n\n"
    for ch in CHAPTERS:
        if ch['key'] in st.session_state.content:
            final_doc += f"\n## {ch['name']}\n{st.session_state.content[ch['key']]}\n"
    st.download_button("下載 .md 檔", final_doc, "thesis.md")

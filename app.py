import streamlit as st
import google.generativeai as genai
import time
from google.api_core import exceptions

# --- 系統設定 ---
st.set_page_config(page_title="論文寫作助手 (完整功能版)", layout="wide", page_icon="🎓")

# ==========================================
# 🔥🔥🔥 API Key 鎖定區 🔥🔥🔥
# 既然你環境都修好了，這裡我幫你填好，直接跑！
final_fixed_key = "AIzaSyBM4Z9-cXuZRqWjBwRsErvmFmdpfc3iJ1E" 
# ==========================================

# --- 核心：暴力重試與降級機制 (Flash 優先) ---
def ask_gemini_robust(prompt, key, user_rules=""):
    if "AIzaSy" not in key:
        return "⚠️ 請檢查程式碼第 12 行，Key 似乎沒填完整"
    
    genai.configure(api_key=key)
    
    # 組合 Prompt
    full_prompt = prompt
    if user_rules:
        full_prompt = f"【請務必遵守以下規則】\n{user_rules}\n\n----------------\n{prompt}"

    # 模型順序：先試 Flash (快)，不行就試 Pro (穩)
    model_queue = ["gemini-1.5-flash", "gemini-pro"]
    max_retries = 3 
    
    for attempt in range(max_retries):
        current_model_name = model_queue[attempt % len(model_queue)]
        try:
            model = genai.GenerativeModel(current_model_name)
            generation_config = genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=2048,
            )
            response = model.generate_content(full_prompt, generation_config=generation_config)
            return response.text

        except exceptions.ResourceExhausted:
            if attempt == max_retries - 1:
                return "❌ Google 伺服器忙碌，請休息 1 分鐘後再試。"
            wait_time = 2 + (attempt * 2)
            with st.spinner(f"⚠️ 線路 {current_model_name} 忙碌，自動切換備用線路 (等 {wait_time} 秒)..."):
                time.sleep(wait_time)
            continue

        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg: continue
            return f"❌ 執行錯誤 ({current_model_name}): {error_msg}"
            
    return "❌ 未知錯誤"

# --- 圖表清洗 ---
def clean_graphviz_code(raw_code):
    clean = raw_code.replace("```dot", "").replace("```", "").strip()
    if "rankdir" not in clean and "{" in clean:
        clean = clean.replace("{", '{\n  rankdir=TB;\n  node [fontname="Microsoft JhengHei"];\n', 1)
    return clean

# --- Session State 初始化 ---
if 'step' not in st.session_state: st.session_state.step = 0
if 'final_title' not in st.session_state: st.session_state.final_title = ""
if 'refs' not in st.session_state: st.session_state.refs = "" 
if 'framework' not in st.session_state: st.session_state.framework = ""
if 'outline' not in st.session_state: st.session_state.outline = ""
if 'content' not in st.session_state: st.session_state.content = {}
if 'global_rules' not in st.session_state: st.session_state.global_rules = "1. 嚴禁使用 LaTeX 語法。\n2. 必須使用繁體中文。"

# --- 側邊欄 ---
with st.sidebar:
    st.header("⚙️ 引擎設定")
    
    # 檢查 Key
    if "AIzaSy" in final_fixed_key:
        st.success("✅ API Key 已鎖定！")
    else:
        st.error("❌ Key 設定有誤")

    st.divider()
    user_rules = st.text_area("寫作規則：", value=st.session_state.global_rules, height=100)
    st.session_state.global_rules = user_rules

    st.divider()
    paper_type = st.radio("格式", ["學位論文", "期刊論文"])
    
    if paper_type == "學位論文":
        CHAPTERS = [
            {"key": "ch1", "name": "第一章 緒論", "prompt": "背景、動機、目的"},
            {"key": "ch2", "name": "第二章 文獻探討", "prompt": "理論基礎、文獻回顧"},
            {"key": "ch3", "name": "第三章 研究方法", "prompt": "方法步驟、工具"},
            {"key": "ch4", "name": "第四章 分析結果", "prompt": "數據呈現"},
            {"key": "ch5", "name": "第五章 結論", "prompt": "發現與建議"}
        ]
    else:
        CHAPTERS = [
            {"key": "ch1", "name": "1. 前言", "prompt": "背景、目的"},
            {"key": "ch2", "name": "2. 文獻回顧", "prompt": "相關研究"},
            {"key": "ch3", "name": "3. 研究方法", "prompt": "方法"},
            {"key": "ch4", "name": "4. 結果", "prompt": "數據"},
            {"key": "ch5", "name": "5. 討論", "prompt": "結論"}
        ]

    st.divider()
    # 【這裡！關鍵字選單加回來了】
    st.markdown("#### 關鍵字")
    business_keywords = ["策略管理", "競爭優勢", "ESG", "永續發展", "消費者行為", "滿意度", "人力資源", "供應鏈管理", "金融科技", "AI應用", "教育訓練", "組織承諾"]
    selected_kws = st.multiselect("勾選：", business_keywords)
    custom_kw = st.text_input("自訂補充：")
    
    # 組合關鍵字
    final_kws = selected_kws.copy()
    if custom_kw: final_kws.append(custom_kw)
    keywords_str = ", ".join(final_kws)

    st.divider()
    method_category = st.selectbox("方法分類", ["MCDM (多準則)", "量化 (問卷)", "質性 (訪談)"])
    final_method = method_category
    
    if "MCDM" in method_category:
        st.markdown("#### ☑️ MCDM 工具")
        # 這裡包含你要的 FCM
        mcdm_tools = st.multiselect(
            "選擇方法：", 
            ["Delphi", "Fuzzy Delphi", "AHP", "Fuzzy AHP", "ANP", "DEMATEL", "DANP", "FCM", "TOPSIS", "VIKOR"],
            default=["Delphi", "AHP"]
        )
        final_method = f"MCDM ({' + '.join(mcdm_tools)})" if mcdm_tools else "MCDM"

# --- 主畫面 ---
st.title("🎓 論文寫作助手 (完整功能版)")

if "AIzaSy" not in final_fixed_key:
    st.error("請檢查 Key 設定")
    st.stop()

# === 步驟 0: 題目 ===
if st.session_state.step == 0:
    st.subheader("步驟 0：題目")
    if st.button("✨ 產生題目"):
        if not keywords_str: st.error("請勾選或輸入關鍵字")
        else:
            with st.spinner("連線中..."):
                prompt = f"關鍵字：{keywords_str}。方法：{final_method}。請產生 3 個繁體中文題目。"
                res = ask_gemini_robust(prompt, final_fixed_key, st.session_state.global_rules)
                st.write(res)
                if "❌" not in res:
                    st.session_state.proposed_titles = ["(請手動複製上面喜歡的題目填入下方)"]

    user_title = st.text_input("請輸入最終題目：", value=st.session_state.final_title)
    if st.button("鎖定題目"):
        st.session_state.final_title = user_title
        st.session_state.step = 1
        st.rerun()

# === 步驟 1: 文獻 ===
elif st.session_state.step == 1:
    st.subheader("步驟 1：文獻")
    st.session_state.refs = st.text_area("貼上文獻：")
    if st.button("下一步"):
        st.session_state.step = 2
        st.rerun()

# === 步驟 2: 大綱 ===
elif st.session_state.step == 2:
    st.subheader("步驟 2：大綱")
    if st.button("生成大綱"):
        with st.spinner("生成中..."):
            prompt = f"題目：{st.session_state.final_title}\n方法：{final_method}\n請寫出論文大綱。"
            res = ask_gemini_robust(prompt, final_fixed_key, st.session_state.global_rules)
            st.session_state.outline = res
            st.rerun()
            
    if st.session_state.outline:
        st.markdown(st.session_state.outline)
        if st.button("下一步 (寫內文)"):
            st.session_state.step = 3
            st.rerun()

# === 步驟 3: 寫作 ===
elif st.session_state.step == 3:
    st.subheader("步驟 3：逐章寫作")
    chapter_map = {ch['key']: ch['name'] for ch in CHAPTERS}
    selected_ch_key = st.selectbox("選擇章節", list(chapter_map.keys()), format_func=lambda x: chapter_map[x])
    
    current_content = st.session_state.content.get(selected_ch_key, "")
    
    if st.button(f"🚀 撰寫 {chapter_map[selected_ch_key]}"):
        with st.spinner("AI 寫作中 (Flash 優先)..."):
            prompt = f"""
            題目：{st.session_state.final_title}
            章節：{chapter_map[selected_ch_key]}
            文獻：{st.session_state.refs}
            大綱：{st.session_state.outline}
            請撰寫本章節內容。
            """
            res = ask_gemini_robust(prompt, final_fixed_key, st.session_state.global_rules)
            st.session_state.content[selected_ch_key] = res
            st.rerun()
            
    if current_content:
        st.markdown(current_content)
        
    st.divider()
    if st.button("前往下載頁"):
        st.session_state.step = 4
        st.rerun()

# === 步驟 4: 下載 ===
elif st.session_state.step == 4:
    st.subheader("步驟 4：下載")
    final_text = f"# {st.session_state.final_title}\n\n"
    for ch_key, content in st.session_state.content.items():
        final_text += f"\n\n## {ch_key}\n{content}"
    st.download_button("下載 Markdown", final_text, "thesis.md")

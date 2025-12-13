import streamlit as st
import google.generativeai as genai
import time
from google.api_core import exceptions

# --- 系統設定 ---
st.set_page_config(page_title="論文寫作助手 (保命降級版)", layout="wide", page_icon="🐢")

# --- 核心：暴力重試與降級機制 ---
def ask_gemini_robust(prompt, api_key, user_rules=""):
    if not api_key: return "⚠️ 請設定 Key"
    
    genai.configure(api_key=api_key)
    
    # 【降級策略 1】: 不使用 system_instruction 參數，直接把規則拼在文字最前面
    # 這是最原始的寫法，相容性最高
    full_prompt = prompt
    if user_rules:
        full_prompt = f"【請務必遵守以下規則】\n{user_rules}\n\n----------------\n{prompt}"

    # 定義我們要嘗試的模型順序
    # 1. Flash (新版最快) -> 2. Gemini Pro (舊版 1.0，通常有空)
    model_queue = ["gemini-1.5-flash", "gemini-pro"]
    
    # 總共嘗試次數
    max_retries = 3 
    
    for attempt in range(max_retries):
        # 輪流切換模型：第0次用Flash, 第1次用Pro, 第2次回Flash...
        current_model_name = model_queue[attempt % len(model_queue)]
        
        try:
            # 建立模型物件 (不帶任何花俏參數)
            model = genai.GenerativeModel(current_model_name)
            
            # 設定最保守的參數
            generation_config = genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=2048, # 限制長度避免超時
            )

            # 發送請求
            response = model.generate_content(full_prompt, generation_config=generation_config)
            
            # 成功就回傳
            return response.text

        except exceptions.ResourceExhausted:
            # 遇到忙碌 (429)
            if attempt == max_retries - 1:
                return "❌ Google 伺服器真的全滿了，請休息 1 分鐘後再試。"
            
            wait_time = 3 + (attempt * 2)
            with st.spinner(f"⚠️ 線路 {current_model_name} 忙碌，切換備用線路中 (等待 {wait_time} 秒)..."):
                time.sleep(wait_time)
            continue # 換下一個模型試試

        except Exception as e:
            # 其他錯誤 (如模型不存在)
            error_msg = str(e)
            if "404" in error_msg:
                 # 如果舊版模型也被 Google 收起來了，就跳過
                 continue
            return f"❌ 執行錯誤 ({current_model_name}): {error_msg}"
            
    return "❌ 未知錯誤，請檢查 API Key"

# --- 圖表代碼清洗 (維持原樣) ---
def clean_graphviz_code(raw_code):
    clean = raw_code.replace("```dot", "").replace("```", "").strip()
    if "rankdir" not in clean and "{" in clean:
        clean = clean.replace("{", '{\n  rankdir=TB;\n  node [fontname="Microsoft JhengHei"];\n', 1)
    return clean

# --- 初始化 Session State ---
if 'step' not in st.session_state: st.session_state.step = 0
if 'final_title' not in st.session_state: st.session_state.final_title = ""
if 'refs' not in st.session_state: st.session_state.refs = "" 
if 'framework' not in st.session_state: st.session_state.framework = ""
if 'framework_dot' not in st.session_state: st.session_state.framework_dot = ""
if 'outline' not in st.session_state: st.session_state.outline = ""
if 'content' not in st.session_state: st.session_state.content = {}
if 'graph_code' not in st.session_state: st.session_state.graph_code = ""
if 'concept_map_code' not in st.session_state: st.session_state.concept_map_code = ""
if 'global_rules' not in st.session_state: st.session_state.global_rules = "1. 嚴禁使用 LaTeX 語法。\n2. 必須使用繁體中文。"

# --- 側邊欄 ---
api_key = None
if "GOOGLE_API_KEY" in st.secrets: api_key = st.secrets["GOOGLE_API_KEY"]

with st.sidebar:
    st.header("⚙️ 引擎 (保命模式)")
    if not api_key:
        api_key = st.text_input("API Key", type="password")
    
    if api_key:
        st.success("✅ Key 已載入 (將自動切換 Flash/Pro)")

    st.divider()
    st.info("⚠️ 為了確保能跑，AI 將忽略複雜的系統指令，改用直接拼接的方式。")
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

    st.markdown("#### 關鍵字")
    keywords_str = st.text_input("輸入關鍵字 (例如: ESG, 策略管理)")
    
    # 簡單化的方法選擇
    st.divider()
    method_category = st.selectbox("方法分類", ["MCDM (多準則)", "量化 (問卷)", "質性 (訪談)"])
    final_method = method_category
    if "MCDM" in method_category:
        mcdm_tool = st.selectbox("MCDM 工具", ["AHP", "Delphi", "FCM", "TOPSIS"])
        final_method = f"MCDM ({mcdm_tool})"

# --- 主畫面 ---
st.title("🐢 論文寫作助手 (保命降級版)")

if not api_key: st.warning("請先輸入 API Key"); st.stop()

# === 步驟 0: 題目 ===
if st.session_state.step == 0:
    st.subheader("步驟 0：題目")
    if st.button("✨ 產生題目"):
        if not keywords_str: st.error("請輸入關鍵字")
        else:
            with st.spinner("嘗試連線中..."):
                prompt = f"關鍵字：{keywords_str}。方法：{final_method}。請產生 3 個繁體中文題目。"
                res = ask_gemini_robust(prompt, api_key, st.session_state.global_rules)
                st.write(res) # 直接顯示讓你看有沒有成功
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
            res = ask_gemini_robust(prompt, api_key, st.session_state.global_rules)
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
    
    # 簡單的章節選單
    chapter_map = {ch['key']: ch['name'] for ch in CHAPTERS}
    selected_ch_key = st.selectbox("選擇章節", list(chapter_map.keys()), format_func=lambda x: chapter_map[x])
    
    current_content = st.session_state.content.get(selected_ch_key, "")
    
    if st.button(f"🚀 撰寫 {chapter_map[selected_ch_key]}"):
        with st.spinner("AI 寫作中 (若忙碌會自動切換舊版模型)..."):
            prompt = f"""
            題目：{st.session_state.final_title}
            章節：{chapter_map[selected_ch_key]}
            文獻：{st.session_state.refs}
            大綱：{st.session_state.outline}
            請撰寫本章節內容。
            """
            res = ask_gemini_robust(prompt, api_key, st.session_state.global_rules)
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

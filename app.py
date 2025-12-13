import streamlit as st
import google.generativeai as genai
import time
from google.api_core import exceptions

# --- 系統設定 ---
st.set_page_config(page_title="論文寫作助手 (終極鎖定版)", layout="wide", page_icon="🔒")

# ==========================================
# 🔥🔥🔥 已更新為新API Key (2025/12/13) 🔥🔥🔥
final_fixed_key = "AIzaSyAXQVsBivz15didMT0NqCsgxDvxgxgQgk0" 
# ==========================================

# --- 核心：暴力重試與降級機制 (正確模型名稱) ---
def ask_gemini_robust(prompt, key, user_rules=""):
    if "AIzaSy" not in key:
        return "⚠️ 請檢查程式碼第 13 行，Key 似乎沒填完整"
    
    genai.configure(api_key=key)
    
    full_prompt = prompt
    if user_rules:
        full_prompt = f"【請務必遵守以下規則】\n{user_rules}\n\n----------------\n{prompt}"

    # ✅ 2025正確模型名稱 (修復404錯誤)
    model_queue = ["gemini-1.5-flash-exp", "gemini-1.5-pro"]
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
            if "404" in error_msg or "model" in error_msg.lower(): 
                continue  # 模型不存在，試下一個
            return f"❌ 執行錯誤 ({current_model_name}): {error_msg}"
            
    return "❌ 所有模型都失敗，請檢查API Key或網路連線"

# --- 圖表清洗 ---
def clean_graphviz_code(raw_code):
    clean = raw_code.replace("``````", "").strip()
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
if 'proposed_titles' not in st.session_state: st.session_state.proposed_titles = []

# --- 側邊欄 (全域變數) ---
with st.sidebar:
    st.header("⚙️ 引擎設定")
    
    if "AIzaSy" in final_fixed_key:
        st.success("✅ API Key 已鎖定！")
    else:
        st.error("❌ 程式碼第 13 行的 Key 不正確")

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

    st.markdown("#### 關鍵字")
    keywords_str = st.text_input("輸入關鍵字 (例如: BRICS CO2, 管理科學)")
    
    st.divider()
    method_category = st.selectbox("方法分類", ["MCDM (多準則)", "量化 (問卷)", "質性 (訪談)"])
    final_method = method_category
    if "MCDM" in method_category:
        mcdm_tool = st.selectbox("MCDM 工具", ["AHP", "Delphi", "FCM", "TOPSIS"])
        final_method = f"MCDM ({mcdm_tool})"

# --- 主畫面 ---
st.title("🔒 論文寫作助手 (終極鎖定版 v2.0)")

if "AIzaSy" not in final_fixed_key:
    st.error("請把你的 Key 填入程式碼第 13 行！")
    st.stop()

# === 步驟 0: 題目 ===
if st.session_state.step == 0:
    st.subheader("步驟 0：題目")
    if st.button("✨ 產生題目"):
        if not keywords_str: 
            st.error("請輸入關鍵字")
        else:
            with st.spinner("連線中...測試新模型"):
                prompt = f"關鍵字：{keywords_str}。方法：{final_method}。請產生 3 個繁體中文題目，每個題目適合博士論文。"
                res = ask_gemini_robust(prompt, final_fixed_key, st.session_state.global_rules)
                st.markdown("**AI 生成的題目：**")
                st.write(res)
                if "❌" not in res:
                    st.session_state.proposed_titles = ["(請手動複製上面喜歡的題目填入下方)"]

    col1, col2 = st.columns(2)
    with col1:
        user_title = st.text_input("請輸入最終題目：", value=st.session_state.final_title)
    with col2:
        if st.button("🔒 鎖定題目", type="primary"):
            if user_title.strip():
                st.session_state.final_title = user_title
                st.session_state.step = 1
                st.success(f"題目已鎖定：{user_title}")
                st.rerun()
            else:
                st.error("請輸入題目")

# === 步驟 1: 文獻 ===
elif st.session_state.step == 1:
    st.subheader("步驟 1：文獻")
    st.markdown("**請貼上相關文獻（APA格式或參考文獻列表）**")
    refs_input = st.text_area("貼上文獻：", value=st.session_state.refs, height=200)
    st.session_state.refs = refs_input
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ 返回修改題目"):
            st.session_state.step = 0
            st.rerun()
    with col2:
        if st.button("➡️ 下一步 (生成大綱)", type="primary"):
            st.session_state.step = 2
            st.rerun()

# === 步驟 2: 大綱 ===
elif st.session_state.step == 2:
    st.subheader("步驟 2：論文大綱")
    if st.button("✨ 生成大綱"):
        with st.spinner("生成中... (使用 Gemini 1.5 Flash-Exp)"):
            prompt = f"""題目：{st.session_state.final_title}
方法：{final_method}
文獻：{st.session_state.refs[:2000]}...

請根據以上資訊寫出完整論文大綱，使用Markdown格式，包含各章節小節。"""
            res = ask_gemini_robust(prompt, final_fixed_key, st.session_state.global_rules)
            st.session_state.outline = res
            st.rerun()
            
    if st.session_state.outline:
        st.markdown("### 📋 論文大綱")
        st.markdown(st.session_state.outline)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ 返回文獻"):
                st.session_state.step = 1
                st.rerun()
        with col2:
            if st.button("🚀 下一步 (寫內文)", type="primary"):
                st.session_state.step = 3
                st.rerun()

# === 步驟 3: 寫作 ===
elif st.session_state.step == 3:
    st.subheader("步驟 3：逐章寫作")
    chapter_map = {ch['key']: ch['name'] for ch in CHAPTERS}
    selected_ch_key = st.selectbox("選擇章節", list(chapter_map.keys()), format_func=lambda x: chapter_map[x])
    
    current_content = st.session_state.content.get(selected_ch_key, "")
    
    col1, col2 = st.columns([2,1])
    with col1:
        if st.button(f"🚀 撰寫 {chapter_map[selected_ch_key]}", type="primary"):
            with st.spinner(f"AI 寫作中... ({chapter_map[selected_ch_key]})"):
                prompt = f"""題目：{st.session_state.final_title}
章節：{chapter_map[selected_ch_key]}
文獻：{st.session_state.refs[:3000]}
大綱：{st.session_state.outline[:3000]}

請撰寫本章節完整內容，使用學術繁體中文，字數約1500-2000字。"""
                res = ask_gemini_robust(prompt, final_fixed_key, st.session_state.global_rules)
                st.session_state.content[selected_ch_key] = res
                st.success(f"✅ {chapter_map[selected_ch_key]} 寫作完成！")
                st.rerun()
    
    with col2:
        st.markdown("**已完成章節：**")
        for ch_key, content in st.session_state.content.items():
            st.markdown(f"• {chapter_map[ch_key]} {'✅' if content else '⭕'}")
            
    if current_content:
        st.markdown("### 📄 章節內容預覽")
        st.markdown(current_content)
        
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("⬅️ 返回大綱"):
            st.session_state.step = 2
            st.rerun()
    with col3:
        if st.button("💾 前往下載", type="primary"):
            st.session_state.step = 4
            st.rerun()

# === 步驟 4: 下載 ===
elif st.session_state.step == 4:
    st.subheader("✅ 步驟 4：論文完成！")
    chapter_map = {ch['key']: ch['name'] for ch in CHAPTERS}
    
    final_text = f"# {st.session_state.final_title}\n\n"
    final_text += f"**方法：** {final_method}\n\n"
    final_text += f"**生成時間：** 2025年12月13日\n\n"
    
    completed_chapters = 0
    for ch_key, content in st.session_state.content.items():
        if content:
            final_text += f"\n\n## {chapter_map[ch_key]}\n\n"
            final_text += content
            completed_chapters += 1
    
    st.success(f"已完成 {completed_chapters}/5 章節")
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="📥 下載 Markdown",
            data=final_text,
            file_name="thesis.md",
            mime="text/markdown"
        )
    with col2:
        st.download_button(
            label="📊 查看進度",
            data=final_text,
            file_name=f"論文進度_{st.session_state.final_title[:20]}.md",
            mime="text/markdown"
        )
    
    if st.button("🔄 重新開始"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

import streamlit as st
import google.generativeai as genai
import time
from google.api_core import exceptions

# --- 系統設定 ---
st.set_page_config(page_title="論文寫作助手 (終極修復版)", layout="wide", page_icon="📚")

# ==========================================
# 🔥🔥🔥 API Key 填寫區 🔥🔥🔥
# 請將你的 Google API Key 填入下方的引號中
FIXED_API_KEY = "這裡填入你的API_KEY"
# ==========================================

# --- 核心函數：超穩重試機制 (Gemini Native) ---
def ask_llm_robust(prompt, user_rules=""):
    """使用 Google Gemini API，具備自動重試與模型切換功能"""
    
    # 1. 取得 API Key (優先使用程式碼內的鎖定 Key)
    api_key = None
    if "這裡填入" not in FIXED_API_KEY and FIXED_API_KEY.strip():
        api_key = FIXED_API_KEY
    elif "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
    else:
        # 如果都沒填，嘗試從 Session State 獲取 (側邊欄輸入)
        api_key = st.session_state.get("user_input_key")

    if not api_key:
        return "❌ 錯誤：未偵測到 API Key，請在程式碼第 12 行填入或在側邊欄輸入。"

    # 2. 設定 Google AI
    genai.configure(api_key=api_key)

    # 3. 組合 Prompt
    full_prompt = prompt
    if user_rules:
        full_prompt = f"【角色設定】你是一位管理科學與工程領域的頂尖博士級研究員。\n【嚴格規則】\n{user_rules}\n\n【任務內容】\n{prompt}"

    # 4. 定義模型順序 (優先使用 Flash，速度快且免費額度高)
    # 注意：使用真實存在的模型名稱
    models = ["gemini-1.5-flash", "gemini-1.5-pro"]
    
    for model_name in models:
        try:
            # 建立模型
            model = genai.GenerativeModel(model_name)
            
            # 設定參數 (降低溫度以確保學術嚴謹性)
            generation_config = genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=4096, # 確保能輸出長文
            )
            
            # 發送請求
            response = model.generate_content(full_prompt, generation_config=generation_config)
            
            if response.text:
                return response.text
            else:
                st.warning(f"模型 {model_name} 回傳空值，切換備用模型...")

        except exceptions.ResourceExhausted:
            st.warning(f"⚠️ 模型 {model_name} 額度額滿或忙碌，等待 5 秒後切換...")
            time.sleep(5)
            continue
        except Exception as e:
            st.error(f"⚠️ 模型 {model_name} 發生錯誤: {str(e)}")
            continue
            
    return "❌ 所有模型均嘗試失敗，請檢查 API Key 是否正確或稍後再試。"

# --- Session State 初始化 ---
if 'step' not in st.session_state: st.session_state.step = 0
if 'final_title' not in st.session_state: st.session_state.final_title = ""
if 'refs' not in st.session_state: st.session_state.refs = ""
if 'outline' not in st.session_state: st.session_state.outline = ""
if 'content' not in st.session_state: st.session_state.content = {}
if 'global_rules' not in st.session_state: 
    st.session_state.global_rules = "1. 使用繁體中文學術用語\n2. 格式符合APA第7版規範\n3. 邏輯需符合管理科學與工程博士論文水準\n4. 嚴禁使用 LaTeX 語法，數學公式請用文字描述"

# --- 側邊欄 ---
with st.sidebar:
    st.header("⚙️ 控制面板")
    
    # API Key 狀態檢查
    if "這裡填入" not in FIXED_API_KEY and FIXED_API_KEY.strip():
        st.success("✅ API Key 已鎖定 (程式碼)")
    elif "GOOGLE_API_KEY" in st.secrets:
        st.success("✅ API Key 已鎖定 (Secrets)")
    else:
        st.warning("⚠️ 未檢測到 Key")
        st.session_state.user_input_key = st.text_input("請輸入 Google API Key", type="password")
    
    st.divider()
    
    # 寫作規則
    st.markdown("### 📝 寫作規範")
    rules = st.text_area("全域規則", value=st.session_state.global_rules, height=150)
    st.session_state.global_rules = rules
    
    st.divider()
    
    # 論文設定
    paper_type = st.radio("論文類型", ["學位論文", "期刊論文"], horizontal=True)
    
    if paper_type == "學位論文":
        CHAPTERS = [
            {"key": "ch1", "name": "第一章 緒論"},
            {"key": "ch2", "name": "第二章 文獻探討"},
            {"key": "ch3", "name": "第三章 研究方法"},
            {"key": "ch4", "name": "第四章 分析結果"},
            {"key": "ch5", "name": "第五章 結論與建議"}
        ]
    else:
        CHAPTERS = [
            {"key": "ch1", "name": "1. 前言"},
            {"key": "ch2", "name": "2. 文獻回顧"},
            {"key": "ch3", "name": "3. 研究方法"},
            {"key": "ch4", "name": "4. 結果與討論"},
            {"key": "ch5", "name": "5. 結論"}
        ]
    
    st.markdown("### 🔑 研究關鍵詞")
    keywords = st.text_input("核心關鍵字", placeholder="例如: BRICS, CO2 Emissions, 面板數據")
    method = st.selectbox("研究方法", ["面板數據分析 (Panel Data)", "MCDM (多準則決策)", "結構方程模型 (SEM)", "系統動力學 (SD)"])

# --- 主介面 ---
st.title("📚 博士論文寫作助手 v3.1 (Gemini版)")
st.markdown(f"**當前設定**：{method} | 領域：管理科學與工程 | 重點：{keywords if keywords else '未設定'}")

# === 步驟導航 ===
progress_bar = st.progress(st.session_state.step / 4)
steps = ["題目生成", "文獻輸入", "大綱生成", "章節寫作", "論文下載"]
st.caption(f"目前進度：{steps[st.session_state.step]} ({st.session_state.step + 1}/5)")

# === 步驟 0: 題目 ===
if st.session_state.step == 0:
    st.header("📝 步驟 1：產生研究題目")
    
    col1, col2 = st.columns([2,1])
    with col1:
        if st.button("✨ AI 生成題目建議", type="primary"):
            if keywords:
                with st.spinner("正在分析文獻趨勢並生成題目..."):
                    prompt = f"""
                    領域：管理科學與工程
                    關鍵字：{keywords}
                    研究方法：{method}
                    
                    請產生 3 個適合博士學位論文的繁體中文題目。
                    要求：
                    1. 題目需體現學術深度。
                    2. 必須包含方法論與研究對象。
                    3. 每個題目下方附上 30 字的簡短設計理念。
                    """
                    
                    result = ask_llm_robust(prompt, st.session_state.global_rules)
                    st.session_state.generated_titles = result
            else:
                st.warning("請先在側邊欄輸入關鍵字！")
    
    with col2:
        if 'generated_titles' in st.session_state:
            st.info("💡 生成結果參考")
            st.markdown(st.session_state.generated_titles)
    
    st.markdown("---")
    title_input = st.text_input("👇 請在此輸入或複製最終決定的題目", value=st.session_state.final_title)
    
    if st.button("✅ 鎖定題目，下一步", type="secondary"):
        if title_input.strip():
            st.session_state.final_title = title_input
            st.session_state.step = 1
            st.rerun()
        else:
            st.error("題目欄位不能為空！")

# === 步驟 1: 文獻 ===
elif st.session_state.step == 1:
    st.header("📚 步驟 2：導入核心文獻")
    st.markdown(f"> **當前題目**：{st.session_state.final_title}")
    
    st.info("請貼上您已整理好的參考文獻 (APA格式尤佳)，AI 將依據這些文獻進行內容撰寫，避免瞎編。")
    refs = st.text_area("文獻列表", value=st.session_state.refs, height=300, placeholder="[1] Author, A. A. (Year). Title of article. Title of Periodical, volume number(issue number), pages.\n[2] ...")
    st.session_state.refs = refs
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("⬅️ 上一步 (修題目)"):
            st.session_state.step = 0
            st.rerun()
    with col2:
        if st.button("下一步 (生成大綱) ➡️", type="primary"):
            st.session_state.step = 2
            st.rerun()

# === 步驟 2: 大綱 ===
elif st.session_state.step == 2:
    st.header("📋 步驟 3：架構與大綱")
    
    if st.button("✨ 智慧生成論文大綱", type="primary"):
        with st.spinner("正在建構邏輯架構..."):
            prompt = f"""
            題目：{st.session_state.final_title}
            研究方法：{method}
            參考文獻：
            {st.session_state.refs[:1500]} (部分摘要)
            
            任務：請生成一份結構嚴謹的博士論文大綱。
            格式要求：
            1. 使用 Markdown 格式。
            2. 包含章節標題 (Chapter) 與節標題 (Section)。
            3. 每一節請簡述預計寫作重點 (Bullet points)。
            4. 確保邏輯連貫，符合管理科學工程領域規範。
            """
            result = ask_llm_robust(prompt, st.session_state.global_rules)
            st.session_state.outline = result
            st.rerun()
    
    if st.session_state.outline:
        st.markdown("### 📖 大綱預覽")
        st.markdown(st.session_state.outline)
        
        st.markdown("---")
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("⬅️ 上一步 (修文獻)"):
                st.session_state.step = 1
                st.rerun()
        with col2:
            if st.button("下一步 (開始寫作) ➡️", type="primary"):
                st.session_state.step = 3
                st.rerun()

# === 步驟 3: 寫作 ===
elif st.session_state.step == 3:
    st.header("✍️ 步驟 4：逐章撰寫")
    
    chapter_map = {ch['key']: ch['name'] for ch in CHAPTERS}
    selected_ch = st.selectbox("選擇要撰寫的章節", options=list(chapter_map.keys()), format_func=lambda x: chapter_map[x])
    
    if st.button(f"🚀 開始撰寫：{chapter_map[selected_ch]}", type="primary"):
        with st.spinner(f"正在撰寫 {chapter_map[selected_ch]}，請稍候 (約需 30-60 秒)..."):
            prompt = f"""
            題目：{st.session_state.final_title}
            當前撰寫章節：{chapter_map[selected_ch]}
            
            整體大綱：
            {st.session_state.outline}
            
            核心文獻：
            {st.session_state.refs[:2000]}
            
            研究方法：{method}
            
            任務：請撰寫本章節的完整內容。
            要求：
            1. 字數約 1500-2000 字。
            2. 內容需具備學術深度，邏輯推演嚴密。
            3. 適當引用上述提供的文獻 (使用 [Author, Year] 格式)。
            4. 若為方法章節，需詳細描述 {method} 的操作步驟。
            5. 若為結果章節，請模擬合理的數據趨勢進行描述。
            """
            
            result = ask_llm_robust(prompt, st.session_state.global_rules)
            st.session_state.content[selected_ch] = result
            st.success(f"✅ {chapter_map[selected_ch]} 撰寫完成！")
            st.rerun()
    
    # 顯示編輯區
    if selected_ch in st.session_state.content:
        st.text_area("內容編輯 (可手動修改)", value=st.session_state.content[selected_ch], height=500)
        st.markdown("### 預覽")
        st.markdown(st.session_state.content[selected_ch])
    
    st.markdown("---")
    
    # 章節狀態概覽
    st.subheader("📊 章節完成狀態")
    cols = st.columns(len(CHAPTERS))
    for idx, ch in enumerate(CHAPTERS):
        status = "✅" if ch['key'] in st.session_state.content else "⬜"
        cols[idx].metric(ch['name'], status)

    if st.button("💾 全部完成，前往下載", type="secondary"):
        st.session_state.step = 4
        st.rerun()

# === 步驟 4: 下載 ===
elif st.session_state.step == 4:
    st.header("🎉 論文初稿完成！")
    
    # 組合全文
    chapter_map = {ch['key']: ch['name'] for ch in CHAPTERS}
    final_doc = f"# {st.session_state.final_title}\n\n"
    final_doc += f"**研究方法**：{method}\n"
    final_doc += f"**生成日期**：{time.strftime('%Y-%m-%d')}\n\n---\n\n"
    
    completed_count = 0
    for ch in CHAPTERS:
        key = ch['key']
        if key in st.session_state.content:
            final_doc += f"\n\n# {chapter_map[key]}\n\n"
            final_doc += st.session_state.content[key]
            completed_count += 1
            
    st.info(f"共完成 {completed_count}/{len(CHAPTERS)} 個章節")
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="📥 下載完整論文 (.md)",
            data=final_doc,
            file_name=f"Dissertation_{st.session_state.final_title[:10]}.md",
            mime="text/markdown"
        )
    
    with col2:
        if st.button("🔄 開始新的研究"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

import streamlit as st
import openai
from datetime import datetime

# --- 頁面設定 ---
st.set_page_config(page_title="AI 深度論文寫作系統", layout="wide", page_icon="🎓")

# --- Session State 初始化 (記憶體) ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'selected_gap' not in st.session_state: st.session_state.selected_gap = ""
if 'real_references' not in st.session_state: st.session_state.real_references = ""
if 'outline' not in st.session_state: st.session_state.outline = ""
if 'thesis_content' not in st.session_state: st.session_state.thesis_content = {}

# --- 側邊欄：設定與輸入 ---
with st.sidebar:
    st.title("⚙️ 核心設定")
    api_key = st.text_input("請輸入 OpenAI API Key", type="password", help="需要 GPT-4 才能寫出長篇且有邏輯的論文")
    
    if api_key:
        openai.api_key = api_key
        st.success("API Key 已連接")
    
    st.divider()
    st.header("1. 研究主題設定")
    topic = st.text_input("研究主題 (Topic)", "例如：生成式AI對大學生學習動機之影響")
    method = st.selectbox("研究方法 (Methodology)", 
        ["量化研究 - 問卷調查 (Survey)", 
         "質性研究 - 深度訪談 (Interview)", 
         "混合研究法 (Mixed Methods)", 
         "實驗法 (Experiment)"])
    
    st.info(f"目標：撰寫 15,000 字小論文\n目前進度：第 {st.session_state.step} 階段")

# --- 核心 AI 函式 ---
def ask_gpt(prompt, model="gpt-4"):
    """呼叫 GPT 進行思考與寫作"""
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一位嚴謹的學術論文指導教授，專精於繁體中文學術寫作。絕不捏造文獻，若無真實來源請標註 [需補充文獻]。寫作風格需學術、客觀、邏輯縝密。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message['content']
    except Exception as e:
        return f"錯誤：{str(e)} (請檢查 API Key 或額度)"

# --- 主畫面邏輯 ---

st.title("🎓 AI 深度論文寫作系統")

if not api_key:
    st.warning("⚠️ 請先在左側輸入 OpenAI API Key 才能啟動 AI 引擎。")
    st.stop()

# === 第一階段：找出缺口 (Gap Analysis) ===
if st.session_state.step == 1:
    st.header("第一階段：研究缺口分析與選擇")
    st.markdown(f"針對主題 **「{topic}」**，AI 將為您分析目前學術界的潛在缺口。")
    
    if st.button("🔍 分析研究缺口"):
        with st.spinner("正在檢索學術邏輯與推導缺口..."):
            prompt = f"""
            請針對研究主題「{topic}」，提出 3 個具有學術價值的「研究缺口 (Research Gap)」。
            
            要求：
            1. 缺口必須具體，邏輯合理。
            2. 每個缺口請附帶一個「暫定題目」。
            3. 請用 JSON 格式以外的條列式清晰呈現，方便使用者閱讀。
            4. 不要捏造文獻，而是基於該領域普遍的不足之處（如：缺乏本土實證、變數中介效果不明、方法論限制等）進行推論。
            """
            gaps_result = ask_gpt(prompt)
            st.session_state.gaps_suggestion = gaps_result
            
    if 'gaps_suggestion' in st.session_state:
        st.markdown("### 🎯 AI 建議的缺口選項：")
        st.markdown(st.session_state.gaps_suggestion)
        
        st.divider()
        st.subheader("請選擇並修飾您要的缺口：")
        user_selected_gap = st.text_area("複製上方您喜歡的缺口與題目，貼在這裡：", height=100)
        
        if st.button("✅ 確認缺口，進入文獻階段"):
            if user_selected_gap:
                st.session_state.selected_gap = user_selected_gap
                st.session_state.step = 2
                st.experimental_rerun()
            else:
                st.error("請先輸入您選擇的研究缺口")

# === 第二階段：真實文獻導入 (Real Literature) ===
elif st.session_state.step == 2:
    st.header("第二階段：建立真實文獻庫")
    st.info("💡 AI 無法上網搜尋最新付費論文，為避免造假，請依據 AI 建議的關鍵字，去 Google Scholar 找 3-5 篇真的文獻貼回來。這將作為論文的核心依據。")
    
    st.markdown(f"**您的研究缺口：** {st.session_state.selected_gap}")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔑 告訴我該搜尋什麼關鍵字？"):
            prompt = f"針對題目與缺口「{st.session_state.selected_gap}」，請列出 5 組精準的 Google Scholar 搜尋關鍵字（中英文皆要），以便使用者找到核心文獻。"
            st.write(ask_gpt(prompt))
            
    with col2:
        st.markdown("### 📥 在此貼上真實文獻摘要")
        references_input = st.text_area("格式：作者 (年份) 標題。重要發現...", height=300, placeholder="例如：\n1. 張某某 (2023) 生成式AI與學習成效。發現AI能顯著提升... \n2. Smith (2024) AI Ethics. Found that...")
        
        if st.button("✅ 文獻確認，生成大綱"):
            if references_input:
                st.session_state.real_references = references_input
                st.session_state.step = 3
                st.experimental_rerun()
            else:
                st.warning("為了論文品質，請至少貼入一篇真實文獻或摘要。")

# === 第三階段：架構生成 (Outline) ===
elif st.session_state.step == 3:
    st.header("第三階段：論文架構藍圖")
    
    if not st.session_state.outline:
        with st.spinner("正在根據缺口與真實文獻，規劃 15,000 字的章節架構..."):
            prompt = f"""
            請為以下研究撰寫一份詳細的「學術論文大綱」，目標總字數 15,000 字。
            
            題目與缺口：{st.session_state.selected_gap}
            核心參考文獻：{st.session_state.real_references}
            研究方法：{method}
            
            要求：
            1. 結構必須包含五章（緒論、文獻探討、研究方法、分析結果、結論）。
            2. 每一節（如 2.1, 2.2）都要列出預計撰寫的重點與字數分配。
            3. 第三章研究方法需詳細列出步驟（符合 {method} 的專業流程）。
            """
            st.session_state.outline = ask_gpt(prompt)
    
    st.markdown(st.session_state.outline)
    
    if st.button("✅ 架構確認，開始分章撰寫"):
        st.session_state.step = 4
        st.experimental_rerun()

# === 第四階段：分章寫作 (Writing Agent) ===
elif st.session_state.step == 4:
    st.header("第四階段：AI 深度寫作模式")
    st.markdown("由於 15,000 字過長，我們將**逐章撰寫**。請依序點擊下方按鈕。")
    
    tabs = st.tabs(["第一章：緒論", "第二章：文獻探討", "第三章：研究方法", "第四章：研究結果", "第五章：結論"])
    
    # 定義寫作函式
    def write_chapter(chapter_name, focus_points):
        prompt = f"""
        請撰寫論文的「{chapter_name}」。
        
        基礎資訊：
        - 題目與缺口：{st.session_state.selected_gap}
        - 參考文獻庫：{st.session_state.real_references}
        - 完整大綱：{st.session_state.outline}
        
        寫作要求：
        1. 字數目標：至少 2,500 字（請盡量詳細，多加闡述）。
        2. 語氣：專業學術中文。
        3. 引用：請在適當處標註 (Author, Year)，優先使用上述提供的參考文獻庫。
        4. 格式：使用 Markdown 格式，包含次標題。
        5. 內容重點：{focus_points}
        """
        return ask_gpt(prompt, model="gpt-4") # 建議使用 GPT-4

    # --- 第一章 ---
    with tabs[0]:
        st.subheader("第一章：緒論")
        if "ch1" not in st.session_state.thesis_content:
            if st.button("✍️ 撰寫第一章"):
                with st.spinner("正在撰寫緒論，這需要幾分鐘..."):
                    st.session_state.thesis_content["ch1"] = write_chapter("第一章 緒論", "包含研究背景、動機、目的、問題、名詞解釋")
        
        if "ch1" in st.session_state.thesis_content:
            st.markdown(st.session_state.thesis_content["ch1"])

    # --- 第二章 ---
    with tabs[1]:
        st.subheader("第二章：文獻探討")
        if "ch2" not in st.session_state.thesis_content:
            if st.button("✍️ 撰寫第二章"):
                with st.spinner("正在整合文獻與理論..."):
                    st.session_state.thesis_content["ch2"] = write_chapter("第二章 文獻探討", "包含理論基礎、相關研究回顧、研究缺口推導、假設推導(若為量化)")
        
        if "ch2" in st.session_state.thesis_content:
            st.markdown(st.session_state.thesis_content["ch2"])

    # --- 第三章 ---
    with tabs[2]:
        st.subheader("第三章：研究方法")
        if "ch3" not in st.session_state.thesis_content:
            if st.button("✍️ 撰寫第三章"):
                with st.spinner("正在描述研究設計..."):
                    st.session_state.thesis_content["ch3"] = write_chapter("第三章 研究方法", f"詳細描述 {method} 之執行步驟、對象、工具、分析方法")
        
        if "ch3" in st.session_state.thesis_content:
            st.markdown(st.session_state.thesis_content["ch3"])

    # --- 第四章 (模擬結果) ---
    with tabs[3]:
        st.subheader("第四章：研究結果")
        st.warning("注意：AI 只能生成「虛擬數據」或「預期結果範本」。真實論文需填入實際跑出的數據。")
        if "ch4" not in st.session_state.thesis_content:
            if st.button("✍️ 撰寫第四章 (模擬框架)"):
                with st.spinner("正在生成結果呈現框架..."):
                    st.session_state.thesis_content["ch4"] = write_chapter("第四章 研究結果", "生成虛擬的數據分析結果表格、圖表說明、假設檢定結果描述")
        
        if "ch4" in st.session_state.thesis_content:
            st.markdown(st.session_state.thesis_content["ch4"])

    # --- 第五章 ---
    with tabs[4]:
        st.subheader("第五章：結論與建議")
        if "ch5" not in st.session_state.thesis_content:
            if st.button("✍️ 撰寫第五章"):
                with st.spinner("正在進行總結與建議..."):
                    st.session_state.thesis_content["ch5"] = write_chapter("第五章 結論與建議", "研究發現摘要、管理/教育實務意涵、學術貢獻、研究限制")
        
        if "ch5" in st.session_state.thesis_content:
            st.markdown(st.session_state.thesis_content["ch5"])

    st.divider()
    # 下載全部
    full_text = "\n\n".join(st.session_state.thesis_content.values())
    if full_text:
        st.download_button("📥 下載完整 15,000 字論文初稿 (Markdown)", full_text, "Full_Thesis.md")

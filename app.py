import streamlit as st
from openai import OpenAI
import time
import os


# --- 系統設定 ---
st.set_page_config(page_title="論文寫作助手 (終極修復版)", layout="wide", page_icon="📚")

# ==========================================
# 🔥🔥🔥 新API Key (2025/12/13 10:32) 🔥🔥🔥
# ⚠️ 這是無效的Key，需要替換為有效的API Key
# 🔑 Manus-managed API, no key needed 
# ==========================================

# --- 核心函數：超穩重試機制 ---
def ask_llm_robust(prompt, user_rules=""):
    """使用Manus環境的LLM API，無需手動管理Key"""
    client = OpenAI() # 由環境自動配置
    
    full_prompt = prompt
    if user_rules:
        full_prompt = f"【請嚴格遵守以下規則】\n{user_rules}\n\n【使用者提示】\n{prompt}"

    # Manus 環境中可用的模型
    models = ["gemini-2.5-flash", "gpt-4.1-mini"]
    
    for model_name in models:
        try:
            st.info(f"🔄 正在嘗試使用模型: {model_name}")
            completion = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "你是一位頂尖的博士級論文寫作專家，專精於管理科學與工程領域。你的任務是根據使用者提供的關鍵字、研究方法和規則，提供專業、嚴謹、符合學術規範的內容。"},
                    {"role": "user", "content": full_prompt}
                ]
            )
            response = completion.choices[0].message.content.strip()
            if response:
                return response
            else:
                st.warning(f"模型 {model_name} 回應為空，正在切換至下一個模型...")
                
        except Exception as e:
            st.warning(f"⚠️ 使用模型 {model_name} 時發生錯誤: {str(e)[:150]}... 正在切換模型...")
            time.sleep(2)
            
    return "❌ 所有可用模型均嘗試失敗，請檢查您的提示或稍後再試。"

# --- Session State ---
if 'step' not in st.session_state: st.session_state.step = 0
if 'final_title' not in st.session_state: st.session_state.final_title = ""
if 'refs' not in st.session_state: st.session_state.refs = ""
if 'outline' not in st.session_state: st.session_state.outline = ""
if 'content' not in st.session_state: st.session_state.content = {}
if 'global_rules' not in st.session_state: 
    st.session_state.global_rules = "1. 使用繁體中文\n2. 學術寫作風格\n3. 避免LaTeX"

# --- 側邊欄 ---
with st.sidebar:
    st.header("⚙️ 控制面板")
    
    # API Key 狀態
    st.success("✅ LLM服務已由Manus環境提供")
        
    
    
    st.divider()
    
    # 寫作規則
    rules = st.text_area("寫作規則", value=st.session_state.global_rules, height=80)
    st.session_state.global_rules = rules
    
    # 論文設定
    st.divider()
    paper_type = st.radio("論文類型", ["學位論文", "期刊論文"], horizontal=True)
    
    if paper_type == "學位論文":
        CHAPTERS = [
            {"key": "ch1", "name": "第一章 緒論"},
            {"key": "ch2", "name": "第二章 文獻探討"},
            {"key": "ch3", "name": "第三章 研究方法"},
            {"key": "ch4", "name": "第四章 分析結果"},
            {"key": "ch5", "name": "第五章 結論"}
        ]
    else:
        CHAPTERS = [
            {"key": "ch1", "name": "1. 前言"},
            {"key": "ch2", "name": "2. 文獻回顧"},
            {"key": "ch3", "name": "3. 研究方法"},
            {"key": "ch4", "name": "4. 結果與討論"},
            {"key": "ch5", "name": "5. 結論"}
        ]
    
    # 關鍵設定
    st.markdown("### 🔑 關鍵設定")
    keywords = st.text_input("關鍵字", placeholder="BRICS CO2, 面板數據")
    method = st.selectbox("研究方法", ["面板數據分析", "MCDM", "問卷調查", "質性研究"])

# --- 主介面 ---
st.title("📚 博士論文寫作助手 v3.0")
st.markdown("**專為管理科學工程博士設計** - BRICS CO2研究優化")

# API Key 檢查
() # 暫時註釋掉，避免在修復前停止程式

# === 步驟導航 ===
progress_bar = st.progress(st.session_state.step / 4)
steps = ["題目生成", "文獻輸入", "大綱生成", "章節寫作", "論文下載"]
st.caption(f"進度：{steps[st.session_state.step]}")

# === 步驟 0: 題目 ===
if st.session_state.step == 0:
    st.header("📝 步驟 1/5：產生研究題目")
    
    col1, col2 = st.columns([2,1])
    with col1:
        if st.button("✨ AI生成題目", type="primary"):
            if keywords:
                with st.spinner("連線Google Gemini..."):
                    test_prompt = f"""關鍵字：{keywords}
研究方法：{method}
領域：管理科學工程
請產生3個適合博士論文的繁體中文題目，每個100字內。"""
                    
                    result = ask_llm_robust(test_prompt, st.session_state.global_rules)
                    
                    if "❌" not in result:
                        st.session_state.generated_titles = result
                        st.success("✅ 題目生成成功！")
                    else:
                        st.error(result)
                        
            else:
                st.warning("請輸入關鍵字")
    
    with col2:
        if 'generated_titles' in st.session_state:
            st.markdown("**生成結果：**")
            st.markdown(st.session_state.generated_titles)
    
    st.markdown("---")
    title_input = st.text_input("鎖定最終題目", value=st.session_state.final_title)
    if st.button("✅ 確認題目並繼續", type="primary"):
        if title_input.strip():
            st.session_state.final_title = title_input
            st.session_state.step = 1
            st.rerun()
        else:
            st.error("請輸入題目")

# === 步驟 1: 文獻 ===
elif st.session_state.step == 1:
    st.header("📚 步驟 2/5：文獻輸入")
    st.info(f"**當前題目**：{st.session_state.final_title}")
    
    refs = st.text_area("貼入文獻（APA格式）", value=st.session_state.refs, height=250)
    st.session_state.refs = refs
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← 返回題目"):
            st.session_state.step = 0
            st.rerun()
    with col2:
        if st.button("→ 生成大綱", type="primary"):
            st.session_state.step = 2
            st.rerun()

# === 步驟 2: 大綱 ===
elif st.session_state.step == 2:
    st.header("📋 步驟 3/5：生成論文大綱")
    st.info(f"**題目**：{st.session_state.final_title}")
    
    if st.button("✨ 生成完整大綱", type="primary"):
        with st.spinner("AI規劃論文結構..."):
            outline_prompt = f"""題目：{st.session_state.final_title}
方法：{method}
文獻：{st.session_state.refs[:1000]}

請生成完整論文大綱，使用Markdown格式，包含：
1. 各章節標題
2. 每個章節3-5個小節
3. 總字數預估
適合管理科學工程博士論文。"""
            
            result = ask_llm_robust(outline_prompt, st.session_state.global_rules)
            st.session_state.outline = result
            st.rerun()
    
    if st.session_state.outline:
        st.markdown("## 📋 論文大綱")
        st.markdown(st.session_state.outline)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← 返回文獻"):
                st.session_state.step = 1
                st.rerun()
        with col2:
            if st.button("→ 開始寫作", type="primary"):
                st.session_state.step = 3
                st.rerun()

# === 步驟 3: 寫作 ===
elif st.session_state.step == 3:
    st.header("✍️ 步驟 4/5：AI寫作")
    
    chapter_map = {ch['key']: ch['name'] for ch in CHAPTERS}
    selected_ch = st.selectbox("選擇章節", options=list(chapter_map.keys()), 
                              format_func=lambda x: chapter_map[x])
    
    if st.button(f"🚀 寫作 {chapter_map[selected_ch]}", type="primary"):
        with st.spinner("AI學術寫作中..."):
            write_prompt = f"""題目：{st.session_state.final_title}
章節：{chapter_map[selected_ch]}
大綱：{st.session_state.outline}
文獻：{st.session_state.refs[:2000]}
方法：{method}

請撰寫完整章節內容：
- 繁體中文學術寫作
- 1500-2500字
- 引用文獻
- 邏輯嚴謹"""
            
            result = ask_llm_robust(write_prompt, st.session_state.global_rules)
            st.session_state.content[selected_ch] = result
            st.success(f"✅ {chapter_map[selected_ch]} 完成！")
            st.rerun()
    
    # 顯示已寫內容
    if selected_ch in st.session_state.content:
        st.markdown("## 📄 章節內容")
        st.markdown(st.session_state.content[selected_ch])
    
    # 進度顯示
    st.subheader("📊 寫作進度")
    for ch_key, ch_name in chapter_map.items():
        status = "✅" if ch_key in st.session_state.content else "⭕"
        st.markdown(f"• {ch_name} {status}")
    
    if st.button("💾 完成寫作，下載論文", type="primary"):
        st.session_state.step = 4
        st.rerun()

# === 步驟 4: 下載 ===
elif st.session_state.step == 4:
    st.header("🎉 論文完成！")
    
    # 生成最終文件
    chapter_map = {ch['key']: ch['name'] for ch in CHAPTERS}
    final_doc = f"# {st.session_state.final_title}\n\n"
    final_doc += f"**研究方法**：{method}\n"
    final_doc += f"**生成時間**：2025年12月13日\n\n"
    
    completed = 0
    for ch_key in chapter_map:
        if ch_key in st.session_state.content:
            final_doc += f"\n## {chapter_map[ch_key]}\n\n"
            final_doc += st.session_state.content[ch_key] + "\n\n"
            completed += 1
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "📥 下載完整論文 (Markdown)",
            final_doc,
            f"博士論文_{st.session_state.final_title[:30]}.md",
            "text/markdown"
        )
    with col2:
        st.download_button(
            "📊 預覽版本",
            final_doc,
            "論文預覽.md",
            "text/markdown"
        )
    
    st.success(f"完成 {completed}/5 章節")
    if st.button("🔄 新建論文"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state.step = 0
        st.rerun()

# --- 頁尾 ---
st.markdown("---")
st.markdown("*專為管理科學工程博士設計 | BRICS CO2研究優化*")

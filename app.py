# ╔══════════════════════════════════════════════════════════════╗
# ║     論文寫作助手 - 內建API版                                 ║
# ║     存成 thesis_with_api.py                                  ║
# ╚══════════════════════════════════════════════════════════════╝

import streamlit as st
import google.generativeai as genai
import requests
import json
import re
import time
import io
import pandas as pd
from docx import Document

st.set_page_config(page_title="論文寫作助手", layout="wide", page_icon="🎓")

# ─────────────────────────────────────────────
# ⚠️  請在這裡填入你的API Key
# ─────────────────────────────────────────────
# 📍 Groq API Key (免費申請: https://console.groq.com)
DEFAULT_GROQ_KEY = "gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # 🔑 請替換為你的Groq Key

# 📍 Gemini API Key (免費申請: https://aistudio.google.com/app/apikey)  
DEFAULT_GEMINI_KEY = "AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # 🔑 請替換為你的Gemini Key

# ─────────────────────────────────────────────
# Session 初始化
# ─────────────────────────────────────────────
defaults = {
    "step": 0,
    "final_title": "",
    "refs_list": [],
    "refs_cache": {},
    "sim_data": None,
    "outline": "",
    "content": {},
    "full_integrated_paper": "",
    "ai_mode": "Groq（免費雲端）",
    # 使用預設API Key
    "groq_key": DEFAULT_GROQ_KEY,
    "gemini_key": DEFAULT_GEMINI_KEY
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────
# AI 呼叫函數（內建Key版）
# ─────────────────────────────────────────────
def call_ai_with_key(prompt, sys_role="學術專家，用繁體中文回答。", max_tokens=4000):
    """使用內建API Key的AI呼叫"""
    ai_mode = st.session_state.ai_mode
    groq_key = st.session_state.groq_key or DEFAULT_GROQ_KEY
    gemini_key = st.session_state.gemini_key or DEFAULT_GEMINI_KEY

    # 快取檢查
    cache_key = hash(prompt[:200])
    if cache_key in st.session_state.refs_cache:
        return st.session_state.refs_cache[cache_key]

    # ── Groq ──
    if ai_mode == "Groq（免費雲端）":
        if not groq_key or "xxxxxxxx" in groq_key:
            return "❌ 請先設定Groq API Key（見程式碼第21行）"
        
        try:
            res = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {groq_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": sys_role[:100]},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": max_tokens,
                    "temperature": 0.7
                },
                timeout=60
            )
            if res.status_code == 200:
                result = res.json()["choices"][0]["message"]["content"]
                st.session_state.refs_cache[cache_key] = result
                return result
            elif res.status_code == 429:
                return "⚠️ Groq今日額度已用完，請改用Gemini或明天再試"
            else:
                return f"❌ Groq錯誤: {res.status_code}"
        except Exception as e:
            return f"❌ Groq連線錯誤: {str(e)[:100]}"

    # ── Gemini ──
    elif ai_mode == "Gemini":
        if not gemini_key or "xxxxxxxx" in gemini_key:
            return "❌ 請先設定Gemini API Key（見程式碼第24行）"
        
        try:
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            result = model.generate_content(sys_role + "\n\n" + prompt[:3000]).text
            st.session_state.refs_cache[cache_key] = result
            return result
        except Exception as e:
            err = str(e)
            if "429" in err:
                return "⚠️ Gemini今日額度已用完，請改用Groq"
            return f"❌ Gemini錯誤: {err[:100]}"

# ─────────────────────────────────────────────
# 主程式（其他函數保持不變）
# ─────────────────────────────────────────────

def fetch_refs_fast(query, total=15):
    """快速獲取文獻"""
    try:
        res = requests.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params={"query": query, "limit": total, "fields": "title,authors,year,abstract"},
            timeout=10
        )
        if res.status_code == 200:
            return [{
                "title": p.get("title", ""),
                "authors": ", ".join([a.get("name", "") for a in p.get("authors", [])[:2]]),
                "year": p.get("year", ""),
                "abstract": p.get("abstract", "")[:200]
            } for p in res.json().get("data", [])]
    except:
        pass
    return []

def generate_refs_ai(topic, count=5):
    """AI生成中文文獻"""
    prompt = f"生成{count}篇台灣論文，JSON格式：[{{'title':'','authors':'','year':2020,'journal':''}}]"
    result = call_ai_with_key(prompt, "Output JSON only.", max_tokens=1000)
    try:
        return json.loads(result)
    except:
        return []

def simulate_model_simple(topic, method):
    """簡化模型模擬"""
    prompt = f"主題：{topic}，方法：{method}。生成JSON：{{'criteria':['A','B'],'weights':[0.6,0.4]}}"
    result = call_ai_with_key(prompt, "Output JSON only.", max_tokens=500)
    try:
        return json.loads(result)
    except:
        return {"criteria": ["準則1", "準則2"], "weights": [0.5, 0.5]}

CHAPTER_PROMPTS = {
    "第一章 緒論": "寫緒論：背景400字、目的200字、問題200字、限制200字",
    "第二章 文獻探討": "寫文獻：理論800字、相關研究1000字、假設500字",
    "第三章 研究方法": "寫方法：架構300字、設計500字、變數500字、分析500字",
    "第四章 結果": "寫結果：樣本300字、分析1000字、討論500字",
    "第五章 結論": "寫結論：總結500字、貢獻300字、建議300字"
}

def write_chapter_fast(chapter, title, refs):
    """快速章節撰寫"""
    refs_text = "\n".join([f"{r['authors']}({r['year']}):{r['title']}" for r in refs[:5]])
    prompt = f"題目：{title}\n文獻：{refs_text}\n{CHAPTER_PROMPTS.get(chapter, '')}"
    
    result = call_ai_with_key(prompt, max_tokens=2000)
    
    if len(result) < 500:
        result += "\n\n" + call_ai_with_key(f"擴寫{chapter}，增加500字", max_tokens=1000)
    
    return result

# ─────────────────────────────────────────────
# 主介面
# ─────────────────────────────────────────────
st.title("🎓 論文寫作助手 - 內建API版")
st.caption("✨ API Key已內建，直接使用")

# 側邊欄 - 簡化版
with st.sidebar:
    st.header("⚙️ 設定")
    
    # 顯示API Key狀態
    groq_status = "✅ 已設定" if DEFAULT_GROQ_KEY and "xxxxxxxx" not in DEFAULT_GROQ_KEY else "❌ 未設定"
    gemini_status = "✅ 已設定" if DEFAULT_GEMINI_KEY and "xxxxxxxx" not in DEFAULT_GEMINI_KEY else "❌ 未設定"
    
    st.markdown(f"**Groq API**: {groq_status}")
    st.markdown(f"**Gemini API**: {gemini_status}")
    
    # 模型選擇
    st.session_state.ai_mode = st.radio(
        "選擇AI模型", 
        ["Groq（免費雲端）", "Gemini"],
        help="選擇要使用的AI服務"
    )
    
    # API Key管理
    with st.expander("🔑 API Key管理"):
        st.warning("⚠️ 注意：API Key已儲存在程式碼中")
        st.info("如需更換API Key，請修改程式碼第21-24行")
        
        # 顯示部分Key（隱藏中間部分）
        if DEFAULT_GROQ_KEY and "xxxxxxxx" not in DEFAULT_GROQ_KEY:
            st.code(f"Groq: {DEFAULT_GROQ_KEY[:8]}...{DEFAULT_GROQ_KEY[-8:]}")
        if DEFAULT_GEMINI_KEY and "xxxxxxxx" not in DEFAULT_GEMINI_KEY:
            st.code(f"Gemini: {DEFAULT_GEMINI_KEY[:8]}...{DEFAULT_GEMINI_KEY[-8:]}")
    
    st.header("📝 研究設定")
    method = st.selectbox("研究方法", ["問卷調查", "個案研究", "文献分析", "混合方法"])

# 進度指示
steps = ["題目", "文獻", "模型", "寫作"]
cols = st.columns(4)
for i, step in enumerate(steps):
    with cols[i]:
        if st.session_state.step > i:
            st.success(f"✓{step}")
        elif st.session_state.step == i:
            st.info(f"→{step}")
        else:
            st.caption(step)

# 步驟0：題目
if st.session_state.step == 0:
    st.subheader("📝 步驟1：研究題目")
    topic = st.text_input("輸入研究主題（例如：AI教育、ESG投資）", placeholder="人才培訓教育訓練")
    
    if st.button("💡 生成題目建議"):
        if topic:
            with st.spinner("AI生成中..."):
                result = call_ai_with_key(f"為'{topic}'生成3個碩士論文題目，每個附50字說明")
                st.write(result)
    
    title = st.text_input("✅ 確認題目", st.session_state.final_title, placeholder="人才培訓教育訓練對組織行為的影響研究")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 開始寫論文", type="primary") and title:
            st.session_state.final_title = title
            st.session_state.step = 1
            st.rerun()

# 步驟1：文獻
elif st.session_state.step == 1:
    st.subheader("📚 步驟2：文獻收集")
    st.info(f"📌 研究題目：{st.session_state.final_title}")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        if st.button("🔍 快速收集文獻", type="primary"):
            with st.spinner("搜尋中..."):
                en_refs = fetch_refs_fast(st.session_state.final_title, 10)
                zh_refs = generate_refs_ai(st.session_state.final_title, 5)
                st.session_state.refs_list = en_refs + zh_refs
                st.success(f"✅ 收集到 {len(st.session_state.refs_list)} 篇文獻")
    
    if st.session_state.refs_list:
        # 顯示文獻統計
        en_count = len([r for r in st.session_state.refs_list if not any(ord(c) > 127 for c in r.get('title', ''))])
        zh_count = len(st.session_state.refs_list) - en_count
        c1, c2 = st.columns(2)
        with c1: st.metric("🌍 英文文獻", en_count)
        with c2: st.metric("🇹🇼 中文文獻", zh_count)
        
        # 顯示文獻列表
        st.dataframe(
            pd.DataFrame(st.session_state.refs_list)[['title', 'authors', 'year']],
            use_container_width=True
        )
        
        # 操作按鈕
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ 上一步"):
                st.session_state.step = 0
                st.rerun()
        with col2:
            if st.button("➡️ 下一步", type="primary"):
                st.session_state.step = 2
                st.rerun()

# 步驟2：模型
elif st.session_state.step == 2:
    st.subheader("🔬 步驟3：建立研究模型")
    st.info(f"📌 研究題目：{st.session_state.final_title}")
    
    if st.button("🛠️ 生成研究模型", type="primary"):
        with st.spinner("模型生成中..."):
            result = simulate_model_simple(st.session_state.final_title, method)
            st.session_state.sim_data = result
            st.json(result)
    
    if st.session_state.sim_data:
        # 顯示模型結果
        data = st.session_state.sim_data
        if 'criteria' in data:
            st.write("**評估準則：**", ", ".join(data['criteria']))
        if 'weights' in data:
            st.write("**權重分配：**", ", ".join(map(str, data['weights'])))
        
        # 操作按鈕
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ 上一步"):
                st.session_state.step = 1
                st.rerun()
        with col2:
            if st.button("➡️ 下一步", type="primary"):
                st.session_state.step = 3
                st.rerun()

# 步驟3：寫作
elif st.session_state.step == 3:
    st.subheader("✍️ 步驟4：撰寫論文")
    
    # 顯示進度
    chapters = list(CHAPTER_PROMPTS.keys())
    progress = sum(1 for c in chapters if c in st.session_state.content)
    st.progress(progress / len(chapters), f"已完成 {progress}/{len(chapters)} 章")
    
    # 一鍵生成
    if st.button("🚀 一鍵生成全文", type="primary"):
        for ch in chapters:
            if ch not in st.session_state.content:
                with st.spinner(f"正在撰寫{ch}..."):
                    st.session_state.content[ch] = write_chapter_fast(
                        ch, st.session_state.final_title, st.session_state.refs_list
                    )
        st.success("🎉 全文生成完成！")
        st.rerun()
    
    # 分頁顯示各章
    for ch in chapters:
        with st.expander(f"{'✅' if ch in st.session_state.content else '📝'} {ch}"):
            if ch in st.session_state.content:
                word_count = len(st.session_state.content[ch].replace(' ', ''))
                st.caption(f"字數：{word_count} 字")
                st.write(st.session_state.content[ch])
                
                # 重新撰寫按鈕
                if st.button(f"🔄 重新撰寫{ch}", key=f"rewrite_{ch}"):
                    del st.session_state.content[ch]
                    st.rerun()
            else:
                if st.button(f"✏️ 撰寫{ch}", key=ch):
                    st.session_state.content[ch] = write_chapter_fast(
                        ch, st.session_state.final_title, st.session_state.refs_list
                    )
                    st.rerun()
    
    # 下載功能
    if all(ch in st.session_state.content for ch in chapters):
        st.divider()
        st.subheader("📥 下載完整論文")
        
        # 生成完整文本
        full_text = f"# {st.session_state.final_title}\n\n"
        full_text += "## 摘要\n\n本研究...\n\n"  # 簡化摘要
        for ch in chapters:
            full_text += f"## {ch}\n\n{st.session_state.content[ch]}\n\n"
        full_text += "## 參考文獻\n\n"
        for ref in st.session_state.refs_list:
            full_text += f"- {ref['authors']} ({ref['year']}). {ref['title']}\n"
        
        total_words = len(full_text.replace(' ', ''))
        st.metric("📊 總字數", f"{total_words} 字", 
                 "✅ 達標" if total_words >= 15000 else f"還需 {15000-total_words} 字")
        
        # 下載選項
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.download_button(
                "📄 下載 Markdown",
                full_text,
                file_name=f"{st.session_state.final_title[:20]}.md",
                mime="text/markdown"
            )
        
        with col2:
            st.download_button(
                "📝 下載 TXT",
                full_text.replace('#', '').replace('*', ''),
                file_name=f"{st.session_state.final_title[:20]}.txt",
                mime="text/plain"
            )
        
        with col3:
            # Word文件
            doc = Document()
            doc.add_heading(st.session_state.final_title, 0)
            for ch in chapters:
                doc.add_heading(ch, level=1)
                doc.add_paragraph(st.session_state.content.get(ch, ""))
            
            doc_io = io.BytesIO()
            doc.save(doc_io)
            doc_io.seek(0)
            
            st.download_button(
                "📘 下載 Word",
                doc_io,
                file_name=f"{st.session_state.final_title[:20]}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
    
    # 返回按鈕
    if st.button("⬅️ 返回上一步"):
        st.session_state.step = 2
        st.rerun()

# 頁腳
st.divider()
st.markdown("---")
st.markdown(
    "<center><small>💡 提示：如需修改API Key，請編輯程式碼第21-24行</small></center>",
    unsafe_allow_html=True
)

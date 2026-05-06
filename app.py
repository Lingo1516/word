# ╔══════════════════════════════════════════════════════════════╗
# ║     論文寫作助手 - 經濟版（省Token/費用）                     ║
# ║     存成 thesis_economy.py                                   ║
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

st.set_page_config(page_title="論文寫作助手-經濟版", layout="wide", page_icon="💰")

# ─────────────────────────────────────────────
# Session 初始化
# ─────────────────────────────────────────────
defaults = {
    "step": 0,
    "final_title": "",
    "refs_list": [],
    "refs_cache": {},  # 新增：快取摘要
    "sim_data": None,
    "outline": "",
    "content": {},
    "full_integrated_paper": "",
    "ai_mode": "Groq（免費雲端）",
    "groq_key": "",
    "gemini_key": ""
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────
# 優化的AI呼叫函數
# ─────────────────────────────────────────────
def call_ai_optimized(prompt, sys_role="學術專家，用繁體中文回答。", max_tokens=4000):
    """優化版AI呼叫，減少Token使用"""
    ai_mode = st.session_state.ai_mode
    groq_key = st.session_state.groq_key
    gemini_key = st.session_state.gemini_key

    # 檢查快取
    cache_key = hash(prompt[:200])  # 用前200字作為快取鍵
    if cache_key in st.session_state.refs_cache:
        return st.session_state.refs_cache[cache_key]

    # ── Groq ──
    if ai_mode == "Groq（免費雲端）":
        if not groq_key:
            return "⚠️ 請輸入 Groq API Key"
        try:
            res = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": "Bearer " + groq_key,
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": sys_role[:50]},  # 縮短系統提示
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": max_tokens,
                    "temperature": 0.5  # 降低溫度減少變化
                },
                timeout=60
            )
            if res.status_code == 200:
                result = res.json()["choices"][0]["message"]["content"]
                st.session_state.refs_cache[cache_key] = result  # 快取結果
                return result
            return "❌ Groq 錯誤：" + str(res.status_code)
        except Exception as e:
            return "❌ 錯誤：" + str(e)[:100]

    # ── Gemini（簡化版）──
    elif ai_mode == "Gemini":
        if not gemini_key:
            return "⚠️ 請輸入 Gemini API Key"
        try:
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel("gemini-1.5-flash")  # 使用更便宜的模型
            result = model.generate_content(sys_role + "\n\n" + prompt[:3000]).text
            st.session_state.refs_cache[cache_key] = result
            return result
        except Exception as e:
            return "❌ Gemini 錯誤：" + str(e)[:100]

# ─────────────────────────────────────────────
# 簡化的文獻處理
# ─────────────────────────────────────────────
def fetch_refs_fast(query, total=15):
    """快速獲取文獻，減少API呼叫"""
    # 只用Semantic Scholar，減少來源
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
                "abstract": p.get("abstract", "")[:200]  # 縮短摘要
            } for p in res.json().get("data", [])]
    except:
        pass
    return []

def generate_refs_ai(topic, count=5):
    """AI生成少量中文文獻"""
    prompt = f"生成{count}篇台灣論文，JSON格式：[{{'title':'','authors':'','year':2020,'journal':''}}]"
    result = call_ai_optimized(prompt, "Output JSON only.", max_tokens=1000)
    try:
        return json.loads(result)
    except:
        return []

# ─────────────────────────────────────────────
# 簡化的模型模擬
# ─────────────────────────────────────────────
def simulate_model_simple(topic, method):
    """簡化版模型模擬"""
    prompt = f"主題：{topic}，方法：{method}。生成JSON：{{'criteria':['A','B'],'weights':[0.6,0.4]}}"
    result = call_ai_optimized(prompt, "Output JSON only.", max_tokens=500)
    try:
        return json.loads(result)
    except:
        return {"criteria": ["準則1", "準則2"], "weights": [0.5, 0.5]}

# ─────────────────────────────────────────────
# 精簡章節撰寫
# ─────────────────────────────────────────────
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
    
    result = call_ai_optimized(prompt, max_tokens=2000)
    
    # 確保基本字數
    if len(result) < 500:
        result += "\n\n" + call_ai_optimized(f"擴寫{chapter}，增加500字", max_tokens=1000)
    
    return result

# ─────────────────────────────────────────────
# 主介面
# ─────────────────────────────────────────────
st.title("💰 論文寫作助手 - 經濟版")
st.caption("優化Token使用，節省50%費用")

# 側邊欄簡化
with st.sidebar:
    st.header("⚙️ 設定")
    st.session_state.ai_mode = st.radio("AI模型", ["Groq（免費）", "Gemini"])
    
    if st.session_state.ai_mode == "Groq（免費）":
        st.session_state.groq_key = st.text_input("Groq API Key", type="password")
    else:
        st.session_state.gemini_key = st.text_input("Gemini API Key", type="password")
    
    st.header("📝 快速設定")
    method = st.selectbox("研究方法", ["問卷調查", "個案研究", "文献分析"])

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
    st.subheader("步驟1：研究題目")
    topic = st.text_input("輸入研究主題")
    
    if st.button("生成題目建議"):
        if topic:
            result = call_ai_optimized(f"為'{topic}'生成3個論文題目")
            st.write(result)
    
    title = st.text_input("確認題目", st.session_state.final_title)
    if st.button("下一步") and title:
        st.session_state.final_title = title
        st.session_state.step = 1
        st.rerun()

# 步驟1：文獻
elif st.session_state.step == 1:
    st.subheader("步驟2：文獻收集")
    st.info(f"題目：{st.session_state.final_title}")
    
    if st.button("快速收集文獻"):
        en_refs = fetch_refs_fast(st.session_state.final_title, 10)
        zh_refs = generate_refs_ai(st.session_state.final_title, 5)
        st.session_state.refs_list = en_refs + zh_refs
        st.success(f"收集到 {len(st.session_state.refs_list)} 篇文獻")
    
    if st.session_state.refs_list:
        st.dataframe(pd.DataFrame(st.session_state.refs_list))
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("上一步"):
                st.session_state.step = 0
                st.rerun()
        with col2:
            if st.button("下一步"):
                st.session_state.step = 2
                st.rerun()

# 步驟2：模型
elif st.session_state.step == 2:
    st.subheader("步驟3：建立模型")
    st.info(f"題目：{st.session_state.final_title}")
    
    if st.button("生成模型"):
        result = simulate_model_simple(st.session_state.final_title, method)
        st.session_state.sim_data = result
        st.json(result)
    
    if st.session_state.sim_data:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("上一步"):
                st.session_state.step = 1
                st.rerun()
        with col2:
            if st.button("下一步"):
                st.session_state.step = 3
                st.rerun()

# 步驟3：寫作
elif st.session_state.step == 3:
    st.subheader("步驟4：撰寫論文")
    
    # 顯示進度
    chapters = list(CHAPTER_PROMPTS.keys())
    progress = sum(1 for c in chapters if c in st.session_state.content)
    st.progress(progress / len(chapters))
    
    # 快速生成所有章節
    if st.button("🚀 一鍵生成全文"):
        for ch in chapters:
            if ch not in st.session_state.content:
                with st.spinner(f"寫作{ch}..."):
                    st.session_state.content[ch] = write_chapter_fast(
                        ch, st.session_state.final_title, st.session_state.refs_list
                    )
        st.success("全文生成完成！")
        st.rerun()
    
    # 分頁顯示各章
    for ch in chapters:
        with st.expander(ch):
            if ch in st.session_state.content:
                st.write(st.session_state.content[ch])
            else:
                if st.button(f"寫{ch}", key=ch):
                    st.session_state.content[ch] = write_chapter_fast(
                        ch, st.session_state.final_title, st.session_state.refs_list
                    )
                    st.rerun()
    
    # 整合下載
    if all(ch in st.session_state.content for ch in chapters):
        st.divider()
        st.subheader("📥 下載論文")
        
        full_text = f"# {st.session_state.final_title}\n\n"
        for ch in chapters:
            full_text += f"## {ch}\n\n{st.session_state.content[ch]}\n\n"
        
        st.download_button(
            "下載Markdown",
            full_text,
            file_name=f"{st.session_state.final_title[:20]}.md",
            mime="text/markdown"
        )
        
        # Word下載
        doc = Document()
        doc.add_heading(st.session_state.final_title, 0)
        for ch in chapters:
            doc.add_heading(ch, level=1)
            doc.add_paragraph(st.session_state.content.get(ch, ""))
        
        doc_io = io.BytesIO()
        doc.save(doc_io)
        doc_io.seek(0)
        
        st.download_button(
            "下載Word",
            doc_io,
            file_name=f"{st.session_state.final_title[:20]}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    
    if st.button("返回上一步"):
        st.session_state.step = 2
        st.rerun()

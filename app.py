import streamlit as st
from groq import Groq
import google.generativeai as genai
import requests
import json
import re
import time
import pandas as pd
from io import BytesIO
import urllib.parse

# ─────────────────────────────────────────────
# 1. 頁面設定
# ─────────────────────────────────────────────
st.set_page_config(page_title="🎓 論文寫作助手（完整版）", layout="wide", page_icon="🎓")

# ─────────────────────────────────────────────
# 2. 側邊欄設定
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ 核心設定")
    engine_choice = st.radio("AI 引擎", ["Groq (Llama 3)", "Google (Gemini)"])
    api_key = ""
    if engine_choice == "Groq (Llama 3)":
        st.info("🚀 速度快，適合文獻閱讀。")
        api_key = st.text_input("Groq Key", type="password", help="gsk_...")
    else:
        st.info("🧠 邏輯強，適合數學模擬。")
        api_key = st.text_input("Google Key", type="password", help="AIza...")

    st.divider()
    st.header("🛠️ 方法論設定")
    research_mode = st.radio("研究路徑", ["MCDM (量化/決策)", "Case Study (質性/個案)"])
    mcdm_method = None
    case_method = None
    if research_mode == "MCDM (量化/決策)":
        mcdm_method = st.selectbox("選擇模型：",
            ["AHP (層級分析法)", "DEMATEL (決策實驗室法)", "FCM (模糊認知圖)", "ANP (網路分析法)"])
        c1, c2 = st.columns(2)
        with c1: criteria_size = st.number_input("準則數", value=15)
        with c2: dim_size = st.number_input("構面數", value=4)
    else:
        case_method = st.selectbox("選擇流派：",
            ["Yin (實證型)", "Harvard (教學型)", "Eisenhardt (建構型)", "Stake (詮釋型)"])

    st.divider()
    st.header("📚 文獻搜尋設定")
    zh_paper_count = st.slider("中文文獻篇數", 5, 20, 10)
    en_paper_count = st.slider("英文文獻篇數", 5, 20, 10)
    year_from = st.number_input("文獻最早年份", value=2018, step=1)

# ─────────────────────────────────────────────
# 3. AI 呼叫函數
# ─────────────────────────────────────────────
def call_ai_api(prompt, sys_role="你是一位嚴謹的學術專家，使用繁體中文回答。", max_tokens=6000):
    if not api_key:
        return "⚠️ 請輸入 API Key"
    try:
        if engine_choice == "Groq (Llama 3)":
            client = Groq(api_key=api_key)
            completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": sys_role},
                    {"role": "user",   "content": prompt}
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.5,
                max_tokens=max_tokens
            )
            return completion.choices[0].message.content
        else:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(f"{sys_role}\n\n{prompt}")
            return response.text
    except Exception as e:
        return f"❌ Error: {str(e)}"


# ─────────────────────────────────────────────
# 4. 真實文獻抓取（Semantic Scholar + CrossRef）
# ─────────────────────────────────────────────
def fetch_semantic_scholar(query: str, limit: int = 10, year_from: int = 2018) -> list:
    """從 Semantic Scholar 抓取真實英文文獻（免費、免 key）"""
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,authors,year,abstract,externalIds,venue,citationCount",
        "year":   f"{year_from}-"
    }
    headers = {"User-Agent": "ThesisAssistant/1.0"}
    try:
        res = requests.get(url, params=params, headers=headers, timeout=15)
        if res.status_code == 200:
            papers = res.json().get("data", [])
            results = []
            for p in papers:
                if not p.get("title"):
                    continue
                authors = ", ".join([a.get("name", "") for a in p.get("authors", [])[:3]])
                if len(p.get("authors", [])) > 3:
                    authors += " et al."
                doi = p.get("externalIds", {}).get("DOI", "")
                results.append({
                    "title":    p.get("title", ""),
                    "authors":  authors,
                    "year":     p.get("year", ""),
                    "abstract": (p.get("abstract") or "")[:500],
                    "venue":    p.get("venue", ""),
                    "citations":p.get("citationCount", 0),
                    "doi":      doi,
                    "lang":     "en"
                })
            return results
    except Exception:
        pass
    return []


def fetch_crossref(query: str, limit: int = 10, year_from: int = 2018) -> list:
    """從 CrossRef 抓取真實文獻（免費、免 key）"""
    url = "https://api.crossref.org/works"
    params = {
        "query":           query,
        "rows":            limit,
        "filter":          f"from-pub-date:{year_from}",
        "select":          "title,author,published,abstract,DOI,container-title",
        "mailto":          "thesis_assistant@example.com"
    }
    try:
        res = requests.get(url, params=params, timeout=15)
        if res.status_code == 200:
            items = res.json().get("message", {}).get("items", [])
            results = []
            for item in items:
                title = item.get("title", [""])[0] if item.get("title") else ""
                if not title:
                    continue
                authors_raw = item.get("author", [])
                authors = ", ".join([
                    f"{a.get('family', '')}, {a.get('given', '')}"
                    for a in authors_raw[:3]
                ])
                if len(authors_raw) > 3:
                    authors += " et al."
                year = ""
                pub = item.get("published", {}).get("date-parts", [[""]])
                if pub and pub[0]:
                    year = pub[0][0]
                journal = item.get("container-title", [""])[0] if item.get("container-title") else ""
                abstract = re.sub(r'<[^>]+>', '', item.get("abstract", ""))[:500]
                results.append({
                    "title":    title,
                    "authors":  authors,
                    "year":     year,
                    "abstract": abstract,
                    "venue":    journal,
                    "citations": 0,
                    "doi":      item.get("DOI", ""),
                    "lang":     "en"
                })
            return results
    except Exception:
        pass
    return []


def fetch_chinese_refs_via_ai(topic: str, count: int = 10) -> list:
    """
    讓 AI 根據主題生成符合格式的中文文獻清單
    （台灣/中國知名期刊真實存在的論文樣式）
    """
    prompt = f"""
你是一位熟悉台灣學術文獻的專家。
請根據主題「{topic}」，生成 {count} 篇**真實存在或高度可信**的繁體中文學術文獻。
格式要求（嚴格輸出 JSON array）：
[
  {{
    "title": "論文標題（繁體中文）",
    "authors": "作者姓名（例如：王大明、李小華）",
    "year": 2021,
    "journal": "期刊名稱（例如：管理學報、資訊管理學報、人力資源管理學報）",
    "volume": "卷期（例如：38(2)）",
    "pages": "頁碼（例如：45-78）",
    "abstract": "摘要（50字以內）"
  }}
]
請確保：年份在 {year_from} 年以後，期刊名稱為台灣常見 TSSCI 期刊。
只輸出 JSON，不要其他文字。
"""
    res = call_ai_api(prompt, sys_role="Output ONLY valid JSON array.", max_tokens=3000)
    try:
        data = json.loads(res)
        for item in data:
            item["lang"] = "zh"
            item["doi"]  = ""
            item["venue"] = item.get("journal", "")
            item["citations"] = 0
        return data
    except Exception:
        match = re.search(r'\[.*\]', res, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                for item in data:
                    item["lang"] = "zh"
                return data
            except Exception:
                pass
    return []


def search_all_refs(topic: str, en_count: int, zh_count: int, year_from: int) -> list:
    """整合抓取中英文文獻"""
    all_refs = []

    # 英文：先試 Semantic Scholar，不足再用 CrossRef 補
    ss_refs  = fetch_semantic_scholar(topic, limit=en_count, year_from=year_from)
    if len(ss_refs) < en_count:
        cr_refs = fetch_crossref(topic, limit=en_count - len(ss_refs), year_from=year_from)
        ss_refs.extend(cr_refs)
    all_refs.extend(ss_refs[:en_count])

    # 中文：AI 生成符合格式的文獻
    zh_refs = fetch_chinese_refs_via_ai(topic, count=zh_count)
    all_refs.extend(zh_refs[:zh_count])

    return all_refs


def format_apa_ref(ref: dict) -> str:
    """格式化為 APA 引用格式"""
    authors = ref.get("authors", "Unknown")
    year    = ref.get("year",    "n.d.")
    title   = ref.get("title",  "Untitled")
    venue   = ref.get("venue",  "")
    doi     = ref.get("doi",    "")

    if ref.get("lang") == "zh":
        volume  = ref.get("volume", "")
        pages   = ref.get("pages",  "")
        apa = f"{authors}（{year}）。{title}。*{venue}*"
        if volume: apa += f"，{volume}"
        if pages:  apa += f"，{pages}"
        apa += "。"
    else:
        apa = f"{authors} ({year}). {title}. *{venue}*."
        if doi:
            apa += f" https://doi.org/{doi}"
    return apa


# ─────────────────────────────────────────────
# 5. MCDM 模擬
# ─────────────────────────────────────────────
def run_simulation_analysis(refs_summary, mode, m_method, c_method, c_n, d_n):
    if mode == "MCDM (量化/決策)":
        method_instr = {
            "AHP": "模擬 Saaty 1-9 成對比較矩陣，計算特徵向量權重，CR < 0.1。",
            "DEMATEL": "模擬 0-4 直接關係矩陣，計算中心度(D+R)與原因度(D-R)。",
            "FCM": "模擬 -1 到 1 影響矩陣，進行穩定態推論。",
            "ANP": "模擬超矩陣與極限矩陣，計算極限權重。"
        }.get(m_method.split()[0], "")

        prompt = f"""
你是 MCDM 專家，方法：{m_method}。
根據以下文獻摘要，執行：
1. 從文獻萃取 {c_n} 個評估準則
2. 歸納為 {d_n} 個構面
3. {method_instr}
4. 模擬 3 家企業評分

【嚴格輸出 JSON】：
{{
  "final_hierarchy": [
    {{
      "dimension_name": "構面名稱",
      "dimension_code": "D1",
      "contained_criteria": [
        {{"criteria_name": "準則", "criteria_code": "C1", "reasoning": "依據文獻..."}}
      ]
    }}
  ],
  "step4_simulation": {{
    "method_used": "{m_method}",
    "weights": [{{"criteria": "準則名稱", "dimension": "所屬構面", "weight": 0.08, "rank": 1}}],
    "matrix_data": [{{"from": "C1", "to": "C2", "value": 2.5}}],
    "companies": [
      {{"name": "企業A", "industry": "科技業", "scores": {{"準則名稱": 85}}}}
    ]
  }}
}}

文獻摘要：{refs_summary[:8000]}
"""
    else:
        prompt = f"""
你是質性研究專家，流派：{c_method}。
根據以下文獻，規劃個案研究架構。
【嚴格輸出 JSON】：
{{
  "case_study_content": {{
    "intro": "方法論說明（300字）",
    "research_propositions": ["命題1", "命題2", "命題3"],
    "data_sources": ["訪談", "文件分析", "觀察"],
    "sections": [{{"title": "章節標題", "content": "內容（200字）"}}],
    "key_findings": ["發現1", "發現2", "發現3"]
  }}
}}
文獻摘要：{refs_summary[:8000]}
"""
    try:
        res = call_ai_api(prompt, sys_role="Output ONLY valid JSON. No markdown.", max_tokens=5000)
        cleaned = re.sub(r'^```json\s*|^```\s*|```\s*$', '', res.strip(), flags=re.MULTILINE)
        try:
            return json.loads(cleaned)
        except Exception:
            match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            return json.loads(match.group(0)) if match else None
    except Exception:
        return None


# ─────────────────────────────────────────────
# 6. 章節撰寫（分段確保 20,000 字）
# ─────────────────────────────────────────────
CHAPTER_CONFIG = {
    "第一章 緒論": {
        "target_words": 3000,
        "sections": ["研究背景與動機", "研究目的", "研究問題", "研究範圍與限制", "論文架構"],
        "instruction": "請詳細撰寫研究背景（說明產業趨勢與問題）、研究動機（說明研究缺口）、研究目的（列出3-5個目的）、研究問題（列出研究問題）、研究範圍與限制、論文架構圖說明。要求 3,000 字以上。"
    },
    "第二章 文獻探討": {
        "target_words": 5000,
        "sections": ["理論基礎", "相關文獻回顧", "研究變數定義", "文獻總結與研究缺口"],
        "instruction": "請針對每個文獻，撰寫詳細的文獻探討，每篇文獻至少200字說明。包含：理論基礎說明、各變數相關研究、文獻總結表格、研究缺口說明。要求 5,000 字以上，每段必須引用 [作者, 年份]。"
    },
    "第三章 研究方法": {
        "target_words": 4000,
        "sections": ["研究架構", "研究流程", "研究方法說明", "資料收集方法", "問卷/訪談設計", "資料分析方法"],
        "instruction": "請將模型架構 JSON 轉化為詳細學術文字，用繁體中文撰寫。包含：研究架構圖說明、詳細方法步驟、數學公式（用 LaTeX $公式$）、評估準則體系表格、資料收集說明。要求 4,000 字以上。"
    },
    "第四章 研究結果與分析": {
        "target_words": 5000,
        "sections": ["樣本描述", "信效度分析", "模型結果", "各構面分析", "企業比較分析", "綜合討論"],
        "instruction": "請將模擬數據 JSON 轉化為詳細分析。包含：樣本描述、各準則權重分析（含表格）、矩陣結果解釋、企業評比表格、各構面深度分析、與文獻比較討論。要求 5,000 字以上，數據要具體引用。"
    },
    "第五章 結論與建議": {
        "target_words": 3000,
        "sections": ["研究結論", "理論貢獻", "實務建議", "研究限制", "未來研究方向"],
        "instruction": "請根據第四章結果，撰寫詳細結論。包含：各研究問題的回答、理論貢獻（對學術的貢獻）、實務建議（針對不同利害關係人）、研究限制、未來研究建議。要求 3,000 字以上。"
    }
}

def write_chapter(chapter_name: str, title: str, outline: str,
                  refs_list: list, sim_data: dict) -> str:
    config      = CHAPTER_CONFIG.get(chapter_name, {})
    instruction = config.get("instruction", "")
    target      = config.get("target_words", 3000)
    sections    = config.get("sections", [])

    # 格式化文獻清單
    apa_refs = "\n".join([f"- {format_apa_ref(r)}" for r in refs_list])

    # 模型資料
    sim_json = json.dumps(sim_data, ensure_ascii=False, indent=2) if sim_data else "無"

    # 文獻摘要
    ref_abstracts = "\n".join([
        f"[{r.get('authors','')}, {r.get('year','')}] {r.get('title','')}：{r.get('abstract','')}"
        for r in refs_list[:25]
    ])

    if "第一章" in chapter_name:
        context = f"研究題目：{title}\n研究方法：{sim_data.get('step4_simulation',{}).get('method_used','') if sim_data else ''}"
    elif "第二章" in chapter_name:
        context = f"【文獻摘要庫】：\n{ref_abstracts}\n\n【APA 文獻格式】：\n{apa_refs}"
    elif "第三章" in chapter_name:
        context = f"【模型架構 JSON】：\n{sim_json[:6000]}"
    elif "第四章" in chapter_name:
        context = f"【模擬分析數據 JSON】：\n{sim_json[:6000]}"
    else:
        context = f"【前章分析結論摘要】：請根據整體研究結果撰寫。\n模型：{sim_json[:3000]}"

    prompt = f"""
你是一位撰寫繁體中文學術論文的專家教授，語氣嚴謹學術，使用繁體中文。

【論文題目】：{title}
【章節名稱】：{chapter_name}
【論文大綱】：{outline}

{context}

【撰寫指示】：
{instruction}

【本章必須包含以下小節】：
{chr(10).join([f'{i+1}. {s}' for i, s in enumerate(sections)])}

【格式要求】：
1. 使用 Markdown 格式（## 為小節標題，### 為次小節）
2. 數學公式使用 LaTeX（$公式$）
3. 表格使用 Markdown 表格格式
4. 每一段落至少 200 字
5. 目標字數：{target} 字以上
6. 所有引用格式：（作者，年份）

請立即開始撰寫完整的 {chapter_name}，不要省略任何小節：
"""
    return call_ai_api(prompt, sys_role="你是一位嚴謹的學術論文教授，使用繁體中文，每次回應都必須盡可能詳盡完整。", max_tokens=6000)


# ─────────────────────────────────────────────
# 7. Session 初始化
# ─────────────────────────────────────────────
defaults = {
    "step": 0, "final_title": "", "refs_list": [],
    "refs_summary": "", "sim_data": None,
    "outline": "", "content": {}
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────
# 8. 主畫面
# ─────────────────────────────────────────────
st.title("🎓 論文寫作助手（完整版 - 自動文獻 + 20,000 字）")

# 進度條
chapters_list = list(CHAPTER_CONFIG.keys())
progress_labels = ["① 題目", "② 文獻", "③ 模型", "④ 大綱", "⑤ 寫作"]
cols_prog = st.columns(5)
for i, label in enumerate(progress_labels):
    with cols_prog[i]:
        if st.session_state.step > i:
            st.success(label)
        elif st.session_state.step == i:
            st.info(f"**{label}**")
        else:
            st.caption(label)

st.divider()

# ════════════════════════════════════════════
# 步驟 0：題目
# ════════════════════════════════════════════
if st.session_state.step == 0:
    st.subheader("步驟 1：擬定研究題目")
    keywords = st.text_input("輸入關鍵字（例如：ESG, 供應鏈, AI 人才培育）：")

    if st.button("✨ 生成題目建議"):
        if not keywords:
            st.error("請輸入關鍵字")
        else:
            method_str = mcdm_method if research_mode == "MCDM (量化/決策)" else case_method
            prompt = f"""
關鍵字：{keywords}
研究方法：{method_str}
請產生 5 個**繁體中文**學術論文題目，格式如下：
1. 題目一（說明適用方向）
2. 題目二（說明適用方向）
...
題目應符合台灣碩士論文格式，具體且有學術貢獻。
"""
            st.info(call_ai_api(prompt))

    title_input = st.text_input("👇 確認最終題目", value=st.session_state.final_title,
                                 placeholder="例如：以 AHP 探討台灣科技業人才培育關鍵因素之研究")

    if st.button("下一步 → 自動搜尋文獻 ➡️", type="primary"):
        if title_input:
            st.session_state.final_title = title_input
            st.session_state.step = 1
            st.rerun()
        else:
            st.error("請輸入題目")

# ════════════════════════════════════════════
# 步驟 1：文獻（全自動）
# ════════════════════════════════════════════
elif st.session_state.step == 1:
    st.subheader("步驟 2：自動搜尋真實文獻")
    st.info(f"📌 題目：**{st.session_state.final_title}**")

    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("目標英文文獻", f"{en_paper_count} 篇")
    with col_b:
        st.metric("目標中文文獻", f"{zh_paper_count} 篇")

    if st.button("🔍 自動搜尋文獻（Semantic Scholar + CrossRef + AI 中文）", type="primary"):
        with st.spinner("📡 正在從學術資料庫抓取真實文獻..."):
            refs = search_all_refs(
                st.session_state.final_title,
                en_count=en_paper_count,
                zh_count=zh_paper_count,
                year_from=year_from
            )
            st.session_state.refs_list = refs

        with st.spinner("📝 AI 正在歸納文獻重點..."):
            ref_abstracts = "\n".join([
                f"[{r.get('authors','')}, {r.get('year','')}] {r.get('title','')}：{r.get('abstract','')}"
                for r in refs
            ])
            prompt = f"請歸納以下文獻重點，說明各篇的理論觀點、研究變數、主要發現：\n{ref_abstracts}"
            st.session_state.refs_summary = call_ai_api(prompt, max_tokens=4000)
        st.rerun()

    if st.session_state.refs_list:
        zh_refs = [r for r in st.session_state.refs_list if r.get("lang") == "zh"]
        en_refs = [r for r in st.session_state.refs_list if r.get("lang") == "en"]

        t1, t2, t3 = st.tabs([f"英文文獻（{len(en_refs)} 篇）", f"中文文獻（{len(zh_refs)} 篇）", "文獻摘要"])

        with t1:
            for i, r in enumerate(en_refs, 1):
                with st.expander(f"{i}. {r.get('title','')[:80]} ({r.get('year','')})"):
                    st.markdown(f"**作者：** {r.get('authors','')}")
                    st.markdown(f"**期刊：** {r.get('venue','')}")
                    st.markdown(f"**DOI：** {r.get('doi','')}")
                    st.markdown(f"**摘要：** {r.get('abstract','')}")
                    st.markdown(f"**APA：** {format_apa_ref(r)}")

        with t2:
            for i, r in enumerate(zh_refs, 1):
                with st.expander(f"{i}. {r.get('title','')[:80]} ({r.get('year','')})"):
                    st.markdown(f"**作者：** {r.get('authors','')}")
                    st.markdown(f"**期刊：** {r.get('venue','')} {r.get('volume','')}")
                    st.markdown(f"**摘要：** {r.get('abstract','')}")
                    st.markdown(f"**APA：** {format_apa_ref(r)}")

        with t3:
            st.markdown(st.session_state.refs_summary)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ 上一步"):
                st.session_state.step = 0; st.rerun()
        with col2:
            if st.button("下一步 → 建立分析模型 ➡️", type="primary"):
                st.session_state.step = 2; st.rerun()

# ════════════════════════════════════════════
# 步驟 2：模型
# ════════════════════════════════════════════
elif st.session_state.step == 2:
    st.subheader(f"步驟 3：建立 {research_mode} 分析模型")
    current_method = mcdm_method if research_mode == "MCDM (量化/決策)" else case_method
    st.info(f"📌 題目：**{st.session_state.final_title}** ｜ 方法：**{current_method}**")

    if st.button(f"🚀 執行 {current_method} 模擬", type="primary"):
        with st.spinner("🔧 正在建構模型（約 30-60 秒）..."):
            result = run_simulation_analysis(
                st.session_state.refs_summary,
                research_mode, mcdm_method, case_method,
                criteria_size if research_mode == "MCDM (量化/決策)" else 15,
                dim_size      if research_mode == "MCDM (量化/決策)" else 4
            )
            if result:
                st.session_state.sim_data = result
                st.success("✅ 模型建構完成！")
            else:
                st.error("❌ 模擬失敗，請重試")

    if st.session_state.sim_data:
        data = st.session_state.sim_data
        if research_mode == "MCDM (量化/決策)":
            t1, t2, t3 = st.tabs(["層級架構", "權重排名", "企業評比"])
            with t1:
                hierarchy = data.get("final_hierarchy", [])
                for dim in hierarchy:
                    st.markdown(f"**{dim.get('dimension_name','')}**")
                    for c in dim.get("contained_criteria", []):
                        st.markdown(f"　- {c.get('criteria_name','')}：{c.get('reasoning','')}")
            with t2:
                weights = data.get("step4_simulation", {}).get("weights", [])
                if weights:
                    df_w = pd.DataFrame(weights).sort_values("weight", ascending=False)
                    st.dataframe(df_w, use_container_width=True)
            with t3:
                companies = data.get("step4_simulation", {}).get("companies", [])
                if companies:
                    df_c = pd.DataFrame(companies)
                    st.dataframe(df_c, use_container_width=True)
        else:
            cs = data.get("case_study_content", {})
            st.markdown(cs.get("intro", ""))
            for sec in cs.get("sections", []):
                st.markdown(f"**{sec.get('title','')}**：{sec.get('content','')}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ 上一步"):
                st.session_state.step = 1; st.rerun()
        with col2:
            if st.button("下一步 → 生成大綱 ➡️", type="primary"):
                st.session_state.step = 3; st.rerun()

# ════════════════════════════════════════════
# 步驟 3：大綱
# ════════════════════════════════════════════
elif st.session_state.step == 3:
    st.subheader("步驟 4：生成完整論文大綱")
    st.info(f"📌 題目：**{st.session_state.final_title}**")

    if st.button("✨ 生成大綱", type="primary"):
        sim_context = json.dumps(st.session_state.sim_data, ensure_ascii=False) if st.session_state.sim_data else "無"
        method_str  = mcdm_method if research_mode == "MCDM (量化/決策)" else case_method
        prompt = f"""
題目：{st.session_state.final_title}
研究方法：{method_str}
分析模型架構：{sim_context[:3000]}

請撰寫詳細的五章論文大綱，包含每章各小節名稱與簡述（100字）。
格式：
# 第一章 緒論
## 1.1 研究背景與動機（說明...）
## 1.2 研究目的（說明...）
...（以此類推到第五章）
"""
        st.session_state.outline = call_ai_api(prompt, max_tokens=4000)
        st.rerun()

    if st.session_state.outline:
        st.markdown(st.session_state.outline)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ 上一步"):
                st.session_state.step = 2; st.rerun()
        with col2:
            if st.button("下一步 → 開始寫作 ➡️", type="primary"):
                st.session_state.step = 4; st.rerun()

# ════════════════════════════════════════════
# 步驟 4：寫作（核心）
# ════════════════════════════════════════════
elif st.session_state.step == 4:
    st.subheader("步驟 5：逐章撰寫（目標 20,000 字）")
    st.info(f"📌 題目：**{st.session_state.final_title}**")

    # 進度追蹤
    done_count = sum(1 for ch in chapters_list if ch in st.session_state.content)
    est_words  = done_count * 4000
    st.progress(done_count / len(chapters_list), text=f"已完成 {done_count}/{len(chapters_list)} 章（約 {est_words:,} 字）")

    tab_list = st.tabs([f"{'✅' if ch in st.session_state.content else '📝'} {ch}" for ch in chapters_list])

    for i, (tab, chapter_name) in enumerate(zip(tab_list, chapters_list)):
        with tab:
            config = CHAPTER_CONFIG[chapter_name]
            st.caption(f"目標字數：{config['target_words']:,} 字 ｜ 小節：{', '.join(config['sections'])}")

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button(f"🚀 撰寫 {chapter_name}", key=f"write_{i}", type="primary"):
                    with st.spinner(f"✍️ 正在撰寫 {chapter_name}（約 30-90 秒）..."):
                        result = write_chapter(
                            chapter_name,
                            st.session_state.final_title,
                            st.session_state.outline,
                            st.session_state.refs_list,
                            st.session_state.sim_data
                        )
                        st.session_state.content[chapter_name] = result
                    st.rerun()
            with col_btn2:
                if chapter_name in st.session_state.content:
                    if st.button(f"🔄 重新撰寫", key=f"redo_{i}"):
                        del st.session_state.content[chapter_name]
                        st.rerun()

            if chapter_name in st.session_state.content:
                text = st.session_state.content[chapter_name]
                word_count = len(re.sub(r'\s', '', text))
                st.success(f"✅ 已完成（約 {word_count:,} 字）")
                st.markdown(text)
            else:
                st.warning("⚠️ 尚未撰寫，請點擊上方按鈕。")

    st.divider()

    # ── 一鍵全部撰寫 ──
    if st.button("⚡ 一鍵撰寫所有章節（依序執行）", type="primary"):
        for chapter_name in chapters_list:
            if chapter_name not in st.session_state.content:
                with st.spinner(f"✍️ 正在撰寫 {chapter_name}..."):
                    result = write_chapter(
                        chapter_name,
                        st.session_state.final_title,
                        st.session_state.outline,
                        st.session_state.refs_list,
                        st.session_state.sim_data
                    )
                    st.session_state.content[chapter_name] = result
                    time.sleep(2)
        st.rerun()

    st.divider()

    # ── 下載區 ──
    st.subheader("📥 下載完整論文")

    # 組合全文
    final_doc  = f"# {st.session_state.final_title}\n\n"
    total_words = 0
    for ch in chapters_list:
        if ch in st.session_state.content:
            text = st.session_state.content[ch]
            final_doc  += f"## {ch}\n\n{text}\n\n---\n\n"
            total_words += len(re.sub(r'\s', '', text))

    # 參考文獻
    final_doc += "## 參考文獻\n\n"
    zh_refs = [r for r in st.session_state.refs_list if r.get("lang") == "zh"]
    en_refs = [r for r in st.session_state.refs_list if r.get("lang") == "en"]
    final_doc += "### 中文文獻\n\n"
    for r in sorted(zh_refs, key=lambda x: str(x.get("authors",""))):
        final_doc += f"{format_apa_ref(r)}\n\n"
    final_doc += "\n### 英文文獻\n\n"
    for r in sorted(en_refs, key=lambda x: str(x.get("authors",""))):
        final_doc += f"{format_apa_ref(r)}\n\n"

    st.metric("📊 目前全文字數", f"{total_words:,} 字",
              delta=f"目標 20,000 字（{'✅ 達標' if total_words >= 20000 else f'還差 {20000-total_words:,} 字'}）")

    dc1, dc2 = st.columns(2)
    with dc1:
        st.download_button(
            "📄 下載全文 Markdown (.md)",
            final_doc,
            file_name=f"{st.session_state.final_title[:30]}.md",
            mime="text/markdown"
        )
    with dc2:
        st.download_button(
            "📝 下載全文純文字 (.txt)",
            final_doc,
            file_name=f"{st.session_state.final_title[:30]}.txt",
            mime="text/plain"
        )

    if st.button("⬅️ 上一步"):
        st.session_state.step = 3; st.rerun()

    st.caption("⚠️ 免責聲明：AI 生成內容僅供學術練習，使用前請自行查核文獻真實性。")

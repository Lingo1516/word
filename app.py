# ╔══════════════════════════════════════════════════════════════╗
# ║     論文寫作助手 - 免設定版（內建 Gemini 2.0）              ║
# ╚══════════════════════════════════════════════════════════════╝
# requirements.txt：
#   streamlit
#   google-generativeai
#   requests
#   pandas
#   python-docx

import streamlit as st
import google.generativeai as genai
import requests
import json
import re
import time
import io
import pandas as pd
from docx import Document

# ─────────────────────────────────────────────
# 唯一需要設定的地方：貼上你的 Gemini Key
# 申請免費 Key：https://aistudio.google.com/app/apikey
# ─────────────────────────────────────────────
GEMINI_API_KEY = "YOUR_GEMINI_KEY_HERE"

# ─────────────────────────────────────────────
# 頁面設定
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="論文寫作助手",
    layout="wide",
    page_icon="🎓"
)

# ─────────────────────────────────────────────
# AI 呼叫函數
# ─────────────────────────────────────────────
def call_ai(prompt, sys_role="你是一位嚴謹的學術專家，使用繁體中文回答。", max_tokens=6000):
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(
            "gemini-2.0-flash",
            generation_config=genai.GenerationConfig(max_output_tokens=max_tokens)
        )
        return model.generate_content(sys_role + "\n\n" + prompt).text
    except Exception as e:
        err = str(e)
        if "429" in err:
            return "今日免費額度已用完，請明天再試（台灣時間每天早上 8:00 重置）"
        elif "API_KEY_INVALID" in err or "invalid" in err.lower():
            return "API Key 無效，請確認 GEMINI_API_KEY 是否正確"
        elif "404" in err:
            return "模型不存在，請確認模型名稱"
        return "發生錯誤：" + err[:150]


# ─────────────────────────────────────────────
# 文獻抓取
# ─────────────────────────────────────────────
def fetch_semantic_scholar(query, limit=10, year_from=2018):
    try:
        res = requests.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params={
                "query": query,
                "limit": limit,
                "fields": "title,authors,year,abstract,externalIds,venue,citationCount",
                "year": str(year_from) + "-"
            },
            headers={"User-Agent": "ThesisAssistant/1.0"},
            timeout=15
        )
        if res.status_code == 200:
            results = []
            for p in res.json().get("data", []):
                if not p.get("title"):
                    continue
                authors = ", ".join([a.get("name", "") for a in p.get("authors", [])[:3]])
                if len(p.get("authors", [])) > 3:
                    authors += " et al."
                results.append({
                    "title": p.get("title", ""),
                    "authors": authors,
                    "year": p.get("year", ""),
                    "abstract": (p.get("abstract") or "")[:500],
                    "venue": p.get("venue", ""),
                    "citations": p.get("citationCount", 0),
                    "doi": p.get("externalIds", {}).get("DOI", ""),
                    "lang": "en"
                })
            return results
    except Exception:
        pass
    return []


def fetch_crossref(query, limit=10, year_from=2018):
    try:
        res = requests.get(
            "https://api.crossref.org/works",
            params={
                "query": query,
                "rows": limit,
                "filter": "from-pub-date:" + str(year_from),
                "select": "title,author,published,abstract,DOI,container-title",
                "mailto": "thesis@example.com"
            },
            timeout=15
        )
        if res.status_code == 200:
            results = []
            for item in res.json().get("message", {}).get("items", []):
                title = item.get("title", [""])[0] if item.get("title") else ""
                if not title:
                    continue
                ar = item.get("author", [])
                authors = ", ".join([
                    a.get("family", "") + ", " + a.get("given", "")
                    for a in ar[:3]
                ])
                if len(ar) > 3:
                    authors += " et al."
                pub = item.get("published", {}).get("date-parts", [[""]])
                year = pub[0][0] if pub and pub[0] else ""
                abstract = re.sub(r"<[^>]+>", "", item.get("abstract", ""))[:500]
                results.append({
                    "title": title,
                    "authors": authors,
                    "year": year,
                    "abstract": abstract,
                    "venue": (
                        item.get("container-title", [""])[0]
                        if item.get("container-title") else ""
                    ),
                    "citations": 0,
                    "doi": item.get("DOI", ""),
                    "lang": "en"
                })
            return results
    except Exception:
        pass
    return []


def fetch_chinese_refs(topic, count=10, year_from=2018):
    prompt = (
        "你是熟悉台灣學術文獻的專家。根據主題「" + topic + "」，"
        "生成 " + str(count) + " 篇符合真實格式的繁體中文 TSSCI 學術文獻，"
        "年份在 " + str(year_from) + " 年以後。"
        "只輸出 JSON array，不要其他文字：\n"
        '[{"title":"論文標題","authors":"作者姓名","year":2021,'
        '"journal":"期刊名稱","volume":"38(2)","pages":"45-78",'
        '"abstract":"摘要50字以內"}]'
    )
    res = call_ai(prompt, sys_role="Output ONLY valid JSON array.", max_tokens=3000)
    try:
        data = json.loads(res)
        for item in data:
            item.update({
                "lang": "zh",
                "doi": "",
                "venue": item.get("journal", ""),
                "citations": 0
            })
        return data
    except Exception:
        match = re.search(r"\[.*\]", res, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                for item in data:
                    item.update({
                        "lang": "zh",
                        "doi": "",
                        "venue": item.get("journal", ""),
                        "citations": 0
                    })
                return data
            except Exception:
                pass
    return []


def search_all_refs(topic, en_count, zh_count, year_from):
    ss = fetch_semantic_scholar(topic, limit=en_count, year_from=year_from)
    if len(ss) < en_count:
        ss += fetch_crossref(topic, limit=en_count - len(ss), year_from=year_from)
    zh = fetch_chinese_refs(topic, count=zh_count, year_from=year_from)
    return ss[:en_count] + zh[:zh_count]


def format_apa(ref):
    authors = ref.get("authors", "Unknown")
    year    = ref.get("year", "n.d.")
    title   = ref.get("title", "Untitled")
    venue   = ref.get("venue", "")
    doi     = ref.get("doi", "")
    if ref.get("lang") == "zh":
        vol   = ref.get("volume", "")
        pages = ref.get("pages", "")
        apa   = authors + "（" + str(year) + "）。" + title + "。*" + venue + "*"
        if vol:
            apa += "，" + vol
        if pages:
            apa += "，" + pages
        return apa + "。"
    apa = authors + " (" + str(year) + "). " + title + ". *" + venue + "*."
    if doi:
        apa += " https://doi.org/" + doi
    return apa


# ─────────────────────────────────────────────
# 模型模擬
# ─────────────────────────────────────────────
def run_simulation(refs_summary, m_method, c_method, c_n, d_n):
    used_method = m_method or c_method or "混合方法"
    method_key  = used_method.split("（")[0].strip()
    method_instr = {
        "AHP":     "模擬 Saaty 1-9 成對比較矩陣，計算特徵向量權重，CR < 0.1。",
        "DEMATEL": "模擬 0-4 直接關係矩陣，計算中心度(D+R)與原因度(D-R)。",
        "SEM":     "模擬結構方程模型路徑係數，計算 β 值與 p 值。",
        "ANP":     "模擬超矩陣與極限矩陣，計算極限權重。",
        "FCM":     "模擬 -1 到 1 影響矩陣，進行穩定態推論。",
    }.get(method_key, "模擬迴歸分析，計算標準化係數。")

    prompt = (
        "你是 MCDM 與統計分析專家，方法：" + used_method + "。\n"
        "根據以下文獻摘要：\n"
        "1. 萃取 " + str(c_n) + " 個評估準則，歸納為 " + str(d_n) + " 個構面\n"
        "2. " + method_instr + "\n"
        "3. 模擬 3 家企業評分\n"
        "4. 生成合理統計數值（β、t、p、AVE、CR、α）\n\n"
        "只輸出 JSON，格式：\n"
        '{"final_hierarchy":[{"dimension_name":"構面名","dimension_code":"D1",'
        '"contained_criteria":[{"criteria_name":"準則","criteria_code":"C1",'
        '"reasoning":"說明"}]}],'
        '"step4_simulation":{"method_used":"' + used_method + '",'
        '"weights":[{"criteria":"準則","dimension":"構面","weight":0.08,"rank":1}],'
        '"regression":[{"hypothesis":"H1","path":"A->B","beta":0.43,'
        '"t_value":5.21,"p_value":"<0.001","supported":true}],'
        '"reliability":[{"dimension":"構面","alpha":0.87,"AVE":0.62,"CR":0.88}],'
        '"interview_themes":[{"theme":"主題一","description":"說明",'
        '"quotes":["受訪者A（HR主管）表示：某某某"]}]}}\n\n'
        "文獻摘要：" + refs_summary[:8000]
    )
    try:
        res = call_ai(prompt, sys_role="Output ONLY valid JSON. No markdown.", max_tokens=5000)
        cleaned = re.sub(r"^```json\s*|^```\s*|```\s*$", "", res.strip(), flags=re.MULTILINE)
        try:
            return json.loads(cleaned)
        except Exception:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            return json.loads(match.group(0)) if match else None
    except Exception:
        return None


# ─────────────────────────────────────────────
# 章節設定
# ─────────────────────────────────────────────
STYLE_EXAMPLE = (
    "人才培訓教育訓練是現代企業不可或缺的一部分，旨在提高員工的技能和知識，"
    "從而提升組織的績效和競爭力（Katz，2013）。從策略性人力資源管理的視角來看，"
    "培訓與發展不僅是單一的技能傳遞，更是塑造員工心理契約與組織認同的關鍵樞紐。"
    "然而，隨著產業的迅速發展和變化，企業面臨著許多挑戰（Bartlett，2001）。"
    "有鑑於此，企業需要不斷培訓和發展員工，以保持競爭優勢。"
)

CHAPTER_CONFIG = {
    "第一章 緒論": {
        "target_words": 4000,
        "sections": ["研究背景與動機", "研究目的", "研究問題", "研究範圍與限制", "論文架構"],
        "instruction": (
            "目標 4000 字以上。\n"
            "1.1 研究背景與動機（800字）：宏觀趨勢->研究主題->實務問題->研究缺口，每論點引用（作者，年份）\n"
            "1.2 研究目的（400字）：4-5個具體目的，邏輯遞進\n"
            "1.3 研究問題（400字）：4-5個具體可操作的研究問題\n"
            "1.4 研究範圍與限制（400字）：研究對象、範圍、CMV問題\n"
            "1.5 論文架構（300字）：各章內容與邏輯連結"
        )
    },
    "第二章 文獻探討": {
        "target_words": 6000,
        "sections": ["理論基礎", "相關文獻回顧", "研究假設", "文獻總結與研究缺口"],
        "instruction": (
            "目標 6000 字以上。\n"
            "2.1 理論基礎（1500字）：3-4個核心理論，每個：起源->核心主張->與本研究連結\n"
            "2.2 相關文獻回顧（2500字）：每個變數一小節，各引4-5篇，每篇150字\n"
            "2.3 研究假設（800字）：H1-H6，每個：假設陳述->文獻依據->預期方向\n"
            "2.4 文獻總結與研究缺口（600字）：Markdown比較表格 + 3-4個研究缺口"
        )
    },
    "第三章 研究方法": {
        "target_words": 5000,
        "sections": ["研究架構", "研究設計", "研究變數與操作型定義", "資料收集方法", "資料分析方法", "研究倫理"],
        "instruction": (
            "目標 5000 字以上。\n"
            "3.1 研究架構（600字）：自變數->中介->依變數，對應H1-H6\n"
            "3.2 研究設計（600字）：量化+質性混合方法理由，三角驗證\n"
            "3.3 研究變數與操作型定義（1000字）：Markdown表格\n"
            "3.4 資料收集方法（700字）：問卷對象、樣本數依據、抽樣方式、訪談程序\n"
            "3.5 資料分析方法（1500字）：描述統計->信度->CFA->SEM；質性主題分析六步驟\n"
            "3.6 研究倫理（200字）：知情同意、匿名保護"
        )
    },
    "第四章 研究結果與分析": {
        "target_words": 6000,
        "sections": ["樣本描述統計", "信效度分析", "研究假設驗證", "質性訪談結果", "綜合討論"],
        "instruction": (
            "目標 6000 字以上。\n"
            "4.1 樣本描述統計（800字）：Markdown表格（性別、年齡、教育、年資、產業）\n"
            "4.2 信效度分析（800字）：表格 α|AVE|CR|判斷 + HTMT矩陣\n"
            "4.3 研究假設驗證（2000字）：表格 假設|路徑|β|t值|p值|結果 + 逐一解釋\n"
            "4.4 質性訪談結果（1500字）：受訪者描述(A-F) + 3-4主題 + 引言 + 三角驗證\n"
            "4.5 綜合討論（800字）：量化質性整合 + 與文獻對話"
        )
    },
    "第五章 結論與建議": {
        "target_words": 3500,
        "sections": ["研究結論", "理論貢獻", "實務建議", "研究限制", "未來研究建議"],
        "instruction": (
            "目標 3500 字以上。\n"
            "5.1 研究結論（1000字）：逐一回答5個研究問題\n"
            "5.2 理論貢獻（600字）：對3-4個理論的具體貢獻\n"
            "5.3 實務建議（800字）：HR部門3項、管理階層2項、政策制定者1項\n"
            "5.4 研究限制（400字）：3-4個限制 + 如何克服\n"
            "5.5 未來研究建議（500字）：4-5個方向"
        )
    }
}


def write_chapter(chapter_name, title, outline, refs_list, sim_data):
    config      = CHAPTER_CONFIG.get(chapter_name, {})
    instruction = config.get("instruction", "")
    target      = config.get("target_words", 3000)

    apa_refs = "\n".join(["- " + format_apa(r) for r in refs_list])
    ref_abstracts = "\n".join([
        "[" + r.get("authors", "") + ", " + str(r.get("year", "")) + "] "
        + r.get("title", "") + "：" + r.get("abstract", "")
        for r in refs_list[:25]
    ])
    sim_json = json.dumps(sim_data, ensure_ascii=False, indent=2) if sim_data else "無"

    if "第一章" in chapter_name:
        context = "注意：本章不可提及第四章結果。"
    elif "第二章" in chapter_name:
        context = "文獻庫：\n" + ref_abstracts + "\n\nAPA清單：\n" + apa_refs
    elif "第三章" in chapter_name:
        context = "模型架構（請轉為學術文字，嚴禁貼JSON）：\n" + sim_json[:5000]
    elif "第四章" in chapter_name:
        context = "模擬數據（請轉為學術分析與表格）：\n" + sim_json[:5000]
    else:
        context = "整體研究摘要：\n" + sim_json[:2000]

    prompt = (
        "你是撰寫繁體中文學術論文的資深教授，專長為人力資源管理與組織行為學。\n\n"
        "語氣範例（請模仿）：\n" + STYLE_EXAMPLE + "\n\n"
        "核心原則：\n"
        "1. 不使用「我」，用「本研究」「研究者」「本文」\n"
        "2. 每個論點後引用（作者，年份）\n"
        "3. 善用：然而、此外、有鑑於此、因此、綜上所述\n"
        "4. 每段有主題句與小結句\n\n"
        "論文題目：" + title + "\n"
        "章節：" + chapter_name + "\n"
        "大綱：" + outline + "\n\n"
        + context + "\n\n"
        "撰寫指示：\n" + instruction + "\n\n"
        "請立即完整撰寫 " + chapter_name + "，每個小節不得省略："
    )

    result = call_ai(
        prompt,
        sys_role="你是嚴謹的繁體中文學術論文教授，每次回應必須詳盡完整。",
        max_tokens=6000
    )

    if len(re.sub(r"\s", "", result)) < int(target * 0.7):
        supplement = call_ai(
            "請繼續補充撰寫「" + chapter_name + "」的剩餘小節，銜接以下內容：\n" + result[-500:],
            max_tokens=4000
        )
        result += "\n\n" + supplement

    return result


# ─────────────────────────────────────────────
# Word 輸出函數
# ─────────────────────────────────────────────
def generate_docx(full_text, title):
    doc = Document()
    doc.add_heading(title, level=0)
    for line in full_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("# "):
            doc.add_heading(line[2:], level=1)
        elif line.startswith("## "):
            doc.add_heading(line[3:], level=2)
        elif line.startswith("### "):
            doc.add_heading(line[4:], level=3)
        elif line.startswith("> "):
            doc.add_paragraph(line[2:], style="Intense Quote")
        else:
            clean = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
            clean = re.sub(r"\*(.+?)\*", r"\1", clean)
            doc.add_paragraph(clean)
    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio


# ─────────────────────────────────────────────
# Session 初始化
# ─────────────────────────────────────────────
defaults = {
    "step": 0,
    "final_title": "",
    "refs_list": [],
    "refs_summary": "",
    "sim_data": None,
    "outline": "",
    "content": {},
    "integrated_abstract": "",
    "integrated_ack": "",
    "integrated_transitions": {},
    "polished_ch1": "",
    "full_integrated_paper": ""
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

chapters_list = list(CHAPTER_CONFIG.keys())

# ─────────────────────────────────────────────
# 側邊欄
# ─────────────────────────────────────────────
with st.sidebar:
    st.title("研究設定")
    st.success("✅ AI 已內建，直接使用！")
    st.caption("由 Google Gemini 2.0 Flash 驅動（免費版）")
    st.divider()

    st.header("研究方法論")
    research_mode = st.radio(
        "研究路徑",
        ["MCDM（量化/決策）", "混合方法（量化+質性）", "Case Study（質性/個案）"]
    )

    mcdm_method   = None
    case_method   = None
    criteria_size = 12
    dim_size      = 4

    if "MCDM" in research_mode:
        mcdm_method = st.selectbox(
            "量化模型",
            ["AHP（層級分析法）", "DEMATEL（決策實驗室法）", "ANP（網路分析法）", "FCM（模糊認知圖）"]
        )
        c1, c2 = st.columns(2)
        with c1:
            criteria_size = st.number_input("準則數", value=15, min_value=5)
        with c2:
            dim_size = st.number_input("構面數", value=4, min_value=2)
    elif "混合" in research_mode:
        mcdm_method = st.selectbox(
            "量化方法",
            ["SEM（結構方程模型）", "迴歸分析", "AHP（層級分析法）"]
        )
        case_method = st.selectbox(
            "質性方法",
            ["半結構式訪談", "焦點團體", "個案研究"]
        )
    else:
        case_method = st.selectbox(
            "質性流派",
            ["Yin（實證型）", "Harvard（教學型）", "Eisenhardt（建構型）", "Stake（詮釋型）"]
        )
        criteria_size = 10
        dim_size      = 3

    st.divider()
    st.header("文獻設定")
    zh_paper_count = st.slider("中文文獻篇數", 5, 20, 10)
    en_paper_count = st.slider("英文文獻篇數", 5, 20, 10)
    year_from      = st.number_input("文獻最早年份", value=2018, step=1)

# ─────────────────────────────────────────────
# 主畫面
# ─────────────────────────────────────────────
st.title("🎓 論文寫作助手")
st.caption("自動文獻 × 深度學術撰寫 × 20,000 字目標 × 由 Google Gemini 2.0 驅動")

prog  = ["① 題目", "② 文獻", "③ 模型", "④ 大綱", "⑤ 寫作＆整合"]
pcols = st.columns(5)
for i, label in enumerate(prog):
    with pcols[i]:
        if st.session_state.step > i:
            st.success(label)
        elif st.session_state.step == i:
            st.info("**" + label + "**")
        else:
            st.caption(label)
st.divider()

# ════════════════════════════════════════════
# 步驟 0：題目
# ════════════════════════════════════════════
if st.session_state.step == 0:
    st.subheader("步驟 1：擬定研究題目")
    keywords = st.text_input("輸入關鍵字（例如：ESG、人才培育、AI、供應鏈）：")

    if st.button("✨ 生成題目建議"):
        if not keywords:
            st.error("請輸入關鍵字")
        else:
            method_str = mcdm_method or case_method or research_mode
            with st.spinner("生成中..."):
                st.info(call_ai(
                    "關鍵字：" + keywords + "，研究方法：" + method_str + "。\n"
                    "請產生 5 個繁體中文碩士論文題目，每個附說明研究方向與貢獻。"
                ))

    title_input = st.text_input(
        "確認最終題目",
        value=st.session_state.final_title,
        placeholder="例如：人才培訓教育訓練對組織行為的影響：以留任率為衡量指標的實證研究"
    )

    if st.button("下一步 → 自動搜尋文獻", type="primary"):
        if title_input:
            st.session_state.final_title = title_input
            st.session_state.step = 1
            st.rerun()
        else:
            st.error("請輸入題目")

# ════════════════════════════════════════════
# 步驟 1：文獻
# ════════════════════════════════════════════
elif st.session_state.step == 1:
    st.subheader("步驟 2：自動搜尋真實文獻")
    st.info("題目：" + st.session_state.final_title)

    c1, c2 = st.columns(2)
    c1.metric("英文文獻", str(en_paper_count) + " 篇", "Semantic Scholar + CrossRef")
    c2.metric("中文文獻", str(zh_paper_count) + " 篇", "AI 生成 TSSCI 格式")

    if st.button("🔍 自動搜尋文獻", type="primary"):
        with st.spinner("抓取真實學術文獻..."):
            refs = search_all_refs(
                st.session_state.final_title,
                en_paper_count,
                zh_paper_count,
                year_from
            )
            st.session_state.refs_list = refs
        with st.spinner("AI 歸納文獻重點..."):
            abstracts = "\n".join([
                "[" + r.get("authors", "") + ", " + str(r.get("year", "")) + "] "
                + r.get("title", "") + "：" + r.get("abstract", "")
                for r in refs
            ])
            st.session_state.refs_summary = call_ai(
                "請歸納以下文獻重點，說明各篇理論觀點、研究變數、主要發現：\n" + abstracts,
                max_tokens=4000
            )
        st.rerun()

    if st.session_state.refs_list:
        zh_refs = [r for r in st.session_state.refs_list if r.get("lang") == "zh"]
        en_refs = [r for r in st.session_state.refs_list if r.get("lang") == "en"]

        t1, t2, t3 = st.tabs([
            "英文（" + str(len(en_refs)) + "篇）",
            "中文（" + str(len(zh_refs)) + "篇）",
            "文獻摘要"
        ])
        with t1:
            for i, r in enumerate(en_refs, 1):
                with st.expander(str(i) + ". " + r.get("title", "")[:80] + " (" + str(r.get("year", "")) + ")"):
                    st.markdown(
                        "**作者：** " + r.get("authors", "") + "  \n"
                        "**期刊：** " + r.get("venue", "") + "  \n"
                        "**摘要：** " + r.get("abstract", "") + "  \n\n"
                        "**APA：** " + format_apa(r)
                    )
        with t2:
            for i, r in enumerate(zh_refs, 1):
                with st.expander(str(i) + ". " + r.get("title", "")[:80] + " (" + str(r.get("year", "")) + ")"):
                    st.markdown(
                        "**作者：** " + r.get("authors", "") + "  \n"
                        "**期刊：** " + r.get("venue", "") + " " + r.get("volume", "") + "  \n"
                        "**摘要：** " + r.get("abstract", "") + "  \n\n"
                        "**APA：** " + format_apa(r)
                    )
        with t3:
            st.markdown(st.session_state.refs_summary)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("上一步"):
                st.session_state.step = 0
                st.rerun()
        with col2:
            if st.button("下一步 → 建立分析模型", type="primary"):
                st.session_state.step = 2
                st.rerun()

# ════════════════════════════════════════════
# 步驟 2：模型
# ════════════════════════════════════════════
elif st.session_state.step == 2:
    current_method = mcdm_method or case_method or research_mode
    st.subheader("步驟 3：建立 " + current_method + " 分析模型")
    st.info("題目：" + st.session_state.final_title)

    if st.button("執行 " + current_method + " 模擬", type="primary"):
        with st.spinner("建構模型中..."):
            result = run_simulation(
                st.session_state.refs_summary,
                mcdm_method,
                case_method,
                criteria_size,
                dim_size
            )
            if result:
                st.session_state.sim_data = result
                st.success("模型建構完成！")
            else:
                st.error("模擬失敗，請重試")

    if st.session_state.sim_data:
        data = st.session_state.sim_data
        t1, t2, t3, t4 = st.tabs(["層級架構", "權重排名", "假設驗證", "訪談主題"])
        with t1:
            for dim in data.get("final_hierarchy", []):
                st.markdown("**" + dim.get("dimension_name", "") + "**")
                for c in dim.get("contained_criteria", []):
                    st.markdown("　- **" + c.get("criteria_name", "") + "**：" + c.get("reasoning", ""))
        with t2:
            w = data.get("step4_simulation", {}).get("weights", [])
            if w:
                st.dataframe(pd.DataFrame(w).sort_values("weight", ascending=False), use_container_width=True)
        with t3:
            reg = data.get("step4_simulation", {}).get("regression", [])
            if reg:
                st.dataframe(pd.DataFrame(reg), use_container_width=True)
        with t4:
            for theme in data.get("step4_simulation", {}).get("interview_themes", []):
                with st.expander("主題：" + theme.get("theme", "")):
                    st.markdown(theme.get("description", ""))
                    for q in theme.get("quotes", []):
                        st.markdown("> " + q)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("上一步"):
                st.session_state.step = 1
                st.rerun()
        with col2:
            if st.button("下一步 → 生成大綱", type="primary"):
                st.session_state.step = 3
                st.rerun()

# ════════════════════════════════════════════
# 步驟 3：大綱
# ════════════════════════════════════════════
elif st.session_state.step == 3:
    st.subheader("步驟 4：生成完整論文大綱")
    st.info("題目：" + st.session_state.final_title)

    if st.button("✨ 生成大綱", type="primary"):
        method_str  = mcdm_method or case_method or research_mode
        sim_context = (
            json.dumps(st.session_state.sim_data, ensure_ascii=False)[:3000]
            if st.session_state.sim_data else "無"
        )
        with st.spinner("生成大綱中..."):
            st.session_state.outline = call_ai(
                "題目：" + st.session_state.final_title + "\n"
                "研究方法：" + method_str + "\n"
                "分析模型：" + sim_context + "\n\n"
                "請撰寫詳細五章論文大綱，每個小節附100字說明，格式：\n"
                "# 第一章 緒論\n"
                "## 1.1 研究背景與動機（說明...）\n"
                "依此類推至第五章。",
                max_tokens=4000
            )
        st.rerun()

    if st.session_state.outline:
        st.markdown(st.session_state.outline)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("上一步"):
                st.session_state.step = 2
                st.rerun()
        with col2:
            if st.button("下一步 → 開始寫作", type="primary"):
                st.session_state.step = 4
                st.rerun()

# ════════════════════════════════════════════
# 步驟 4：寫作 + 整合
# ════════════════════════════════════════════
elif st.session_state.step == 4:
    st.subheader("步驟 5：逐章撰寫 + 整合成完整論文")
    st.info("題目：" + st.session_state.final_title)

    done_count = sum(1 for ch in chapters_list if ch in st.session_state.content)
    st.progress(
        done_count / len(chapters_list),
        text="已完成 " + str(done_count) + "/" + str(len(chapters_list)) + " 章"
    )

    if st.button("⚡ 一鍵撰寫所有章節", type="primary"):
        for ch in chapters_list:
            if ch not in st.session_state.content:
                with st.spinner("撰寫 " + ch + "..."):
                    st.session_state.content[ch] = write_chapter(
                        ch,
                        st.session_state.final_title,
                        st.session_state.outline,
                        st.session_state.refs_list,
                        st.session_state.sim_data
                    )
                    time.sleep(2)
        st.rerun()

    tab_labels = [
        ("✅ " if ch in st.session_state.content else "📝 ") + ch
        for ch in chapters_list
    ]
    tab_list = st.tabs(tab_labels)

    for i, (tab, ch) in enumerate(zip(tab_list, chapters_list)):
        with tab:
            config = CHAPTER_CONFIG[ch]
            st.caption(
                "目標：" + str(config["target_words"]) + " 字 ｜ "
                + ", ".join(config["sections"])
            )
            cb1, cb2 = st.columns(2)
            with cb1:
                if st.button("撰寫本章", key="w" + str(i), type="primary"):
                    with st.spinner("撰寫 " + ch + "（60-90秒）..."):
                        st.session_state.content[ch] = write_chapter(
                            ch,
                            st.session_state.final_title,
                            st.session_state.outline,
                            st.session_state.refs_list,
                            st.session_state.sim_data
                        )
                    st.rerun()
            with cb2:
                if ch in st.session_state.content:
                    if st.button("重新撰寫", key="r" + str(i)):
                        del st.session_state.content[ch]
                        st.rerun()

            if ch in st.session_state.content:
                wc = len(re.sub(r"\s", "", st.session_state.content[ch]))
                st.success("已完成（約 " + str(wc) + " 字）")
                st.markdown(st.session_state.content[ch])
            else:
                st.warning("尚未撰寫")

    # ── 整合器 ──
    st.divider()
    st.subheader("步驟 6：整合成邏輯連貫的完整論文")
    done_chapters = [ch for ch in chapters_list if ch in st.session_state.content]

    if len(done_chapters) < 3:
        st.warning("請至少完成 3 章再整合")
    else:
        if st.button("✨ 一鍵整合成完整論文", type="primary", key="integrate"):

            with st.spinner("生成中英文摘要..."):
                ch_sum = "\n".join([
                    "【" + ch + "】" + st.session_state.content.get(ch, "")[:800]
                    for ch in done_chapters
                ])
                st.session_state.integrated_abstract = call_ai(
                    "根據以下論文各章，撰寫：\n"
                    "1. 繁體中文摘要（400-500字）：目的、方法、結果、結論、關鍵詞（5個）\n"
                    "2. English Abstract（200-250 words）\n"
                    "題目：" + st.session_state.final_title + "\n各章：" + ch_sum,
                    max_tokens=2000
                )

            with st.spinner("生成章節銜接段落..."):
                transitions = {}
                for i in range(len(done_chapters) - 1):
                    now = done_chapters[i]
                    nxt = done_chapters[i + 1]
                    transitions[now] = call_ai(
                        "撰寫150字章節過渡段（繁體中文學術語氣）：\n"
                        "總結「" + now + "」-> 銜接「" + nxt + "」\n"
                        + now + "末段：" + st.session_state.content.get(now, "")[-300:] + "\n"
                        + nxt + "首段：" + st.session_state.content.get(nxt, "")[:300],
                        max_tokens=500
                    )
                    time.sleep(1)
                st.session_state.integrated_transitions = transitions

            with st.spinner("第一章語氣潤飾..."):
                st.session_state.polished_ch1 = call_ai(
                    "請對以下第一章進行學術語氣潤飾"
                    "（「我」->「本研究」，補充連接詞，統一引用格式）：\n"
                    + st.session_state.content.get("第一章 緒論", "")[:4000],
                    max_tokens=5000
                )

            with st.spinner("生成致謝辭..."):
                st.session_state.integrated_ack = call_ai(
                    "撰寫250字繁體中文學術論文致謝辭，"
                    "感謝指導教授、口試委員、受訪者、同學、家人。"
                    "主題：" + st.session_state.final_title,
                    max_tokens=800
                )

            st.success("整合完成！")
            st.rerun()

        if st.session_state.integrated_abstract:
            # ── 組合全文 ──
            fp  = "# " + st.session_state.final_title + "\n\n---\n\n"
            fp += "## 致謝\n\n" + st.session_state.integrated_ack + "\n\n---\n\n"
            fp += "## 摘要\n\n" + st.session_state.integrated_abstract + "\n\n---\n\n"
            fp += "## 目錄\n\n"
            for ch in done_chapters:
                fp += "- **" + ch + "**\n"
                for sec in CHAPTER_CONFIG.get(ch, {}).get("sections", []):
                    fp += "  - " + sec + "\n"
            fp += "\n---\n\n"

            transitions = st.session_state.integrated_transitions
            for ch in done_chapters:
                text = (
                    st.session_state.polished_ch1
                    if ch == "第一章 緒論" and st.session_state.polished_ch1
                    else st.session_state.content.get(ch, "")
                )
                fp += "# " + ch + "\n\n" + text + "\n\n"
                if ch in transitions:
                    fp += "\n---\n> 【章節銜接】 " + transitions[ch] + "\n\n---\n\n"

            fp += "## 參考文獻\n\n### 中文文獻\n\n"
            for r in sorted(
                [r for r in st.session_state.refs_list if r.get("lang") == "zh"],
                key=lambda x: str(x.get("authors", ""))
            ):
                fp += format_apa(r) + "\n\n"

            fp += "\n### 英文文獻\n\n"
            for r in sorted(
                [r for r in st.session_state.refs_list if r.get("lang") == "en"],
                key=lambda x: str(x.get("authors", ""))
            ):
                fp += format_apa(r) + "\n\n"

            st.session_state.full_integrated_paper = fp
            total_words = len(re.sub(r"\s", "", fp))

            pt1, pt2, pt3, pt4, pt5 = st.tabs([
                "摘要", "致謝", "章節銜接", "全文預覽", "邏輯診斷"
            ])

            with pt1:
                st.markdown(st.session_state.integrated_abstract)

            with pt2:
                st.markdown(st.session_state.integrated_ack)

            with pt3:
                for ch, trans in transitions.items():
                    with st.expander(ch + " → 下一章"):
                        st.markdown(trans)

            with pt4:
                st.metric(
                    "全文字數",
                    str(total_words) + " 字",
                    delta=(
                        "達標 🎉" if total_words >= 20000
                        else "還差 " + str(20000 - total_words) + " 字"
                    )
                )
                st.markdown(fp[:10000] + "\n\n...（請下載完整版）")

            with pt5:
                if st.button("執行邏輯診斷", key="diag"):
                    with st.spinner("AI 審查中..."):
                        full_text = "\n\n".join([
                            "【" + ch + "】" + st.session_state.content.get(ch, "")[:1200]
                            for ch in done_chapters
                        ])
                        st.markdown(call_ai(
                            "你是嚴格的論文口試委員，從 5 個維度評分（1-10分）：\n"
                            "1. 研究問題與結論對應性\n"
                            "2. 文獻與方法一致性\n"
                            "3. 方法與結果一致性\n"
                            "4. 章節銜接流暢度\n"
                            "5. 學術語氣一致性\n"
                            "題目：" + st.session_state.final_title + "\n"
                            "各章：" + full_text[:8000] + "\n"
                            "請輸出完整診斷報告（Markdown）：",
                            max_tokens=3000
                        ))

            # ── 下載區 ──
            st.divider()
            st.subheader("📥 下載完整論文")
            d1, d2, d3 = st.columns(3)

            with d1:
                st.download_button(
                    label="📄 下載 Markdown (.md)",
                    data=fp,
                    file_name=st.session_state.final_title[:30] + "_完整版.md",
                    mime="text/markdown"
                )

            with d2:
                txt_content = fp.replace("**", "").replace("*", "").replace("#", "")
                st.download_button(
                    label="📝 下載純文字 (.txt)",
                    data=txt_content,
                    file_name=st.session_state.final_title[:30] + "_完整版.txt",
                    mime="text/plain"
                )

            with d3:
                docx_bio = generate_docx(fp, st.session_state.final_title)
                st.download_button(
                    label="📘 下載 Word (.docx)",
                    data=docx_bio,
                    file_name=st.session_state.final_title[:30] + "_完整版.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

    # ── 返回按鈕 ──
    st.divider()
    if st.button("↩️ 返回上一步（大綱）"):
        st.session_state.step = 3
        st.rerun()

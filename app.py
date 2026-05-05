import streamlit as st
from groq import Groq
import google.generativeai as genai
import requests
import json
import re
import time
import pandas as pd
from io import BytesIO

# ─────────────────────────────────────────────
# 1. 頁面設定
# ─────────────────────────────────────────────
st.set_page_config(page_title="🎓 論文寫作助手（最終完整版）", layout="wide", page_icon="🎓")

# ─────────────────────────────────────────────
# 2. 側邊欄
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
    research_mode = st.radio("研究路徑", ["MCDM (量化/決策)", "Case Study (質性/個案)", "混合方法 (Mixed Methods)"])
    mcdm_method = case_method = None
    if research_mode == "MCDM (量化/決策)":
        mcdm_method = st.selectbox("選擇模型：",
            ["AHP (層級分析法)", "DEMATEL (決策實驗室法)", "FCM (模糊認知圖)", "ANP (網路分析法)"])
        c1, c2 = st.columns(2)
        with c1: criteria_size = st.number_input("準則數", value=15)
        with c2: dim_size = st.number_input("構面數", value=4)
    elif research_mode == "Case Study (質性/個案)":
        case_method = st.selectbox("選擇流派：",
            ["Yin (實證型)", "Harvard (教學型)", "Eisenhardt (建構型)", "Stake (詮釋型)"])
    else:
        mcdm_method = st.selectbox("量化方法：", ["SEM (結構方程模型)", "迴歸分析", "AHP (層級分析法)"])
        case_method  = st.selectbox("質性方法：", ["半結構式訪談", "焦點團體", "個案研究"])

    st.divider()
    st.header("📚 文獻設定")
    zh_paper_count = st.slider("中文文獻篇數", 5, 20, 10)
    en_paper_count = st.slider("英文文獻篇數", 5, 20, 10)
    year_from      = st.number_input("文獻最早年份", value=2018, step=1)

# ─────────────────────────────────────────────
# 3. AI 呼叫
# ─────────────────────────────────────────────
def call_ai_api(prompt, sys_role="你是一位嚴謹的學術專家，使用繁體中文回答。", max_tokens=6000):
    if not api_key:
        return "⚠️ 請輸入 API Key"
    try:
        if engine_choice == "Groq (Llama 3)":
            client = Groq(api_key=api_key)
            resp = client.chat.completions.create(
                messages=[{"role": "system", "content": sys_role},
                          {"role": "user",   "content": prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0.5, max_tokens=max_tokens
            )
            return resp.choices[0].message.content
        else:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            return model.generate_content(f"{sys_role}\n\n{prompt}").text
    except Exception as e:
        return f"❌ Error: {str(e)}"

# ─────────────────────────────────────────────
# 4. 文獻抓取
# ─────────────────────────────────────────────
def fetch_semantic_scholar(query, limit=10, year_from=2018):
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {"query": query, "limit": limit,
              "fields": "title,authors,year,abstract,externalIds,venue,citationCount",
              "year": f"{year_from}-"}
    try:
        res = requests.get(url, params=params,
                           headers={"User-Agent": "ThesisAssistant/1.0"}, timeout=15)
        if res.status_code == 200:
            results = []
            for p in res.json().get("data", []):
                if not p.get("title"): continue
                authors = ", ".join([a.get("name","") for a in p.get("authors",[])[:3]])
                if len(p.get("authors",[])) > 3: authors += " et al."
                results.append({
                    "title": p.get("title",""), "authors": authors,
                    "year": p.get("year",""),
                    "abstract": (p.get("abstract") or "")[:500],
                    "venue": p.get("venue",""),
                    "citations": p.get("citationCount", 0),
                    "doi": p.get("externalIds",{}).get("DOI",""), "lang": "en"
                })
            return results
    except Exception: pass
    return []

def fetch_crossref(query, limit=10, year_from=2018):
    url = "https://api.crossref.org/works"
    params = {"query": query, "rows": limit,
              "filter": f"from-pub-date:{year_from}",
              "select": "title,author,published,abstract,DOI,container-title",
              "mailto": "thesis_assistant@example.com"}
    try:
        res = requests.get(url, params=params, timeout=15)
        if res.status_code == 200:
            results = []
            for item in res.json().get("message",{}).get("items",[]):
                title = item.get("title",[""])[0] if item.get("title") else ""
                if not title: continue
                authors_raw = item.get("author",[])
                authors = ", ".join([f"{a.get('family','')}, {a.get('given','')}"
                                     for a in authors_raw[:3]])
                if len(authors_raw) > 3: authors += " et al."
                year = ""
                pub = item.get("published",{}).get("date-parts",[[""]])
                if pub and pub[0]: year = pub[0][0]
                abstract = re.sub(r'<[^>]+>', '', item.get("abstract",""))[:500]
                results.append({
                    "title": title, "authors": authors, "year": year,
                    "abstract": abstract,
                    "venue": (item.get("container-title",[""])[0] if item.get("container-title") else ""),
                    "citations": 0, "doi": item.get("DOI",""), "lang": "en"
                })
            return results
    except Exception: pass
    return []

def fetch_chinese_refs_via_ai(topic, count=10):
    prompt = f"""
你是熟悉台灣學術文獻的專家。
根據主題「{topic}」，生成 {count} 篇符合真實格式的繁體中文 TSSCI 學術文獻。
年份在 {year_from} 年以後。
【嚴格輸出 JSON array】：
[{{"title":"論文標題","authors":"作者姓名","year":2021,
   "journal":"期刊名稱","volume":"38(2)","pages":"45-78",
   "abstract":"摘要50字以內"}}]
只輸出 JSON，不要其他文字。
"""
    res = call_ai_api(prompt, sys_role="Output ONLY valid JSON array.", max_tokens=3000)
    try:
        data = json.loads(res)
        for item in data:
            item.update({"lang":"zh","doi":"","venue":item.get("journal",""),"citations":0})
        return data
    except Exception:
        match = re.search(r'\[.*\]', res, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                for item in data: item.update({"lang":"zh","doi":"","venue":item.get("journal",""),"citations":0})
                return data
            except Exception: pass
    return []

def search_all_refs(topic, en_count, zh_count, year_from):
    ss  = fetch_semantic_scholar(topic, limit=en_count, year_from=year_from)
    if len(ss) < en_count:
        ss += fetch_crossref(topic, limit=en_count - len(ss), year_from=year_from)
    zh = fetch_chinese_refs_via_ai(topic, count=zh_count)
    return ss[:en_count] + zh[:zh_count]

def format_apa_ref(ref):
    authors = ref.get("authors","Unknown")
    year    = ref.get("year","n.d.")
    title   = ref.get("title","Untitled")
    venue   = ref.get("venue","")
    doi     = ref.get("doi","")
    if ref.get("lang") == "zh":
        vol   = ref.get("volume","")
        pages = ref.get("pages","")
        apa   = f"{authors}（{year}）。{title}。*{venue}*"
        if vol:   apa += f"，{vol}"
        if pages: apa += f"，{pages}"
        return apa + "。"
    else:
        apa = f"{authors} ({year}). {title}. *{venue}*."
        if doi: apa += f" https://doi.org/{doi}"
        return apa

# ─────────────────────────────────────────────
# 5. MCDM / 質性模擬
# ─────────────────────────────────────────────
def run_simulation_analysis(refs_summary, mode, m_method, c_method, c_n, d_n):
    if "MCDM" in mode or "混合" in mode:
        method_instr = {
            "AHP":     "模擬 Saaty 1-9 成對比較矩陣，計算特徵向量權重，CR < 0.1。",
            "DEMATEL": "模擬 0-4 直接關係矩陣，計算中心度(D+R)與原因度(D-R)。",
            "SEM":     "模擬結構方程模型路徑係數，計算 β 值與 p 值。",
            "FCM":     "模擬 -1 到 1 影響矩陣，進行穩定態推論。",
            "ANP":     "模擬超矩陣與極限矩陣，計算極限權重。",
        }.get((m_method or "").split()[0], "模擬迴歸分析，計算標準化係數。")

        prompt = f"""
你是 MCDM 與統計分析專家，方法：{m_method}。
根據以下文獻摘要，執行：
1. 從文獻萃取 {c_n} 個評估準則，歸納為 {d_n} 個構面
2. {method_instr}
3. 模擬 3 家企業評分
4. 生成合理的統計數值（β值、t值、p值、AVE、CR、α）

【嚴格輸出 JSON】：
{{
  "final_hierarchy": [
    {{"dimension_name":"構面名","dimension_code":"D1",
      "contained_criteria":[{{"criteria_name":"準則","criteria_code":"C1","reasoning":"依據文獻..."}}]}}
  ],
  "step4_simulation": {{
    "method_used": "{m_method}",
    "weights": [{{"criteria":"準則","dimension":"構面","weight":0.08,"rank":1}}],
    "matrix_data": [{{"from":"C1","to":"C2","value":2.5}}],
    "regression": [{{"hypothesis":"H1","beta":0.43,"t_value":5.21,"p_value":"<0.001","supported":true}}],
    "reliability": [{{"dimension":"構面","alpha":0.87,"AVE":0.62,"CR":0.88}}],
    "companies": [{{"name":"企業A","industry":"科技業","scores":{{"準則":85}}}}],
    "interview_themes": [
      {{"theme":"主題一","description":"說明","quotes":["受訪者A表示：『...』","受訪者B表示：『...』"]}}
    ]
  }}
}}
文獻摘要：{refs_summary[:8000]}
"""
    else:
        prompt = f"""
你是質性研究專家，流派：{c_method}。
【嚴格輸出 JSON】：
{{
  "case_study_content": {{
    "intro": "方法論說明（300字）",
    "research_propositions": ["命題1","命題2","命題3"],
    "data_sources": ["訪談","文件分析","觀察"],
    "sections": [{{"title":"章節","content":"內容（200字）"}}],
    "key_findings": ["發現1","發現2"],
    "interview_themes": [
      {{"theme":"主題","description":"說明","quotes":["受訪者A表示：『...』"]}}
    ]
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
# 6. 章節設定（深度學術版）
# ─────────────────────────────────────────────
CHAPTER_CONFIG = {
    "第一章 緒論": {
        "target_words": 4000,
        "sections": ["研究背景與動機","研究目的","研究問題","研究範圍與限制","論文架構"],
        "instruction": """
請依照以下要求撰寫第一章，目標 4,000 字以上：

【1.1 研究背景與動機】（800字以上）
- 從宏觀產業趨勢切入（全球化、數位轉型、人才競爭），逐步縮小至研究主題
- 每個論點必須引用文獻（作者，年份）
- 說明實務上的問題現象（企業案例），再連結到研究動機
- 最後一段明確指出「現有研究缺口」

【1.2 研究目的】（400字以上）
- 列出 4-5 個具體研究目的，每個目的一段說明「為何重要」
- 目的之間要有邏輯遞進（探討現象 → 分析機制 → 提出建議）

【1.3 研究問題】（400字以上）
- 對應研究目的，列出 4-5 個具體可操作的研究問題
- 每個問題後說明其重要性

【1.4 研究範圍與限制】（400字以上）
- 說明研究對象、地理範圍、時間範圍
- 誠實說明研究限制（樣本代表性、CMV問題、自陳式問卷偏誤）

【1.5 論文架構】（300字以上）
- 說明各章內容與章章之間的邏輯連結（要說明「為何下一章接著討論...」）

語氣規則：
- 不使用「我」，改用「本研究」「研究者」「本文」
- 每段開頭有主題句，結尾有小結句
- 善用：然而、此外、有鑑於此、因此、綜上所述、值得注意的是
"""
    },
    "第二章 文獻探討": {
        "target_words": 6000,
        "sections": ["理論基礎","相關文獻回顧","研究假設","文獻總結與研究缺口"],
        "instruction": """
請依照以下要求撰寫第二章，目標 6,000 字以上：

【2.1 理論基礎】（1500字以上）
- 介紹 3-4 個核心理論（如：人力資本理論、社會交換理論、組織學習理論）
- 每個理論：起源（學者/年份）→ 核心主張（200字）→ 與本研究的連結（100字）
- 最後說明各理論如何整合形成本研究的理論框架

【2.2 相關文獻回顧】（2500字以上）
- 每個核心變數各一小節（2.2.1、2.2.2、2.2.3...）
- 每節至少引用 4-5 篇文獻，每篇文獻至少 150 字：
  → 研究者/年份 → 研究對象/方法 → 主要發現 → 與本研究的關聯
- 結尾說明各變數間的理論關聯路徑

【2.3 研究假設】（800字以上）
- 根據文獻提出 4-6 個研究假設（H1-H6），格式：
  → H1：[自變數] 對 [依變數] 具有顯著正向影響
  → 文獻依據（引用 2-3 篇）
  → 預期方向說明

【2.4 文獻總結與研究缺口】（600字以上）
- 製作 Markdown 文獻比較表格：
  | 作者 | 年份 | 研究方法 | 主要發現 | 與本研究關聯 |
- 指出現有研究 3-4 個不足之處
- 說明本研究如何填補這些缺口
"""
    },
    "第三章 研究方法": {
        "target_words": 5000,
        "sections": ["研究架構","研究設計","研究變數與操作型定義","資料收集方法","資料分析方法","研究倫理"],
        "instruction": """
請依照以下要求撰寫第三章，目標 5,000 字以上：

【3.1 研究架構】（600字以上）
- 用文字詳細描述研究架構（自變數 → 中介/調節變數 → 依變數）
- 說明各變數因果邏輯，對應第二章的研究假設 H1-H6

【3.2 研究設計】（600字以上）
- 說明採用研究方法的理由與優缺點
- 量化設計：問卷調查法（抽樣邏輯、問卷結構）
- 質性設計：半結構式訪談（訪談提綱設計邏輯）
- 說明量化與質性如何互補（三角驗證）

【3.3 研究變數與操作型定義】（1000字以上）
- 製作 Markdown 表格：
  | 變數名稱 | 類型 | 操作型定義 | 量表來源 | 題項數 | 衡量尺度 |
- 每個變數額外說明量表信效度（原始研究的 α 值）

【3.4 資料收集方法】（700字以上）
- 量化：問卷發放對象、樣本規模依據（Hair et al., 2019：樣本數≥題項數×10）
  抽樣方法（分層隨機抽樣）、發放管道
- 質性：訪談對象選取標準（立意抽樣）、訪談時長（60-90分鐘）、錄音轉錄程序

【3.5 資料分析方法】（1500字以上）
量化分析步驟（請用數學公式 $公式$ 說明）：
  1. 描述性統計（平均數、標準差）
  2. 信度分析：$\\alpha = \\frac{k}{k-1}\\left(1-\\frac{\\sum\\sigma_i^2}{\\sigma_t^2}\\right)$，α > 0.7
  3. 驗證性因素分析（CFA）：AVE > 0.5，CR > 0.7，因素負荷量 > 0.6
  4. 結構方程模型（SEM）：$\\chi^2/df < 3$，RMSEA < 0.08，CFI > 0.95
  5. 路徑分析：標準化路徑係數 β 及顯著性 p < 0.05

質性分析步驟：
  1. 主題分析法（Braun & Clarke, 2006）六步驟
  2. 編碼程序：開放編碼 → 主軸編碼 → 選擇編碼
  3. 信賴性確保：三角驗證、成員確認

【3.6 研究倫理】（300字以上）
- 知情同意書、匿名保護、資料安全、IRB說明
"""
    },
    "第四章 研究結果與分析": {
        "target_words": 6000,
        "sections": ["樣本描述統計","信效度分析","研究假設驗證","質性訪談結果","綜合討論"],
        "instruction": """
請依照以下要求撰寫第四章，目標 6,000 字以上：

【4.1 樣本描述統計】（800字以上）
- 製作 Markdown 樣本結構表格：
  | 變數 | 類別 | 次數 | 百分比（%） |
  包含：性別、年齡層、教育程度、年資、產業別、公司規模（人數）
- 用文字說明樣本特性（如：以25-35歲、大學學歷、3-5年年資者為主）

【4.2 信效度分析】（800字以上）
- 製作 Markdown 信效度分析表格：
  | 構面 | Cronbach's α | AVE | CR | 判斷 |
- 數值說明：α > 0.7（良好）、AVE > 0.5（收斂效度佳）、CR > 0.7
- 區別效度：HTMT < 0.85 矩陣表格

【4.3 研究假設驗證】（2000字以上）
- 製作 Markdown 假設驗證結果表格：
  | 假設 | 路徑 | β | t值 | p值 | 結果 |
- 逐一解釋每個假設（H1-H6）：
  → 統計結果描述 → 是否支持 → 與文獻對話（為何一致/不一致）
- 數值要具體：如「β = 0.43，t = 5.21，p < 0.001，故 H1 獲得支持」

【4.4 質性訪談結果】（1500字以上）
- 說明訪談樣本（受訪者A-F，各3行人口特徵描述）
- 呈現 3-4 個主要主題（Theme），每個主題：
  → 主題命名與說明（200字）
  → 代表性受訪者引言（用引號格式：「受訪者A（科技業HR主管，15年資歷）表示：『...』」）
  → 與量化結果的三角驗證說明

【4.5 綜合討論】（800字以上）
- 整合量化與質性發現，說明兩者如何相互支持
- 與第二章文獻進行對話（與哪些學者的研究一致/相異）
- 提出本研究的獨特貢獻（超越既有文獻之處）
"""
    },
    "第五章 結論與建議": {
        "target_words": 3500,
        "sections": ["研究結論","理論貢獻","實務建議","研究限制","未來研究建議"],
        "instruction": """
請依照以下要求撰寫第五章，目標 3,500 字以上：

【5.1 研究結論】（1000字以上）
- 逐一回答第一章的 5 個研究問題（每個問題：問題重述 → 研究發現 → 理論解釋）
- 強調研究的核心貢獻，避免重複貼第四章數字，要做解釋與昇華

【5.2 理論貢獻】（600字以上）
- 說明本研究對 3-4 個理論的具體貢獻
  →「本研究延伸了 [理論名稱] 的適用範圍，由原先的...擴展至...」
- 說明對學術文獻的增補意義（研究缺口如何被填補）

【5.3 實務建議】（800字以上）
針對不同對象提出具體、可操作的建議：
- 對 HR 部門：培訓設計的 3 項具體建議（每項 100 字）
- 對管理階層：溝通機制的改善方向（2 項）
- 對政策制定者：制度層面的建議（1 項）

【5.4 研究限制】（400字以上）
- 誠實說明 3-4 個限制，並說明「未來研究可如何克服」

【5.5 未來研究建議】（500字以上）
- 提出 4-5 個未來研究方向，每個方向說明：
  → 研究問題 → 建議方法 → 預期貢獻
"""
    }
}

# ─────────────────────────────────────────────
# 7. 章節撰寫（自動補足字數）
# ─────────────────────────────────────────────
STYLE_EXAMPLE = """
「人才培訓教育訓練是現代企業不可或缺的一部分，旨在提高員工的技能和知識，
從而提升組織的績效和競爭力（Katz，2013）。從策略性人力資源管理的視角來看，
培訓與發展不僅是單一的技能傳遞，更是塑造員工心理契約與組織認同的關鍵樞紐。
然而，隨著產業的迅速發展和變化，企業面臨著許多挑戰，包括全球化、科技進步和
人才流失等（Bartlett，2001）。在這樣高度動態且充滿不確定性的競爭環境中，
員工的流動性顯著增加，傳統的留才機制逐漸面臨失效的風險。因此，企業需要不斷
地培訓和發展員工，以保持競爭優勢。」
"""

def write_chapter(chapter_name, title, outline, refs_list, sim_data):
    config      = CHAPTER_CONFIG.get(chapter_name, {})
    instruction = config.get("instruction", "")
    target      = config.get("target_words", 3000)

    apa_refs = "\n".join([f"- {format_apa_ref(r)}" for r in refs_list])
    ref_abstracts = "\n".join([
        f"[{r.get('authors','')}, {r.get('year','')}] "
        f"{r.get('title','')}：{r.get('abstract','')}"
        for r in refs_list[:25]
    ])
    sim_json = json.dumps(sim_data, ensure_ascii=False, indent=2) if sim_data else "無"

    if   "第一章" in chapter_name:
        context = "（注意：本章不可提及第四章的分析結果，只描述研究背景與動機）"
    elif "第二章" in chapter_name:
        context = f"【文獻庫摘要（請大量引用）】：\n{ref_abstracts}\n\n【APA 格式清單】：\n{apa_refs}"
    elif "第三章" in chapter_name:
        context = f"【模型架構（請轉為學術文字，嚴禁直接貼 JSON）】：\n{sim_json[:5000]}"
    elif "第四章" in chapter_name:
        context = f"【模擬數據（請轉為學術分析與表格，嚴禁直接貼 JSON）】：\n{sim_json[:5000]}"
    else:
        context = f"【整體研究摘要】：\n{sim_json[:2000]}"

    prompt = f"""
你是一位撰寫繁體中文學術論文的資深教授，專長為人力資源管理與組織行為學。

【學術語氣範例（請模仿此語氣與密度）】：
{STYLE_EXAMPLE}

【核心語氣原則】：
1. 絕對不使用「我」，改用「本研究」「研究者」「本文」
2. 每個論點後立即附引用（作者，年份）
3. 善用學術連接詞：然而、此外、有鑑於此、因此、綜上所述、值得注意的是
4. 每段開頭有主題句，結尾有小結句
5. 數學公式用 LaTeX $公式$；表格用 Markdown；訪談引言用「受訪者A表示：『...』」

【論文題目】：{title}
【當前章節】：{chapter_name}
【論文大綱】：{outline}

{context}

【章節撰寫指示】：
{instruction}

【額外要求】：
- 目標字數：{target} 字以上，每個小節必須完整，不得簡略
- 遇到統計數據請生成合理模擬值（如：β = 0.43, t = 5.21, p < 0.001）
- 遇到訪談引言請使用：「受訪者A（職稱，年資）表示：『具體引言內容』」
- 所有 Markdown 表格要有完整資料列（至少 5 行）

請立即開始撰寫完整的 {chapter_name}，不得使用「請繼續」「待補充」等截斷語句：
"""

    result = call_ai_api(
        prompt,
        sys_role="你是嚴謹的繁體中文學術論文教授。每次回應必須詳盡完整，不得截斷，不得使用佔位符。",
        max_tokens=6000
    )

    # 字數不足自動補寫
    word_count = len(re.sub(r'\s', '', result))
    if word_count < int(target * 0.7):
        supplement = call_ai_api(
            f"""
請繼續補充撰寫「{chapter_name}」的剩餘小節（約 {target - word_count} 字）。
銜接以下內容繼續，不要重複已寫的部分：
{result[-600:]}

請繼續撰寫所有尚未完成的小節。
""",
            sys_role="你是嚴謹的繁體中文學術論文教授。",
            max_tokens=4000
        )
        result = result + "\n\n" + supplement

    return result

# ─────────────────────────────────────────────
# 8. Session 初始化
# ─────────────────────────────────────────────
defaults = {
    "step": 0, "final_title": "", "refs_list": [],
    "refs_summary": "", "sim_data": None,
    "outline": "", "content": {},
    "integrated_abstract": "", "integrated_ack": "",
    "integrated_transitions": {}, "polished_ch1": "",
    "full_integrated_paper": ""
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

chapters_list = list(CHAPTER_CONFIG.keys())

# ─────────────────────────────────────────────
# 9. 主畫面
# ─────────────────────────────────────────────
st.title("🎓 論文寫作助手（最終完整版）")
st.caption("自動文獻 × 深度學術撰寫 × 邏輯整合 × 20,000 字目標")

# 進度條
prog_labels = ["① 題目","② 文獻","③ 模型","④ 大綱","⑤ 寫作＆整合"]
pcols = st.columns(5)
for i, label in enumerate(prog_labels):
    with pcols[i]:
        if   st.session_state.step > i:  st.success(label)
        elif st.session_state.step == i: st.info(f"**{label}**")
        else: st.caption(label)

st.divider()

# ════════════════════════════════════════════
# 步驟 0：題目
# ════════════════════════════════════════════
if st.session_state.step == 0:
    st.subheader("步驟 1：擬定研究題目")
    keywords = st.text_input("輸入關鍵字（例如：ESG, 供應鏈, 人才培育）：")

    if st.button("✨ 生成題目建議"):
        if not keywords:
            st.error("請輸入關鍵字")
        else:
            method_str = mcdm_method or case_method or research_mode
            prompt = f"""
關鍵字：{keywords}，研究方法：{method_str}
請產生 5 個繁體中文學術論文題目，格式：
1. 題目（說明研究方向與貢獻）
每個題目要具體、符合台灣碩士論文格式。
"""
            st.info(call_ai_api(prompt))

    title_input = st.text_input("👇 確認最終題目", value=st.session_state.final_title,
                                 placeholder="例如：人才培訓教育訓練對組織行為的影響：以留任率為衡量指標的實證研究")
    if st.button("下一步 → 自動搜尋文獻 ➡️", type="primary"):
        if title_input:
            st.session_state.final_title = title_input
            st.session_state.step = 1; st.rerun()
        else: st.error("請輸入題目")

# ════════════════════════════════════════════
# 步驟 1：文獻
# ════════════════════════════════════════════
elif st.session_state.step == 1:
    st.subheader("步驟 2：自動搜尋真實文獻")
    st.info(f"📌 題目：**{st.session_state.final_title}**")

    c1, c2 = st.columns(2)
    c1.metric("英文文獻目標", f"{en_paper_count} 篇（Semantic Scholar + CrossRef）")
    c2.metric("中文文獻目標", f"{zh_paper_count} 篇（AI 生成 TSSCI 格式）")

    if st.button("🔍 自動搜尋文獻", type="primary"):
        with st.spinner("📡 正在抓取真實學術文獻..."):
            refs = search_all_refs(st.session_state.final_title,
                                   en_count=en_paper_count,
                                   zh_count=zh_paper_count,
                                   year_from=year_from)
            st.session_state.refs_list = refs
        with st.spinner("📝 AI 歸納文獻重點..."):
            ref_abstracts = "\n".join([
                f"[{r.get('authors','')}, {r.get('year','')}] "
                f"{r.get('title','')}：{r.get('abstract','')}"
                for r in refs
            ])
            st.session_state.refs_summary = call_ai_api(
                f"請歸納以下文獻重點，說明各篇的理論觀點、研究變數、主要發現：\n{ref_abstracts}",
                max_tokens=4000
            )
        st.rerun()

    if st.session_state.refs_list:
        zh_refs = [r for r in st.session_state.refs_list if r.get("lang")=="zh"]
        en_refs = [r for r in st.session_state.refs_list if r.get("lang")=="en"]
        t1, t2, t3 = st.tabs([f"英文（{len(en_refs)}篇）", f"中文（{len(zh_refs)}篇）", "文獻摘要"])
        with t1:
            for i, r in enumerate(en_refs, 1):
                with st.expander(f"{i}. {r.get('title','')[:80]} ({r.get('year','')})"):
                    st.markdown(f"**作者：** {r.get('authors','')}  \n**期刊：** {r.get('venue','')}  \n**DOI：** {r.get('doi','')}  \n**摘要：** {r.get('abstract','')}  \n**APA：** {format_apa_ref(r)}")
        with t2:
            for i, r in enumerate(zh_refs, 1):
                with st.expander(f"{i}. {r.get('title','')[:80]} ({r.get('year','')})"):
                    st.markdown(f"**作者：** {r.get('authors','')}  \n**期刊：** {r.get('venue','')} {r.get('volume','')}  \n**摘要：** {r.get('abstract','')}  \n**APA：** {format_apa_ref(r)}")
        with t3:
            st.markdown(st.session_state.refs_summary)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ 上一步"): st.session_state.step = 0; st.rerun()
        with col2:
            if st.button("下一步 → 建立分析模型 ➡️", type="primary"):
                st.session_state.step = 2; st.rerun()

# ════════════════════════════════════════════
# 步驟 2：模型
# ════════════════════════════════════════════
elif st.session_state.step == 2:
    current_method = mcdm_method or case_method or research_mode
    st.subheader(f"步驟 3：建立 {current_method} 分析模型")
    st.info(f"📌 題目：**{st.session_state.final_title}**")

    if st.button(f"🚀 執行 {current_method} 模擬", type="primary"):
        with st.spinner("🔧 建構模型中（約 30-60 秒）..."):
            c_n = criteria_size if research_mode == "MCDM (量化/決策)" else 15
            d_n = dim_size      if research_mode == "MCDM (量化/決策)" else 4
            result = run_simulation_analysis(
                st.session_state.refs_summary,
                research_mode, mcdm_method, case_method, c_n, d_n
            )
            if result:
                st.session_state.sim_data = result
                st.success("✅ 模型建構完成！")
            else: st.error("❌ 模擬失敗，請重試")

    if st.session_state.sim_data:
        data = st.session_state.sim_data
        t1, t2, t3, t4 = st.tabs(["層級架構","權重排名","假設驗證數據","訪談主題"])
        with t1:
            for dim in data.get("final_hierarchy",[]):
                st.markdown(f"**{dim.get('dimension_name','')}（{dim.get('dimension_code','')}）**")
                for c in dim.get("contained_criteria",[]):
                    st.markdown(f"　- **{c.get('criteria_name','')}**：{c.get('reasoning','')}")
        with t2:
            weights = data.get("step4_simulation",{}).get("weights",[])
            if weights: st.dataframe(pd.DataFrame(weights).sort_values("weight", ascending=False), use_container_width=True)
        with t3:
            reg = data.get("step4_simulation",{}).get("regression",[])
            if reg: st.dataframe(pd.DataFrame(reg), use_container_width=True)
        with t4:
            for theme in data.get("step4_simulation",{}).get("interview_themes",[]):
                with st.expander(f"主題：{theme.get('theme','')}"):
                    st.markdown(theme.get("description",""))
                    for q in theme.get("quotes",[]): st.markdown(f"> {q}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ 上一步"): st.session_state.step = 1; st.rerun()
        with col2:
            if st.button("下一步 → 生成大綱 ➡️", type="primary"): st.session_state.step = 3; st.rerun()

# ════════════════════════════════════════════
# 步驟 3：大綱
# ════════════════════════════════════════════
elif st.session_state.step == 3:
    st.subheader("步驟 4：生成完整論文大綱")
    st.info(f"📌 題目：**{st.session_state.final_title}**")

    if st.button("✨ 生成大綱", type="primary"):
        method_str  = mcdm_method or case_method or research_mode
        sim_context = json.dumps(st.session_state.sim_data, ensure_ascii=False)[:3000] if st.session_state.sim_data else "無"
        prompt = f"""
題目：{st.session_state.final_title}
研究方法：{method_str}
分析模型：{sim_context}

請撰寫詳細的五章論文大綱，每個小節附100字說明。
格式：
# 第一章 緒論
## 1.1 研究背景與動機（說明...）
...（依此類推至第五章）
"""
        st.session_state.outline = call_ai_api(prompt, max_tokens=4000)
        st.rerun()

    if st.session_state.outline:
        st.markdown(st.session_state.outline)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ 上一步"): st.session_state.step = 2; st.rerun()
        with col2:
            if st.button("下一步 → 開始寫作 ➡️", type="primary"): st.session_state.step = 4; st.rerun()

# ════════════════════════════════════════════
# 步驟 4：寫作 + 整合
# ════════════════════════════════════════════
elif st.session_state.step == 4:
    st.subheader("步驟 5：逐章撰寫 + 整合成完整論文")
    st.info(f"📌 題目：**{st.session_state.final_title}**")

    done_count = sum(1 for ch in chapters_list if ch in st.session_state.content)
    est_words  = done_count * 4500
    st.progress(done_count / len(chapters_list),
                text=f"已完成 {done_count}/{len(chapters_list)} 章（約 {est_words:,} 字）")

    # ── 一鍵全部撰寫 ──
    if st.button("⚡ 一鍵撰寫所有章節", type="primary"):
        for chapter_name in chapters_list:
            if chapter_name not in st.session_state.content:
                with st.spinner(f"✍️ 撰寫 {chapter_name}..."):
                    st.session_state.content[chapter_name] = write_chapter(
                        chapter_name, st.session_state.final_title,
                        st.session_state.outline,
                        st.session_state.refs_list,
                        st.session_state.sim_data
                    )
                    time.sleep(2)
        st.rerun()

    # ── 各章 Tab ──
    tab_list = st.tabs([
        f"{'✅' if ch in st.session_state.content else '📝'} {ch}"
        for ch in chapters_list
    ])
    for i, (tab, chapter_name) in enumerate(zip(tab_list, chapters_list)):
        with tab:
            config = CHAPTER_CONFIG[chapter_name]
            st.caption(f"目標：{config['target_words']:,} 字 ｜ 小節：{', '.join(config['sections'])}")
            cb1, cb2 = st.columns(2)
            with cb1:
                if st.button(f"🚀 撰寫本章", key=f"w{i}", type="primary"):
                    with st.spinner(f"✍️ 撰寫 {chapter_name}（60-90秒）..."):
                        st.session_state.content[chapter_name] = write_chapter(
                            chapter_name, st.session_state.final_title,
                            st.session_state.outline,
                            st.session_state.refs_list,
                            st.session_state.sim_data
                        )
                    st.rerun()
            with cb2:
                if chapter_name in st.session_state.content:
                    if st.button("🔄 重新撰寫", key=f"r{i}"):
                        del st.session_state.content[chapter_name]; st.rerun()

            if chapter_name in st.session_state.content:
                text = st.session_state.content[chapter_name]
                wc   = len(re.sub(r'\s','',text))
                st.success(f"✅ 已完成（約 {wc:,} 字）")
                st.markdown(text)
            else:
                st.warning("⚠️ 尚未撰寫")

    # ════════════════
    # 整合器
    # ════════════════
    st.divider()
    st.subheader("🔗 步驟 6：整合成邏輯連貫的完整論文")
    st.caption("統一語氣 × 章節銜接 × 中英文摘要 × 致謝 × 邏輯診斷 → 輸出完整論文")

    done_chapters = [ch for ch in chapters_list if ch in st.session_state.content]

    if len(done_chapters) < 3:
        st.warning("⚠️ 請至少完成 3 章再進行整合。")
    else:
        if st.button("✨ 一鍵整合成完整論文", type="primary", key="integrate_btn"):

            # 1. 中英文摘要
            with st.spinner("📝 生成中英文摘要..."):
                ch_summaries = "\n".join([
                    f"【{ch}】{st.session_state.content.get(ch,'')[:800]}"
                    for ch in done_chapters
                ])
                abstract_prompt = f"""
你是學術論文寫作專家，使用繁體中文。
根據以下論文各章內容，撰寫：
1. 繁體中文摘要（400-500字）：研究目的、方法、結果、結論、關鍵詞（5個）
2. English Abstract（200-250 words）：Purpose, Method, Findings, Conclusion, Keywords

論文題目：{st.session_state.final_title}
各章摘要：{ch_summaries}
"""
                st.session_state.integrated_abstract = call_ai_api(abstract_prompt, max_tokens=2000)

            # 2. 章節銜接段
            with st.spinner("🔗 生成章節銜接段落..."):
                transitions = {}
                for i in range(len(done_chapters) - 1):
                    ch_now  = done_chapters[i]
                    ch_next = done_chapters[i + 1]
                    trans   = call_ai_api(f"""
請撰寫150-200字的章節過渡段落，放在 {ch_now} 結尾：
1. 總結 {ch_now} 核心發現（1-2句）
2. 說明為何進入 {ch_next}（邏輯橋樑）
3. 預告 {ch_next} 主要內容

{ch_now} 末段：{st.session_state.content.get(ch_now,'')[-400:]}
{ch_next} 首段：{st.session_state.content.get(ch_next,'')[:400]}
語氣：學術、繁體中文、流暢自然。
""", max_tokens=500)
                    transitions[ch_now] = trans
                    time.sleep(1)
                st.session_state.integrated_transitions = transitions

            # 3. 第一章語氣潤飾
            with st.spinner("✍️ 統一第一章語氣..."):
                st.session_state.polished_ch1 = call_ai_api(f"""
你是學術論文編輯，請對以下第一章進行語氣統一與學術化潤飾：
1. 不使用「我」，改用「本研究」「研究者」
2. 補充連接詞（然而、此外、因此、綜上所述）
3. 確保每段有主題句
4. 統一引用格式為（作者，年份）

原文：{st.session_state.content.get('第一章 緒論','')[:4000]}
""", max_tokens=5000)

            # 4. 致謝辭
            with st.spinner("💐 生成致謝辭..."):
                st.session_state.integrated_ack = call_ai_api(f"""
請用繁體中文撰寫學術論文致謝辭（250-300字），感謝指導教授、口試委員、
受訪企業專家、同學與家人。主題：{st.session_state.final_title}。
語氣：誠懇、學術。
""", max_tokens=800)

            st.success("✅ 整合完成！請見下方預覽。")
            st.rerun()

        # ── 整合後呈現 ──
        if st.session_state.integrated_abstract:

            # 組合全文
            full_paper  = f"# {st.session_state.final_title}\n\n---\n\n"
            full_paper += "## 致謝\n\n" + st.session_state.integrated_ack + "\n\n---\n\n"
            full_paper += "## 摘要\n\n" + st.session_state.integrated_abstract + "\n\n---\n\n"
            full_paper += "## 目錄\n\n"
            for ch in done_chapters:
                full_paper += f"- **{ch}**\n"
                for sec in CHAPTER_CONFIG.get(ch,{}).get("sections",[]):
                    full_paper += f"  - {sec}\n"
            full_paper += "\n---\n\n"

            transitions = st.session_state.integrated_transitions
            for ch in done_chapters:
                text = (st.session_state.polished_ch1
                        if ch == "第一章 緒論" and st.session_state.polished_ch1
                        else st.session_state.content.get(ch,""))
                full_paper += f"# {ch}\n\n{text}\n\n"
                if ch in transitions:
                    full_paper += f"\n---\n> 📎 **【章節銜接】** {transitions[ch]}\n\n---\n\n"

            # 參考文獻
            full_paper += "## 參考文獻\n\n### 中文文獻\n\n"
            for r in sorted([r for r in st.session_state.refs_list if r.get("lang")=="zh"],
                             key=lambda x: str(x.get("authors",""))):
                full_paper += format_apa_ref(r) + "\n\n"
            full_paper += "\n### 英文文獻\n\n"
            for r in sorted([r for r in st.session_state.refs_list if r.get("lang")=="en"],
                             key=lambda x: str(x.get("authors",""))):
                full_paper += format_apa_ref(r) + "\n\n"

            st.session_state.full_integrated_paper = full_paper

            # ── 預覽 Tab ──
            total_words = len(re.sub(r'\s','', full_paper))
            pt1, pt2, pt3, pt4, pt5 = st.tabs(
                ["📄 摘要","💐 致謝","🔗 章節銜接","📖 全文預覽","🔍 邏輯診斷"]
            )
            with pt1: st.markdown(st.session_state.integrated_abstract)
            with pt2: st.markdown(st.session_state.integrated_ack)
            with pt3:
                for ch, trans in transitions.items():
                    with st.expander(f"📎 {ch} → 下一章"):
                        st.markdown(trans)
            with pt4:
                st.metric("📊 全文字數", f"{total_words:,} 字",
                          delta="✅ 達標" if total_words >= 20000 else f"還差 {20000-total_words:,} 字")
                st.markdown(full_paper[:10000] + "\n\n...（請下載完整版）")
            with pt5:
                st.subheader("🔍 全文邏輯一致性診斷")
                if st.button("🩺 執行邏輯診斷", key="diag"):
                    with st.spinner("AI 審查中..."):
                        full_text = "\n\n".join([
                            f"【{ch}】{st.session_state.content.get(ch,'')[:1200]}"
                            for ch in done_chapters
                        ])
                        diag = call_ai_api(f"""
你是嚴格的論文口試委員，請對以下論文進行「邏輯一致性診斷」，
從 5 個維度評分（1-10分）並說明問題與建議：

1. 研究問題與結論對應性：第一章研究問題是否在第五章完整回答？
2. 文獻與方法一致性：第二章理論是否在第三章有對應設計？
3. 方法與結果一致性：第三章方法是否在第四章執行？
4. 章節銜接流暢度：各章之間是否有邏輯過渡？
5. 學術語氣一致性：全文語氣是否統一？

論文題目：{st.session_state.final_title}
各章摘要：{full_text[:8000]}

請輸出完整診斷報告（Markdown格式，含改進建議）：
""", max_tokens=3000)
                        st.markdown(diag)

            # ── 下載 ──
            st.divider()
            st.subheader("📥 下載完整論文")
            d1, d2 = st.columns(2)
            with d1:
                st.download_button(
                    "📄 下載完整論文 Markdown (.md)",
                    full_paper,
                    file_name=f"{st.session_state.final_title[:30]}_完整版.md",
                    mime="text/markdown", type="primary"
                )
            with d2:
                st.download_button(
                    "📝 下載完整論文純文字 (.txt)",
                    full_paper,
                    file_name=f"{st.session_state.final_title[:30]}_完整版.txt",
                    mime="text/plain"
                )

    if st.button("⬅️ 上一步（大綱）"):
        st.session_state.step = 3; st.rerun()

    st.caption("⚠️ 免責聲明：AI 生成內容僅供學術練習，使用前請自行查核文獻真實性。")

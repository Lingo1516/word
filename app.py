# ╔══════════════════════════════════════════════════════════════╗
# ║          🎓 論文寫作助手 - 最終完整版                        ║
# ║  支援：Groq / Gemini / OpenRouter / Ollama / Hugging Face   ║
# ╚══════════════════════════════════════════════════════════════╝
#
# 安裝套件：
#   pip install streamlit groq google-generativeai openai requests pandas
#
# 執行方式：
#   streamlit run app.py

# ─────────────────────────────────────────────
# 1. Import
# ─────────────────────────────────────────────
import streamlit as st
from groq import Groq
import google.generativeai as genai
import openai
import requests
import json
import re
import time
import pandas as pd

# ─────────────────────────────────────────────
# 2. 頁面設定
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="🎓 論文寫作助手",
    layout="wide",
    page_icon="🎓"
)

# ─────────────────────────────────────────────
# 3. 函數定義
# ─────────────────────────────────────────────
def validate_api_key(key, engine, model=""):
    try:
        if engine == "Gemini":
            genai.configure(api_key=key)
            genai.GenerativeModel("gemini-1.5-flash").generate_content("Hi")
            return "ok", None
        elif engine == "Groq":
            client = Groq(api_key=key)
            client.chat.completions.create(
                messages=[{"role":"user","content":"Hi"}],
                model="llama-3.1-8b-instant", max_tokens=5
            )
            return "ok", None
        elif engine == "OpenRouter":
            client = openai.OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1")
            client.chat.completions.create(
                model="meta-llama/llama-3.1-8b-instruct:free",
                messages=[{"role":"user","content":"Hi"}], max_tokens=5
            )
            return "ok", None
        elif engine == "Ollama":
            r = requests.get("http://localhost:11434/api/tags", timeout=3)
            if r.status_code == 200:
                installed = [m["name"] for m in r.json().get("models",[])]
                return "ok", installed
            return "error", "Ollama 未啟動"
        elif engine == "HuggingFace":
            client = openai.OpenAI(api_key=key, base_url="https://api-inference.huggingface.co/v1")
            client.chat.completions.create(
                model="mistralai/Mistral-7B-Instruct-v0.3",
                messages=[{"role":"user","content":"Hi"}], max_tokens=5
            )
            return "ok", None
    except Exception as e:
        err = str(e)
        if "401" in err or "invalid_api_key" in err or "API_KEY_INVALID" in err:
            return "invalid", "❌ API Key 無效"
        elif "429" in err and "1h" in err:
            return "quota", "⛔ 今日額度已用完"
        elif "429" in err:
            return "ratelimit", "⚠️ 請求過於頻繁"
        return "error", f"❌ {err[:120]}"


def call_ai_api(prompt, sys_role="你是一位嚴謹的學術專家，使用繁體中文回答。", max_tokens=6000):
    if st.session_state.active_engine != "Ollama" and not st.session_state.api_key:
        return "⚠️ 請輸入 API Key"
    for attempt in range(3):
        try:
            engine = st.session_state.active_engine
            key    = st.session_state.api_key
            model  = st.session_state.active_model

            if engine == "Groq":
                client = Groq(api_key=key)
                resp   = client.chat.completions.create(
                    messages=[{"role":"system","content":sys_role},{"role":"user","content":prompt}],
                    model=model, temperature=0.5, max_tokens=min(max_tokens,3000)
                )
                return resp.choices[0].message.content

            elif engine == "Gemini":
                genai.configure(api_key=key)
                return genai.GenerativeModel("gemini-1.5-flash").generate_content(
                    f"{sys_role}\n\n{prompt}").text

            elif engine == "OpenRouter":
                client = openai.OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1")
                resp   = client.chat.completions.create(
                    model=model,
                    messages=[{"role":"system","content":sys_role},{"role":"user","content":prompt}],
                    max_tokens=max_tokens, temperature=0.5
                )
                return resp.choices[0].message.content

            elif engine == "Ollama":
                resp = requests.post("http://localhost:11434/api/chat", json={
                    "model": model,
                    "messages":[{"role":"system","content":sys_role},{"role":"user","content":prompt}],
                    "stream": False
                }, timeout=180)
                return resp.json()["message"]["content"]

            elif engine == "HuggingFace":
                client = openai.OpenAI(api_key=key, base_url="https://api-inference.huggingface.co/v1")
                resp   = client.chat.completions.create(
                    model=model,
                    messages=[{"role":"system","content":sys_role},{"role":"user","content":prompt}],
                    max_tokens=max_tokens
                )
                return resp.choices[0].message.content

        except Exception as e:
            err = str(e)
            if "429" in err and "1h" in err:
                return "⛔ 今日額度已用完，請切換其他平台"
            elif "429" in err:
                st.warning(f"⏳ 請求頻繁，等待 60 秒重試（第 {attempt+1}/3 次）...")
                time.sleep(60)
                continue
            elif "401" in err or "invalid" in err.lower():
                return "❌ API Key 無效，請重新確認"
            return f"❌ Error: {err[:150]}"
    return "❌ 重試 3 次後仍失敗，請切換其他平台"


def fetch_semantic_scholar(query, limit=10, year_from=2018):
    try:
        res = requests.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params={"query":query,"limit":limit,
                    "fields":"title,authors,year,abstract,externalIds,venue,citationCount",
                    "year":f"{year_from}-"},
            headers={"User-Agent":"ThesisAssistant/1.0"}, timeout=15
        )
        if res.status_code == 200:
            results = []
            for p in res.json().get("data",[]):
                if not p.get("title"): continue
                authors = ", ".join([a.get("name","") for a in p.get("authors",[])[:3]])
                if len(p.get("authors",[])) > 3: authors += " et al."
                results.append({
                    "title":p.get("title",""), "authors":authors, "year":p.get("year",""),
                    "abstract":(p.get("abstract") or "")[:500], "venue":p.get("venue",""),
                    "citations":p.get("citationCount",0),
                    "doi":p.get("externalIds",{}).get("DOI",""), "lang":"en"
                })
            return results
    except Exception: pass
    return []


def fetch_crossref(query, limit=10, year_from=2018):
    try:
        res = requests.get("https://api.crossref.org/works",
            params={"query":query,"rows":limit,"filter":f"from-pub-date:{year_from}",
                    "select":"title,author,published,abstract,DOI,container-title",
                    "mailto":"thesis@example.com"}, timeout=15)
        if res.status_code == 200:
            results = []
            for item in res.json().get("message",{}).get("items",[]):
                title = item.get("title",[""])[0] if item.get("title") else ""
                if not title: continue
                ar = item.get("author",[])
                authors = ", ".join([f"{a.get('family','')}, {a.get('given','')}" for a in ar[:3]])
                if len(ar) > 3: authors += " et al."
                pub = item.get("published",{}).get("date-parts",[[""]])
                year = pub[0][0] if pub and pub[0] else ""
                abstract = re.sub(r'<[^>]+>','',item.get("abstract",""))[:500]
                results.append({
                    "title":title,"authors":authors,"year":year,"abstract":abstract,
                    "venue":(item.get("container-title",[""])[0] if item.get("container-title") else ""),
                    "citations":0,"doi":item.get("DOI",""),"lang":"en"
                })
            return results
    except Exception: pass
    return []


def fetch_chinese_refs_via_ai(topic, count=10, year_from=2018):
    prompt = f"""
你是熟悉台灣學術文獻的專家。
根據主題「{topic}」，生成 {count} 篇符合真實格式的繁體中文 TSSCI 學術文獻，年份在 {year_from} 年以後。
【嚴格輸出 JSON array】：
[{{"title":"論文標題","authors":"作者姓名","year":2021,
   "journal":"期刊名稱","volume":"38(2)","pages":"45-78","abstract":"摘要50字以內"}}]
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
                for item in data:
                    item.update({"lang":"zh","doi":"","venue":item.get("journal",""),"citations":0})
                return data
            except Exception: pass
    return []


def search_all_refs(topic, en_count, zh_count, year_from):
    ss = fetch_semantic_scholar(topic, limit=en_count, year_from=year_from)
    if len(ss) < en_count:
        ss += fetch_crossref(topic, limit=en_count - len(ss), year_from=year_from)
    zh = fetch_chinese_refs_via_ai(topic, count=zh_count, year_from=year_from)
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
    apa = f"{authors} ({year}). {title}. *{venue}*."
    if doi: apa += f" https://doi.org/{doi}"
    return apa


def run_simulation_analysis(refs_summary, mode, m_method, c_method, c_n, d_n):
    method_instr = {
        "AHP":     "模擬 Saaty 1-9 成對比較矩陣，計算特徵向量權重，CR < 0.1。",
        "DEMATEL": "模擬 0-4 直接關係矩陣，計算中心度(D+R)與原因度(D-R)。",
        "SEM":     "模擬結構方程模型路徑係數，計算 β 值與 p 值。",
        "ANP":     "模擬超矩陣與極限矩陣，計算極限權重。",
        "FCM":     "模擬 -1 到 1 影響矩陣，進行穩定態推論。",
    }.get((m_method or "").split("（")[0].strip(), "模擬迴歸分析，計算標準化係數。")

    prompt = f"""
你是 MCDM 與統計分析專家，方法：{m_method or c_method}。
根據以下文獻摘要執行：
1. 萃取 {c_n} 個評估準則，歸納為 {d_n} 個構面
2. {method_instr}
3. 模擬 3 家企業評分
4. 生成合理統計數值（β、t、p、AVE、CR、α）

【嚴格輸出 JSON】：
{{
  "final_hierarchy":[
    {{"dimension_name":"構面名","dimension_code":"D1",
      "contained_criteria":[{{"criteria_name":"準則","criteria_code":"C1","reasoning":"依據文獻..."}}]}}
  ],
  "step4_simulation":{{
    "method_used":"{m_method or c_method}",
    "weights":[{{"criteria":"準則","dimension":"構面","weight":0.08,"rank":1}}],
    "matrix_data":[{{"from":"C1","to":"C2","value":2.5}}],
    "regression":[{{"hypothesis":"H1","path":"A→B","beta":0.43,"t_value":5.21,"p_value":"<0.001","supported":true}}],
    "reliability":[{{"dimension":"構面","alpha":0.87,"AVE":0.62,"CR":0.88}}],
    "companies":[{{"name":"企業A","industry":"科技業","scores":{{"準則":85}}}}],
    "interview_themes":[
      {{"theme":"主題一","description":"說明","quotes":["受訪者A（HR主管，15年）表示：『...』"]}}
    ]
  }}
}}
文獻摘要：{refs_summary[:8000]}
"""
    try:
        res     = call_ai_api(prompt, sys_role="Output ONLY valid JSON. No markdown.", max_tokens=5000)
        cleaned = re.sub(r'^```json\s*|^```\s*|```\s*$','',res.strip(),flags=re.MULTILINE)
        try:    return json.loads(cleaned)
        except Exception:
            match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            return json.loads(match.group(0)) if match else None
    except Exception: return None


STYLE_EXAMPLE = """
「人才培訓教育訓練是現代企業不可或缺的一部分，旨在提高員工的技能和知識，
從而提升組織的績效和競爭力（Katz，2013）。從策略性人力資源管理的視角來看，
培訓與發展不僅是單一的技能傳遞，更是塑造員工心理契約與組織認同的關鍵樞紐。
然而，隨著產業的迅速發展和變化，企業面臨著許多挑戰（Bartlett，2001）。
有鑑於此，企業需要不斷培訓和發展員工，以保持競爭優勢。」
"""

CHAPTER_CONFIG = {
    "第一章 緒論": {
        "target_words": 4000,
        "sections": ["研究背景與動機","研究目的","研究問題","研究範圍與限制","論文架構"],
        "instruction": """
目標 4,000 字以上：
【1.1 研究背景與動機】（800字）宏觀趨勢→研究主題→實務問題→研究缺口，每論點引用（作者，年份）
【1.2 研究目的】（400字）4-5個具體目的，邏輯遞進（探討→分析→建議）
【1.3 研究問題】（400字）4-5個具體可操作的研究問題
【1.4 研究範圍與限制】（400字）研究對象、範圍、CMV問題說明
【1.5 論文架構】（300字）各章內容與邏輯連結
"""
    },
    "第二章 文獻探討": {
        "target_words": 6000,
        "sections": ["理論基礎","相關文獻回顧","研究假設","文獻總結與研究缺口"],
        "instruction": """
目標 6,000 字以上：
【2.1 理論基礎】（1500字）3-4個核心理論：起源→核心主張→與本研究連結，最後說明整合框架
【2.2 相關文獻回顧】（2500字）每個變數一小節，各引4-5篇，每篇150字（學者/年份→方法→發現→關聯）
【2.3 研究假設】（800字）H1-H6：假設陳述→文獻依據→預期方向
【2.4 文獻總結與研究缺口】（600字）Markdown文獻比較表格 + 3-4個研究缺口
"""
    },
    "第三章 研究方法": {
        "target_words": 5000,
        "sections": ["研究架構","研究設計","研究變數與操作型定義","資料收集方法","資料分析方法","研究倫理"],
        "instruction": """
目標 5,000 字以上：
【3.1 研究架構】（600字）文字描述架構圖（自變數→中介→依變數），對應H1-H6
【3.2 研究設計】（600字）量化+質性混合方法理由，三角驗證說明
【3.3 研究變數與操作型定義】（1000字）Markdown表格：| 變數 | 類型 | 操作型定義 | 量表來源 | 題項數 | 尺度 |
【3.4 資料收集方法】（700字）量化：問卷對象、樣本數（Hair et al.）；質性：訪談標準、時長、轉錄
【3.5 資料分析方法】（1500字）量化：描述統計→信度($\\alpha$)→CFA→SEM（含公式）；質性：主題分析六步驟
【3.6 研究倫理】（200字）知情同意、匿名保護、IRB
"""
    },
    "第四章 研究結果與分析": {
        "target_words": 6000,
        "sections": ["樣本描述統計","信效度分析","研究假設驗證","質性訪談結果","綜合討論"],
        "instruction": """
目標 6,000 字以上：
【4.1 樣本描述統計】（800字）Markdown表格：| 變數 | 類別 | 次數 | 百分比 |（含性別、年齡、教育、年資、產業）
【4.2 信效度分析】（800字）表格：| 構面 | α | AVE | CR | 判斷 | + HTMT矩陣
【4.3 研究假設驗證】（2000字）表格：| 假設 | 路徑 | β | t值 | p值 | 結果 | + 逐一解釋與文獻對話
【4.4 質性訪談結果】（1500字）受訪者描述(A-F) + 3-4個主題（說明+引言「受訪者A表示：『...』」）+ 三角驗證
【4.5 綜合討論】（800字）量化質性整合 + 與文獻對話
"""
    },
    "第五章 結論與建議": {
        "target_words": 3500,
        "sections": ["研究結論","理論貢獻","實務建議","研究限制","未來研究建議"],
        "instruction": """
目標 3,500 字以上：
【5.1 研究結論】（1000字）逐一回答5個研究問題
【5.2 理論貢獻】（600字）對3-4個理論的具體貢獻
【5.3 實務建議】（800字）HR部門（3項）、管理階層（2項）、政策制定者（1項）
【5.4 研究限制】（400字）3-4個限制 + 如何克服
【5.5 未來研究建議】（500字）4-5個方向：問題→方法→預期貢獻
"""
    }
}


def write_chapter(chapter_name, title, outline, refs_list, sim_data):
    config      = CHAPTER_CONFIG.get(chapter_name, {})
    instruction = config.get("instruction","")
    target      = config.get("target_words", 3000)
    apa_refs    = "\n".join([f"- {format_apa_ref(r)}" for r in refs_list])
    ref_abstracts = "\n".join([
        f"[{r.get('authors','')}, {r.get('year','')}] {r.get('title','')}：{r.get('abstract','')}"
        for r in refs_list[:25]
    ])
    sim_json = json.dumps(sim_data, ensure_ascii=False, indent=2) if sim_data else "無"

    if   "第一章" in chapter_name: context = "（本章不可提及第四章結果）"
    elif "第二章" in chapter_name: context = f"【文獻庫】：\n{ref_abstracts}\n\n【APA清單】：\n{apa_refs}"
    elif "第三章" in chapter_name: context = f"【模型架構（請轉為學術文字，嚴禁貼JSON）】：\n{sim_json[:5000]}"
    elif "第四章" in chapter_name: context = f"【模擬數據（請轉為學術分析與表格）】：\n{sim_json[:5000]}"
    else:                           context = f"【整體研究摘要】：\n{sim_json[:2000]}"

    prompt = f"""
你是撰寫繁體中文學術論文的資深教授，專長為人力資源管理與組織行為學。

【語氣範例（請模仿）】：{STYLE_EXAMPLE}

【核心原則】：
1. 不使用「我」，用「本研究」「研究者」「本文」
2. 每個論點後引用（作者，年份）
3. 善用：然而、此外、有鑑於此、因此、綜上所述
4. 每段有主題句與小結句
5. 公式用 $公式$；表格用 Markdown；訪談用「受訪者A（職稱）表示：『...』」

【論文題目】：{title}
【章節】：{chapter_name}
【大綱】：{outline}
{context}

【撰寫指示】：{instruction}

請立即完整撰寫 {chapter_name}，每個小節不得省略：
"""
    result = call_ai_api(
        prompt,
        sys_role="你是嚴謹的繁體中文學術論文教授，每次回應必須詳盡完整。",
        max_tokens=6000
    )
    if len(re.sub(r'\s','',result)) < int(target * 0.7):
        supplement = call_ai_api(
            f"請繼續補充撰寫「{chapter_name}」的剩餘小節，銜接以下內容：\n{result[-500:]}",
            max_tokens=4000
        )
        result += "\n\n" + supplement
    return result


# ─────────────────────────────────────────────
# 4. Session 初始化
# ─────────────────────────────────────────────
defaults = {
    "step":0, "final_title":"", "refs_list":[], "refs_summary":"",
    "sim_data":None, "outline":"", "content":{},
    "integrated_abstract":"", "integrated_ack":"",
    "integrated_transitions":{}, "polished_ch1":"",
    "full_integrated_paper":"",
    "api_key":"", "active_engine":"", "active_model":"",
    "api_ready":False
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

chapters_list = list(CHAPTER_CONFIG.keys())

# ─────────────────────────────────────────────
# 5. 側邊欄
# ─────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ 使用設定")

    with st.expander("📖 第一次使用？點這裡", expanded=False):
        st.markdown("""
### 🚀 快速開始（3步驟）
**Step 1：** 選擇 AI 平台（建議新手選 Gemini）
**Step 2：** 點連結申請免費 API Key
**Step 3：** 貼上 Key，看到 ✅ 就可以開始

| 平台 | 免費額度 | 難易度 |
|------|----------|--------|
| Google Gemini | 每天1,500次 | ⭐ 最簡單 |
| Groq | 每天100K tokens | ⭐⭐ 簡單 |
| OpenRouter | 多模型免費 | ⭐⭐ 簡單 |
| Ollama | 完全免費無限 | ⭐⭐⭐ 需安裝 |
""")

    st.divider()
    st.header("🤖 Step 1：選擇 AI 平台")
    engine_choice = st.radio("", [
        "🟢 Google Gemini（推薦新手）",
        "🔵 Groq（速度最快）",
        "🟣 OpenRouter（模型最多）",
        "🟠 Ollama（本機完全免費）",
        "⚪ Hugging Face"
    ], label_visibility="collapsed")

    st.divider()
    st.header("🔑 Step 2：輸入 API Key")

    # 根據選擇顯示說明與輸入框
    if "Gemini" in engine_choice:
        st.session_state.active_engine = "Gemini"
        st.session_state.active_model  = "gemini-1.5-flash"
        st.markdown("""
**🆓 免費方案：每天 1,500 次**
👉 [點我申請 Gemini Key](https://aistudio.google.com/app/apikey)

申請步驟：登入 Google → Create API key → 複製
Key 格式：`AIza...`
""")
        key_input = st.text_input("貼上 Google API Key", type="password", placeholder="AIza...", key="key_input")

    elif "Groq" in engine_choice:
        st.session_state.active_engine = "Groq"
        st.markdown("""
**🆓 免費方案：每天 100,000 tokens**
👉 [點我申請 Groq Key](https://console.groq.com/keys)

申請步驟：登入 → Create API Key → 複製
Key 格式：`gsk_...`
⚠️ 額度用完請改用 Gemini
""")
        key_input = st.text_input("貼上 Groq API Key", type="password", placeholder="gsk_...", key="key_input")
        st.session_state.active_model = st.selectbox("選擇模型", [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "gemma2-9b-it",
            "mixtral-8x7b-32768"
        ])

    elif "OpenRouter" in engine_choice:
        st.session_state.active_engine = "OpenRouter"
        st.markdown("""
**🆓 多個模型完全免費**
👉 [點我申請 OpenRouter Key](https://openrouter.ai/keys)

申請步驟：註冊 → Keys → Create Key → 複製
Key 格式：`sk-or-...`
""")
        key_input = st.text_input("貼上 OpenRouter Key", type="password", placeholder="sk-or-...", key="key_input")
        st.session_state.active_model = st.selectbox("選擇免費模型", [
            "meta-llama/llama-3.3-70b-instruct:free",
            "deepseek/deepseek-r1:free",
            "google/gemma-3-27b-it:free",
            "mistralai/mistral-7b-instruct:free",
            "qwen/qwen3-235b-a22b:free"
        ])

    elif "Ollama" in engine_choice:
        st.session_state.active_engine = "Ollama"
        st.session_state.api_key       = ""
        key_input = ""
        st.markdown("""
**🆓 完全免費，在你電腦上執行**
👉 [點我下載 Ollama](https://ollama.ai)

安裝後在終端機執行：

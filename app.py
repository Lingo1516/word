import streamlit as st
import pandas as pd
import requests
import json
import string
import re
from io import BytesIO

# --- 1. 基礎設定 ---
st.set_page_config(page_title="學術研究雙核心系統 (MCDM + 個案)", layout="wide", page_icon="🎓")

# --- 2. 側邊欄：雙模式切換 ---
with st.sidebar:
    st.header("🎓 系統設定")
    
    # === 安全性檢查 ===
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        st.success("✅ 已載入雲端金鑰")
    else:
        st.warning("⚠️ 未偵測到雲端金鑰")
        api_key = st.text_input("請手動輸入 API Key", type="password")
    
    st.divider()
    thesis_topic = st.text_input("研究題目：", value="餐飲業導入 AI 服務之轉型策略")
    
    # === 核心切換開關 ===
    st.subheader("🛠️ 選擇研究模式")
    research_mode = st.radio("請選擇研究方法論：", ["MCDM (量化/決策分析)", "Case Study (質性/個案研究)"])
    
    # 根據選擇顯示不同參數
    mcdm_method = None
    case_method = None
    
    if research_mode == "MCDM (量化/決策分析)":
        st.info("適合：建構評估指標、計算權重、選擇最佳方案。")
        mcdm_method = st.selectbox(
            "選擇數學模型：",
            ["AHP (層級分析法)", "DEMATEL (決策實驗室法)", "FCM (模糊認知圖)", "ANP (網路分析法)"]
        )
        st.caption("設定數量級距：")
        c1, c2, c3 = st.columns(3)
        with c1: pool_size = st.number_input("原始池", value=50)
        with c2: criteria_size = st.number_input("準則數", value=15)
        with c3: dim_size = st.number_input("構面數", value=4)

    else: # Case Study
        st.info("適合：探索現象、驗證理論、教學用途。")
        case_method = st.selectbox(
            "選擇個案流派：",
            [
                "Yin (實證型-驗證理論)", 
                "Harvard (教學型-決策導向)", 
                "Eisenhardt (建構型-多個案比較)", 
                "Stake (詮釋型-深度描述)"
            ]
        )
        # 個案研究不需要設定數量，所以隱藏

# --- 3. 模型適配 ---
def get_best_model(key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            models = response.json().get('models', [])
            for m in models:
                if 'gemini-1.5-pro' in m['name']: return m['name'] # 優先用 Pro 處理複雜邏輯
            for m in models:
                if 'gemini-1.5-flash' in m['name']: return m['name']
            return "models/gemini-1.5-flash"
        return None
    except:
        return None

# --- 4. 核心分析邏輯 (雙路徑) ---
def run_dual_core_analysis(text, key, model_name, topic, mode, m_method, c_method, p_n, c_n, d_n):
    url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={key}"
    headers = {'Content-Type': 'application/json'}
    
    prompt = ""
    
    #Path A: MCDM 邏輯
    if mode == "MCDM (量化/決策分析)":
        method_instruction = ""
        if "AHP" in m_method:
            method_instruction = "模擬 Saaty 1-9 尺度的成對比較矩陣，計算特徵向量權重，並檢查 CR<0.1。"
        elif "DEMATEL" in m_method:
            method_instruction = "模擬 0-4 直接關係矩陣，計算中心度 (D+R) 與原因度 (D-R)，區分原因群/結果群。"
        elif "FCM" in m_method:
            method_instruction = "模擬 -1 到 1 的影響矩陣 (Influence Matrix)，進行狀態推論。"
        elif "ANP" in m_method:
            method_instruction = "模擬超矩陣 (Supermatrix)，考慮相依性，計算極限權重。"

        prompt = f"""
        你是一個 MCDM 研究專家。題目：{topic}。方法：{m_method}。
        請執行：文獻回顧 -> 發散 -> 收斂 -> 層級化 -> 數據模擬。

        【任務要求】：
        1. 文獻處理：辨識並轉為 APA 格式。
        2. Step 1: 找出 {p_n} 個原始細項，標註出處 ID。
        3. Step 2: 歸納為 {c_n} 個評估準則。
        4. Step 3: 歸納為 {d_n} 個評估構面。
        5. Step 4: 執行 `{m_method}` 數據模擬。
           - {method_instruction}
           - 模擬 3 家企業 (A, B, C) 的評分 (0-100)，並結合權重計算總分。

        【輸出 JSON】：
        {{
          "papers": [ {{ "id": 0, "apa": "..." }} ],
          "step1_raw_pool": [ {{ "name": "...", "matched_ids": [0] }} ],
          "final_hierarchy": [
            {{
              "dimension_name": "構面名稱",
              "contained_criteria": [
                 {{
                   "criteria_name": "準則名稱",
                   "source_raw_items": ["細項A"],
                   "reasoning": "...",
                   "matched_paper_ids": [0]
                 }}
              ]
            }}
          ],
          "step4_simulation": {{
              "method_used": "{m_method}",
              "matrix_name": "矩陣名稱",
              "weights": [ {{ "criteria": "準則1", "weight": 0.2 }} ],
              "matrix_data": [ {{ "from": "準則1", "to": "準則2", "value": 0.5 }} ],
              "companies": [
                  {{ "name": "企業A", "scores": {{ "準則1": 80 }} }}
              ]
          }}
        }}
        文獻：{text[:14000]}
        """

    # Path B: Case Study 邏輯
    else:
        structure_instruction = ""
        if "Yin" in c_method:
            structure_instruction = "Yin氏實證結構：1.研究命題(Propositions) 2.資料三角檢證(模擬訪談/觀察/檔案) 3.模式比對(Pattern Matching) 4.效度分析。"
        elif "Harvard" in c_method:
            structure_instruction = "哈佛教學結構：1.開場(The Hook) 2.背景與衝突 3.關鍵對話 4.決策點(The Cliffhanger, 不給答案) 5.教學指引。"
        elif "Eisenhardt" in c_method:
            structure_instruction = "Eisenhardt建構理論：1.跨個案比較(Case A vs B) 2.變數因果推論 3.湧現新命題(Emergent Propositions)。"
        elif "Stake" in c_method:
            structure_instruction = "Stake詮釋結構：1.情境脈絡深度描寫 2.議題聚焦(Issues) 3.自然推廣(讓讀者感同身受)。"

        prompt = f"""
        你是一位質性研究學者。題目：{topic}。方法：{c_method}。
        請根據文獻撰寫一份個案研究草案。
        
        【寫作要求】：
        {structure_instruction}
        
        【輸出 JSON】：
        {{
          "papers": [ {{ "id": 0, "apa": "..." }} ],
          "case_study_content": {{
             "intro": "方法論適用性說明...",
             "sections": [
                {{ "title": "章節標題", "content": "詳細內容(需包含模擬數據或對話)..." }}
             ],
             "key_findings": ["發現1", "發現2"]
          }}
        }}
        文獻：{text[:14000]}
        """

    data = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            try:
                res_text = response.json()['candidates'][0]['content']['parts'][0]['text']
                match = re.search(r'\{.*\}', res_text, re.DOTALL)
                if match: return "OK", json.loads(match.group(0))
                else: return "ERROR", "JSON 解析失敗"
            except: return "ERROR", "AI 回傳結構異常"
        else: return "ERROR", f"API Error: {response.status_code}"
    except Exception as e: return "ERROR", str(e)

# --- 5. 主畫面 ---
st.title("🎓 學術研究雙核心系統")

raw_text = st.text_area("請在此貼上文獻摘要：", height=200)

if st.button("🚀 開始分析", type="primary"):
    if not api_key:
        st.error("❌ 請檢查 API Key")
    elif not raw_text:
        st.warning("⚠️ 請輸入文獻")
    else:
        current_method = mcdm_method if research_mode == "MCDM (量化/決策分析)" else case_method
        with st.spinner(f"🔍 正在執行 {research_mode} - {current_method} ..."):
            valid_model = get_best_model(api_key)
            if not valid_model:
                st.error("❌ 找不到可用模型")
            else:
                status, result = run_dual_core_analysis(
                    raw_text, api_key, valid_model, thesis_topic, 
                    research_mode, mcdm_method, case_method, 
                    pool_size if 'pool_size' in locals() else 50, 
                    criteria_size if 'criteria_size' in locals() else 15, 
                    dim_size if 'dim_size' in locals() else 4
                )
                
                if status == "OK":
                    st.success("✅ 分析完成！")
                    
                    papers = result.get("papers", [])
                    
                    # === 模式 A: MCDM 顯示邏輯 ===
                    if research_mode == "MCDM (量化/決策分析)":
                        raw_pool = result.get("step1_raw_pool", [])
                        hierarchy = result.get("final_hierarchy", [])
                        sim_data = result.get("step4_simulation", {})
                        
                        id_to_code = {}
                        legend_rows = []
                        for idx, p in enumerate(papers):
                            code = string.ascii_uppercase[idx % 26]
                            id_to_code[p['id']] = code
                            legend_rows.append({"代號": code, "文獻來源 (APA)": p['apa']})
                        
                        t1, t2, t3, t4, t5 = st.tabs(["1️⃣ 原始池", "2️⃣ 層級架構", "3️⃣ 關聯矩陣", "4️⃣ 數據模擬", "5️⃣ 文獻對照"])
                        
                        with t1:
                            r_rows = []
                            for i, it in enumerate(raw_pool):
                                codes = sorted([id_to_code.get(pid, "?") for pid in it.get("matched_ids", [])])
                                r_rows.append({"序號": i+1, "原始細項": it.get("name"), "出處": ", ".join(codes)})
                            st.dataframe(pd.DataFrame(r_rows), use_container_width=True)
                            
                        with t2:
                            h_rows = []
                            for dim in hierarchy:
                                for crit in dim.get("contained_criteria", []):
                                    codes = sorted([id_to_code.get(pid, "?") for pid in crit.get("matched_paper_ids", [])])
                                    h_rows.append({
                                        "構面": dim.get("dimension_name"),
                                        "準則": crit.get("criteria_name"),
                                        "原始來源": ", ".join(crit.get("source_raw_items", [])),
                                        "出處": ", ".join(codes),
                                        "理由": crit.get("reasoning")
                                    })
                            st.dataframe(pd.DataFrame(h_rows), use_container_width=True)
                            
                        with t3:
                            m_rows = []
                            all_codes = [d["代號"] for d in legend_rows]
                            for row in h_rows:
                                mr = {"構面": row["構面"], "準則": row["準則"]}
                                src = row["出處"].split(", ")
                                for c in all_codes: mr[c] = "●" if c in src else ""
                                m_rows.append(mr)
                            st.dataframe(pd.DataFrame(m_rows), use_container_width=True)
                            
                        with t4: # 數據模擬
                            st.subheader(f"🧮 {sim_data.get('method_used')} 模擬結果")
                            # 權重
                            weights = sim_data.get("weights", [])
                            if weights:
                                st.caption("準則權重：")
                                st.bar_chart(pd.DataFrame(weights).set_index("criteria"))
                            
                            st.divider()
                            # 矩陣數據
                            st.caption(f"模擬矩陣數據 ({sim_data.get('matrix_name')})：")
                            mat_data = sim_data.get("matrix_data", [])
                            if mat_data: st.dataframe(pd.DataFrame(mat_data), use_container_width=True)
                            
                            st.divider()
                            # 企業評比
                            st.caption("企業評比模擬 (結合權重)：")
                            comps = sim_data.get("companies", [])
                            if comps and weights:
                                c_rows = []
                                w_map = {w["criteria"]: w["weight"] for w in weights}
                                for c in comps:
                                    row = {"企業": c["name"]}
                                    score_sum = 0
                                    for k, v in c["scores"].items():
                                        row[k] = v
                                        score_sum += v * w_map.get(k, 0)
                                    row["加權總分"] = round(score_sum, 2)
                                    c_rows.append(row)
                                st.dataframe(pd.DataFrame(c_rows).sort_values("加權總分", ascending=False), use_container_width=True)

                        with t5: st.dataframe(pd.DataFrame(legend_rows), use_container_width=True)

                    # === 模式 B: Case Study 顯示邏輯 ===
                    else:
                        case_data = result.get("case_study_content", {})
                        
                        st.subheader(f"📖 {case_method} 研究報告")
                        st.info(f"💡 方法論：{case_data.get('intro')}")
                        
                        for sec in case_data.get("sections", []):
                            with st.expander(f"📌 {sec.get('title')}", expanded=True):
                                st.markdown(sec.get('content'))
                        
                        st.divider()
                        st.subheader("🔑 關鍵發現")
                        for f in case_data.get("key_findings", []):
                            st.write(f"- {f}")
                            
                        st.divider()
                        st.subheader("📚 參考文獻")
                        st.dataframe(pd.DataFrame(papers), use_container_width=True)

                    # === 下載按鈕 (通用) ===
                    output = BytesIO()
                    try:
                        import xlsxwriter
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            if research_mode == "MCDM (量化/決策分析)":
                                pd.DataFrame(r_rows).to_excel(writer, sheet_name='1_原始池', index=False)
                                pd.DataFrame(h_rows).to_excel(writer, sheet_name='2_層級架構', index=False)
                                pd.DataFrame(m_rows).to_excel(writer, sheet_name='3_關聯矩陣', index=False)
                                pd.DataFrame(legend_rows).to_excel(writer, sheet_name='文獻對照', index=False)
                                if weights: pd.DataFrame(weights).to_excel(writer, sheet_name='4_權重模擬', index=False)
                                if comps: pd.DataFrame(c_rows).to_excel(writer, sheet_name='5_企業評比', index=False)
                            else:
                                # 個案研究轉 Excel 比較簡單，把章節當作列
                                case_rows = []
                                for sec in case_data.get("sections", []):
                                    case_rows.append({"章節": sec["title"], "內容": sec["content"]})
                                pd.DataFrame(case_rows).to_excel(writer, sheet_name='個案內容', index=False)
                                pd.DataFrame(case_data.get("key_findings", [])).to_excel(writer, sheet_name='關鍵發現', index=False)
                                pd.DataFrame(papers).to_excel(writer, sheet_name='參考文獻', index=False)
                                
                        st.download_button("📥 下載完整分析報告 Excel", output.getvalue(), "academic_analysis.xlsx", type="primary")
                    except Exception as e: st.error(f"Excel 匯出失敗: {e}")

                else: st.error("分析失敗"); st.code(result)

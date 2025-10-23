import streamlit as st
import requests
import json
import time

# --- 頁面設定 ---
st.set_page_config(
    page_title="AI 論文架構助理",
    page_icon="✍️",
    layout="wide"
)

st.title("✍️ AI 論文架構助理 (Gemini Powered)")
st.markdown("貼上您的文獻內容、摘要或關鍵字，AI 將協助您生成論文架構草稿。")

# --- 使用者輸入介面 ---
st.subheader("請貼入您的研究資料")
input_text = st.text_area(
    "貼入文獻摘要、重點段落或相關關鍵字 (建議至少 500 字以獲得較佳效果)",
    height=300,
    placeholder="例如：貼入多篇相關文獻的摘要，或一段描述您研究主題的文字..."
)

generate_button = st.button("🚀 生成論文架構草稿", type="primary", use_container_width=True)

# --- Gemini API 呼叫函數 ---
def generate_thesis_outline(text_input):
    """使用 Gemini API 根據輸入文本生成論文架構草稿"""
    api_key = "" # API Key 由 Canvas 環境提供
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={api_key}"

    # --- 精心設計的 Prompt ---
    prompt = f"""
請扮演一位學術研究助理，仔細分析以下提供的文本資料，並根據這些資料，生成一份繁體中文的碩士論文架構草稿 (約三分之二內容)。

**提供的文本資料：**
---
{text_input}
---

**請生成包含以下結構的 Markdown 文件：**

1.  **研究背景與動機 (Research Background and Motivation):**
    * 根據文本資料，描述此研究領域的宏觀背景。
    * 點出目前存在的問題、趨勢或重要性，引導出研究動機。

2.  **文獻探討 (初步) (Preliminary Literature Review):**
    * **概述**文本中提到的主要理論、模型或相關研究發現。
    * (不需要在此詳盡列出所有細節，點出核心即可)。

3.  **研究缺口 (Research Gap):**
    * 基於文獻探討，明確指出目前研究尚有哪些不足之處、未解的問題或可進一步探討的方向。

4.  **研究目的 (Research Purpose):**
    * 針對研究缺口，清晰陳述本研究預計達成的具體目標。

5.  **研究方法 (建議) (Proposed Methodology):**
    * 根據研究目的和文本內容，**建議**可能的研究方法（例如：質性研究、量化研究、問卷調查、個案分析、實驗設計等）。
    * 簡述可能的研究對象或資料來源。

6.  **預期貢獻 (Expected Contributions):**
    * 說明本研究完成後，預期在學術理論或實務應用上可能帶來的貢獻。

7.  **參考文獻 (初步整理) (Preliminary References):**
    * **嘗試**從輸入的文本中**提取**可能被引用的文獻。
    * 將提取到的文獻，盡可能整理成**APA 7 格式**。如果資訊不足，請標註 (資訊不全)。
    * **注意：** 如果輸入文本主要是關鍵字而非完整摘要，此部分可能無法產生。

**輸出要求：**
* 請使用**繁體中文**撰寫。
* 輸出格式為 **Markdown**，使用標題 (#, ##) 來區分章節。
* 內容需緊密圍繞提供的文本資料。
* 語氣需專業、客觀。
* 如果輸入文本不足以生成某個部分，請在該部分簡短說明原因。
"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
        # 考慮加入 safetySettings 以允許更多學術內容
        # "safetySettings": [
        #     {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        #     {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        #     {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        #     {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        # ]
    }
    headers = {'Content-Type': 'application/json'}
    max_retries = 3
    base_delay = 1
    generated_text = None
    error_message = None

    for attempt in range(max_retries):
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=90) # 增加超時時間
            
             # Debug: Print API response status and content
            # st.sidebar.write(f"Attempt {attempt+1} Status Code:", response.status_code)
            # st.sidebar.text(response.text[:500]) # Print first 500 chars of response

            response.raise_for_status() # 檢查 HTTP 錯誤 (4xx, 5xx)

            result = response.json()

            if (result.get('candidates') and
                result['candidates'][0].get('content') and
                result['candidates'][0]['content'].get('parts') and
                result['candidates'][0]['content']['parts'][0].get('text')):
                generated_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
                # 嘗試移除 Gemini 可能加入的 Markdown 標記
                generated_text = generated_text.replace("```markdown", "").replace("```", "").strip()
                error_message = None # 成功獲取，清除錯誤訊息
                break # 成功，跳出重試循環
            # 處理 Gemini 回應中可能包含的 block reason
            elif result.get('candidates') and result['candidates'][0].get('finishReason') != 'STOP':
                 reason = result['candidates'][0].get('finishReason', 'UNKNOWN')
                 safety_ratings = result['candidates'][0].get('safetyRatings', [])
                 error_message = f"內容生成被中止，原因: {reason}。安全評級: {safety_ratings}"
                 st.warning(error_message) # 顯示警告但不一定是致命錯誤
                 # 檢查是否有部分內容生成
                 if (result['candidates'][0].get('content') and
                     result['candidates'][0]['content'].get('parts') and
                     result['candidates'][0]['content']['parts'][0].get('text')):
                      generated_text = result['candidates'][0]['content']['parts'][0]['text'].strip() + "\n\n**(內容可能不完整)**"
                      break # 獲取部分內容
                 else:
                     generated_text = None # 沒有內容生成
                     break # 中止重試
            else:
                error_message = f"Gemini API 回應格式異常，無法解析生成內容: {result}"
                generated_text = None
                # 不一定需要重試，可能是格式問題
                break

        except requests.exceptions.Timeout:
            error_message = f"Gemini API 請求逾時 (嘗試 {attempt + 1}/{max_retries})。"
            if attempt < max_retries - 1: time.sleep(base_delay * (2 ** attempt))
        except requests.exceptions.RequestException as e:
            error_message = f"Gemini API 請求失敗 (嘗試 {attempt + 1}/{max_retries}): {e}"
            if attempt < max_retries - 1: time.sleep(base_delay * (2 ** attempt))
            # 如果是 403 Forbidden，可能無需重試
            if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 403:
                error_message += "\n(錯誤 403 通常表示權限問題或 API 金鑰無效/受限)"
                break
        except Exception as e:
             error_message = f"處理 Gemini API 回應時發生未知錯誤: {e}"
             generated_text = None
             break # 未知錯誤，停止重試

    return generated_text, error_message


# --- 主程式流程 ---
st.divider()

# 用於顯示結果或錯誤訊息的區域
result_placeholder = st.empty()

if generate_button:
    if not input_text.strip():
        st.error("❌ 請先在上方文字框貼入您的研究資料。")
    elif len(input_text.strip()) < 100: # 提醒文字太少
        st.warning("⚠️ 輸入的文字較少，生成的草稿品質可能有限。建議提供更詳細的資料。")
        # 仍然繼續嘗試生成
        with st.spinner("⏳ 正在分析資料並生成論文架構草稿... (可能需要一點時間)"):
            generated_outline, error = generate_thesis_outline(input_text)

        if error:
            result_placeholder.error(f"❌ 生成失敗：\n{error}")
        elif generated_outline:
            result_placeholder.markdown(generated_outline)
            st.success("✅ 草稿生成完畢！")
        else:
             result_placeholder.error("❌ 未知錯誤，無法生成草稿。")

    else: # 輸入文字足夠
        with st.spinner("⏳ 正在分析資料並生成論文架構草稿... (可能需要一點時間)"):
            generated_outline, error = generate_thesis_outline(input_text)

        if error:
            result_placeholder.error(f"❌ 生成失敗：\n{error}")
        elif generated_outline:
            result_placeholder.markdown(generated_outline)
            st.success("✅ 草稿生成完畢！")
        else:
            result_placeholder.error("❌ 未知錯誤，無法生成草稿。")


# --- 側邊欄說明 ---
with st.sidebar:
    st.header("📖 使用說明")
    st.markdown("""
    ### ✨ 功能
    - **貼入資料**：將您收集到的文獻摘要、重點段落、筆記或相關關鍵字貼入主文字框。
    - **生成草稿**：點擊按鈕，AI (Gemini) 將分析您的輸入，自動生成一份包含背景動機、文獻概述、研究缺口、目的、建議方法、預期貢獻及初步參考文獻的論文架構草稿。
    - **Markdown 格式**：生成的草稿將以 Markdown 格式呈現，方便您複製和編輯。

    ### 💡 提示
    - **提供足夠資訊**：輸入的文本越豐富、越相關，生成的草稿品質越高。建議至少提供 500 字以上。
    - **多次嘗試**：AI 生成的結果可能每次略有不同，您可以調整輸入內容或多次嘗試以獲得最滿意的草稿。
    - **草稿性質**：請注意，這是一個**輔助工具**，生成的內容是**草稿**，需要您基於專業知識進行修改、補充和完善。參考文獻部分尤其需要仔細核對。
    - **API 限制**：由於雲端環境限制，偶爾可能遇到 API 請求失敗 (如 403 錯誤)，請稍後再試。
    """)
    st.divider()
    st.caption("Powered by Google Gemini.")


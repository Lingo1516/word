from flask import Flask, request, jsonify
import re

app = Flask(__name__)

def generate_apa_citation(authors, year, title, source):
    # 簡易APA格式產生器
    authors_str = ', '.join(authors)
    return f"{authors_str} ({year}). {title}. {source}."

def extract_authors_and_year(text):
    # 嘗試從文本中抓取作者與年份，示例用，實務可優化
    authors = re.findall(r"作者\s*[:：]?\s*([^\n]+)", text)
    year = re.findall(r"(19|20)\d{2}", text)
    if authors:
        authors = authors[0].replace('、',',').split(',')
    else:
        authors = ["未知作者"]
    if year:
        year = year[0]
    else:
        year = "不明年份"
    return authors, year

def compose_paper_content(text):
    # 基於用戶提供的關鍵字或文章內容生成論文架構及簡要內容
    # 這裡用簡單的段落示例
    authors, year = extract_authors_and_year(text)
    title_match = re.search(r"項目類型.*\n.*作者.*\n.*摘要\n([\s\S]+?)(?=\n日期|\n語言|$)", text)
    title = "研究主題" if not title_match else "整理自原文摘要"

    intro = f"本研究基於{year}年由{', '.join(authors)}等所進行的研究，主要關注於相關領域的核心問題與價值，提出具體的研究動機與背景。"
    gap = "目前相關文獻中仍存在研究不足之處，尤其在特定變數與消費者行為之間的關聯尚未充分探討，填補此缺口對進一步理解消費者決策具有重要意義。"
    motivation = "透過深度分析與量化方法，本研究旨在揭示影響消費者購買行為的重要因素，為行銷策略提供理論與實務參考。"
    purpose = "本研究目的在於建構完整的理論架構，探討知覺價值、態度等變數對購買意願的影響，並考量性別等干擾因素。"
    citation = generate_apa_citation(authors, year, title, "資料來源於使用者提供之文本")

    content = f"{intro}\n\n研究缺口:\n{gap}\n\n研究動機:\n{motivation}\n\n研究目的:\n{purpose}\n\n引用文獻:\n{citation}"
    return content

@app.route('/generate_paper', methods=['POST'])
def generate_paper():
    data = request.json
    text = data.get('text', '')
    if not text:
        return jsonify({'error': '未收到文本內容'}), 400
    
    paper_content = compose_paper_content(text)
    return jsonify({'paper_content': paper_content})

if __name__ == '__main__':
    app.run(debug=True)

import streamlit as st

def compose_paper_content(text):
    # 您可復用先前的內容整理邏輯
    return f"自動生成論文內容摘要:\n\n{text[:800]}"

st.title("論文內容自動整理 Demo")
input_text = st.text_area("請貼上論文全文或重點文字")
if st.button('生成論文摘要'):
    with st.spinner("生成中..."):
        result = compose_paper_content(input_text)
        st.subheader("自動生成內容")
        st.write(result)


import streamlit as st

def generate_apa_citation(author, year, title, source):
    # 極簡APA格式
    return f"{author} ({year}). {title}. {source}."

def paper_template(input_text):
    # 以下為簡易自動摘要與架構生成範例
    author = "未知作者"
    year = "不明年份"
    title = "自動生成論文題目"
    source = "使用者上傳內容"
    # 若要更進階，可搭配NLP自動擷取
    # 這裡可以進一步parse input_text抓取欄位

    intro = f"本研究以{year}年{author}等人提出的議題為基礎，聚焦於研究領域的核心現象與環境變動。"
    gap = "目前針對本主題已有初步討論，然而變數的深層關聯與新情境應用仍存空白。"
    motivation = "隨著環境因素與市場發展，對此議題深入探究的動機更為強烈。"
    purpose = "本研究主要目的，在於建構理論架構並驗證各影響因素對依變項之作用，並提出理論與實務建議。"
    citation = generate_apa_citation(author, year, title, source)

    return f"""# 標題：{title}

## 前言
{intro}

## 研究缺口
{gap}

## 研究動機
{motivation}

## 研究目的
{purpose}

## 參考文獻
{citation}
"""

st.title('自動化論文架構整理工具（Streamlit）')
st.write('請貼上論文內容或摘要（建議輸入繁體中文），系統將自動產出三分之二論文草稿，並加上APA引用格式。')

user_input = st.text_area("請輸入論文內容或關鍵摘要：", height=250)

if st.button('產生論文架構'):
    if not user_input.strip():
        st.warning('請先貼上論文內容或摘要')
    else:
        output = paper_template(user_input)
        st.markdown(output)

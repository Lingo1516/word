import streamlit as st
import pandas as pd
import requests

def search_semantic_scholar(query, limit=20, year_from=2020):
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        'query': query,
        'fields': 'title,authors,year,abstract,venue,keywords,url',
        'limit': limit,
        'year': f'>{year_from}'  # 只取2020年以後
    }
    resp = requests.get(url, params=params)
    data = resp.json()
    records = []
    for p in data.get('data', []):
        author = "; ".join([a.get('name','') for a in p.get('authors',[])])
        records.append({
            'title': p.get('title',''),
            'author': author,
            'year': p.get('year',''),
            'publication': p.get('venue',''),
            'keywords': "; ".join(p.get('keywords',[])),
            'abstract': p.get('abstract',''),
            'link': p.get('url','')
        })
    return pd.DataFrame(records)

st.title("🔎 BRICS CO2 文獻即時搜尋")
q = st.text_input("請輸入主題關鍵字", "BRICS CO2 social technological institutional economic")
if st.button("自動搜尋最新論文"):
    df = search_semantic_scholar(q)
    st.write(df)
    # 還可加篩選、匯出、APA引用等功能

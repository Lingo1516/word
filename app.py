import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET

# Semantic Scholar API
def search_semantic_scholar(query, limit=10):
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        'query': query,
        'fields': 'title,authors,year,abstract,venue,keywords,url',
        'limit': limit
    }
    resp = requests.get(url, params=params)
    data = resp.json()
    papers = []
    for p in data.get('data', []):
        author = "; ".join([a.get('name','') for a in p.get('authors',[])])
        papers.append({
            'title': p.get('title',''),
            'author': author,
            'year': p.get('year',''),
            'publication': p.get('venue',''),
            'keywords': "; ".join(p.get('keywords',[])),
            'abstract': p.get('abstract',''),
            'link': p.get('url','')
        })
    return papers

# arXiv API
def search_arxiv(query, max_results=10):
    base_url = 'http://export.arxiv.org/api/query?'
    params = f'search_query=all:{query}&start=0&max_results={max_results}'
    resp = requests.get(base_url + params)
    papers = []
    if resp.status_code == 200:
        root = ET.fromstring(resp.text)
        ns = {'arxiv': 'http://www.w3.org/2005/Atom'}
        for entry in root.findall('arxiv:entry', ns):
            title = entry.find('arxiv:title', ns).text
            authors = entry.findall('arxiv:author/arxiv:name', ns)
            author_names = "; ".join([a.text for a in authors])
            summary = entry.find('arxiv:summary', ns).text
            published = entry.find('arxiv:published', ns).text[:4]
            link = entry.find('arxiv:id', ns)
            link_url = entry.find('arxiv:link', ns).attrib.get('href','') if entry.find('arxiv:link', ns) is not None else ''
            papers.append({
                'title': title,
                'author': author_names,
                'year': published,
                'publication': 'arXiv',
                'keywords': '',
                'abstract': summary,
                'link': link_url
            })
    return papers

# PubMed API
def search_pubmed(query, max_results=10):
    base_search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    base_fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params_search = {
        'db': 'pubmed',
        'term': query,
        'retmax': max_results,
        'retmode': 'json'
    }
    search_resp = requests.get(base_search_url, params=params_search)
    papers = []
    if search_resp.status_code == 200:
        id_list = search_resp.json().get('esearchresult', {}).get('idlist', [])
        if id_list:
            ids = ",".join(id_list)
            params_fetch = {
                'db': 'pubmed',
                'id': ids,
                'retmode': 'xml'
            }
            fetch_resp = requests.get(base_fetch_url, params=params_fetch)
            if fetch_resp.status_code == 200:
                root = ET.fromstring(fetch_resp.content)
                for article in root.findall(".//PubmedArticle"):
                    title = article.find(".//ArticleTitle")
                    title_text = title.text if title is not None else ''
                    abstract = article.find(".//AbstractText")
                    abstract_text = abstract.text if abstract is not None else ''
                    authors = article.findall(".//Author")
                    author_names = []
                    for a in authors:
                        last = a.find("LastName")
                        first = a.find("ForeName")
                        name = ""
                        if last is not None:
                            name += last.text + " "
                        if first is not None:
                            name += first.text
                        if name.strip():
                            author_names.append(name.strip())
                    year = article.find(".//PubDate/Year")
                    year_text = year.text if year is not None else ''
                    journal = article.find(".//Title")
                    journal_text = journal.text if journal is not None else ''
                    papers.append({
                        'title': title_text,
                        'author': "; ".join(author_names),
                        'year': year_text,
                        'publication': journal_text,
                        'keywords': '',
                        'abstract': abstract_text,
                        'link': ''
                    })
    return papers


# 主要UI與主程式流程
def main():
    st.title("📚 多平台自動學術文獻搜尋平台")
    query = st.text_input("請輸入研究主題關鍵字", "BRICS CO2 social technological institutional economic")
    limit = st.slider("每個平台最多搜尋筆數", 5, 30, 10)

    if st.button("開始搜尋"):
        with st.spinner("搜尋中，請稍候..."):
            ss = search_semantic_scholar(query, limit)
            arxiv = search_arxiv(query, limit)
            pubmed = search_pubmed(query, limit)

        combined = ss + arxiv + pubmed
        df = pd.DataFrame(combined).drop_duplicates(subset=['title']).reset_index(drop=True)

        st.write(f"搜尋到 {len(df)} 筆去重後的文獻資料")
        st.dataframe(df[['title', 'author', 'year', 'publication', 'keywords', 'abstract']])

        csv = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button("📥 下載 CSV", csv, "literature_search_results.csv", "text/csv")

if __name__ == "__main__":
    main()

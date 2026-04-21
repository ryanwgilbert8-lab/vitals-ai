import requests
import time
import os
import xml.etree.ElementTree as ET
from openai import OpenAI
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
supabase_client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

QUERIES = [
    "heart rate variability athletes recovery",
    "sleep quality athletic performance",
    "overtraining syndrome HRV",
    "resting heart rate sport performance",
    "HRV recovery monitoring wearable",
    "sleep deprivation sports performance",
    "autonomic nervous system athlete training",
    "recovery metrics endurance athletes"
]

def fetch_pubmed_ids(query, max_results=500):
    response = requests.get(f"{BASE}/esearch.fcgi", params={
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json"
    })
    return response.json()["esearchresult"]["idlist"]

def fetch_abstracts(ids):
    response = requests.get(f"{BASE}/efetch.fcgi", params={
        "db": "pubmed",
        "id": ",".join(ids),
        "rettype": "abstract",
        "retmode": "xml"
    })
    return response.text

def parse_articles(xml_text):
    papers = []
    try:
        root = ET.fromstring(xml_text)
        for article in root.findall('.//PubmedArticle'):
            title = article.findtext('.//ArticleTitle', '')
            abstract_parts = article.findall('.//AbstractText')
            abstract = ' '.join([p.text or '' for p in abstract_parts])
            year_el = article.find('.//PubDate/Year')
            year = int(year_el.text) if year_el is not None else None
            if title and abstract and len(abstract) > 100:
                papers.append({'title': title, 'abstract': abstract, 'year': year})
    except Exception as e:
        print(f"Parse error: {e}")
    return papers

def embed_and_store(paper):
    try:
        text = f"{paper['title']}. {paper['abstract']}"[:8000]
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        embedding = response.data[0].embedding
        supabase_client.table('papers').insert({
            'title': paper['title'],
            'abstract': paper['abstract'],
            'year': paper['year'],
            'source': 'pubmed',
            'embedding': embedding
        }).execute()
        return True
    except Exception as e:
        print(f"Error storing paper: {e}")
        return False

def main():
    all_ids = set()
    print("Fetching paper IDs...")
    for query in QUERIES:
        ids = fetch_pubmed_ids(query)
        all_ids.update(ids)
        print(f"  '{query}': {len(ids)} papers found")
        time.sleep(0.5)

    all_ids = list(all_ids)
    print(f"\nTotal unique papers: {len(all_ids)}")
    print("Fetching abstracts and embedding...")

    stored = 0
    for i in range(0, len(all_ids), 100):
        batch = all_ids[i:i+100]
        xml = fetch_abstracts(batch)
        papers = parse_articles(xml)
        for paper in papers:
            if embed_and_store(paper):
                stored += 1
                if stored % 50 == 0:
                    print(f"  Stored {stored} papers...")
        time.sleep(0.35)

    print(f"\nDone. Total papers stored: {stored}")

if __name__ == "__main__":
    main()

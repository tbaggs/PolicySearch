import os
import csv
from typing import List
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from openai import AzureOpenAI
import uuid

load_dotenv()

SEARCH_ENDPOINT = os.getenv('AZURE_SEARCH_ENDPOINT')
SEARCH_KEY = os.getenv('AZURE_SEARCH_ADMIN_KEY')
INDEX_NAME = os.getenv('AZURE_SEARCH_INDEX_NAME', 'policies-index')
CSV_PATH = os.getenv('CSV_PATH', 'c:/Source/AI-Policy-Agent/PolicyDocTitles.csv')

AOAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
AOAI_KEY = os.getenv('AZURE_OPENAI_API_KEY')
AOAI_DEPLOYMENT = os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT')
AOAI_API_VERSION = os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-15-preview')

if not (SEARCH_ENDPOINT and SEARCH_KEY):
    raise SystemExit('Missing AZURE_SEARCH_ENDPOINT or AZURE_SEARCH_ADMIN_KEY')
if not (AOAI_ENDPOINT and AOAI_KEY and AOAI_DEPLOYMENT):
    raise SystemExit('Missing Azure OpenAI settings')

search = SearchClient(SEARCH_ENDPOINT, INDEX_NAME, AzureKeyCredential(SEARCH_KEY))
openai = AzureOpenAI(azure_endpoint=AOAI_ENDPOINT, api_key=AOAI_KEY, api_version=AOAI_API_VERSION)

BATCH = 64

def embed_batch(texts: List[str]) -> List[List[float]]:
    resp = openai.embeddings.create(input=texts, model=AOAI_DEPLOYMENT)
    ordered = sorted(resp.data, key=lambda d: d.index)
    return [d.embedding for d in ordered]

def main():
    rows = []
    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    docs = []
    for i in range(0, len(rows), BATCH):
        chunk = rows[i:i+BATCH]
        titles = [r.get('Title') or '' for r in chunk]
        vectors = embed_batch(titles)
        for r, vec in zip(chunk, vectors):
            title = r.get('Title') or ''
            url = r.get('URL') or ''
            primary = (r.get('Primary') or '').strip().lower() == 'true'
            secondary = (r.get('Secondary') or '').strip().lower() == 'true'
            docs.append({
                'Id': str(uuid.uuid4()),
                'PolicyURL': url,  # key field
                'PolicyTitle': title,
                'PrimaryPolicy': primary,
                'SecondaryPolicy': secondary,
                'PolicyTitleVector': vec
            })

    for i in range(0, len(docs), BATCH):
        batch = docs[i:i+BATCH]
        results = search.upload_documents(batch)
        failures = [r for r in results if not r.succeeded]
        if failures:
            print(f"Batch {i//BATCH}: {len(failures)} failures")
        print(f"Uploaded {min(i+BATCH, len(docs))}/{len(docs)}")

    print('Ingestion complete.')

if __name__ == '__main__':
    main()

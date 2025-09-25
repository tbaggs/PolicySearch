import os
import sys
import json
from typing import List
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from openai import AzureOpenAI

load_dotenv()

SEARCH_ENDPOINT = os.getenv('AZURE_SEARCH_ENDPOINT')
SEARCH_KEY = os.getenv('AZURE_SEARCH_ADMIN_KEY')
INDEX_NAME = os.getenv('AZURE_SEARCH_INDEX_NAME', 'policies-index')
SEMANTIC_CONFIG = os.getenv('AZURE_SEARCH_SEMANTIC_CONFIG', 'policies-semantic')

AOAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
AOAI_KEY = os.getenv('AZURE_OPENAI_API_KEY')
AOAI_DEPLOYMENT = os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT')
AOAI_API_VERSION = os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-15-preview')

if not (SEARCH_ENDPOINT and SEARCH_KEY and AOAI_ENDPOINT and AOAI_KEY):
    raise SystemExit('Missing environment. Check .env')

search = SearchClient(SEARCH_ENDPOINT, INDEX_NAME, AzureKeyCredential(SEARCH_KEY))
openai = AzureOpenAI(azure_endpoint=AOAI_ENDPOINT, api_key=AOAI_KEY, api_version=AOAI_API_VERSION)
queryType = "vectoronly" # Could be hybrid, vectorOnly or semantic


def embed(texts: List[str]):
    resp = openai.embeddings.create(input=texts, model=AOAI_DEPLOYMENT)
    ordered = sorted(resp.data, key=lambda d: d.index)
    return [d.embedding for d in ordered]

query = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else 'Covid-19 Time Off Policy'


match queryType.lower():
    case "hybrid":

        # For hybrid search we need the embedding vector too
        if not AOAI_DEPLOYMENT:
            raise SystemExit('Missing AZURE_OPENAI_EMBEDDING_DEPLOYMENT for hybrid (vector) search.')
        vec = embed([query])[0]

        # Hybrid search: include keyword text and vector query together
        results = search.search(
            search_text=query,
            vector_queries=[{
                'kind': 'vector',
                'vector': vec,
                'fields': 'PolicyTitleVector',
                'k_nearest_neighbors_count': 5
            }],
            select=["PolicyTitle", "PolicyURL", "PrimaryPolicy", "SecondaryPolicy"],
            top=10
        )

    case "vectoronly":

        # For hybrid search we need the embedding vector too
        if not AOAI_DEPLOYMENT:
            raise SystemExit('Missing AZURE_OPENAI_EMBEDDING_DEPLOYMENT for hybrid (vector) search.')
        vec = embed([query])[0]

        # Hybrid search: include keyword text and vector query together
        results = search.search(
            search_text=None,
            vector_queries=[{
                'kind': 'vector',
                'vector': vec,
                'fields': 'PolicyTitleVector',
                'k_nearest_neighbors_count': 5
            }],
            select=["PolicyTitle", "PolicyURL", "PrimaryPolicy", "SecondaryPolicy"],
            top=10
        )

    case "semantic":
        #Semantic only search
        results = search.search(
            search_text=query,
            query_type='semantic',
            #query_rewrites="generative|count-5",
            #query_language="en",
            #debug="queryRewrites",
            semantic_configuration_name=SEMANTIC_CONFIG,
            select=["PolicyTitle", "PolicyURL", "PrimaryPolicy", "SecondaryPolicy"],
            top=10
        )

    case _:
        print(f"Unknown queryType '{queryType}', defaulting to 'hybrid'")
        queryType = "hybrid"



scored = []
for r in results:
    score = r.get('@search.score', 0.0)
    if r['PolicyTitle'] != query:
        scored.append({
            'title': r['PolicyTitle'],
            'url': r['PolicyURL'],
            'score': float(score)
        })

for item in scored:
    print(f"{item['title']} | score={item['score']:.3f} | {item['url']}")

# Prepare list for LLM prompt
titles_list = [s['title'] for s in scored]
chat_deployment = os.getenv('AZURE_OPENAI_CHAT_DEPLOYMENT')

if chat_deployment and titles_list:
    user_prompt = (
        f"Look at the following list and extract only the titles that are directly related to: {query}\n\n"
        f"List:\n" + "\n".join(f"- {t}" for t in titles_list) +
        "\n\nReturn a JSON array of the exact matching titles only."
    )

    try:
        resp = openai.chat.completions.create(
            model=chat_deployment,
            messages=[
                {"role": "system", "content": "You are a precise assistant that returns only the requested JSON with no commentary."},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )

        text = resp.choices[0].message.content.strip()

        try:
            related = json.loads(text)
            if isinstance(related, list):
                print("\nDirectly related titles (LLM-filtered):")
                for t in related:
                    print(f"- {t}")
            else:
                print("\nLLM response:")
                print(text)
        except json.JSONDecodeError:
            print("\nLLM response (couldn't parse JSON):")
            print(text)
    except Exception as e:
        print(f"\nLLM filtering failed: {e}")
else:
    if not chat_deployment:
        print("\nTip: Set AZURE_OPENAI_CHAT_DEPLOYMENT in .env to enable LLM-based filtering of related titles.")


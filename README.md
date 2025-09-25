# AI Policy Agent (Python Only)

This project builds an Azure AI Search index of policy titles from `PolicyDocTitles.csv` and enables vector search of similar titles using Azure OpenAI embeddings.

## Options
- Direct ingest (client-side embeddings): generate embeddings locally and upload docs
- Indexer pipeline (service-side embeddings): CSV in Blob Storage + Skillset (Azure OpenAI Embedded Skill)

## Prerequisites
- Azure AI Search (endpoint + admin key)
- Azure OpenAI with an embeddings deployment
- Python 3.10+

## Setup
```pwsh
cd c:\Source\AI-Policy-Agent
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.template .env
# Edit .env with your values
```

## Configure environment
Edit `.env`:
- AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_ADMIN_KEY
- AZURE_SEARCH_INDEX_NAME (default: policies-index)
- AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_EMBEDDING_DEPLOYMENT, AZURE_OPENAI_API_VERSION
- EMBEDDING_DIMENSIONS (default 1536, must match your embedding model)
- CSV_PATH (optional, defaults to `c:/Source/AI-Policy-Agent/PolicyDocTitles.csv`)

## Create or reset the index
```pwsh
python src_py/create_index.py
```

## Option A: Direct ingest (client-side embeddings)
```pwsh
python src_py/ingest_csv.py
python src_py/search_similar.py "covid time off"
```

## Option B: Indexer pipeline (Blob + Skillset)
1) Upload CSV to Blob Storage:
```pwsh
python src_py/upload_to_blob.py
```
2) Create/Update data source, skillset, and indexer:
```pwsh
python src_py/create_indexer_pipeline.py
```
3) Run the indexer (examples):
```pwsh
# PowerShell
$api = (Get-Content .env | Select-String 'AZURE_SEARCH_ADMIN_KEY' | ForEach-Object { $_ })
# Or just run the curl printed by the script
```

Notes
- Index fields: PolicyURL (key), PolicyTitle, PrimaryPolicy, SecondaryPolicy, PolicyTitleVector
- EMBEDDING_DIMENSIONS must match your embedding model
- CSV headers expected: Title,URL,Primary,Secondary

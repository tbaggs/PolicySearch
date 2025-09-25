import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

SEARCH_ENDPOINT = os.getenv('AZURE_SEARCH_ENDPOINT')
SEARCH_KEY = os.getenv('AZURE_SEARCH_ADMIN_KEY')
INDEX_NAME = os.getenv('AZURE_SEARCH_INDEX_NAME', 'policies-index')

API_VERSION = os.getenv('AZURE_SEARCH_API_VERSION', '2024-07-01')

STORAGE_CONN = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
STORAGE_CONTAINER = os.getenv('AZURE_STORAGE_CONTAINER', 'policies')
BLOB_NAME = os.getenv('BLOB_NAME', 'PolicyDocTitles.csv')

AOAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
AOAI_KEY = os.getenv('AZURE_OPENAI_API_KEY')
AOAI_DEPLOYMENT = os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT')

if not (SEARCH_ENDPOINT and SEARCH_KEY):
    raise SystemExit('Missing AZURE_SEARCH_ENDPOINT or AZURE_SEARCH_ADMIN_KEY')
if not (STORAGE_CONN and STORAGE_CONTAINER and BLOB_NAME):
    raise SystemExit('Missing Azure Storage settings for data source')
if not (AOAI_ENDPOINT and AOAI_KEY and AOAI_DEPLOYMENT):
    raise SystemExit('Missing Azure OpenAI settings for skillset')

headers = {
    'Content-Type': 'application/json',
    'api-key': SEARCH_KEY
}

base = SEARCH_ENDPOINT.rstrip('/')

def put(path: str, payload: dict):
    url = f"{base}{path}?api-version={API_VERSION}"
    resp = requests.put(url, headers=headers, data=json.dumps(payload))
    if resp.status_code >= 300:
        raise RuntimeError(f"PUT {url} failed: {resp.status_code} {resp.text}")
    return resp.json() if resp.text else {}

# 1) Create/Update Data Source
DS_NAME = 'policies-ds'

datasource = {
    'name': DS_NAME,
    'type': 'azureblob',
    'credentials': { 'connectionString': STORAGE_CONN },
    'container': { 'name': STORAGE_CONTAINER, 'query': BLOB_NAME },
    'description': 'Policy titles CSV in blob storage'
}

print('Creating/Updating data source...')
put('/datasources', datasource)
print('Data source ready.')

# 2) Create/Update Skillset with Azure OpenAI Embedding Skill
SKILLSET_NAME = 'policies-skillset'

skillset = {
    'name': SKILLSET_NAME,
    'description': 'Embed policy titles using Azure OpenAI',
    'skills': [
        {
            '@odata.type': '#Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill',
            'description': 'Generate vector from PolicyTitle',
            'context': '/document',
            'resourceUri': AOAI_ENDPOINT,
            'deploymentName': AOAI_DEPLOYMENT,
            'apiKey': AOAI_KEY,
            'inputs': [ { 'name': 'text', 'source': '/document/PolicyTitle' } ],
            'outputs': [ { 'name': 'embedding', 'targetName': 'PolicyTitleVector' } ]
        }
    ]
}

print('Creating/Updating skillset...')
put('/skillsets', skillset)
print('Skillset ready.')

# 3) Create/Update Indexer to map CSV -> index + skill output
INDEXER_NAME = 'policies-indexer'

indexer = {
    'name': INDEXER_NAME,
    'dataSourceName': DS_NAME,
    'targetIndexName': INDEX_NAME,
    'skillsetName': SKILLSET_NAME,
    'parameters': {
        'configuration': {
            'parsingMode': 'delimitedText',
            'firstLineContainsHeaders': True,
            'delimitedTextHeaders': [ 'Title', 'URL', 'Primary', 'Secondary' ],
            'delimitedTextDelimiter': ','
        }
    },
    'fieldMappings': [
        { 'sourceFieldName': 'Title', 'targetFieldName': 'PolicyTitle' },
        { 'sourceFieldName': 'URL', 'targetFieldName': 'PolicyURL' },
        { 'sourceFieldName': 'Primary', 'targetFieldName': 'PrimaryPolicy', 'mappingFunction': { 'name': 'parseBoolean' } },
        { 'sourceFieldName': 'Secondary', 'targetFieldName': 'SecondaryPolicy', 'mappingFunction': { 'name': 'parseBoolean' } }
    ],
    'outputFieldMappings': [
        { 'sourceFieldName': '/document/PolicyTitleVector', 'targetFieldName': 'PolicyTitleVector' }
    ]
}

print('Creating/Updating indexer...')
put('/indexers', indexer)
print('Indexer ready.')

print('All indexer resources created. To run the indexer:')
print(f"curl -X POST -H 'api-key: {SEARCH_KEY}' '{base}/indexers/{INDEXER_NAME}/run?api-version={API_VERSION}'")

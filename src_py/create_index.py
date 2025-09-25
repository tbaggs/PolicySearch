import os
from dotenv import load_dotenv
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import SearchIndex, SimpleField, SearchField, SearchFieldDataType, HnswAlgorithmConfiguration, VectorSearch, VectorSearchProfile
from azure.core.credentials import AzureKeyCredential

load_dotenv()

endpoint = os.getenv('AZURE_SEARCH_ENDPOINT')
admin_key = os.getenv('AZURE_SEARCH_ADMIN_KEY')
index_name = os.getenv('AZURE_SEARCH_INDEX_NAME', 'policies-index')
embedding_dimensions = int(os.getenv('EMBEDDING_DIMENSIONS', '1536'))

if not endpoint or not admin_key:
    raise SystemExit('Missing AZURE_SEARCH_ENDPOINT or AZURE_SEARCH_ADMIN_KEY')

client = SearchIndexClient(endpoint, AzureKeyCredential(admin_key))

fields = [
    # Use PolicyURL as the unique key
    SimpleField(name='Id', type=SearchFieldDataType.String, key=True),
    SimpleField(name='PolicyURL', type=SearchFieldDataType.String, key=False),
    SearchField(name='PolicyTitle', type=SearchFieldDataType.String, searchable=True, analyzer_name='en.microsoft'),
    SimpleField(name='PrimaryPolicy', type=SearchFieldDataType.Boolean, filterable=True, facetable=True),
    SimpleField(name='SecondaryPolicy', type=SearchFieldDataType.Boolean, filterable=True, facetable=True),
    SearchField(name='PolicyTitleVector', type=SearchFieldDataType.Collection(SearchFieldDataType.Single), searchable=True, vector_search_dimensions=embedding_dimensions, vector_search_profile_name='vector-profile')
]

index = SearchIndex(
    name=index_name,
    fields=fields,
    vector_search=VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name='hnsw')],
        profiles=[VectorSearchProfile(name='vector-profile', algorithm_configuration_name='hnsw')]
    )
)

try:
    try:
        client.delete_index(index_name)
    except Exception:
        pass
    client.create_index(index)
    print(f"Index '{index_name}' created.")
except Exception as e:
    raise SystemExit(f'Failed to create index: {e}')

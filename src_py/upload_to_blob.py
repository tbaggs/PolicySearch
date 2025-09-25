import os
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient

load_dotenv()

CONN = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
CONTAINER = os.getenv('AZURE_STORAGE_CONTAINER', 'policies')
BLOB_NAME = os.getenv('BLOB_NAME', 'PolicyDocTitles.csv')
CSV_PATH = os.getenv('CSV_PATH', 'c:/Source/AI-Policy-Agent/PolicyDocTitles.csv')

if not CONN:
    raise SystemExit('Missing AZURE_STORAGE_CONNECTION_STRING')

svc = BlobServiceClient.from_connection_string(CONN)
client = svc.get_container_client(CONTAINER)
client.create_container(exist_ok=True)

with open(CSV_PATH, 'rb') as f:
    client.upload_blob(name=BLOB_NAME, data=f, overwrite=True)

print(f'Uploaded {CSV_PATH} to container {CONTAINER} as {BLOB_NAME}.')

## Run once
Run `create_elastic_index.ipynb` to create index with correct mappings

## Run Server
`python3 main.py`

## APIs

### Upload presentations
`http://127.0.0.1:8080/api/presentation/upload-documents`

Form Data:
files[] : files to upload
path    : "/ppt"

Result:
JSON

### Search & Generate Presentation
`http://127.0.0.1:8080/api/presentation/upload-documents`

Queries:
query   : "query"

Result:
attachment
import os
import sys
import pprint
from pathlib import Path

from tqdm import tqdm
from elasticsearch.helpers import bulk, BulkIndexError
from elasticsearch.exceptions import BadRequestError, NotFoundError

from app.config import Config
from app.models.elasticClient import ElasticClient
from app.utils.presentationmanager import PresentationManager

class ElasticService:

    INDEX = Config.ELASTIC_INDEX
    REQUEST_TIMEOUT = Config.REQUEST_TIMEOUT
    MAX_RETRIES = Config.REQUEST_TIMEOUT
    pp = pprint.PrettyPrinter(depth=6)  

    @staticmethod
    def search_in_index(query, user_id, index=INDEX, size=10):
        es = ElasticClient.connect()
        from_index = 0

        try:
            resp = es.search(
                        index=index,
                        size=size,
                        from_=from_index,
                        query={"bool": {
                            "must": [
                                {"match" : {
                                    "content": {
                                        "query": query,
                                        "fuzziness": "AUTO"
                                    }                        
                                }},
                                {"term": {
                                    "user_id": str(user_id)
                                }}                                    
                            ]
                        }},
                        highlight={"fields": {
                            "content": {}
                            }},
                    )
        except BadRequestError as e:
            print(f"{e} at {index}")
            return None
        
        return resp['hits']
    
    @staticmethod
    def index_single(data, index=INDEX):
        es = ElasticClient.connect()
        # Get document ID
        doc_id = data['_id']['$oid'] if isinstance(data['_id'], dict) else str(data['_id'])
        # Get only relevant fields from document
        doc = ElasticService._strip_document(data)
        if not doc:
            return []        
        resp = es.index(index=index, document=doc, id=doc_id) 
        success_count = resp['_shards']['successful']
        success = True if success_count >= 1 else False
        if not success:
            print("Could not index to", index)  

        return success             


    @staticmethod
    def _strip_document(data):
        KEYS = [
            'user_id',
            'title',
            'content',
            'slide_id',
            'slide_index',
            'virtualFileName',
            'originalFileName',
            'root'
        ]  
        try:
            doc = {
                key: data[key] for key in KEYS
            }
        except KeyError as e:
            raise Exception("Document missing field:", e)
        return doc   


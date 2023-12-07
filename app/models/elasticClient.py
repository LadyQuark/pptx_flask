import sys

from elasticsearch import Elasticsearch

from app.config import Config

class ElasticClient:
    __db = None
    REQUEST_TIMEOUT = Config.REQUEST_TIMEOUT
    MAX_RETRIES = Config.REQUEST_TIMEOUT

    @staticmethod
    def connect():
        if not ElasticClient.__db:
            ElasticClient()
        return ElasticClient.__db
    
    def __init__(self) -> None:
        if not ElasticClient.__db:
            try:
                if Config.ELASTIC_CLOUD_ID:
                    ElasticClient.__db = self.connect_to_cloud()
                else:
                    ElasticClient.__db = self.connect_to_local()
            except Exception as e:
                raise Exception("Error connecting to elasticsearch", e)
            
            if not ElasticClient.__db.ping():
                raise Exception("Could not connect to ElasticSearch. Ping failed")
                
            
    def connect_to_local(self):
        print("Connecting to local ElasticSearch")
        return Elasticsearch(
            "http://localhost:9200",
            max_retries=self.MAX_RETRIES, 
            retry_on_timeout=True,
            request_timeout=self.REQUEST_TIMEOUT
        )
    
    def connect_to_cloud(self):
        return Elasticsearch(
                    cloud_id=Config.ELASTIC_CLOUD_ID,
                    basic_auth=(Config.ELASTIC_USER, Config.ELASTIC_PASSWORD),
                    max_retries=Config.MAX_RETRIES, 
                    retry_on_timeout=True,
                    request_timeout=Config.REQUEST_TIMEOUT                    
                )
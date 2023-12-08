import pprint
import traceback
import pprint
pp = pprint.PrettyPrinter(depth=6) 

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
    BATCH = 1000
    MAX_RESULT = 1000
    pp = pprint.PrettyPrinter(depth=6)  

    def search_in_index(self, query, user_id, index=None, from_i=0, size=10):
        es = ElasticClient.connect()
        index = index or self.INDEX
        from_i = 0

        try:
            resp = es.search(
                        index=index,
                        size=size,
                        from_=from_i,
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
    
    def search_in_index_all(self, query, user_id, index=None):
        from_i = 0
        results = []
        while True:
            hits = self.search_in_index(
                query=query,
                user_id=user_id,
                index=index,
                from_i=0,
                size=self.MAX_RESULT
            )
            total = hits['total']['value']
            batch_results = [item['_source'] for item in hits['hits']]
            results.extend(batch_results)
            from_i += self.MAX_RESULT
            if from_i >= total:
                break
        return results



    def index_single(self, data, index=None):
        es = ElasticClient.connect()
        index = index or self.INDEX
        # Get only relevant fields from document
        doc = self._strip_document(data)
        if not doc:
            return []        
        resp = es.index(index=index, document=doc) 
        success_count = resp['_shards']['successful']
        success = True if success_count >= 1 else False
        if not success:
            print("Could not index to", index)  

        return success             

    def index_batch(self, docs, index=None):
        """ Index documents in `index` in bulk in batches of size `BATCH`"""

        try:
            es = ElasticClient.connect()
            if not es.ping():
                raise Exception("Could not connect to ElasticSearch")
            
            index = index or self.INDEX
            print(f"Indexing to {index}")
            requests = []
            
            # Make list of requests
            total = len(docs)
            pbar = tqdm(docs)
            for doc in pbar:
                pbar.set_description(doc["title"])     
                # Prepare requests
                request = {}
                request = doc
                request["_op_type"] = "index"
                request["_index"] = index
                requests.append(request)
            
            success = 0
            errors = []
            # Index docs in batches of size BATCH
            for batch_request in self._chunks(requests, n=self.BATCH):
                try:
                    count, e = bulk(client=es.options(
                                        request_timeout=self.REQUEST_TIMEOUT,
                                        max_retries=self.MAX_RETRIES, 
                                        retry_on_timeout=True), 
                                    actions=batch_request, 
                                    request_timeout=self.REQUEST_TIMEOUT
                                    )
                
                except BulkIndexError as e:
                    # Print errors in detail
                    traceback.print_exc()
                    for item in e.errors:
                        for key in item['index']:
                            if key != "data":
                                print(item['index'][key])
                        print("\n")
                    # Set number of successfully indexed documents        
                    count = total - len(e.errors)
                    errors.extend(e.errors)
                
                # Update number of indexed docs
                success += count

            return success, errors
        
        except Exception as e:
            traceback.print_exc()
            return 0, []

    @staticmethod
    def _chunks(data, n):
        """ Generates chunks of given list """
        for i in range(0, len(data), n):
            yield data[i:i + n]    

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


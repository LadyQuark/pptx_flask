import os

from dotenv import load_dotenv

# load environment variables from .env file
load_dotenv()


class Config(object):
    MONGO_DB = os.getenv("MONGO_DB", "Texplicit")
    MONGO_CONNECTION_STRING = os.getenv("MONGO_CONNECTION_STRING", "mongodb://localhost:27017/")
    
    ELASTIC_CLOUD_ID = os.getenv('ELASTIC_CLOUD_ID')
    ELASTIC_USER = os.getenv('ELASTIC_USER')
    ELASTIC_PASSWORD = os.getenv('ELASTIC_PASSWORD')
    ELASTIC_INDEX = os.getenv("ELASTIC_INDEX", "docs")
    
    REQUEST_TIMEOUT = 900
    MAX_RETRIES = 10

    GCP_PROD_ENV = False
    USER_FOLDER = os.getcwd() + "/assets/users"
    MONGO_DOCUMENT_MASTER_COLLECTION = "DOCUMENTS_MASTER"

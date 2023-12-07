import sys

import pymongo

from app.config import Config

class MongoClient:
    __MongoDB = None

    def __init__(self):
        """
            The __init__ function is called when the class is instantiated.
            It sets up the connection to MongoDB and creates a database object that can be used by other functions in this class.

            Args:
                self: Represent the instance of the class

            Returns:
                The mongoclient object
        """
        if MongoClient.__MongoDB is None:
            connection_string = Config.MONGO_CONNECTION_STRING
            
            # print('[database] connecting to database', connection_string, file=sys.stdout)
            sys.stdout.flush()

            try:
                client = pymongo.MongoClient(connection_string, maxPoolSize=None)
                print('mongo server_info: ', client.server_info(), file=sys.stdout)
                sys.stdout.flush()

                database = client[Config.MONGO_DB]

                MongoClient.__MongoDB = database
                print('connected to db')
                sys.stdout.flush()

            except Exception as e:
                raise Exception("error in connecting to db", e)

    @staticmethod
    def connect():
        """
            The connect function is a static method that returns the MongoDB instance.
            If it does not exist, it creates one and then returns it.

            Args:

            Returns:
                A mongodb instance
        """
        if MongoClient.__MongoDB is None:
            MongoClient()

        return MongoClient.__MongoDB
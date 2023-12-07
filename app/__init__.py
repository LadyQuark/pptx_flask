from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

from .config import Config

def create_app():
    """
    The create_app function wraps the creation of a new Flask object, and returns it after it's loaded up with
    configuration settings using app.config.from_object(Config). (For those unfamiliar, a decorator is just a fancy
    way to wrap a function and modify its behavior.)

    Args:

    Returns:
        The app object
    """
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS_ALLOW_ORIGIN = "*,*"
    CORS_EXPOSE_HEADERS = "*,*"
    CORS_ALLOW_HEADERS = "content-type,*"
    CORS(
        app, 
        origins=CORS_ALLOW_ORIGIN.split(","), 
        allow_headers=CORS_ALLOW_HEADERS.split(","), 
        expose_headers=CORS_EXPOSE_HEADERS.split(","), 
        supports_credentials=True
        )
    
    # SocketIO documentation : https://flask-socketio.readthedocs.io/en/latest/api.html
    socketio = SocketIO(
        app, cors_allowed_origins="*", async_mode="threading", async_handlers=True
    ) 
    
    with app.app_context():
        from app.models.elasticClient import ElasticClient
        from app.models.mongoClient import MongoClient

        ElasticClient.connect()
        MongoClient.connect()


        return app, socketio
    
app, socketio = create_app()

# Register blueprints
from app.routes.user.presentation.routes import presentation

app.register_blueprint(presentation)
   

from flask import Flask
from .MainYolo import main
from .database import DatabaseOperations
from mysql.connector import connect

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'n1994PS_'

    from .views import views

    app.register_blueprint(views, url_prefix='/')

    return app

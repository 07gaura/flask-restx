from flask import Flask,request,Blueprint
from flask_restx import Api,Resource,reqparse,fields
from .config import BaseConfig
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
blueprint = Blueprint('api',__name__,url_prefix="/api")

api = Api(blueprint,doc='/')
app.config["SWAGGER_UI_JSONEDITOR"]=True
app.config.from_object(BaseConfig)
db = SQLAlchemy(app)
app.register_blueprint(blueprint)
from . import routes, models
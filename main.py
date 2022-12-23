from flask import Flask,request,Blueprint
from flask_restx import Api,Resource,reqparse,fields

app = Flask(__name__)
blueprint = Blueprint('api',__name__,url_prefix='/')
api = Api(app)
app.config['SWAGGER_UI_JSONEDITOR']=True
app.register_blueprint(blueprint)
a_language = api.model('Language',{'language':fields.String('the language'),'id':fields.String('id')})

languages = []
python = {'language':'python'}
languages.append(python)

@api.route('/language')
class Language(Resource):
    @api.marshal_with(a_language)
    def get(self):
        return languages
    @api.expect(a_language)
    def post(self):
        new_language = api.payload
        new_language['id'] = len(languages)+1
        languages.append(new_language)
        return languages
if __name__=="__main__":
    app.run(debug=True)
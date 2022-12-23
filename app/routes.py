from app import app,api,request,db
from app.models import User, Cart,CartProduct,Product,Category
from datetime import datetime,timedelta
from app.config import *
import jwt
from app import Resource,fields
from functools import wraps

parser = api.parser()
parser.add_argument("Authorization",location='headers')
url_parser = api.parser()
url_parser.add_argument("id",type=int)
a_login = api.model('login_user',{"username":fields.String('username'),"password":fields.String('password')})
update = api.model('home',{"product_quantity":fields.Integer("quantity")})
add_product_in_cart = api.model('consumer_cart',{"product_id":fields.Integer,"quantity":fields.Integer})
delete_product_in_cart = api.model('delete_cart',{"product_id":fields.Integer})
seller_product_update = api.model('seller_update',{"product_id":fields.Integer,"price":fields.String})
seller_product_add = api.model('seller_add',{"product_id":fields.Integer,"product_name":fields.String,"price":fields.Integer,"category_id":fields.Integer})
def token_required(f):
    @wraps(f)
    def decorated(*args,**kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers["Authorization"]
        if not token:
            return {'Message': ' Token is missing'}, 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms='HS256')

            current_user = User.query.filter_by(user_id=data['public_id']).first()

        # print(current_user.user_role)
        except Exception as e:
            print(e)
            return {'Message': 'Token is invalid here'}, 401
        return f(current_user, *args, **kwargs)
    return decorated

@api.route('/login')
class login_user(Resource):
    @api.expect(a_login)
    def post(self):
        auth = api.payload
        if not auth or not auth["username"] or not auth["password"]:
            return "could not verify"
        user = User.query.filter_by(user_name = auth["username"],password=auth["password"]).first()
        if user.password:
            token = jwt.encode({
                'public_id':user.user_id,
                'exp':datetime.utcnow()+timedelta(minutes=45)
            }
            ,BaseConfig.SECRET_KEY,
            "HS256"
            )
            return token
        return "Login failed",401

@api.route('/home')
class home(Resource):
    @api.expect(parser)
    @token_required
    def get(current_user,self):
        return {"home":"Hii"}
    @api.expect(update)
    def put(self):
        data = api.payload
        return "update"

@api.route('/consumer/cart')
class consumerCart(Resource):
    @api.expect(parser)
    @token_required
    def get(current_user,self):
        details = user_prod = db.session.query(Cart,CartProduct,Product,Category).filter(Cart.user_id==current_user.user_id).filter(CartProduct.cart_id==Cart.cart_id).filter(Product.product_id==CartProduct.product_id).filter(Product.category_id==Category.category_id).first()

        #user_cart = Cart.query.filter_by(user_id=current_user).first()
        print(user_prod,"**********Data**********")
        dicts = {
            "cartproducts":{
                "product":{
                    "product_id":details[2].product_id,
                    "price":details[2].price,
                    "product_name":details[2].product_name,
                    "category": {
                        "category_id": details[3].category_id,
                        "category_name": details[3].category_name
                    }
                },
                "cp_id":details[1].cp_id
            },
            "cart_id": details[0].cart_id,
            "total_amount": details[0].total_amount
        }
        return [dicts]
    @api.expect(add_product_in_cart,parser)
    @token_required
    def post(current_user,self):
        data = api.payload
        user_id = current_user.user_id
        cart_details = Cart.query.filter_by(user_id=user_id).first()
        product = Product.query.filter_by(product_id=data["product_id"]).first()
        cart_product_details = CartProduct.query.filter_by(product_id = data["product_id"]).first()
        product_name = product.product_name
        amount = product.price * int(data["quantity"])
        print(cart_product_details)
        if cart_product_details==None:
            add_cart_prod = CartProduct(cart_id=cart_details.cart_id,product_id=product.product_id,quantity=data["quantity"])
            db.session.add(add_cart_prod)
            db.session.commit()
            amount = update_cart(amount,user_id)
            return amount
        return "product already present"

    @api.expect(parser,delete_product_in_cart)
    @token_required
    def delete(current_user,self):
        data = api.payload
        cart = Cart.query.filter_by(user_id = current_user.user_id).first()
        print(cart.cart_id,data["product_id"])
        cartProduct = CartProduct.query.filter_by(cart_id = cart.cart_id,product_id = data["product_id"]).first()
        if cartProduct:
            product = Product.query.filter_by(product_id=data["product_id"]).first()
            amount = int(product.price)*int(cartProduct.quantity)
            amount = reduce_cart_value(amount,current_user.user_id)
            db.session.delete(cartProduct)
            db.session.commit()
            return amount
        return "product not found"

def reduce_cart_value(amount,user_id):
    cart_details = Cart.query.filter_by(user_id=user_id).first()
    amount = abs(amount - int(cart_details.total_amount))
    cart_details.total_amount = amount
    db.session.merge(cart_details)
    db.session.flush()
    db.session.commit()
    return amount
@api.route("/cart/update")
class update_cart_values(Resource):
    @api.expect(add_product_in_cart,parser)
    @token_required
    def put(current_user,self):
        data  = api.payload
        cart = Cart.query.filter_by(user_id=current_user.user_id).first()
        product = Product.query.filter_by(product_id=data["product_id"]).first()
        cart_product = CartProduct.query.filter_by(cart_id=cart.cart_id,product_id=product.product_id).first()
        prod_amount = int(product.price)*int(data["quantity"])
        amount = int(product.price)*abs(int(data["quantity"])-int(cart_product.quantity))
        cart_product.quantity = data["quantity"]
        db.session.merge(cart_product)
        db.session.flush()
        db.session.commit()
        amount = update_cart(amount=amount,user_id=current_user.user_id)
        return amount, 200

def update_cart(amount,user_id):
    cart_details = Cart.query.filter_by(user_id=user_id).first()

    if cart_details:
        amount += int(cart_details.total_amount)
        cart_details.total_amount= amount
        db.session.merge(cart_details)
        db.session.flush()
        db.session.commit()
        return amount
    else:
        cart = Cart(total_amount = amount,user_id=user_id)
        db.session.add(cart)
        db.session.commit()
        return amount

@api.route("/product/<string:product_id>")
class seller_product_id(Resource):
    @api.expect(parser)
    @token_required
    def get(current_user,self,product_id):
        if product_id is not None:
            product = db.session.query(Product,Category).filter(Product.seller_id==current_user.user_id,Product.product_id==product_id).filter(Product.category_id==Category.category_id).all()
            data = []
            dicts = {}
            dicts["category"]={"category_id":product[0].Category.category_id,"category_name":product[0].Category.category_name}
            dicts["price"]=product[0].Product.price
            dicts["product_id"]=product[0].Product.product_id
            dicts["product_name"]=product[0].Product.product_name
            dicts["seller_id"]=product[0].Product.seller_id
            print(dicts)
        return [dicts]
    @api.expect(parser)
    @token_required
    def delete(current_user,self, product_id):
        if product_id is not None:
            product = Product.query.filter_by(product_id=product_id,seller_id=current_user.user_id).first()
            print(product)
            if product is not None:
                db.session.delete(product)
                db.session.commit()
                return 200
            else:
                return "",404

@api.route("/product/")
class seller_product(Resource):
    @api.expect(parser)
    @token_required
    def get(current_user,self):
        product = db.session.query(Product,Category).filter(Product.seller_id==current_user.user_id).filter(Product.category_id==Category.category_id).all()
        print(product)
        data = []
        for i in product:
            dicts = {}
            dicts["category"] = {"category_id": i.Category.category_id,
                                 "category_name": i.Category.category_name}
            dicts["price"] = i.Product.price
            dicts["product_id"] = i.Product.product_id
            dicts["product_name"] = i.Product.product_name
            dicts["seller_id"] = i.Product.seller_id
            data.append(dicts)
        return data
@api.route("/productadd")
class seller_add(Resource):
    @api.expect(seller_product_add,parser)
    @token_required
    def post(current_user,self):
        if request.headers.get("Content-Type")=="application/json":
            data = api.payload
            product = Product.query.filter_by(product_id=data["product_id"]).first()
            print(product)
            if product is not None:
                return 409
            add_data = Product(product_id=data["product_id"],product_name=data["product_name"],price=data["price"],category_id=data["category_id"],seller_id=current_user.user_id)
            db.session.add(add_data)
            db.session.commit()
            return data["product_id"]





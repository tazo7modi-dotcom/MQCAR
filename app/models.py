from .extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    
    cart = db.relationship('Cart', backref='user', uselist=False)
    orders = db.relationship('Order', backref='user', lazy=True)
    
    
    addresses = db.relationship('Address', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Address(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
 
    full_name = db.Column(db.String(100)) 
    phone = db.Column(db.String(20))
    street_address = db.Column(db.String(200))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100)) 
    zip_code = db.Column(db.String(20))
    country = db.Column(db.String(100), default="Bahrain")
    is_default = db.Column(db.Boolean, default=False)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    model_years = db.Column(db.String(50), nullable=True)
    
    parent_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)

    subcategories = db.relationship('Category', 
        backref=db.backref('parent', remote_side=[id]), 
        lazy=True
    )
    products = db.relationship('Product', backref='category', lazy=True)
    


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(500))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    label = db.Column(db.String(100), nullable=True)
    discount_percentage = db.Column(db.Integer, default=0)
    quantity = db.Column(db.Integer, default=1)
    loyverse_id = db.Column(db.String(100), unique=True, nullable=True)
    is_juice = db.Column(db.Boolean, default=False)
    juice_flavors = db.Column(db.String(500))
    juice_nicotine = db.Column(db.String(500))

    def get_price(self):
        """Returns the price AFTER discount"""
        if self.discount_percentage and self.discount_percentage > 0:
            discount_amount = self.price * (self.discount_percentage / 100)
            return self.price - discount_amount
        return self.price

    def on_sale(self):
        """Helper to check if product is on sale"""
        return self.discount_percentage and self.discount_percentage > 0
    
 
    has_sizes = db.Column(db.Boolean, default=False)
    available_sizes = db.Column(db.String(500)) 
    
    has_colors = db.Column(db.Boolean, default=False)
    available_colors = db.Column(db.String(500)) 
    
   
    extras = db.relationship('Extra', backref='product', cascade="all, delete-orphan", lazy=True)



class Extra(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    name = db.Column(db.String(100)) 
    price = db.Column(db.Float)      

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    cart_items = db.relationship('CartItem', backref='cart', lazy=True)



class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('cart.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    product = db.relationship('Product')
    quantity = db.Column(db.Integer, default=1)
    

    size = db.Column(db.String(50))
    color = db.Column(db.String(50))

    selected_extras = db.Column(db.String(500)) 
   
    unit_price = db.Column(db.Float) 

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    product = db.relationship('Product')
    quantity = db.Column(db.Integer)
    price = db.Column(db.Float) 
    size = db.Column(db.String(50))
    color = db.Column(db.String(50))
    selected_extras = db.Column(db.String(500))

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    total_amount = db.Column(db.Float)
    status = db.Column(db.String(20), default='Pending')
    payment_status = db.Column(db.String(20), default='Unpaid') 
    tap_charge_id = db.Column(db.String(200))
    items = db.relationship('OrderItem', backref='order', lazy=True)
    

    shipping_details = db.Column(db.Text) 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
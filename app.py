import os
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

from models.user import db, User, Product, DemoRequest, Cart
from blockchain.blockchain import LightBlockchain
from iot.iot_sensor import IoTSensor

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-12345'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///traceability.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

blockchain = LightBlockchain()


# =========================
# 🔐 ADMIN DECORATOR
# =========================
def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if current_user.role != "admin":
            abort(403)
        return f(*args, **kwargs)
    return wrapper


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# =========================
# ROUTES
# =========================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/get-started')
def get_started():
    return render_template('get_started.html')


# -------------------------
# USER LOGIN
# -------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()

        if user and user.check_password(request.form.get('password')) and user.role == "user":
            login_user(user)
            return redirect(url_for('dashboard'))

        flash("Invalid user credentials")

    return render_template('login.html')


# -------------------------
# ADMIN LOGIN
# -------------------------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()

        if user and user.check_password(request.form.get('password')) and user.role == "admin":

            if request.form.get('admin_key') != "ADMIN123":
                flash("Invalid Admin Key")
                return redirect(url_for('admin_login'))

            login_user(user)
            return redirect(url_for('dashboard'))

        flash("Invalid admin credentials")

    return render_template('admin_register.html')


# -------------------------
# USER SIGNUP
# -------------------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':

        if User.query.filter_by(username=request.form.get('username')).first():
            flash("Username exists")
            return redirect(url_for('signup'))

        if User.query.filter_by(email=request.form.get('email')).first():
            flash("Email already exists")
            return redirect(url_for('signup'))

        user = User(
            username=request.form.get('username'),
            email=request.form.get('email'),
            full_name=request.form.get('full_name'),
            role='user'
        )

        user.set_password(request.form.get('password'))
        db.session.add(user)
        db.session.commit()

        flash("Account created")
        return redirect(url_for('login'))

    return render_template('signup.html')


# -------------------------
# ADMIN REGISTER
# -------------------------
@app.route('/admin/register', methods=['GET', 'POST'])
def admin_register():
    if request.method == 'POST':

        if request.form.get('admin_key') != "ADMIN123":
            flash("Invalid Admin Key")
            return redirect(url_for('admin_register'))

        if User.query.filter_by(username=request.form.get('username')).first():
            flash("Username exists")
            return redirect(url_for('admin_register'))

        if User.query.filter_by(email=request.form.get('email')).first():
            flash("Email already exists")
            return redirect(url_for('admin_register'))

        admin = User(
            username=request.form.get('username'),
            email=request.form.get('email'),
            role='admin'
        )

        admin.set_password(request.form.get('password'))

        db.session.add(admin)
        db.session.commit()

        flash("Admin created")
        return redirect(url_for('admin_login'))

    return render_template('admin_register.html')


# -------------------------
# LOGOUT
# -------------------------
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


# -------------------------
# DASHBOARD
# -------------------------
@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        products = Product.query.order_by(Product.created_at.desc()).all()
        return render_template('admin_dashboard.html', products=products)

    products = Product.query.order_by(Product.created_at.desc()).limit(5).all()
    return render_template('user_dashboard.html', products=products)


# -------------------------
# HISTORY
# -------------------------
@app.route('/history')
@login_required
def history():
    products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template('history.html', products=products)


# -------------------------
# PRODUCTS (USER)
# -------------------------
@app.route('/products')
@login_required
def products():
    if current_user.role != "user":
        return redirect(url_for('dashboard'))

    products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template('products.html', products=products)


# -------------------------
# ADD TO CART
# -------------------------
@app.route('/cart/add/<product_id>')
@login_required
def add_to_cart(product_id):

    if current_user.role != "user":
        return redirect(url_for('dashboard'))

    if not Product.query.filter_by(product_id=product_id).first():
        flash("Product not found")
        return redirect(url_for('products'))

    if not Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first():
        db.session.add(Cart(user_id=current_user.id, product_id=product_id))
        db.session.commit()
        flash("Added to cart")
    else:
        flash("Already in cart")

    return redirect(url_for('products'))


# -------------------------
# VIEW CART
# -------------------------
@app.route('/cart')
@login_required
def view_cart():
    items = Cart.query.filter_by(user_id=current_user.id).all()

    products = [
        Product.query.filter_by(product_id=i.product_id).first()
        for i in items if Product.query.filter_by(product_id=i.product_id).first()
    ]

    return render_template('cart.html', products=products)


# -------------------------
# REMOVE CART
# -------------------------
@app.route('/cart/remove/<product_id>')
@login_required
def remove_from_cart(product_id):
    item = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first()

    if item:
        db.session.delete(item)
        db.session.commit()
        flash("Removed")

    return redirect(url_for('view_cart'))


# -------------------------
# ADD PRODUCT (ADMIN)
# -------------------------
@app.route('/product/add', methods=['POST'])
@login_required
@admin_required
def add_product():

    if Product.query.filter_by(product_id=request.form.get('product_id')).first():
        flash("Product exists")
        return redirect(url_for('dashboard'))

    p = Product(
        product_id=request.form.get('product_id'),
        name=request.form.get('name'),
        category=request.form.get('category'),
        origin=request.form.get('origin'),
        harvest_date=datetime.now()
    )

    db.session.add(p)
    db.session.commit()

    blockchain.add_block({
        "product_id": p.product_id,
        "name": p.name,
        "event": "HARVESTED",
        "origin": p.origin
    })

    flash("Product added")
    return redirect(url_for('dashboard'))


# -------------------------
# TRACE PRODUCT
# -------------------------
@app.route('/product/trace/<product_id>')
def trace_product(product_id):

    history = blockchain.get_product_traceability(product_id)
    product = Product.query.filter_by(product_id=product_id).first()

    if not product:
        return redirect(url_for('index'))

    if not any(h['data'].get('event') == 'TRANSIT' for h in history):
        sensor = IoTSensor(product_id, product.category)
        data = sensor.read_sensors()
        data['event'] = 'TRANSIT'
        blockchain.add_block(data)
        history = blockchain.get_product_traceability(product_id)

    return render_template('traceability.html', history=history, product=product)


# -------------------------
# DEMO REQUEST
# -------------------------
@app.route('/contact', methods=['POST'])
def contact():
    db.session.add(DemoRequest(
        name=request.form.get('name'),
        email=request.form.get('email'),
        phone=request.form.get('phone'),
        message=request.form.get('message')
    ))
    db.session.commit()

    flash("Request submitted")
    return redirect(url_for('index'))


# -------------------------
# ADMIN VIEW REQUESTS
# -------------------------
@app.route('/admin/demo-requests')
@login_required
@admin_required
def demo_requests():
    data = DemoRequest.query.order_by(DemoRequest.created_at.desc()).all()
    return render_template('demo_requests.html', requests=data)


# -------------------------
# RUN
# -------------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    app.run(debug=True, host="0.0.0.0", port=5000)
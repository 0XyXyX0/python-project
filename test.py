from flask import Flask, render_template, redirect, session, url_for, request, send_file
from flask_sqlalchemy import SQLAlchemy
import os
from utils import check_in_session
from functools import wraps
from datetime import datetime
from werkzeug.utils import secure_filename






app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///books.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'random'
db = SQLAlchemy(app)


purchases = db.Table('purchases',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('product_id', db.Integer, db.ForeignKey('product.id'), primary_key=True)
)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    budget = db.Column(db.Integer)
    username = db.Column(db.String(30))
    password = db.Column(db.String(30))
    profile_picture = db.Column(db.String(150), nullable=True)
    purchased_products = db.relationship('Product', secondary=purchases, backref=db.backref('purchased_by', lazy=True))
    is_admin = db.Column(db.Boolean, default=False)
    products = db.relationship('Product', backref='publisher', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    price = db.Column(db.Integer)
    name = db.Column(db.String(30))
    image = db.Column(db.String(500))
    pdf = db.Column(db.String(500))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.String(500), nullable=False)
    likes = db.Column(db.Integer, default=0, nullable=False)
    user = db.relationship('User', backref=db.backref('user_reviews', lazy=True))
    product = db.relationship('Product', backref=db.backref('product_reviews', lazy=True))


class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    review_id = db.Column(db.Integer, db.ForeignKey('review.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('user_likes', lazy=True))
    review = db.relationship('Review', backref=db.backref('review_likes', lazy=True))



class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    user = db.relationship('User', backref=db.backref('purchases', lazy=True))
    product = db.relationship('Product', backref=db.backref('purchases', lazy=True))


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_messages')



def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))

        user = User.query.get(session['user_id'])
        if not user.is_admin:
            return render_template('error.html', message='You do not have permission to access this page.')
        return f(*args, **kwargs)
    return wrapper


@app.route("/index", methods=["GET"])
def index():
    return render_template("index.html", products=Product.query.all())




@app.route("/profile", methods=["GET", "POST"])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])

    if request.method == "POST":
        new_username = request.form.get("username")
        if new_username:
            user.username = new_username

        picture = request.files.get("picture")
        if picture and picture.filename != "":
            picture_filename = secure_filename(picture.filename)
            picture_path = os.path.join("static", picture_filename)
            picture.save(picture_path)
            user.profile_picture = picture_filename

        db.session.commit()
        return redirect(url_for("profile"))

    return render_template("profile.html", user=user)

@app.route("/")
def products():
    products = Product.query.all()
    return render_template("product.html",products=products, check_in_session=check_in_session)


@app.route("/purchased_products")
def purchased_products():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    purchases = Purchase.query.filter_by(user_id=user.id).all()
    return render_template("purchased_products.html", purchases=purchases)


@app.route("/products", methods=["GET", "POST"])
def add_products():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == "POST":
        name = request.form["name"]
        price = request.form["price"]
        image = request.files["image"]
        pdf = request.files["pdf"]
        
        if image.filename == "":
            return "No selected image file"
        if pdf.filename == "":
            return "No selected PDF file"
        
        user_id = session['user_id']
        
        image_filename = secure_filename(image.filename)
        pdf_filename = secure_filename(pdf.filename)

        image_path = os.path.join("static", image_filename)
        pdf_path = os.path.join("static", pdf_filename)

        image.save(image_path)
        pdf.save(pdf_path)

        product = Product(name=name, price=price, image=image_filename, pdf=pdf_filename, user_id=user_id)
        db.session.add(product)
        db.session.commit()
        
        return redirect(url_for("index"))

    return render_template("product.html")



@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        budget = request.form["budget"]
        role = request.form["role"]
        
        existing_user = User.query.filter_by(username=username).first()

        if existing_user:
            return render_template('error.html', message='Username already exists. Please choose a different username.')
        
        if len(username) < 8:
            return render_template('error.html', message='Username should be at least 8 characters long.')
        
        if len(password) < 8:
            return render_template('error.html', message='Password should be at least 8 characters long.')
        
        if role == "Admin":
            user = User(username=username, password=password, budget=budget, is_admin=True)
        else:
            user = User(username=username, password=password, budget=budget, is_admin=False)
            
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("register.html")




@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin  
            return redirect(url_for('products'))
        else:
            return render_template('error_login.html', message='Invalid Username or Password.')
    return render_template('login.html')

@app.route("/admin")
@admin_required
def admin():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user.is_admin:
        return redirect(url_for('index'))

    users = User.query.all()
    products = Product.query.all()
    return render_template("admin.html", users=users, products=products)


@app.route("/delete_user/<int:user_id>", methods=["POST"])
@admin_required
def delete_user(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user.is_admin:
        return redirect(url_for('index'))

    user_to_delete = User.query.get_or_404(user_id)

    db.session.delete(user_to_delete)
    db.session.commit()
    return redirect(url_for('admin'))


@app.route("/delete_product/<int:product_id>", methods=["POST"])
@admin_required
def delete_product(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user.is_admin:
        return redirect(url_for('index'))

    product_to_delete = Product.query.get_or_404(product_id)
    db.session.delete(product_to_delete)
    db.session.commit()
    return redirect(url_for('admin'))

@app.route("/update_product/<int:product_id>", methods=["POST"])
@admin_required
def update_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    name = request.form["name"]
    price = request.form["price"]
    image = request.files.get("image")
    pdf = request.files.get("pdf")

    if name:
        product.name = name
    if price:
        product.price = price
    if image and image.filename:
        image_filename = "".join(image.filename.split())
        image_path = os.path.join("static", image_filename)
        image.save(image_path)
        product.image = image_filename
    if pdf and pdf.filename:
        pdf_filename = "".join(pdf.filename.split())
        pdf_path = os.path.join("static", pdf_filename)
        pdf.save(pdf_path)
        product.pdf = pdf_filename

    db.session.commit()
    return redirect(url_for("admin"))



@app.route("/buy/<int:product_id>", methods=["POST"])

def buy_product(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    product = Product.query.get(product_id)
    
    if product.user_id == user.id:
        return render_template('error_buy.html', message="You cannot buy your own products", product=product)
    
    if user.budget >= product.price:
        user.budget -= product.price

        publisher = User.query.get(product.user_id)
        publisher.budget += product.price

        purchase = Purchase.query.filter_by(user_id=user.id, product_id=product.id).first()
        if purchase:
            purchase.quantity += 1
        else:
            purchase = Purchase(user_id=user.id, product_id=product.id, quantity=1)
            db.session.add(purchase)

        db.session.commit()

        pdf_path = os.path.join(os.getcwd(), 'static', product.pdf)
        return send_file(pdf_path, as_attachment=True)
    else:
        return render_template('deposit.html', message="Insufficient funds to buy this product.")


@app.route("/download_product/<int:product_id>")
def download_product(product_id):
    product = Product.query.get_or_404(product_id)
    if not product.pdf:
        return "No PDF available for this product", 404
    
    return redirect(url_for('static', filename=product.pdf.split('static/')[-1]))



@app.route("/favorite_products")

def favorite_products():
    favorite_product_ids = session.get("favorites", [])
    favorite_products = Product.query.filter(Product.id.in_(favorite_product_ids)).all()
    return render_template("favorite_products.html", favorite_products=favorite_products)

@app.route("/add_to_favorite/<int:product_id>", methods=["POST"])
def add_to_favorite(product_id):
    if "favorites" not in session:
        session["favorites"] = []
    if product_id not in session["favorites"]:
        session["favorites"].append(product_id)
        session.modified = True
    return redirect(url_for("index"))

@app.route("/remove_from_favorite/<int:product_id>", methods=["POST"])
def remove_from_favorite(product_id):
    if "favorites" in session and product_id in session["favorites"]:
        session["favorites"].remove(product_id)
        session.modified = True
    return redirect(url_for("index"))




@app.route("/product/<int:product_id>")
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    reviews = Review.query.filter_by(product_id=product.id).all()
    return render_template('product_detail.html', product=product, reviews=reviews)

@app.route("/add_review/<int:product_id>", methods=["POST"])

def add_review(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    rating = request.form['rating']
    comment = request.form['comment']

    review = Review(user_id=session['user_id'], product_id=product_id, rating=rating, comment=comment)
    db.session.add(review)
    db.session.commit()

    return redirect(url_for('product_detail', product_id=product_id))



@app.route("/like_review/<int:review_id>", methods=["POST"])
def like_review(review_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    like_exists = Like.query.filter_by(user_id=user_id, review_id=review_id).first()

    if like_exists:
        return redirect(url_for('product_detail', product_id=like_exists.review.product_id))

    review = Review.query.get_or_404(review_id)
    like = Like(user_id=user_id, review_id=review_id)
    review.likes += 1

    db.session.add(like)
    db.session.commit()

    return redirect(url_for('product_detail', product_id=review.product_id))



@app.route("/deposit", methods=["GET", "POST"])
def deposit():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == "POST":
        amount = request.form["amount"]
        if not amount.isdigit():
            return render_template('error.html', message='Invalid amount. Please enter a positive number.')

        amount = int(amount)
        if amount <= 0:
            return render_template('error.html', message='Amount must be greater than zero.')

        user = User.query.get(session['user_id'])
        user.budget += amount
        db.session.commit()
        return render_template('success.html', message=f"Successfully deposited ${amount}. Your new budget is ${user.budget}.")

    return render_template("deposit.html")



@app.route("/messages", methods=["GET", "POST"])
def messages():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    
    if request.method == "POST":
        recipient_id = request.form["recipient_id"]
        content = request.form["content"]
        if not content:
            return render_template('error.html', message='Message content cannot be empty.')
        message = Message(sender_id=user.id, recipient_id=recipient_id, content=content, timestamp=datetime.utcnow())
        db.session.add(message)
        db.session.commit()
        return redirect(url_for('messages'))
    
    if user.is_admin:
        users = User.query.filter(User.id != user.id).all()
        messages_received = Message.query.filter_by(recipient_id=user.id).all()
        messages_sent = Message.query.filter_by(sender_id=user.id).all()
    else:
        users = User.query.filter(User.is_admin == True).all()
        messages_received = Message.query.filter_by(recipient_id=user.id).all()
        messages_sent = Message.query.filter_by(sender_id=user.id).all()
    
    return render_template("messages.html", users=users, messages_received=messages_received, messages_sent=messages_sent)



@app.route("/message/<int:user_id>", methods=["GET", "POST"])
def message_user(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    current_user = User.query.get(session['user_id'])
    recipient = User.query.get(user_id)
    
    if request.method == "POST":
        content = request.form["content"]
        if not content:
            return render_template('error.html', message='Message content cannot be empty.')
        message = Message(sender_id=current_user.id, recipient_id=recipient.id, content=content, timestamp=datetime.utcnow())
        db.session.add(message)
        db.session.commit()
        return redirect(url_for('messages'))
    
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.recipient_id == recipient.id)) | 
        ((Message.sender_id == recipient.id) & (Message.recipient_id == current_user.id))
    ).order_by(Message.timestamp.asc()).all()
    
    return render_template("message_user.html", recipient=recipient, messages=messages)


@app.route("/logout")
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for("products"))



if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
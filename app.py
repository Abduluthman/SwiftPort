from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity
)
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
import requests
import uuid
import hmac
import hashlib

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///fxport.db"

db = SQLAlchemy(app)
jwt = JWTManager(app)

print("PAYSTACK KEY LOADED:", Config.PAYSTACK_SECRET_KEY)

# DATABASE MODELS
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Wallet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    balance = db.Column(db.Float, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(100), unique=True, nullable=False)
    type = db.Column(db.String(50))  # e.g., "fund", "purchase"
    amount = db.Column(db.Float)
    status = db.Column(db.String(50))  # "pending", "success", "failed"
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

class EsimPurchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    plan_id = db.Column(db.String(50))   # Airalo plan id
    country = db.Column(db.String(50))
    amount = db.Column(db.Float)
    status = db.Column(db.String(20))  #"pending", "active", "failed"
    esim_data = db.Column(db.JSON)  # stores QR code, activation info


# PAGE ROUTES
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/register")
def register():
    return render_template("register.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/wallet")
def wallet():
    return render_template("wallet.html")

@app.route("/fund-wallet", endpoint="fund-wallet")
def fund_wallet():
    return render_template("fund_wallet.html")

@app.route("/esim")
def esim():
    return render_template("esim.html")

@app.route("/transactions")
def transactions():
    return render_template("transactions.html")

@app.route("/profile")
def profile():
    return render_template("profile.html")

@app.route("/payment-success")
def payment_success():
    return render_template("payment_success.html")

# AUTH API
@app.route("/api/auth/register", methods=["POST"])
def api_register():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists"}), 400

    hashed_pw = generate_password_hash(password)
    user = User(email=email, password=hashed_pw)
    db.session.add(user)
    db.session.commit()

    # Create wallet for user
    wallet = Wallet(user_id=user.id, balance=0)
    db.session.add(wallet)
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    return jsonify({"token": token})

@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password, password):
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_access_token(identity=str(user.id))
    return jsonify({"token": token})

@app.route("/api/auth/profile", methods=["GET"])
@jwt_required()
def api_profile():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    return jsonify({"email": user.email})

@app.route("/api/auth/profile/update", methods=["POST"])
@jwt_required()
def api_profile_update():
    data = request.get_json()
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    email = data.get("email")
    password = data.get("password")

    if email:
        if User.query.filter(User.email==email, User.id!=user_id).first():
            return jsonify({"error": "Email already taken"}), 400
        user.email = email

    if password:
        user.password = generate_password_hash(password)

    db.session.commit()
    return jsonify({"success": True})

# WALLET API
@app.route("/api/wallet", methods=["GET"])
@jwt_required()
def api_wallet():
    user_id = get_jwt_identity()
    wallet = Wallet.query.filter_by(user_id=user_id).first()
    return jsonify({"balance": wallet.balance})

@app.route("/api/payments/paystack/initiate", methods=["POST"])
@jwt_required()
def paystack_initiate():
    data = request.get_json()
    print("Raw request data:", request.data)
    print("Parsed JSON:", data)

    if not data:
        return {"error": "Invalid JSON body"}, 422

    amount = data.get("amount")
    if amount is None:
        return {"error": "Amount is required"}, 400

    try:
        amount = float(amount)
        if amount <= 0:
            return {"error": "Amount must be greater than 0"}, 400
    except ValueError:
        return {"error": "Amount must be a number"}, 400

    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return {"error": "User not found"}, 400

    # Ensure email is a valid non-empty string
    email = str(user.email).strip() if user.email else ""
    if not email:
        # Fallback for testing
        email = "test@example.com"

    reference = str(uuid.uuid4())
    print("Reference:", reference, "User email:", email, "Amount:", amount)

    # Record pending transaction
    tx = Transaction(
        reference=reference,
        type="fund",
        amount=amount,
        status="pending",
        user_id=user_id
    )
    db.session.add(tx)
    db.session.commit()

    headers = {
        "Authorization": f"Bearer {Config.PAYSTACK_SECRET_KEY}",  # ensure this is sk_test_xxx
        "Content-Type": "application/json"
    }

    payload = {
       "email": user.email,
       "amount": int(amount * 100),
       "reference": reference,
       "callback_url": "http://127.0.0.1:5000/payment-success"
    }
    print("Payload sent to Paystack:", payload)

    try:
        res = requests.post(
            "https://api.paystack.co/transaction/initialize",
            json=payload,
            headers=headers,
            timeout=10
        ).json()
        print("Paystack response:", res)
    except Exception as e:
        print("Error calling Paystack:", e)
        return {"error": "Failed to connect to Paystack"}, 500

    if not res.get("status"):
        return {"error": res.get("message") or "Paystack error"}, 400

    return {"checkout_url": res["data"]["authorization_url"], "reference": reference}


@app.route("/api/payments/paystack/webhook", methods=["POST"])
def paystack_webhook():
    signature = request.headers.get("X-Paystack-Signature")
    raw_body = request.get_data()

    if not signature:
        return "", 400

    expected_signature = hmac.new(
        Config.PAYSTACK_SECRET_KEY.encode(),
        raw_body,
        hashlib.sha512
    ).hexdigest()

    if not hmac.compare_digest(signature, expected_signature):
        return "", 403

    payload = request.get_json()
    event = payload.get("event")

    if event != "charge.success":
        return "", 200

    data = payload["data"]
    reference = data["reference"]
    amount = data["amount"] / 100  # convert kobo to naira
    email = data["customer"]["email"]

    tx = Transaction.query.filter_by(reference=reference).first()
    if not tx or tx.status == "success":
        return "", 200

    user = User.query.filter_by(email=email).first()
    if not user:
        return "", 200

    wallet = Wallet.query.filter_by(user_id=user.id).first()
    wallet.balance += amount
    tx.status = "success"
    db.session.commit()

    return "", 200

@app.route("/api/payments/paystack/verify")
@jwt_required()
def paystack_verify():
    reference = request.args.get("reference")
    if not reference:
        return {"error": "Reference required"}, 400

    headers = {
        "Authorization": f"Bearer {Config.PAYSTACK_SECRET_KEY}"
    }

    res = requests.get(
        f"https://api.paystack.co/transaction/verify/{reference}",
        headers=headers
    ).json()

    if not res.get("status"):
        return {"error": "Verification failed"}, 400

    data = res["data"]

    if data["status"] != "success":
        return {"error": "Payment not successful"}, 400

    tx = Transaction.query.filter_by(reference=reference).first()
    if not tx or tx.status == "success":
        return {"error": "Invalid transaction"}, 400

    user_id = get_jwt_identity()
    wallet = Wallet.query.filter_by(user_id=user_id).first()

    wallet.balance += tx.amount
    tx.status = "success"
    db.session.commit()

    return {"success": True}

# Transaction API
@app.route("/api/transactions", methods=["GET"])
@jwt_required()
def api_transactions():
    user_id = get_jwt_identity()
    txs = Transaction.query.filter_by(user_id=user_id).order_by(Transaction.id.desc()).all()
    return jsonify([
        {
            "reference": tx.reference,
            "type": tx.type,
            "amount": tx.amount,
            "status": tx.status
        } for tx in txs
    ])

# ESim (Airalo) API
# Dummy data for testing (replace with Airalo API later)
ESIM_PLANS = {
    "US": [
        {"id": "plan_us_1", "data": 1, "price": 500},
        {"id": "plan_us_2", "data": 3, "price": 1200},
        {"id": "plan_us_3", "data": 5, "price": 1800}
    ]
}

@app.route("/api/esim/packages")
@jwt_required()
def get_esim_packages():
    country = request.args.get("country")
    if not country or country not in ESIM_PLANS:
        return {"error": "Invalid country"}, 400
    return jsonify(ESIM_PLANS[country])


@app.route("/api/esim/buy", methods=["POST"])
@jwt_required()
def buy_esim():
    data = request.get_json()
    plan_id = data.get("plan_id")
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)

    # Lookup plan
    plan = None
    for c in ESIM_PLANS.values():
        for p in c:
            if p["id"] == plan_id:
                plan = p
                break
    if not plan:
        return {"error": "Invalid plan ID"}, 400

    wallet = Wallet.query.filter_by(user_id=user.id).first()
    if wallet.balance < plan["price"]:
        return {"error": "Insufficient balance"}, 400

    # Deduct wallet
    wallet.balance -= plan["price"]

    # Create purchase transaction
    tx = Transaction(
        reference=str(uuid.uuid4()),
        type="purchase",
        amount=plan["price"],
        status="success",
        user_id=user.id
    )
    db.session.add(tx)

    # Store purchased eSIM
    esim_purchase = EsimPurchase(
        user_id=user.id,
        plan_id=plan["id"],
        country="US",
        amount=plan["price"],
        status="active",
        esim_data={"data": plan["data"], "plan_id": plan["id"]}
    )
    db.session.add(esim_purchase)
    db.session.commit()

    return {"success": True, "esim": esim_purchase.esim_data}


# INIT
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)

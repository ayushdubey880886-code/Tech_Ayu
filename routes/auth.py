from flask import Blueprint, request, jsonify
from flask_jwt_extended import (create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity)
from flask_bcrypt import Bcrypt
from models.db import db, User
from utils.security import sanitize
import smtplib
import random
import time
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

auth_bp = Blueprint("auth", __name__)
bcrypt  = Bcrypt()

# Temporary OTP storage (In-memory for demo/dev)
# In production, use Redis or a Database
otp_store = {}


@auth_bp.route("/register", methods=["POST"])
def register():
    d = request.get_json(silent=True) or {}
    name    = sanitize(d.get("name", ""), 120)
    email   = sanitize(d.get("email", ""), 200).lower()
    password= d.get("password", "")
    consent = d.get("data_consent", False)

    if not name or not email or not password:
        return jsonify({"error": "name, email and password required"}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400
    if "@" not in email:
        return jsonify({"error": "Invalid email"}), 400
    if not consent:
        return jsonify({"error": "Data consent required (GDPR/Indian IT Act)"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    from flask_bcrypt import generate_password_hash
    user = User(
        name=name, email=email,
        password_hash=generate_password_hash(password).decode(),
        college=sanitize(d.get("college", ""), 200),
        degree=sanitize(d.get("degree", "BTech"), 100),
        graduation_yr=d.get("graduation_yr"),
        skills=",".join(sanitize(s, 50) for s in d.get("skills", []) if s),
        data_consent=True,
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({
        "message":       "Registration successful",
        "access_token":  create_access_token(identity=str(user.id)),
        "refresh_token": create_refresh_token(identity=str(user.id)),
        "user":          user.to_dict(),
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    d       = request.get_json(silent=True) or {}
    email   = sanitize(d.get("email", ""), 200).lower()
    password= d.get("password", "")
    user    = User.query.filter_by(email=email).first()
    from flask_bcrypt import check_password_hash
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid email or password"}), 401
    return jsonify({
        "message":       "Login successful",
        "access_token":  create_access_token(identity=str(user.id)),
        "refresh_token": create_refresh_token(identity=str(user.id)),
        "user":          user.to_dict(),
    })


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    return jsonify({"access_token": create_access_token(identity=get_jwt_identity())})


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    return jsonify({"message": "Logged out"})


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    user = User.query.get(int(get_jwt_identity()))
    return jsonify({"user": user.to_dict()}) if user else (jsonify({"error": "Not found"}), 404)


@auth_bp.route("/send-otp", methods=["POST"])
def send_otp():
    d = request.get_json(silent=True) or {}
    email = sanitize(d.get("email", ""), 200).lower()

    if not email or "@" not in email:
        return jsonify({"error": "Valid email required"}), 400

    otp = str(random.randint(100000, 999999))
    expiry = time.time() + 300  # 5 minutes
    otp_store[email] = {"otp": otp, "expiry": expiry}

    # Send Email
    try:
        msg = MIMEMultipart()
        msg['From'] = os.getenv("MAIL_USERNAME")
        msg['To'] = email
        msg['Subject'] = "CareerHub - Your OTP Verification Code"

        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f4f7f6; padding: 20px;">
                <div style="max-width: 600px; margin: auto; background: #fff; padding: 30px; border-radius: 10px; border: 1px solid #e1e4e8;">
                    <h2 style="color: #007bff; text-align: center;">CareerHub OTP Verification</h2>
                    <p>Hello,</p>
                    <p>Your verification code is:</p>
                    <div style="font-size: 32px; font-weight: bold; text-align: center; letter-spacing: 5px; color: #333; margin: 20px 0;">
                        {otp}
                    </div>
                    <p>This OTP is valid for 5 minutes. Do not share this code with anyone.</p>
                    <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                    <p style="font-size: 12px; color: #777; text-align: center;">
                        © 2025 CareerHub. All rights reserved.
                    </p>
                </div>
            </body>
        </html>
        """
        msg.attach(MIMEText(body, 'html'))

        server = smtplib.SMTP(os.getenv("MAIL_SERVER", "smtp.gmail.com"), int(os.getenv("MAIL_PORT", 587)))
        server.starttls()
        server.login(os.getenv("MAIL_USERNAME"), os.getenv("MAIL_PASSWORD"))
        server.send_message(msg)
        server.quit()
    except smtplib.SMTPAuthenticationError:
        error_msg = "SMTP Authentication Error: Check your MAIL_USERNAME and MAIL_PASSWORD (App Password)."
        print(error_msg)
        return jsonify({"error": error_msg}), 500
    except Exception as e:
        error_msg = f"Failed to send email: {str(e)}"
        print(f"SMTP Error: {str(e)}")
        return jsonify({"error": error_msg}), 500

    return jsonify({"message": "OTP sent successfully"}), 200


@auth_bp.route("/verify-otp", methods=["POST"])
def verify_otp():
    d = request.get_json(silent=True) or {}
    email = sanitize(d.get("email", ""), 200).lower()
    user_otp = d.get("otp", "")

    if not email or not user_otp:
        return jsonify({"error": "Email and OTP required"}), 400

    record = otp_store.get(email)
    if not record:
        return jsonify({"error": "No OTP sent to this email"}), 400

    if time.time() > record["expiry"]:
        del otp_store[email]
        return jsonify({"error": "OTP expired"}), 400

    if record["otp"] != user_otp:
        return jsonify({"error": "Invalid OTP"}), 400

    # Success! Clear OTP
    del otp_store[email]

    # Check if user exists, else create (Optional, based on requirement)
    user = User.query.filter_by(email=email).first()
    if not user:
        # Auto-register user if they don't exist
        user = User(
            name=email.split("@")[0],
            email=email,
            password_hash=bcrypt.generate_password_hash(str(random.random())).decode(),
            data_consent=True
        )
        db.session.add(user)
        db.session.commit()

    return jsonify({
        "message": "Login successful",
        "access_token": create_access_token(identity=str(user.id)),
        "refresh_token": create_refresh_token(identity=str(user.id)),
        "user": user.to_dict()
    }), 200

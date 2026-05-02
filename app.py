"""CareerHub — Flask Backend"""
import os, sys, io
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

load_dotenv()

from models.db import db, init_mongo
from routes.auth import auth_bp
from routes.jobs import jobs_bp, hackathons_bp, webinars_bp, rec_bp, user_bp

def create_app():
    app = Flask(__name__)

    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:Ayush12521198@localhost:5432/careerhub")
    db_url = db_url.replace("postgres://", "postgresql://")

    app.config.update(
        SECRET_KEY                     = os.getenv("SECRET_KEY", "careerhub-secret-2025-xK9mP2"),
        JWT_SECRET_KEY                 = os.getenv("JWT_SECRET_KEY", "careerhub-jwt-2025-nR7vQ4"),
        JWT_ACCESS_TOKEN_EXPIRES       = 3600,
        JWT_REFRESH_TOKEN_EXPIRES      = 86400 * 30,
        SQLALCHEMY_DATABASE_URI        = db_url,
        SQLALCHEMY_TRACK_MODIFICATIONS = False,
        SQLALCHEMY_ENGINE_OPTIONS      = {
            "pool_pre_ping":  True,
            "pool_recycle":   300,
            "pool_size":      5,
            "max_overflow":   10,
        },
        MAX_CONTENT_LENGTH = 10 * 1024 * 1024,  # 10MB upload limit
    )

    # Allow all origins for production ease, or use environment variable
    CORS(app, resources={r"/api/*": {
        "origins": "*",
        "methods": ["GET","POST","PUT","DELETE","OPTIONS"],
        "allow_headers": ["Content-Type","Authorization"],
    }})

    db.init_app(app)
    JWTManager(app)
    Bcrypt(app)
    Limiter(get_remote_address, app=app,
            default_limits=["500 per day", "100 per hour"],
            storage_uri="memory://")

    with app.app_context():
        init_mongo(app)

    app.register_blueprint(auth_bp,       url_prefix="/api/auth")
    app.register_blueprint(jobs_bp,       url_prefix="/api/jobs")
    app.register_blueprint(hackathons_bp, url_prefix="/api/hackathons")
    app.register_blueprint(webinars_bp,   url_prefix="/api/webinars")
    app.register_blueprint(rec_bp,        url_prefix="/api/recommendations")
    app.register_blueprint(user_bp,       url_prefix="/api/user")

    with app.app_context():
        try:
            db.create_all()
            print("✅ PostgreSQL — all tables created/verified")
        except Exception as e:
            print(f"❌ DB Error: {e}")
            print("   Make sure PostgreSQL is running and DATABASE_URL is correct in .env")
            sys.exit(1)

    @app.route("/")
    def health():
        return jsonify({"status": "CareerHub API ✅", "version": "2.0.0"})

    @app.route("/api/health")
    def api_health():
        try:
            from sqlalchemy import text
            db.session.execute(text("SELECT 1"))
            pg = True
        except Exception:
            pg = False
        from models.db import get_mongo
        mongo = get_mongo() is not None
        return jsonify({
            "postgres": "✅ connected" if pg else "❌ disconnected",
            "mongodb":  "✅ connected" if mongo else "⚠️ not connected (optional)",
            "jsearch":  "✅ key set" if os.getenv("JSEARCH_API_KEY") else "❌ key missing",
        }), 200 if pg else 500

    @app.errorhandler(404)
    def not_found(e):    return jsonify({"error": "Not found"}), 404
    @app.errorhandler(413)
    def too_large(e):    return jsonify({"error": "File too large (max 10MB)"}), 413
    @app.errorhandler(429)
    def rate_limited(e): return jsonify({"error": "Too many requests — slow down"}), 429
    @app.errorhandler(500)
    def server_err(e):   return jsonify({"error": "Server error"}), 500

    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV", "development") == "development"
    print(f"\n🚀 CareerHub backend starting on http://localhost:{port}")
    print(f"   Health check: http://localhost:{port}/api/health\n")
    app.run(debug=debug, host="0.0.0.0", port=port)

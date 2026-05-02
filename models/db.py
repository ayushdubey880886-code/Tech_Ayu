"""
PostgreSQL (structured) + MongoDB (cache, optional)
"""
import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from pymongo import MongoClient, ASCENDING, TEXT
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

db = SQLAlchemy()
_mongo_client = None
_mongo_db     = None

def init_mongo(app):
    global _mongo_client, _mongo_db
    uri = os.getenv("MONGO_URI", "")
    if not uri:
        app.logger.info("MONGO_URI not set — MongoDB cache disabled (OK)")
        return
    try:
        _mongo_client = MongoClient(uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=5000)
        _mongo_client.admin.command("ping")
        _mongo_db = _mongo_client.get_database()
        _create_indexes()
        app.logger.info("✅ MongoDB connected")
    except Exception as e:
        app.logger.warning(f"⚠️ MongoDB not available: {e} — continuing without cache")
        _mongo_db = None

def _create_indexes():
    if _mongo_db is None: return
    try:
        _mongo_db["jobs"].create_index([("title", TEXT), ("description", TEXT)])
        _mongo_db["jobs"].create_index([("id", ASCENDING)], unique=True, sparse=True)
        _mongo_db["events"].create_index([("id", ASCENDING)], unique=True, sparse=True)
    except Exception: pass

def get_mongo():
    return _mongo_db

# ── Models ────────────────────────────────────────────────────────────────────

class User(db.Model):
    __tablename__ = "users"
    id              = db.Column(db.Integer, primary_key=True)
    name            = db.Column(db.String(120), nullable=False)
    email           = db.Column(db.String(200), unique=True, nullable=False)
    password_hash   = db.Column(db.String(256), nullable=False)
    college         = db.Column(db.String(200), default="")
    degree          = db.Column(db.String(100), default="BTech")
    graduation_yr   = db.Column(db.Integer)
    skills          = db.Column(db.Text, default="")
    resume_text     = db.Column(db.Text, default="")
    resume_filename = db.Column(db.String(300), default="")
    data_consent    = db.Column(db.Boolean, default=False)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    interactions = db.relationship("UserInteraction", backref="user", lazy=True, cascade="all, delete-orphan")
    saved_items  = db.relationship("SavedItem",       backref="user", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id":              self.id,
            "name":            self.name,
            "email":           self.email,
            "college":         self.college,
            "degree":          self.degree,
            "graduation_yr":   self.graduation_yr,
            "skills":          [s.strip() for s in self.skills.split(",") if s.strip()],
            "has_resume":      bool(self.resume_text),
            "resume_filename": self.resume_filename,
            "created_at":      self.created_at.isoformat(),
        }

class UserInteraction(db.Model):
    __tablename__ = "user_interactions"
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    item_id    = db.Column(db.String(100), nullable=False)
    item_type  = db.Column(db.String(20))
    action     = db.Column(db.String(20))
    dwell_secs = db.Column(db.Integer, default=0)
    timestamp  = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (
        db.Index("ix_inter_user", "user_id"),
        db.Index("ix_inter_item", "item_id"),
    )

class SavedItem(db.Model):
    __tablename__ = "saved_items"
    id        = db.Column(db.Integer, primary_key=True)
    user_id   = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    item_id   = db.Column(db.String(100), nullable=False)
    item_type = db.Column(db.String(20))
    title     = db.Column(db.String(300), default="")
    company   = db.Column(db.String(200), default="")
    saved_at  = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint("user_id", "item_id"),)

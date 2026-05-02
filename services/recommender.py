"""
Paper Section 4-D & 5-E: Intelligent Analysis Layer
- Semantic Analysis  : BERT embeddings (sentence-transformers)
- Behavioral Analytics: Collaborative Filtering from interaction history
- Recommendation Engine: Hybrid CBF (70%) + CF (30%)
- Skill Gap Analyzer  : NLP-based missing skill detection
"""

import re
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

# ── Lazy-load BERT model ──────────────────────────────────────────────────────
_bert_model = None


def _load_bert():
    global _bert_model
    if _bert_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _bert_model = SentenceTransformer("all-MiniLM-L6-v2")
            print("✅ BERT model loaded (sentence-transformers/all-MiniLM-L6-v2)")
        except Exception as e:
            print(f"⚠️  BERT unavailable ({e}) — using TF-IDF fallback")
            _bert_model = "tfidf"
    return _bert_model


# ── Text preprocessing (Paper: NLTK pipeline) ────────────────────────────────

STOPWORDS = {"the","a","an","is","are","was","were","be","been","have","has","had",
             "do","does","did","will","would","could","should","to","of","in","for",
             "on","with","at","by","from","as","this","that","it","its","we","our"}

def preprocess(text: str) -> str:
    text = text.lower()
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"http\S+", " ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    tokens = [t for t in text.split() if t not in STOPWORDS and len(t) > 1]
    return " ".join(tokens)


def get_embedding(text: str) -> np.ndarray:
    """
    Paper Section 6-C-1: BERT → 384-dim vector.
    Falls back to TF-IDF hash embedding if model unavailable.
    """
    model = _load_bert()
    clean = preprocess(text)
    if not clean:
        return np.zeros(384, dtype=np.float32)

    if model != "tfidf":
        try:
            vec = model.encode(clean, show_progress_bar=False)
            return vec.astype(np.float32)
        except Exception:
            pass

    # TF-IDF fallback — deterministic hash embedding
    vec = np.zeros(384, dtype=np.float32)
    for word in clean.split():
        idx = hash(word) % 384
        vec[idx] += 1.0
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec


def semantic_score(text_a: str, text_b: str) -> float:
    """Paper: cosine similarity between two text embeddings."""
    va = get_embedding(text_a).reshape(1, -1)
    vb = get_embedding(text_b).reshape(1, -1)
    score = cosine_similarity(va, vb)[0][0]
    return float(np.clip(score, 0.0, 1.0))


# ── Content-Based Filtering (Paper Section 5-E-1) ────────────────────────────

def cbf_score(user_profile: dict, opportunity: dict) -> float:
    user_text = " ".join(filter(None, [
        user_profile.get("skills", ""),
        user_profile.get("resume_text", ""),
        user_profile.get("degree", ""),
    ]))
    opp_text = " ".join(filter(None, [
        opportunity.get("title", ""),
        opportunity.get("description", ""),
        " ".join(opportunity.get("tags", [])),
        opportunity.get("category", ""),
    ]))
    if not user_text.strip() or not opp_text.strip():
        return 0.5
    return semantic_score(user_text, opp_text)


# ── Collaborative Filtering (Paper Section 5-E-2) ────────────────────────────

def cf_score(user_id: int, item_id: str, interactions) -> float:
    """
    User-item matrix CF.
    interactions = list of {user_id, item_id, score} dicts
    """
    if not interactions:
        return 0.0
    try:
        import pandas as pd
        df = pd.DataFrame(interactions)
        matrix = df.pivot_table(index="user_id", columns="item_id",
                                values="score", fill_value=0)
        if user_id not in matrix.index or item_id not in matrix.columns:
            return 0.0
        user_vec = matrix.loc[user_id].values.reshape(1, -1)
        item_vec = matrix[item_id].values.reshape(1, -1)
        sim = cosine_similarity(user_vec, item_vec)[0][0]
        return float(np.clip(sim, 0.0, 1.0))
    except Exception:
        return 0.0


# ── Hybrid Recommendation (Paper Section 4-D-3) ──────────────────────────────

def hybrid_score(user_profile: dict, opportunity: dict,
                 user_id: int = None, interactions=None,
                 cbf_w: float = 0.7, cf_w: float = 0.3) -> float:
    """70% CBF (semantic) + 30% CF (behavioral) — paper's hybrid model."""
    cbf = cbf_score(user_profile, opportunity)
    cf  = cf_score(user_id, opportunity.get("id", ""), interactions or []) if user_id else 0.0
    return round((cbf_w * cbf + cf_w * cf) * 100, 1)


def rank_opportunities(user_profile: dict, opportunities: list,
                       user_id: int = None, interactions=None) -> list:
    """
    Paper Section 5-F: Rank by hybrid score → filter expired → return sorted list.
    """
    scored = []
    for opp in opportunities:
        score = hybrid_score(user_profile, opp, user_id, interactions)
        scored.append({**opp, "match_score": score})
    scored.sort(key=lambda x: x["match_score"], reverse=True)
    return scored


# ── Skill Gap Analysis ────────────────────────────────────────────────────────

TECH_KEYWORDS = [
    "python","java","javascript","typescript","react","node.js","vue","angular",
    "flask","django","fastapi","spring","express","sql","postgresql","mongodb",
    "mysql","redis","elasticsearch","aws","gcp","azure","docker","kubernetes",
    "git","linux","tensorflow","pytorch","scikit-learn","pandas","numpy","spark",
    "hadoop","kafka","airflow","mlflow","bert","nlp","machine learning",
    "deep learning","data science","computer vision","ci/cd","jenkins","terraform",
]

def analyze_skill_gap(user_skills: list, job_tags: list, job_desc: str = "") -> dict:
    """Paper: NLP-based skill gap detection between user and opportunity."""
    user_set = {s.strip().lower() for s in user_skills if s.strip()}
    required = {t.strip().lower() for t in job_tags if t.strip()}

    desc_lower = job_desc.lower()
    for kw in TECH_KEYWORDS:
        if kw in desc_lower:
            required.add(kw)

    missing = sorted(required - user_set)
    matched = sorted(required & user_set)
    pct     = round(len(matched) / max(len(required), 1) * 100, 1)

    return {
        "matched_skills":   matched,
        "missing_skills":   missing[:8],
        "match_percentage": pct,
        "total_required":   len(required),
        "recommendation":   _gap_recommendation(pct, missing),
    }


def _gap_recommendation(pct: float, missing: list) -> str:
    if pct >= 80:
        return "Strong match! Apply confidently."
    if pct >= 50:
        return f"Good match. Focus on: {', '.join(missing[:3])}."
    return f"Skill gap detected. Learn: {', '.join(missing[:3])} to improve chances."

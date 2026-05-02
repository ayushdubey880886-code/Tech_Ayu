"""
CareerHub — Jobs, Hackathons, Webinars, Resume, Recommendations
Job API: JSearch (RapidAPI) — LinkedIn / Indeed / Glassdoor / Naukri
"""
import re, os, io
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from models.db import db, User, UserInteraction, SavedItem
from utils.security import sanitize
import httpx

jobs_bp       = Blueprint("jobs",            __name__)
hackathons_bp = Blueprint("hackathons",      __name__)
webinars_bp   = Blueprint("webinars",        __name__)
rec_bp        = Blueprint("recommendations", __name__)
user_bp       = Blueprint("user",            __name__)

JSEARCH_KEY      = os.getenv("JSEARCH_API_KEY",  "")
TICKETMASTER_KEY = os.getenv("TICKETMASTER_KEY", "")
EVENTBRITE_TOKEN = os.getenv("EVENTBRITE_TOKEN", "")

# ── Skills dictionary ─────────────────────────────────────────────────────────
SKILLS = {
    "python":"Python","javascript":"JavaScript","typescript":"TypeScript",
    "react":"React","angular":"Angular","vue":"Vue.js","node":"Node.js",
    "flask":"Flask","django":"Django","fastapi":"FastAPI","spring":"Spring Boot",
    "sql":"SQL","postgresql":"PostgreSQL","mysql":"MySQL","mongodb":"MongoDB",
    "redis":"Redis","kafka":"Kafka","elasticsearch":"Elasticsearch",
    "aws":"AWS","azure":"Azure","gcp":"GCP","docker":"Docker",
    "kubernetes":"Kubernetes","terraform":"Terraform","linux":"Linux",
    "git":"Git","devops":"DevOps","ci/cd":"CI/CD",
    "machine learning":"Machine Learning","deep learning":"Deep Learning",
    "data science":"Data Science","nlp":"NLP","computer vision":"Computer Vision",
    "tensorflow":"TensorFlow","pytorch":"PyTorch","scikit":"Scikit-learn",
    "pandas":"Pandas","numpy":"NumPy","matplotlib":"Matplotlib",
    "java":"Java","kotlin":"Kotlin","golang":"Go","rust":"Rust","c++":"C++","scala":"Scala",
    "android":"Android","ios":"iOS","flutter":"Flutter","swift":"Swift",
    "react native":"React Native","graphql":"GraphQL","rest api":"REST API",
    "microservices":"Microservices","spark":"Apache Spark","hadoop":"Hadoop",
    "html":"HTML","css":"CSS","sass":"SASS","jquery":"jQuery",
    "jenkins":"Jenkins","github actions":"GitHub Actions","ansible":"Ansible",
    "tableau":"Tableau","power bi":"Power BI","excel":"Excel",
}

# ── Static Hackathons (20) ────────────────────────────────────────────────────
HACKATHONS = [
    {"id":"h1","title":"Smart India Hackathon 2026","organizer":"Govt of India / AICTE","mode":"offline","location":"Pan India","prize":"₹1,00,000+","deadline":"2026-08-30","tags":["AI","GovTech","Innovation"],"url":"https://sih.gov.in","type":"hackathon","difficulty":"Intermediate","description":"India's largest hackathon solving real government challenges. Over 1 lakh students participate every year."},
    {"id":"h2","title":"HackWithInfy 2026","organizer":"Infosys","mode":"online","location":"Online","prize":"₹75,000","deadline":"2026-07-15","tags":["ML","Cloud","Web Dev"],"url":"https://hackwithinfy.com","type":"hackathon","difficulty":"Beginner","description":"Infosys annual hackathon. Winners get internship offers, PPOs and cash prizes."},
    {"id":"h3","title":"Flipkart Grid 6.0","organizer":"Flipkart","mode":"online","location":"Online","prize":"PPO + ₹1,50,000","deadline":"2026-09-01","tags":["E-Commerce","AI","Supply Chain"],"url":"https://unstop.com/hackathons/flipkart-grid-60","type":"hackathon","difficulty":"Advanced","description":"Flipkart's flagship engineering challenge with Pre-Placement Offers for winners."},
    {"id":"h4","title":"HackRx 6.0","organizer":"Bajaj Finserv","mode":"online","location":"Online","prize":"₹1,50,000","deadline":"2026-07-20","tags":["HealthTech","FinTech","AI"],"url":"https://unstop.com/hackathons","type":"hackathon","difficulty":"Intermediate","description":"Build innovative health and finance solutions using open APIs."},
    {"id":"h5","title":"Google Solution Challenge 2026","organizer":"Google","mode":"online","location":"Global","prize":"$3000 + Mentorship","deadline":"2026-08-10","tags":["Google Cloud","ML","Android"],"url":"https://developers.google.com/community/gdsc-solution-challenge","type":"hackathon","difficulty":"Intermediate","description":"Build solutions for UN Sustainable Development Goals using Google technologies."},
    {"id":"h6","title":"ETHIndia 2026","organizer":"Devfolio","mode":"offline","location":"Bangalore","prize":"$1,00,000+","deadline":"2026-11-01","tags":["Web3","Blockchain","DeFi","Solidity"],"url":"https://ethindia.co","type":"hackathon","difficulty":"Advanced","description":"India's largest Ethereum hackathon for Web3 builders. Past editions saw 2000+ hackers."},
    {"id":"h7","title":"Code for Good — JPMorgan","organizer":"JPMorgan Chase","mode":"offline","location":"Mumbai","prize":"PPO + ₹50,000","deadline":"2026-07-25","tags":["FinTech","Social Impact","Python"],"url":"https://careers.jpmorgan.com","type":"hackathon","difficulty":"Intermediate","description":"24-hour hackathon building tech solutions for non-profit organizations."},
    {"id":"h8","title":"Microsoft Imagine Cup 2026","organizer":"Microsoft","mode":"online","location":"Global","prize":"$100,000+","deadline":"2026-08-15","tags":["AI","Azure","Innovation"],"url":"https://imaginecup.microsoft.com","type":"hackathon","difficulty":"Advanced","description":"Microsoft's global student competition. Build AI solutions for real-world problems."},
    {"id":"h9","title":"HackOn With Amazon 2026","organizer":"Amazon","mode":"online","location":"Online","prize":"₹5,00,000+","deadline":"2026-07-30","tags":["AWS","ML","Cloud","Backend"],"url":"https://hackon.amazon.in","type":"hackathon","difficulty":"Intermediate","description":"Amazon India's flagship hackathon for students and professionals."},
    {"id":"h10","title":"TCS CodeVita 2026","organizer":"TCS","mode":"online","location":"Online","prize":"Job Offer + ₹1,00,000","deadline":"2026-09-15","tags":["DSA","Problem Solving","Competitive Programming"],"url":"https://www.tcscodevita.com","type":"hackathon","difficulty":"Advanced","description":"TCS global coding competition. Winners get direct job offers."},
    {"id":"h11","title":"Myntra HackerRamp WeForShe","organizer":"Myntra","mode":"online","location":"Online","prize":"PPO + Cash","deadline":"2026-08-05","tags":["Fashion Tech","AI","ML","React"],"url":"https://unstop.com/hackathons","type":"hackathon","difficulty":"Beginner","description":"Myntra hackathon focused on fashion technology and women in tech."},
    {"id":"h12","title":"Hack the Mountain 4.0","organizer":"Coding Blocks","mode":"hybrid","location":"Delhi/Online","prize":"₹2,00,000+","deadline":"2026-08-20","tags":["Open Innovation","AI","Web Dev"],"url":"https://hackthemountain.co","type":"hackathon","difficulty":"Beginner","description":"India's largest student hackathon with 10,000+ participants."},
    {"id":"h13","title":"Walmart Sparkathon 2026","organizer":"Walmart","mode":"online","location":"Online","prize":"PPO + ₹2,00,000","deadline":"2026-09-05","tags":["Retail Tech","ML","Supply Chain"],"url":"https://walmart.com/sparkathon","type":"hackathon","difficulty":"Advanced","description":"Walmart global hackathon focused on retail technology innovation."},
    {"id":"h14","title":"GitHub Constellation India 2026","organizer":"GitHub","mode":"offline","location":"Bangalore","prize":"Swag + Recognition","deadline":"2026-08-01","tags":["Open Source","Git","DevOps","AI"],"url":"https://githubconstellation.com","type":"hackathon","difficulty":"Beginner","description":"GitHub's annual developer conference and hackathon in India."},
    {"id":"h15","title":"HackerEarth University Hackathon","organizer":"HackerEarth","mode":"online","location":"Online","prize":"₹1,00,000+","deadline":"2026-08-12","tags":["ML","Data Science","Python"],"url":"https://www.hackerearth.com/challenges/hackathon","type":"hackathon","difficulty":"Beginner","description":"Open hackathon for college students across India with monthly challenges."},
    {"id":"h16","title":"ICICI Appathon 2026","organizer":"ICICI Bank","mode":"online","location":"Online","prize":"₹1,50,000","deadline":"2026-07-22","tags":["FinTech","Banking","Mobile","Flutter"],"url":"https://unstop.com/hackathons","type":"hackathon","difficulty":"Beginner","description":"Build innovative fintech solutions for the banking sector."},
    {"id":"h17","title":"Hack2Skill National Hackathon","organizer":"Hack2Skill","mode":"online","location":"Online","prize":"₹5,00,000+","deadline":"2026-08-18","tags":["AI","ML","Web3","IoT"],"url":"https://hack2skill.com","type":"hackathon","difficulty":"Intermediate","description":"National level hackathon with multiple problem statements across domains."},
    {"id":"h18","title":"SAP Labs India CodeJam","organizer":"SAP Labs","mode":"offline","location":"Bangalore","prize":"₹75,000 + Internship","deadline":"2026-07-28","tags":["SAP","Cloud","Enterprise Tech"],"url":"https://community.sap.com/events","type":"hackathon","difficulty":"Intermediate","description":"Build enterprise solutions using SAP technologies."},
    {"id":"h19","title":"Namma Yatri Open Mobility Challenge","organizer":"Namma Yatri","mode":"online","location":"Online","prize":"₹3,00,000+","deadline":"2026-08-25","tags":["Mobility","Open Source","Flutter","Backend"],"url":"https://nammayatri.in/challenge","type":"hackathon","difficulty":"Intermediate","description":"Build solutions for open mobility and urban transportation challenges."},
    {"id":"h20","title":"Devfolio Fellowship Hackathon","organizer":"Devfolio","mode":"online","location":"Online","prize":"$5,000 + Fellowship","deadline":"2026-09-10","tags":["Web3","Ethereum","Solidity","DeFi"],"url":"https://devfolio.co/hackathons","type":"hackathon","difficulty":"Advanced","description":"Exclusive hackathon for serious Web3 builders with mentorship."},
]

# ── Static Webinars (20) ──────────────────────────────────────────────────────
WEBINARS = [
    {"id":"w1","title":"LLMs in Production: Prototype to Scale","host":"Google DeepMind","date":"2026-04-15","time":"6:00 PM IST","mode":"Online","platform":"YouTube Live","tags":["LLM","MLOps","GenAI","Python"],"url":"https://developers.google.com/events","type":"webinar","free":True,"category":"AI/ML","description":"Deploy large language models in production. Real-world best practices from Google engineers."},
    {"id":"w2","title":"Crack Data Science Interviews at FAANG","host":"Scaler","date":"2026-04-18","time":"5:00 PM IST","mode":"Online","platform":"Zoom","tags":["Data Science","Interview","ML","Statistics"],"url":"https://scaler.com/events","type":"webinar","free":True,"category":"Career","description":"DS interview strategies, common pitfalls and how to stand out from thousands of applicants."},
    {"id":"w3","title":"Full Stack: Next.js 14 + Flask Backend","host":"Coding Ninjas","date":"2026-04-20","time":"7:00 PM IST","mode":"Online","platform":"Discord","tags":["Next.js","React","Python","Flask","PostgreSQL"],"url":"https://www.codingninjas.com/events","type":"webinar","free":True,"category":"Web Dev","description":"End-to-end full stack project with Next.js frontend and Python Flask backend with PostgreSQL."},
    {"id":"w4","title":"AWS Cloud Free Bootcamp — EC2, S3, Lambda","host":"AWS India","date":"2026-04-22","time":"4:00 PM IST","mode":"Online","platform":"AWS Events","tags":["AWS","Cloud","DevOps","EC2","Lambda"],"url":"https://aws.amazon.com/events/india","type":"webinar","free":True,"category":"Cloud","description":"Free 3-hour bootcamp covering EC2, S3, RDS, Lambda with hands-on live demos."},
    {"id":"w5","title":"Open Source Contribution — First PR Guide","host":"GitHub India","date":"2026-04-24","time":"6:30 PM IST","mode":"Online","platform":"GitHub Live","tags":["Git","GitHub","Open Source","Collaboration"],"url":"https://github.com/events","type":"webinar","free":True,"category":"Community","description":"Step-by-step guide to making your first open source contribution to real projects."},
    {"id":"w6","title":"System Design Masterclass — FAANG Level","host":"AlgoUniversity","date":"2026-04-25","time":"7:00 PM IST","mode":"Online","platform":"YouTube","tags":["System Design","Backend","Scalability","Databases"],"url":"https://www.algouniversity.com/events","type":"webinar","free":True,"category":"Career","description":"Design YouTube, WhatsApp, Uber at scale. Interview-focused system design concepts."},
    {"id":"w7","title":"Resume Building for Tech Freshers 2026","host":"Internshala","date":"2026-04-26","time":"5:00 PM IST","mode":"Online","platform":"Zoom","tags":["Resume","Career","Fresher","ATS"],"url":"https://internshala.com/trainings","type":"webinar","free":True,"category":"Career","description":"HR professionals review resumes live. Learn ATS optimization techniques."},
    {"id":"w8","title":"Python for Data Science — Zero to Hero","host":"Analytics Vidhya","date":"2026-04-27","time":"6:00 PM IST","mode":"Online","platform":"YouTube Live","tags":["Python","Data Science","Pandas","NumPy","Matplotlib"],"url":"https://www.analyticsvidhya.com/events","type":"webinar","free":True,"category":"AI/ML","description":"Complete Python data science bootcamp from basics to advanced ML concepts."},
    {"id":"w9","title":"Docker & Kubernetes for Beginners","host":"KodeKloud","date":"2026-04-28","time":"7:00 PM IST","mode":"Online","platform":"Zoom","tags":["Docker","Kubernetes","DevOps","Cloud","Containers"],"url":"https://kodekloud.com/events","type":"webinar","free":True,"category":"Cloud","description":"Hands-on containerization workshop with real deployment exercises."},
    {"id":"w10","title":"React JS Complete Masterclass 2026","host":"Traversy Media","date":"2026-04-29","time":"8:00 PM IST","mode":"Online","platform":"YouTube Live","tags":["React","JavaScript","Frontend","Hooks","Redux"],"url":"https://www.youtube.com/@TraversyMedia","type":"webinar","free":True,"category":"Web Dev","description":"Complete React JS course covering hooks, context API, Redux Toolkit."},
    {"id":"w11","title":"How to Get Your First Tech Job in 2026","host":"LinkedIn India","date":"2026-04-30","time":"5:00 PM IST","mode":"Online","platform":"LinkedIn Live","tags":["Career","Job Search","LinkedIn","Networking","Portfolio"],"url":"https://www.linkedin.com/events","type":"webinar","free":True,"category":"Career","description":"LinkedIn India recruiters share insider tips on landing your first tech job."},
    {"id":"w12","title":"Machine Learning with Scikit-Learn","host":"Kaggle","date":"2026-05-01","time":"6:30 PM IST","mode":"Online","platform":"YouTube Live","tags":["ML","Scikit-learn","Python","Classification","Regression"],"url":"https://www.kaggle.com/learn/events","type":"webinar","free":True,"category":"AI/ML","description":"Hands-on ML workshop using real Kaggle competition datasets."},
    {"id":"w13","title":"Flutter App Development — Bootcamp","host":"Google Flutter","date":"2026-05-03","time":"4:00 PM IST","mode":"Online","platform":"YouTube Live","tags":["Flutter","Dart","Android","iOS","Mobile"],"url":"https://flutter.dev/events","type":"webinar","free":True,"category":"Web Dev","description":"Build cross-platform mobile apps with Flutter from scratch to deployment."},
    {"id":"w14","title":"Generative AI for Developers — Azure OpenAI","host":"Microsoft Azure","date":"2026-05-05","time":"6:00 PM IST","mode":"Online","platform":"Teams Live","tags":["GenAI","Azure","OpenAI","ChatGPT","LLM"],"url":"https://developer.microsoft.com/en-us/events","type":"webinar","free":True,"category":"AI/ML","description":"Build GenAI applications using Azure OpenAI Service with hands-on labs."},
    {"id":"w15","title":"DSA for Placements — Top 100 Problems","host":"Striver (takeUforward)","date":"2026-05-06","time":"8:00 PM IST","mode":"Online","platform":"YouTube Live","tags":["DSA","LeetCode","Arrays","Trees","Graphs","DP"],"url":"https://www.youtube.com/@takeUforward","type":"webinar","free":True,"category":"Career","description":"Solve the most frequently asked DSA problems in FAANG placement interviews."},
    {"id":"w16","title":"MongoDB Atlas + Node.js — Full Stack","host":"MongoDB","date":"2026-05-07","time":"6:00 PM IST","mode":"Online","platform":"MongoDB Live","tags":["MongoDB","Node.js","Atlas","Express","MERN"],"url":"https://www.mongodb.com/events","type":"webinar","free":True,"category":"Web Dev","description":"Build a complete MERN stack application with MongoDB Atlas cloud."},
    {"id":"w17","title":"Power BI & Data Visualization Masterclass","host":"Microsoft","date":"2026-05-08","time":"4:00 PM IST","mode":"Online","platform":"Teams Live","tags":["Power BI","Data Visualization","Analytics","Excel"],"url":"https://powerbi.microsoft.com/en-us/events","type":"webinar","free":True,"category":"AI/ML","description":"Create stunning dashboards and reports using Microsoft Power BI."},
    {"id":"w18","title":"Ethical Hacking & Cybersecurity Basics","host":"EC-Council","date":"2026-05-09","time":"7:00 PM IST","mode":"Online","platform":"Zoom","tags":["Cybersecurity","Ethical Hacking","Network Security","OWASP"],"url":"https://www.eccouncil.org/events","type":"webinar","free":True,"category":"Community","description":"Introduction to ethical hacking, penetration testing and cybersecurity fundamentals."},
    {"id":"w19","title":"Product Management for Engineers","host":"Product School","date":"2026-05-10","time":"5:30 PM IST","mode":"Online","platform":"Zoom","tags":["Product Management","Career","Strategy","Agile"],"url":"https://productschool.com/events","type":"webinar","free":True,"category":"Career","description":"How engineers can successfully transition to product management roles."},
    {"id":"w20","title":"Startup Funding 101 — For Tech Founders","host":"YCombinator","date":"2026-05-12","time":"9:00 PM IST","mode":"Online","platform":"YouTube Live","tags":["Startup","Funding","Entrepreneurship","VC","Pitch"],"url":"https://www.ycombinator.com/events","type":"webinar","free":True,"category":"Community","description":"Y Combinator partners explain how to raise seed funding for your tech startup."},
]

# ── Helpers ───────────────────────────────────────────────────────────────────
def get_tags(text):
    t = text.lower()
    return list(dict.fromkeys([v for k, v in SKILLS.items() if k in t]))[:6]

def is_intern(title):
    return any(w in title.lower() for w in ["intern","internship","trainee","apprentice","co-op","fresher"])

def strip_html(text):
    text = re.sub(r'<[^>]+>', ' ', text or '')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# ── JSearch API ───────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
# API 1: JSearch (RapidAPI) — 500 free/month
# ══════════════════════════════════════════════════════════════════════════════
def from_jsearch(query, location="india", page=1):
    if not JSEARCH_KEY:
        return [], "no_key"
    try:
        resp = httpx.get(
            "https://jsearch.p.rapidapi.com/search",
            params={"query": f"{query} {location}", "page": str(page),
                    "num_pages": "3", "country": "in", "date_posted": "all"},
            headers={"X-RapidAPI-Key": JSEARCH_KEY,
                     "X-RapidAPI-Host": "jsearch.p.rapidapi.com"},
            timeout=20,
        )
        if resp.status_code in (429, 403):
            return [], "quota_exceeded"
        if resp.status_code != 200:
            return [], "error"
        d = resp.json()
        if d.get("status") == "ERROR":
            return [], "quota_exceeded"
        out, seen = [], set()
        for j in d.get("data", []):
            key = (j.get("job_title","") + j.get("employer_name","")).lower()
            if key in seen: continue
            seen.add(key)
            title = j.get("job_title","")
            desc  = strip_html(j.get("job_description",""))
            loc   = f"{j.get('job_city','')}, {j.get('job_country','')}".strip(", ") or location
            out.append({
                "id": f"js_{j.get('job_id','')}", "title": title,
                "company": j.get("employer_name",""), "location": loc,
                "description": desc[:600], "salary_min": j.get("job_min_salary"),
                "salary_max": j.get("job_max_salary"),
                "url": j.get("job_apply_link") or j.get("job_google_link","#"),
                "tags": get_tags(title+" "+desc), "posted": j.get("job_posted_at_datetime_utc",""),
                "type": "internship" if is_intern(title) else "job",
                "source": "JSearch", "logo": j.get("employer_logo",""),
                "remote": j.get("job_is_remote", False),
            })
        return out, None
    except Exception:
        return [], "error"

# ══════════════════════════════════════════════════════════════════════════════
# API 2: Adzuna — Completely FREE, no quota, register at developer.adzuna.com
# ══════════════════════════════════════════════════════════════════════════════
ADZUNA_ID  = os.getenv("ADZUNA_APP_ID",  "")
ADZUNA_KEY = os.getenv("ADZUNA_APP_KEY", "")

def from_adzuna(query, location="india", page=1, intern_mode=False):
    if not ADZUNA_ID or not ADZUNA_KEY:
        return []
    try:
        what = f"{query} internship" if intern_mode and "intern" not in query.lower() else query
        params = {
            "app_id": ADZUNA_ID, "app_key": ADZUNA_KEY,
            "results_per_page": 20, "what": what,
            "sort_by": "date", "content-type": "application/json",
        }
        if location.lower() not in ("india","in",""):
            params["where"] = location
        r = httpx.get(
            f"https://api.adzuna.com/v1/api/jobs/in/search/{page}",
            params=params, timeout=15,
        )
        if r.status_code != 200:
            return []
        out = []
        for j in r.json().get("results", []):
            title = j.get("title","")
            desc  = strip_html(j.get("description",""))
            sal   = j.get("salary_min"), j.get("salary_max")
            out.append({
                "id": f"az_{j.get('id','')}", "title": title,
                "company": j.get("company",{}).get("display_name",""),
                "location": j.get("location",{}).get("display_name","India"),
                "description": desc[:600],
                "salary_min": int(sal[0]) if sal[0] else None,
                "salary_max": int(sal[1]) if sal[1] else None,
                "url": j.get("redirect_url","#"),
                "tags": get_tags(title+" "+desc), "posted": j.get("created",""),
                "type": "internship" if (intern_mode or is_intern(title)) else "job",
                "source": "Adzuna", "logo": "", "remote": False,
            })
        return out
    except Exception:
        return []

# ══════════════════════════════════════════════════════════════════════════════
# API 3: Remotive — 100% FREE, no key needed, remote tech jobs
# ══════════════════════════════════════════════════════════════════════════════
def from_remotive(query, intern_mode=False):
    try:
        r = httpx.get(
            "https://remotive.com/api/remote-jobs",
            params={"search": query, "limit": 30},
            timeout=15,
            headers={"User-Agent": "CareerHub/2.0"},
        )
        if r.status_code != 200:
            return []
        out = []
        for j in r.json().get("jobs", []):
            title = j.get("title","")
            desc  = strip_html(j.get("description",""))
            jtype = "internship" if (intern_mode or is_intern(title)) else "job"
            out.append({
                "id": f"rem_{j.get('id','')}", "title": title,
                "company": j.get("company_name",""),
                "location": j.get("candidate_required_location","Remote") or "Remote",
                "description": desc[:600], "salary_min": None, "salary_max": None,
                "url": j.get("url","#"),
                "tags": get_tags(title+" "+desc+" "+(j.get("tags","") or "")),
                "posted": j.get("publication_date",""), "type": jtype,
                "source": "Remotive", "logo": j.get("company_logo",""), "remote": True,
            })
        return out
    except Exception:
        return []

# ══════════════════════════════════════════════════════════════════════════════
# API 4: The Muse — 100% FREE, no key needed, global companies
# ══════════════════════════════════════════════════════════════════════════════
def from_themuse(query, page=1, intern_mode=False):
    try:
        cat_map = {
            "python":"Engineering","javascript":"Engineering","react":"Engineering",
            "node":"Engineering","java":"Engineering","backend":"Engineering",
            "frontend":"Engineering","data":"Data Science","machine learning":"Data Science",
            "ml":"Data Science","ai":"Data Science","devops":"IT","design":"Design",
            "android":"Engineering","flutter":"Engineering","cloud":"IT",
        }
        cat = next((v for k,v in cat_map.items() if k in query.lower()), "Engineering")
        params = {"page": page, "descending": "true", "category": cat}
        if intern_mode:
            params["level"] = "Internship"
        r = httpx.get("https://www.themuse.com/api/public/jobs",
                      params=params, timeout=15,
                      headers={"User-Agent": "CareerHub/2.0"})
        if r.status_code != 200:
            return []
        out = []
        for j in r.json().get("results", []):
            title = j.get("name","")
            desc  = strip_html(j.get("contents",""))
            levels = [l.get("name","") for l in j.get("levels",[])]
            locs   = j.get("locations",[])
            loc    = locs[0].get("name","Remote") if locs else "Remote"
            jtype  = "internship" if (intern_mode or "Internship" in levels or is_intern(title)) else "job"
            out.append({
                "id": f"muse_{j.get('id','')}", "title": title,
                "company": j.get("company",{}).get("name",""),
                "location": loc, "description": desc[:600],
                "salary_min": None, "salary_max": None,
                "url": j.get("refs",{}).get("landing_page","#"),
                "tags": get_tags(title+" "+desc), "posted": j.get("publication_date",""),
                "type": jtype, "source": "The Muse",
                "logo": j.get("company",{}).get("refs",{}).get("logo_image",""), "remote": False,
            })
        return out
    except Exception:
        return []

# ══════════════════════════════════════════════════════════════════════════════
# MASTER FETCHER — 4 APIs, automatic fallback, deduplication
# ══════════════════════════════════════════════════════════════════════════════
def from_himalayas(query, intern_mode=False):
    """Himalayas — FREE JSON API, no key, no signup, real companies with salaries"""
    try:
        params = {"q": query, "limit": 20}
        if intern_mode:
            params["employment_type"] = "Intern"
        r = httpx.get(
            "https://himalayas.app/jobs/api/search",
            params=params,
            headers={"User-Agent": "CareerHub/2.0", "Accept": "application/json"},
            timeout=12,
        )
        if r.status_code != 200:
            return []
        out = []
        for j in r.json().get("jobs", []):
            title   = j.get("title", "")
            company = j.get("companyName", "")
            desc    = strip_html(j.get("description", "") or j.get("shortDescription", ""))
            locs    = j.get("locationRestrictions") or []
            loc     = ", ".join(locs) if locs else "Remote / Worldwide"
            sal_min = j.get("salaryMin")
            sal_max = j.get("salaryMax")
            out.append({
                "id":          f"hm_{j.get('id', abs(hash(j.get('applicationLink',''))))}",
                "title":       title,
                "company":     company,
                "location":    loc,
                "description": desc[:600],
                "salary_min":  int(sal_min) if sal_min else None,
                "salary_max":  int(sal_max) if sal_max else None,
                "url":         j.get("applicationLink") or f"https://himalayas.app/jobs/{j.get('slug','')}",
                "tags":        get_tags(title + " " + desc + " " + " ".join(j.get("skills", []))),
                "posted":      j.get("createdAt", ""),
                "type":        "internship" if (intern_mode or is_intern(title)) else "job",
                "source":      "Himalayas",
                "logo":        j.get("companyLogo", ""),
                "remote":      True,
            })
        return out
    except Exception:
        return []


def from_arbeitnow(query, intern_mode=False):
    """Arbeitnow — FREE API, no key, global tech jobs"""
    try:
        r = httpx.get(
            "https://www.arbeitnow.com/api/job-board-api",
            params={"q": query, "page": 1},
            headers={"User-Agent": "CareerHub/2.0", "Accept": "application/json"},
            timeout=12,
        )
        if r.status_code != 200:
            return []
        out = []
        ql = query.lower().split()[0] if query else ""
        for j in r.json().get("data", [])[:20]:
            title = j.get("title", "")
            desc  = strip_html(j.get("description", ""))
            if ql and ql not in (title + desc).lower():
                continue
            tags_raw = j.get("tags", [])
            out.append({
                "id":          f"an_{j.get('slug', abs(hash(j.get('url',''))))}",
                "title":       title,
                "company":     j.get("company_name", ""),
                "location":    j.get("location", "Remote"),
                "description": desc[:600],
                "salary_min":  None,
                "salary_max":  None,
                "url":         j.get("url", "#"),
                "tags":        tags_raw[:6] if tags_raw else get_tags(title + " " + desc),
                "posted":      j.get("created_at", ""),
                "type":        "internship" if (intern_mode or is_intern(title)) else "job",
                "source":      "Arbeitnow",
                "logo":        "",
                "remote":      j.get("remote", False),
            })
        return out
    except Exception:
        return []


def from_jobicy(query, intern_mode=False):
    """Jobicy — FREE JSON API, no key, tech jobs"""
    try:
        r = httpx.get(
            "https://jobicy.com/api/v2/remote-jobs",
            params={"count": 20, "geo": "india", "industry": "tech", "tag": query},
            headers={"User-Agent": "CareerHub/2.0", "Accept": "application/json"},
            timeout=12,
        )
        if r.status_code != 200:
            return []
        out = []
        for j in r.json().get("jobs", []):
            title = j.get("jobTitle", "")
            desc  = strip_html(j.get("jobDescription", ""))
            out.append({
                "id":          f"jc_{j.get('id', abs(hash(j.get('url',''))))}",
                "title":       title,
                "company":     j.get("companyName", ""),
                "location":    j.get("jobGeo", "India") or "India",
                "description": desc[:600],
                "salary_min":  None,
                "salary_max":  None,
                "url":         j.get("url", "#"),
                "tags":        get_tags(title + " " + desc),
                "posted":      j.get("pubDate", ""),
                "type":        "internship" if (intern_mode or is_intern(title)) else "job",
                "source":      "Jobicy",
                "logo":        j.get("companyLogo", ""),
                "remote":      True,
            })
        return out
    except Exception:
        return []


def fetch_jobs(query, location="india", page=1, intern_mode=False):
    if not query or not query.strip():
        return {"results":[], "count":0, "error":"Query required"}

    # API 1: JSearch (best — LinkedIn/Indeed/Naukri)
    jobs, err = from_jsearch(query, location, page)
    if jobs:
        if intern_mode:
            interns = [j for j in jobs if j["type"]=="internship"]
            jobs = interns if interns else jobs
        return {"results": jobs, "count": len(jobs),
                "source": "JSearch — LinkedIn / Indeed / Glassdoor / Naukri"}

    # API 2: Adzuna (free, India jobs)
    az_jobs = from_adzuna(query, location, page, intern_mode)
    if az_jobs:
        return {"results": az_jobs, "count": len(az_jobs), "source": "Adzuna India (Free)"}

    # API 3: Himalayas (free JSON API, no key, real companies + salaries)
    hm = from_himalayas(query, intern_mode)
    if hm:
        return {"results": hm, "count": len(hm), "source": "Himalayas (Free — No Key)"}

    # API 4: Arbeitnow (free JSON API, no key, global tech jobs)
    an = from_arbeitnow(query, intern_mode)
    if an:
        return {"results": an, "count": len(an), "source": "Arbeitnow (Free — No Key)"}

    # API 5: Jobicy (free JSON API, no key, tech jobs)
    jc = from_jobicy(query, intern_mode)
    if jc:
        return {"results": jc, "count": len(jc), "source": "Jobicy (Free — No Key)"}

    msg = "Koi result nahi mila. Dusri query try karo (e.g. 'python', 'react', 'data science')."
    return {"results":[], "count":0, "source":"none", "error": msg}

# ── Ranking (TF-IDF + BERT-style cosine similarity) ──────────────────────────
def _get_profile(uid):
    u = User.query.get(uid)
    if not u: return {}
    return {"skills":u.skills or "", "degree":u.degree or "", "resume_text":u.resume_text or ""}

def _rank(profile, items):
    if not items: return items
    combined = f"{profile.get('skills','')} {profile.get('degree','')} {profile.get('resume_text','')[:500]}".strip()
    if not combined: return items
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        for item in items:
            it = f"{item.get('title','')} {' '.join(item.get('tags',[]))} {item.get('description','')[:200]}"
            try:
                mat = TfidfVectorizer(stop_words="english").fit_transform([combined, it])
                item["match_score"] = round(float(cosine_similarity(mat[0], mat[1])[0][0])*100, 1)
            except Exception:
                item["match_score"] = 0
        items.sort(key=lambda x: x.get("match_score",0), reverse=True)
    except Exception as e:
        print(f"[rank] {e}")
    return items

def _try_rank(items):
    try:
        verify_jwt_in_request(optional=True)
        uid = get_jwt_identity()
        if uid:
            return _rank(_get_profile(int(uid)), items)
    except Exception: pass
    return items

# ── Routes: Jobs ──────────────────────────────────────────────────────────────
@jobs_bp.route("/")
def get_jobs():
    q    = request.args.get("q","").strip()
    loc  = request.args.get("location","india").strip()
    page = max(1, int(request.args.get("page",1)))
    data = fetch_jobs(q, loc, page, intern_mode=False)
    data["results"] = [j for j in data["results"] if j.get("type")!="internship"]
    data["results"] = _try_rank(data["results"])
    data["count"]   = len(data["results"])
    return jsonify(data)

@jobs_bp.route("/internships")
def get_internships():
    q   = request.args.get("q","").strip()
    loc = request.args.get("location","india").strip()
    iq  = q if "intern" in q.lower() else f"{q} internship"
    data = fetch_jobs(iq, loc, 1, intern_mode=True)
    for j in data["results"]: j["type"] = "internship"
    data["results"] = _try_rank(data["results"])
    data["count"]   = len(data["results"])
    return jsonify(data)

@jobs_bp.route("/skill-gap", methods=["POST"])
@jwt_required()
def skill_gap():
    user = User.query.get(int(get_jwt_identity()))
    if not user: return jsonify({"error":"User not found"}), 404
    d = request.get_json(silent=True) or {}
    user_skills = set(s.strip().lower() for s in (user.skills or "").split(",") if s.strip())
    required    = set(t.strip().lower() for t in d.get("job_tags",[]))
    for kw in SKILLS:
        if kw in (d.get("job_description","") or "").lower():
            required.add(kw)
    missing = sorted(required - user_skills)
    matched = sorted(required & user_skills)
    pct     = round(len(matched)/max(len(required),1)*100,1)
    rec     = "Strong match! Apply now." if pct>=80 else (
              f"Learn: {', '.join(missing[:3])}" if missing else "Good match!")
    return jsonify({"matched_skills":matched,"missing_skills":missing[:8],
                    "match_percentage":pct,"recommendation":rec})

@jobs_bp.route("/interact", methods=["POST"])
@jwt_required()
def interact():
    d = request.get_json(silent=True) or {}
    db.session.add(UserInteraction(
        user_id=int(get_jwt_identity()), item_id=str(d.get("item_id","")),
        item_type=d.get("item_type","job"), action=d.get("action","click"),
        dwell_secs=int(d.get("dwell_secs",0)),
    ))
    db.session.commit()
    return jsonify({"message":"Recorded"}), 201

# ── Routes: Hackathons ────────────────────────────────────────────────────────
@hackathons_bp.route("/")
def get_hackathons():
    mode=request.args.get("mode"); diff=request.args.get("difficulty")
    q=request.args.get("q","").lower(); res=HACKATHONS[:]
    if TICKETMASTER_KEY:
        try:
            r=httpx.get("https://app.ticketmaster.com/discovery/v2/events.json",
                params={"apikey":TICKETMASTER_KEY,"keyword":"hackathon",
                        "countryCode":"IN","size":10,"sort":"date,asc"},timeout=8)
            if r.status_code==200:
                for e in r.json().get("_embedded",{}).get("events",[]):
                    res.append({"id":f"tm_{e.get('id','')}","title":e.get("name",""),
                        "organizer":"Live Event","mode":"offline","location":"India","prize":"Check website",
                        "deadline":e.get("dates",{}).get("start",{}).get("localDate",""),
                        "tags":["Hackathon","Tech","Live"],"url":e.get("url","#"),"type":"hackathon",
                        "difficulty":"Intermediate","description":(e.get("info","") or "")[:300]})
        except Exception: pass
    if mode: res=[h for h in res if h["mode"]==mode]
    if diff: res=[h for h in res if h["difficulty"]==diff]
    if q:    res=[h for h in res if q in h["title"].lower() or any(q in t.lower() for t in h.get("tags",[]))]
    return jsonify({"count":len(res),"results":_try_rank(res)})

@hackathons_bp.route("/<hid>")
def get_hackathon(hid):
    item=next((h for h in HACKATHONS if h["id"]==hid),None)
    return (jsonify(item),200) if item else (jsonify({"error":"Not found"}),404)

# ── Routes: Webinars ──────────────────────────────────────────────────────────
@webinars_bp.route("/")
def get_webinars():
    cat=request.args.get("category"); q=request.args.get("q","").lower(); res=WEBINARS[:]
    if EVENTBRITE_TOKEN:
        try:
            r=httpx.get("https://www.eventbriteapi.com/v3/events/search/",
                headers={"Authorization":f"Bearer {EVENTBRITE_TOKEN}"},
                params={"q":"technology webinar india","sort_by":"date",
                        "start_date.range_start":"2026-01-01T00:00:00","expand":"organizer"},timeout=8)
            if r.status_code==200:
                for e in r.json().get("events",[])[:10]:
                    name=e.get("name",{}).get("text","")
                    if not name: continue
                    res.append({"id":f"eb_{e.get('id','')}","title":name,
                        "host":(e.get("organizer") or {}).get("name","Tech Event"),
                        "date":e.get("start",{}).get("local","")[:10],
                        "time":e.get("start",{}).get("local","")[11:16]+" IST",
                        "mode":"Online" if e.get("online_event") else "Offline",
                        "platform":"Eventbrite","tags":["Technology","Webinar","Live"],
                        "url":e.get("url","#"),"type":"webinar","free":e.get("is_free",True),
                        "category":"Tech","description":(e.get("description",{}).get("text","") or "")[:300]})
        except Exception: pass
    if cat: res=[w for w in res if w.get("category")==cat]
    if q:   res=[w for w in res if q in w["title"].lower() or any(q in t.lower() for t in w.get("tags",[]))]
    return jsonify({"count":len(res),"results":_try_rank(res)})

@webinars_bp.route("/<wid>")
def get_webinar(wid):
    item=next((w for w in WEBINARS if w["id"]==wid),None)
    return (jsonify(item),200) if item else (jsonify({"error":"Not found"}),404)

# ── Routes: Recommendations ───────────────────────────────────────────────────
@rec_bp.route("/feed")
@jwt_required()
def feed():
    uid=int(get_jwt_identity()); user=User.query.get(uid)
    if not user: return jsonify({"error":"Not found"}),404
    skills_list=[s.strip() for s in (user.skills or "software developer").split(",") if s.strip()]
    q=skills_list[0] if skills_list else "software developer"
    data=fetch_jobs(q)
    profile=_get_profile(uid)
    ranked=_rank(profile, data["results"]+HACKATHONS+WEBINARS)
    return jsonify({
        "jobs":       [o for o in ranked if o.get("type") not in ("hackathon","webinar")][:6],
        "hackathons": [o for o in ranked if o.get("type")=="hackathon"][:4],
        "webinars":   [o for o in ranked if o.get("type")=="webinar"][:4],
    })

@rec_bp.route("/search")
def search_all():
    q=request.args.get("q","").strip()
    if len(q)<2: return jsonify({"error":"Query too short"}),400
    ql=q.lower()
    hacks=[h for h in HACKATHONS if ql in h["title"].lower() or any(ql in t.lower() for t in h["tags"])]
    webs=[w for w in WEBINARS if ql in w["title"].lower() or any(ql in t.lower() for t in w["tags"])]
    data=fetch_jobs(q)
    return jsonify({"jobs":data["results"][:5],"hackathons":hacks[:3],"webinars":webs[:3],
                    "total":len(data["results"])+len(hacks)+len(webs)})

# ── Routes: User / Resume ─────────────────────────────────────────────────────
@user_bp.route("/profile", methods=["GET"])
@jwt_required()
def get_profile():
    user=User.query.get(int(get_jwt_identity()))
    return jsonify({"user":user.to_dict()}) if user else (jsonify({"error":"Not found"}),404)

@user_bp.route("/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    user=User.query.get(int(get_jwt_identity()))
    if not user: return jsonify({"error":"Not found"}),404
    d=request.get_json(silent=True) or {}
    if "name"          in d: user.name         =sanitize(d["name"],120)
    if "college"       in d: user.college       =sanitize(d["college"],200)
    if "degree"        in d: user.degree        =sanitize(d["degree"],100)
    if "graduation_yr" in d: user.graduation_yr =d["graduation_yr"]
    if "skills"        in d: user.skills        =",".join(sanitize(s,50) for s in d["skills"] if s)
    if "resume_text"   in d: user.resume_text   =sanitize(d["resume_text"],10000)
    db.session.commit()
    return jsonify({"message":"Updated","user":user.to_dict()})

@user_bp.route("/resume", methods=["POST"])
@jwt_required()
def upload_resume():
    user=User.query.get(int(get_jwt_identity()))
    if not user: return jsonify({"error":"Not found"}),404
    if "resume" not in request.files:
        return jsonify({"error":"Send file with field name 'resume'"}),400
    f=request.files["resume"]
    if not f.filename: return jsonify({"error":"Empty filename"}),400
    ext=f.filename.rsplit(".",1)[-1].lower() if "." in f.filename else ""
    if ext not in ("pdf","txt","doc","docx"):
        return jsonify({"error":"Only PDF, TXT, DOC, DOCX allowed"}),400
    raw=f.read()
    text=""
    if ext=="pdf":
        try:
            import pypdf
            reader=pypdf.PdfReader(io.BytesIO(raw))
            text=" ".join((p.extract_text() or "") for p in reader.pages)
        except Exception: pass
    elif ext in ("doc","docx"):
        try:
            from docx import Document
            text="\n".join(p.text for p in Document(io.BytesIO(raw)).paragraphs)
        except Exception: pass
    else:
        text=raw.decode("utf-8","ignore")
    text=re.sub(r'\s+',' ',text).strip()
    if len(text)<30:
        return jsonify({"error":"Could not extract text from resume. Try a text-based PDF or DOCX."}),400
    detected=list(dict.fromkeys([label for kw,label in SKILLS.items() if kw in text.lower()]))
    existing=set(s.strip() for s in (user.skills or "").split(",") if s.strip())
    merged=sorted(existing|set(detected))
    user.resume_text    =text[:10000]
    user.resume_filename=sanitize(f.filename,200)
    user.skills         =",".join(merged)
    db.session.commit()
    return jsonify({"message":"Resume uploaded and parsed!","skills_detected":detected,
                    "all_skills":merged,"resume_filename":user.resume_filename,
                    "text_length":len(text)}),200

@user_bp.route("/resume/recommendations", methods=["GET"])
@jwt_required()
def resume_recommendations():
    user=User.query.get(int(get_jwt_identity()))
    if not user: return jsonify({"error":"Not found"}),404
    if not user.resume_text and not user.skills:
        return jsonify({"error":"Upload resume first or add skills to profile"}),400
    profile    =_get_profile(int(get_jwt_identity()))
    skills_list=[s.strip() for s in (user.skills or "developer").split(",") if s.strip()]
    # Use top 3 skills to search for more relevant results
    q          =" ".join(skills_list[:3]) if skills_list else "software developer"
    job_data   =fetch_jobs(q)
    all_items  =job_data["results"]+HACKATHONS+WEBINARS
    ranked     =_rank(profile, all_items)
    return jsonify({
        "query_used":  q,
        "skills_used": skills_list[:10],
        "jobs":        [i for i in ranked if i.get("type") not in ("hackathon","webinar")][:8],
        "internships": [i for i in ranked if i.get("type")=="internship"][:6],
        "hackathons":  [i for i in ranked if i.get("type")=="hackathon"][:6],
        "webinars":    [i for i in ranked if i.get("type")=="webinar"][:6],
    })

@user_bp.route("/saved", methods=["GET"])
@jwt_required()
def get_saved():
    uid=int(get_jwt_identity())
    saved=SavedItem.query.filter_by(user_id=uid).all()
    return jsonify({"saved":[{"item_id":s.item_id,"item_type":s.item_type,
        "title":s.title,"company":s.company,"saved_at":s.saved_at.isoformat()} for s in saved]})

@user_bp.route("/saved", methods=["POST"])
@jwt_required()
def toggle_saved():
    uid=int(get_jwt_identity()); d=request.get_json(silent=True) or {}
    ex=SavedItem.query.filter_by(user_id=uid,item_id=str(d.get("item_id",""))).first()
    if ex:
        db.session.delete(ex); db.session.commit()
        return jsonify({"message":"Removed","saved":False})
    db.session.add(SavedItem(user_id=uid,item_id=str(d.get("item_id","")),
        item_type=d.get("item_type","job"),title=sanitize(d.get("title",""),300),
        company=sanitize(d.get("company",""),200)))
    db.session.commit()
    return jsonify({"message":"Saved","saved":True}),201

@user_bp.route("/delete-account", methods=["DELETE"])
@jwt_required()
def delete_account():
    uid=int(get_jwt_identity()); user=User.query.get(uid)
    if not user: return jsonify({"error":"Not found"}),404
    db.session.delete(user); db.session.commit()
    return jsonify({"message":"Account deleted"})

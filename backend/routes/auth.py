from datetime import datetime, timedelta, timezone
import re, jwt
from flask import Blueprint, request, jsonify, current_app, g
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_connection, row
from middleware.auth import require_auth

bp = Blueprint("auth", __name__, url_prefix="/api/auth")
EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

def issue_token(user):
    return jwt.encode({"sub": str(user["user_id"]), "exp": datetime.now(timezone.utc) + timedelta(hours=12)}, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")

@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    name, email, phone, password = [str(data.get(k, "")).strip() for k in ("full_name", "email", "phone", "password")]
    if not name or len(name) > 120 or not EMAIL.match(email) or len(password) < 8:
        return jsonify(error="Enter a name, valid email, and password with at least 8 characters"), 400
    conn = get_connection(); cur = conn.cursor(dictionary=True)
    try:
        cur.execute("INSERT INTO users (full_name,email,phone,password_hash,role) VALUES (%s,%s,%s,%s,'customer')", (name,email.lower(),phone or None,generate_password_hash(password)))
        conn.commit(); user={"user_id":cur.lastrowid,"full_name":name,"email":email.lower(),"role":"customer"}
        return jsonify(user=user, token=issue_token(user)), 201
    except Exception as exc:
        conn.rollback()
        if getattr(exc, "errno", None) == 1062: return jsonify(error="An account with this email already exists"), 409
        raise
    finally: cur.close(); conn.close()

@bp.post("/login")
def login():
    data=request.get_json(silent=True) or {}; email=str(data.get("email"," ")).strip().lower(); password=str(data.get("password",""))
    conn=get_connection(); cur=conn.cursor(dictionary=True)
    cur.execute("SELECT user_id,full_name,email,role,password_hash FROM users WHERE email=%s",(email,)); user=row(cur); cur.close(); conn.close()
    if not user or not check_password_hash(user["password_hash"],password): return jsonify(error="Email or password is incorrect"),401
    user.pop("password_hash"); return jsonify(user=user,token=issue_token(user))

@bp.get("/me")
@require_auth()
def me(): return jsonify(user=g.user)

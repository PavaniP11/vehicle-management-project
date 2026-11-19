from functools import wraps
from flask import request, jsonify, current_app, g
import jwt
from database import get_connection, row

def require_auth(roles=None):
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            header = request.headers.get("Authorization", "")
            if not header.startswith("Bearer "):
                return jsonify(error="Authentication required"), 401
            try:
                payload = jwt.decode(header[7:], current_app.config["JWT_SECRET_KEY"], algorithms=["HS256"])
                conn = get_connection(); cur = conn.cursor(dictionary=True)
                cur.execute("SELECT user_id, full_name, email, role FROM users WHERE user_id=%s", (payload.get("sub"),))
                g.user = row(cur); cur.close(); conn.close()
                if not g.user: return jsonify(error="Account not found"), 401
                if roles and g.user["role"] not in roles: return jsonify(error="Administrator access required"), 403
            except jwt.ExpiredSignatureError:
                return jsonify(error="Session expired"), 401
            except jwt.InvalidTokenError:
                return jsonify(error="Invalid token"), 401
            return fn(*args, **kwargs)
        return wrapped
    return decorator

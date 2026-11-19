from flask import Blueprint, request, jsonify
from database import get_connection, rows, row
from middleware.auth import require_auth

bp=Blueprint("vehicles",__name__,url_prefix="/api/vehicles")
FIELDS=("vehicle_name","brand","model","vehicle_type","registration_number","description","fuel_type","transmission","seating_capacity","rent_per_day","image_url","availability_status")
def payload(data):
    d={k:data.get(k) for k in FIELDS}
    if not all(str(d[k] or "").strip() for k in ("vehicle_name","brand","model","registration_number")) or d["vehicle_type"] not in ("car","bike","scooter") or not d["rent_per_day"]: raise ValueError("Name, brand, model, registration, type, and daily price are required")
    try:
        d["rent_per_day"]=float(d["rent_per_day"]);d["seating_capacity"]=int(d["seating_capacity"] or 2)
        if d["rent_per_day"]<=0 or d["seating_capacity"]<=0: raise ValueError()
    except (TypeError,ValueError): raise ValueError("Daily price and seating capacity must be positive numbers")
    d["availability_status"]=d["availability_status"] or "available"
    if d["availability_status"] not in ("available","rented","maintenance"): raise ValueError("Invalid availability status")
    return d

@bp.get("")
def listing():
    q=request.args; sql="SELECT * FROM vehicles WHERE 1=1"; params=[]
    if q.get("search"): sql+=" AND (vehicle_name LIKE %s OR brand LIKE %s OR model LIKE %s)"; params += [f"%{q['search']}%"]*3
    if q.get("type") in ("car","bike","scooter"): sql+=" AND vehicle_type=%s"; params.append(q["type"])
    if q.get("available")=="true": sql+=" AND availability_status='available'"
    if q.get("max_price"):
        try: sql+=" AND rent_per_day<=%s"; params.append(float(q["max_price"]))
        except ValueError: return jsonify(error="Invalid max_price"),400
    sort=q.get("sort"); sql += " ORDER BY rent_per_day " + ("DESC" if sort=="price_desc" else "ASC" if sort=="price_asc" else "ASC")
    conn=get_connection(); cur=conn.cursor(dictionary=True); cur.execute(sql,tuple(params)); result=rows(cur); cur.close();conn.close();return jsonify(vehicles=result)

@bp.get("/<int:vehicle_id>")
def detail(vehicle_id):
    conn=get_connection();cur=conn.cursor(dictionary=True);cur.execute("SELECT * FROM vehicles WHERE vehicle_id=%s",(vehicle_id,));v=row(cur);cur.close();conn.close()
    return (jsonify(vehicle=v),200) if v else (jsonify(error="Vehicle not found"),404)

@bp.post("")
@require_auth(["admin"])
def create(): return mutate(None)

@bp.put("/<int:vehicle_id>")
@require_auth(["admin"])
def update(vehicle_id): return mutate(vehicle_id)

def mutate(vehicle_id):
    try: d=payload(request.get_json(silent=True) or {})
    except ValueError as e: return jsonify(error=str(e)),400
    conn=get_connection();cur=conn.cursor(dictionary=True)
    try:
        if vehicle_id:
            cur.execute("UPDATE vehicles SET "+", ".join(f"{k}=%s" for k in FIELDS)+" WHERE vehicle_id=%s",tuple(d.values())+(vehicle_id,))
            if not cur.rowcount: conn.rollback();return jsonify(error="Vehicle not found"),404
            vid=vehicle_id
        else:
            cur.execute("INSERT INTO vehicles ("+",".join(FIELDS)+") VALUES ("+",".join(["%s"]*len(FIELDS))+")",tuple(d.values()));vid=cur.lastrowid
        conn.commit();return jsonify(vehicle_id=vid),200 if vehicle_id else 201
    except Exception as e:
        conn.rollback()
        if getattr(e,"errno",None)==1062:return jsonify(error="Registration number already exists"),409
        raise
    finally:cur.close();conn.close()

@bp.delete("/<int:vehicle_id>")
@require_auth(["admin"])
def delete(vehicle_id):
    conn=get_connection();cur=conn.cursor();cur.execute("DELETE FROM vehicles WHERE vehicle_id=%s",(vehicle_id,));conn.commit();n=cur.rowcount;cur.close();conn.close()
    return ("",204) if n else (jsonify(error="Vehicle not found"),404)

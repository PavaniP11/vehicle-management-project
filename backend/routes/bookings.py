from datetime import date
from flask import Blueprint, request, jsonify, g
from database import get_connection, rows, row
from middleware.auth import require_auth

bp=Blueprint("bookings",__name__,url_prefix="/api/bookings")
@bp.post("")
@require_auth()
def create():
    d=request.get_json(silent=True) or {}
    try: vid=int(d.get("vehicle_id")); start=date.fromisoformat(d.get("pickup_date","")); end=date.fromisoformat(d.get("return_date","")); location=str(d.get("pickup_location","")).strip()
    except (ValueError,TypeError): return jsonify(error="Choose a vehicle and valid pickup and return dates"),400
    if start<date.today() or end<=start or not location:return jsonify(error="Return date must follow pickup date and dates must be today or later"),400
    conn=get_connection();cur=conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        cur.execute("SELECT rent_per_day,availability_status FROM vehicles WHERE vehicle_id=%s FOR UPDATE",(vid,));v=row(cur)
        if not v or v["availability_status"]!="available":conn.rollback();return jsonify(error="Vehicle is unavailable"),409
        cur.execute("SELECT booking_id FROM bookings WHERE vehicle_id=%s AND booking_status IN ('pending','confirmed') AND pickup_date < %s AND return_date > %s FOR UPDATE",(vid,end,start))
        if cur.fetchone():conn.rollback();return jsonify(error="Vehicle is already booked for those dates"),409
        days=(end-start).days; amount=days*float(v["rent_per_day"])
        cur.execute("INSERT INTO bookings (user_id,vehicle_id,pickup_date,return_date,pickup_location,total_days,total_amount,booking_status) VALUES (%s,%s,%s,%s,%s,%s,%s,'pending')",(g.user["user_id"],vid,start,end,location,days,amount))
        bid=cur.lastrowid;conn.commit();return jsonify(booking_id=bid,total_days=days,total_amount=amount,status="pending"),201
    except Exception:conn.rollback();raise
    finally:cur.close();conn.close()

@bp.get("/my")
@require_auth()
def mine():
    conn=get_connection();cur=conn.cursor(dictionary=True);cur.execute("SELECT b.*,v.vehicle_name,v.brand,v.image_url,p.payment_status FROM bookings b JOIN vehicles v ON v.vehicle_id=b.vehicle_id LEFT JOIN (SELECT booking_id,MAX(payment_status) payment_status FROM payments GROUP BY booking_id) p ON p.booking_id=b.booking_id WHERE b.user_id=%s ORDER BY b.created_at DESC",(g.user["user_id"],));r=rows(cur);cur.close();conn.close();return jsonify(bookings=r)

@bp.get("/<int:booking_id>")
@require_auth()
def detail(booking_id):
    conn=get_connection();cur=conn.cursor(dictionary=True);cur.execute("SELECT b.*,v.vehicle_name,v.brand FROM bookings b JOIN vehicles v ON v.vehicle_id=b.vehicle_id WHERE b.booking_id=%s AND (b.user_id=%s OR %s='admin')",(booking_id,g.user["user_id"],g.user["role"]));b=row(cur);cur.close();conn.close()
    return (jsonify(booking=b),200) if b else (jsonify(error="Booking not found"),404)

@bp.put("/<int:booking_id>/cancel")
@require_auth()
def cancel(booking_id):
    conn=get_connection();cur=conn.cursor();cur.execute("UPDATE bookings SET booking_status='cancelled' WHERE booking_id=%s AND user_id=%s AND booking_status IN ('pending','confirmed') AND pickup_date>CURDATE()",(booking_id,g.user["user_id"]));conn.commit();n=cur.rowcount;cur.close();conn.close()
    return jsonify(status="cancelled") if n else (jsonify(error="Booking cannot be cancelled"),409)

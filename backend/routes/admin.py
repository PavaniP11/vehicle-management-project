from flask import Blueprint, request, jsonify
from database import get_connection, rows
from middleware.auth import require_auth
bp=Blueprint("admin",__name__,url_prefix="/api/admin")
@bp.get("/dashboard")
@require_auth(["admin"])
def dashboard():
    c=get_connection();q=c.cursor(dictionary=True)
    q.execute("SELECT COUNT(*) total_customers FROM users WHERE role='customer'"); customers=q.fetchone()["total_customers"]
    q.execute("SELECT COUNT(*) total_vehicles, SUM(availability_status='available') available_vehicles, SUM(availability_status='rented') rented_vehicles FROM vehicles"); vehicles=q.fetchone()
    q.execute("SELECT COUNT(*) total_bookings, SUM(booking_status='pending') pending_bookings FROM bookings"); bookings=q.fetchone()
    q.execute("SELECT COALESCE(SUM(amount),0) revenue FROM payments WHERE payment_status='paid'"); revenue=q.fetchone()["revenue"]
    q.close();c.close();return jsonify(customers=customers,**vehicles,**bookings,revenue=float(revenue))
@bp.get("/users")
@require_auth(["admin"])
def users():
    c=get_connection();q=c.cursor(dictionary=True);q.execute("SELECT user_id,full_name,email,phone,role,created_at FROM users ORDER BY created_at DESC");r=rows(q);q.close();c.close();return jsonify(users=r)
@bp.get("/bookings")
@require_auth(["admin"])
def bookings():
    c=get_connection();q=c.cursor(dictionary=True);q.execute("SELECT b.*,u.full_name,u.email,v.vehicle_name,v.brand FROM bookings b JOIN users u ON u.user_id=b.user_id JOIN vehicles v ON v.vehicle_id=b.vehicle_id ORDER BY b.created_at DESC");r=rows(q);q.close();c.close();return jsonify(bookings=r)
@bp.get("/payments")
@require_auth(["admin"])
def payments():
    c=get_connection();q=c.cursor(dictionary=True);q.execute("SELECT p.*,b.user_id,u.full_name,b.vehicle_id,v.vehicle_name FROM payments p JOIN bookings b ON b.booking_id=p.booking_id JOIN users u ON u.user_id=b.user_id JOIN vehicles v ON v.vehicle_id=b.vehicle_id ORDER BY p.created_at DESC");r=rows(q);q.close();c.close();return jsonify(payments=r)
@bp.put("/bookings/<int:booking_id>/status")
@require_auth(["admin"])
def set_status(booking_id):
    status=(request.get_json(silent=True) or {}).get("status")
    if status not in ("confirmed","rejected","completed","cancelled"):return jsonify(error="Invalid booking status"),400
    c=get_connection();q=c.cursor();q.execute("UPDATE bookings SET booking_status=%s WHERE booking_id=%s AND booking_status IN ('pending','confirmed')",(status,booking_id));c.commit();n=q.rowcount;q.close();c.close()
    return (jsonify(status=status),200) if n else (jsonify(error="Booking not found or cannot be updated"),404)

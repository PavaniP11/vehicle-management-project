import uuid
from flask import Blueprint,request,jsonify,g
from database import get_connection,rows
from middleware.auth import require_auth
bp=Blueprint("payments",__name__,url_prefix="/api/payments")
@bp.post("")
@require_auth()
def pay():
    d=request.get_json(silent=True) or {}
    try: bid=int(d.get("booking_id"))
    except (ValueError,TypeError):return jsonify(error="booking_id is required"),400
    method=d.get("payment_method","simulated")
    if method not in ("simulated","cash","upi"):return jsonify(error="Unsupported payment method"),400
    c=get_connection();q=c.cursor(dictionary=True);q.execute("SELECT booking_id,total_amount FROM bookings WHERE booking_id=%s AND user_id=%s AND booking_status IN ('confirmed','completed')",(bid,g.user["user_id"]));b=q.fetchone()
    if not b:q.close();c.close();return jsonify(error="Eligible booking not found"),404
    q.execute("SELECT payment_id FROM payments WHERE booking_id=%s AND payment_status='paid' LIMIT 1",(bid,))
    if q.fetchone():q.close();c.close();return jsonify(error="This booking already has a recorded payment"),409
    reference="SIM-"+uuid.uuid4().hex[:12].upper();q.execute("INSERT INTO payments (booking_id,amount,payment_method,payment_status,transaction_reference,payment_date) VALUES (%s,%s,%s,'paid',%s,NOW())",(bid,b["total_amount"],method,reference));c.commit();pid=q.lastrowid;q.close();c.close();return jsonify(payment_id=pid,amount=float(b["total_amount"]),status="paid",transaction_reference=reference),201
@bp.get("/booking/<int:booking_id>")
@require_auth()
def for_booking(booking_id):
    c=get_connection();q=c.cursor(dictionary=True);q.execute("SELECT p.* FROM payments p JOIN bookings b ON b.booking_id=p.booking_id WHERE p.booking_id=%s AND (b.user_id=%s OR %s='admin') ORDER BY p.payment_date DESC",(booking_id,g.user["user_id"],g.user["role"]));r=rows(q);q.close();c.close();return jsonify(payments=r)

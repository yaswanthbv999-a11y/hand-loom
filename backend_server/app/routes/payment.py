from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from app import db
from app.models.payment import Payment, PAYEE_TYPES, PAYMENT_MODES, PAYMENT_STATUSES
from app.models.inventory import ProductionBatch

payment_bp = Blueprint("payment", __name__)

def core_only():
    if get_jwt().get("role") != "core_team_member":
        return jsonify({"success": False, "message": "Core team only"}), 403

@payment_bp.route("", methods=["POST"])
@jwt_required()
def create_payment():
    """
    Create a payment record
    ---
    tags: [Payments]
    summary: Record a payment to farmer or artisan
    description: "Story 3.5: Artisan & Farmer Payments — link payment to batch"
    security: [{BearerAuth: []}]
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [payee_id, payee_type, amount, mode]
          properties:
            payee_id: {type: string}
            payee_type: {type: string, enum: [farmer, artisan]}
            batch_id: {type: string}
            amount: {type: number, example: 5000.0}
            mode: {type: string, enum: [bank_transfer, upi, cash]}
            notes: {type: string}
    responses:
      201: {description: Payment recorded}
      400: {description: Validation error}
      403: {description: Core team only}
    """
    err = core_only()
    if err: return err
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "message": "JSON required"}), 400

    payee_id = data.get("payee_id", "").strip()
    payee_type = data.get("payee_type", "").strip()
    amount = data.get("amount")
    mode = data.get("mode", "").strip()

    if not all([payee_id, payee_type, amount is not None, mode]):
        return jsonify({"success": False, "message": "payee_id, payee_type, amount, mode required"}), 400
    if payee_type not in PAYEE_TYPES:
        return jsonify({"success": False, "message": f"payee_type must be one of {PAYEE_TYPES}"}), 400
    if mode not in PAYMENT_MODES:
        return jsonify({"success": False, "message": f"mode must be one of {PAYMENT_MODES}"}), 400
    if not isinstance(amount, (int, float)) or amount <= 0:
        return jsonify({"success": False, "message": "amount must be positive"}), 400

    batch_id = data.get("batch_id", "").strip() or None
    if batch_id and not db.session.get(ProductionBatch, batch_id):
        return jsonify({"success": False, "message": "Batch not found"}), 404

    p = Payment(payee_id=payee_id, payee_type=payee_type, batch_id=batch_id,
                recorded_by=get_jwt_identity(), amount=amount, mode=mode,
                notes=data.get("notes", "").strip() or None)
    db.session.add(p)
    db.session.commit()
    return jsonify({"success": True, "data": {"payment": p.to_dict()}}), 201


@payment_bp.route("", methods=["GET"])
@jwt_required()
def list_payments():
    """
    List payments
    ---
    tags: [Payments]
    security: [{BearerAuth: []}]
    parameters:
      - {in: query, name: payee_id, type: string}
      - {in: query, name: payee_type, type: string}
      - {in: query, name: batch_id, type: string}
      - {in: query, name: status, type: string}
    responses:
      200: {description: List of payments}
    """
    q = Payment.query
    for field in ["payee_id", "payee_type", "batch_id", "status"]:
        val = request.args.get(field)
        if val:
            q = q.filter(getattr(Payment, field) == val)
    payments = q.order_by(Payment.paid_at.desc()).all()
    return jsonify({"success": True, "data": {"payments": [p.to_dict() for p in payments], "count": len(payments)}}), 200


@payment_bp.route("/<pid>", methods=["GET"])
@jwt_required()
def get_payment(pid):
    """
    Get payment by ID
    ---
    tags: [Payments]
    security: [{BearerAuth: []}]
    parameters:
      - {in: path, name: pid, required: true, type: string}
    responses:
      200: {description: Payment}
      404: {description: Not found}
    """
    p = db.session.get(Payment, pid)
    if not p:
        return jsonify({"success": False, "message": "Payment not found"}), 404
    return jsonify({"success": True, "data": {"payment": p.to_dict()}}), 200


@payment_bp.route("/<pid>/status", methods=["PATCH"])
@jwt_required()
def update_status(pid):
    """
    Update payment status
    ---
    tags: [Payments]
    security: [{BearerAuth: []}]
    parameters:
      - {in: path, name: pid, required: true, type: string}
      - in: body
        name: body
        schema:
          type: object
          required: [status]
          properties:
            status: {type: string, enum: [pending, completed, failed]}
    responses:
      200: {description: Status updated}
      400: {description: Invalid status}
      403: {description: Core team only}
      404: {description: Not found}
    """
    err = core_only()
    if err: return err
    p = db.session.get(Payment, pid)
    if not p:
        return jsonify({"success": False, "message": "Payment not found"}), 404
    data = request.get_json(silent=True) or {}
    status = data.get("status", "").strip()
    if status not in PAYMENT_STATUSES:
        return jsonify({"success": False, "message": f"status must be one of {PAYMENT_STATUSES}"}), 400
    p.status = status
    db.session.commit()
    return jsonify({"success": True, "data": {"payment": p.to_dict()}}), 200


@payment_bp.route("/summary/<payee_type>/<payee_id>", methods=["GET"])
@jwt_required()
def payee_summary(payee_type, payee_id):
    """
    Payment summary for a payee
    ---
    tags: [Payments]
    description: "Total paid, pending, failed for a farmer or artisan"
    security: [{BearerAuth: []}]
    parameters:
      - {in: path, name: payee_type, required: true, type: string}
      - {in: path, name: payee_id, required: true, type: string}
    responses:
      200: {description: Summary}
      400: {description: Invalid payee_type}
    """
    if payee_type not in PAYEE_TYPES:
        return jsonify({"success": False, "message": f"payee_type must be one of {PAYEE_TYPES}"}), 400
    payments = Payment.query.filter_by(payee_id=payee_id, payee_type=payee_type).all()
    summary = {s: sum(p.amount for p in payments if p.status == s) for s in PAYMENT_STATUSES}
    summary["total_records"] = len(payments)
    return jsonify({"success": True, "data": {"payee_id": payee_id, "payee_type": payee_type, "summary": summary}}), 200

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from datetime import datetime
from app import db
from app.models.events import Workshop, Registration, WORKSHOP_TYPES

workshop_bp = Blueprint("workshop", __name__)

def core_only():
    if get_jwt().get("role") != "core_team_member":
        return jsonify({"success": False, "message": "Core team only"}), 403

def parse_dt(s):
    try: return datetime.fromisoformat(s)
    except: return None

@workshop_bp.route("", methods=["POST"])
@jwt_required()
def create_workshop():
    """
    Create workshop
    ---
    tags: [Workshops]
    summary: Create a spinning/weaving/dyeing workshop
    description: "Story 3.1: Workshop Registration"
    security: [{BearerAuth: []}]
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [title, workshop_type, capacity]
          properties:
            title: {type: string}
            workshop_type: {type: string, enum: [spinning, weaving, dyeing]}
            date: {type: string, example: "2026-09-01T10:00:00"}
            venue: {type: string}
            capacity: {type: integer, example: 20}
            fee: {type: number, example: 500.0}
            event_id: {type: string}
    responses:
      201: {description: Workshop created}
      400: {description: Validation error}
      403: {description: Core team only}
    """
    err = core_only()
    if err: return err
    data = request.get_json(silent=True)
    if not data: return jsonify({"success": False, "message": "JSON required"}), 400
    title = data.get("title","").strip()
    wtype = data.get("workshop_type","").strip()
    capacity = data.get("capacity")
    if not title or not wtype or capacity is None:
        return jsonify({"success": False, "message": "title, workshop_type, capacity required"}), 400
    if wtype not in WORKSHOP_TYPES:
        return jsonify({"success": False, "message": f"workshop_type must be one of {WORKSHOP_TYPES}"}), 400
    if not isinstance(capacity, int) or capacity <= 0:
        return jsonify({"success": False, "message": "capacity must be positive integer"}), 400
    w = Workshop(created_by=get_jwt_identity(), title=title, workshop_type=wtype,
                 capacity=capacity, fee=data.get("fee", 0.0),
                 venue=data.get("venue","").strip() or None,
                 date=parse_dt(data.get("date","")) if data.get("date") else None,
                 event_id=data.get("event_id","").strip() or None)
    db.session.add(w); db.session.commit()
    return jsonify({"success": True, "data": {"workshop": w.to_dict()}}), 201


@workshop_bp.route("", methods=["GET"])
@jwt_required()
def list_workshops():
    """
    List workshops
    ---
    tags: [Workshops]
    security: [{BearerAuth: []}]
    parameters:
      - {in: query, name: workshop_type, type: string}
    responses:
      200: {description: List of workshops}
    """
    q = Workshop.query
    if t := request.args.get("workshop_type"): q = q.filter_by(workshop_type=t)
    ws = q.order_by(Workshop.date.asc()).all()
    return jsonify({"success": True, "data": {"workshops": [w.to_dict() for w in ws], "count": len(ws)}}), 200


@workshop_bp.route("/<wid>", methods=["GET"])
@jwt_required()
def get_workshop(wid):
    """
    Get workshop by ID
    ---
    tags: [Workshops]
    security: [{BearerAuth: []}]
    parameters:
      - {in: path, name: wid, required: true, type: string}
    responses:
      200: {description: Workshop}
      404: {description: Not found}
    """
    w = db.session.get(Workshop, wid)
    if not w: return jsonify({"success": False, "message": "Workshop not found"}), 404
    regs = Registration.query.filter_by(workshop_id=wid).all()
    return jsonify({"success": True, "data": {"workshop": w.to_dict(), "registrations": [r.to_dict() for r in regs]}}), 200


@workshop_bp.route("/<wid>", methods=["PUT"])
@jwt_required()
def update_workshop(wid):
    """
    Update workshop
    ---
    tags: [Workshops]
    security: [{BearerAuth: []}]
    parameters:
      - {in: path, name: wid, required: true, type: string}
      - in: body
        name: body
        schema:
          type: object
          properties:
            title: {type: string}
            venue: {type: string}
            date: {type: string}
            fee: {type: number}
            capacity: {type: integer}
    responses:
      200: {description: Updated}
      403: {description: Core team only}
      404: {description: Not found}
    """
    err = core_only()
    if err: return err
    w = db.session.get(Workshop, wid)
    if not w: return jsonify({"success": False, "message": "Workshop not found"}), 404
    data = request.get_json(silent=True) or {}
    if "title" in data and data["title"].strip(): w.title = data["title"].strip()
    if "venue" in data: w.venue = data["venue"].strip() or None
    if "date" in data: w.date = parse_dt(data["date"])
    if "fee" in data: w.fee = data["fee"]
    if "capacity" in data:
        if not isinstance(data["capacity"], int) or data["capacity"] <= 0:
            return jsonify({"success": False, "message": "capacity must be positive integer"}), 400
        w.capacity = data["capacity"]
    db.session.commit()
    return jsonify({"success": True, "data": {"workshop": w.to_dict()}}), 200


@workshop_bp.route("/<wid>/register", methods=["POST"])
@jwt_required()
def register_for_workshop(wid):
    """
    Register for workshop
    ---
    tags: [Workshops]
    summary: Customer self-registers for a workshop
    description: "Story 3.1: Workshop Registration with auto confirmation"
    security: [{BearerAuth: []}]
    parameters:
      - {in: path, name: wid, required: true, type: string}
    responses:
      201: {description: Registered successfully}
      400: {description: Already registered or workshop full}
      404: {description: Workshop not found}
    """
    w = db.session.get(Workshop, wid)
    if not w: return jsonify({"success": False, "message": "Workshop not found"}), 404
    uid = get_jwt_identity()
    if Registration.query.filter_by(workshop_id=wid, customer_id=uid).first():
        return jsonify({"success": False, "message": "Already registered"}), 400
    if w.enrolled_count >= w.capacity:
        return jsonify({"success": False, "message": "Workshop is full"}), 400
    r = Registration(workshop_id=wid, customer_id=uid, confirmation_sent=True)
    w.enrolled_count += 1
    db.session.add(r); db.session.commit()
    return jsonify({"success": True, "message": "Registered successfully. Confirmation sent.", "data": {"registration": r.to_dict()}}), 201


@workshop_bp.route("/<wid>/registrations", methods=["GET"])
@jwt_required()
def list_registrations(wid):
    """
    List registrations for a workshop
    ---
    tags: [Workshops]
    security: [{BearerAuth: []}]
    parameters:
      - {in: path, name: wid, required: true, type: string}
    responses:
      200: {description: Registrations list}
      404: {description: Workshop not found}
    """
    w = db.session.get(Workshop, wid)
    if not w: return jsonify({"success": False, "message": "Workshop not found"}), 404
    regs = Registration.query.filter_by(workshop_id=wid).all()
    return jsonify({"success": True, "data": {"registrations": [r.to_dict() for r in regs], "count": len(regs)}}), 200


@workshop_bp.route("/registrations/<rid>/payment", methods=["PATCH"])
@jwt_required()
def update_reg_payment(rid):
    """
    Update registration payment status
    ---
    tags: [Workshops]
    security: [{BearerAuth: []}]
    parameters:
      - {in: path, name: rid, required: true, type: string}
      - in: body
        name: body
        schema:
          type: object
          required: [payment_status]
          properties:
            payment_status: {type: string, enum: [pending, paid, refunded]}
    responses:
      200: {description: Payment status updated}
      400: {description: Invalid status}
      403: {description: Core team only}
      404: {description: Registration not found}
    """
    err = core_only()
    if err: return err
    reg = db.session.get(Registration, rid)
    if not reg: return jsonify({"success": False, "message": "Registration not found"}), 404
    data = request.get_json(silent=True) or {}
    status = data.get("payment_status","").strip()
    if status not in ["pending","paid","refunded"]:
        return jsonify({"success": False, "message": "payment_status must be pending/paid/refunded"}), 400
    reg.payment_status = status
    db.session.commit()
    return jsonify({"success": True, "data": {"registration": reg.to_dict()}}), 200

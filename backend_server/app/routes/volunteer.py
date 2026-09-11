from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from datetime import datetime
from app import db
from app.models.volunteer import Availability, Shift, SHIFT_STATUSES
from app.models.events import Event

volunteer_bp = Blueprint("volunteer", __name__)

def core_only():
    if get_jwt().get("role") != "core_team_member":
        return jsonify({"success": False, "message": "Core team only"}), 403

# ── POST /volunteers/availability ────────────────────────────
@volunteer_bp.route("/availability", methods=["POST"])
@jwt_required()
def submit_availability():
    """
    Submit availability
    ---
    tags: [Volunteers]
    summary: Volunteer submits availability for an event
    description: "Story 2.1: Volunteer Availability Submission"
    security: [{BearerAuth: []}]
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [event_id]
          properties:
            event_id: {type: string}
            preferred_slots: {type: string, example: "morning,afternoon"}
    responses:
      201: {description: Availability submitted}
      400: {description: Already submitted}
      404: {description: Event not found}
    """
    data = request.get_json(silent=True)
    if not data: return jsonify({"success": False, "message": "JSON required"}), 400
    event_id = data.get("event_id","").strip()
    if not event_id: return jsonify({"success": False, "message": "event_id required"}), 400
    if not db.session.get(Event, event_id):
        return jsonify({"success": False, "message": "Event not found"}), 404
    uid = get_jwt_identity()
    if Availability.query.filter_by(volunteer_id=uid, event_id=event_id).first():
        return jsonify({"success": False, "message": "Availability already submitted for this event"}), 400
    a = Availability(volunteer_id=uid, event_id=event_id,
                     preferred_slots=data.get("preferred_slots","").strip() or None)
    db.session.add(a); db.session.commit()
    return jsonify({"success": True, "message": "Availability submitted", "data": {"availability": a.to_dict()}}), 201


# ── GET /volunteers/availability ─────────────────────────────
@volunteer_bp.route("/availability", methods=["GET"])
@jwt_required()
def list_availability():
    """
    List availabilities
    ---
    tags: [Volunteers]
    security: [{BearerAuth: []}]
    parameters:
      - {in: query, name: event_id, type: string}
      - {in: query, name: volunteer_id, type: string}
    responses:
      200: {description: List of availabilities}
    """
    q = Availability.query
    if e := request.args.get("event_id"): q = q.filter_by(event_id=e)
    if v := request.args.get("volunteer_id"): q = q.filter_by(volunteer_id=v)
    avails = q.all()
    return jsonify({"success": True, "data": {"availabilities": [a.to_dict() for a in avails], "count": len(avails)}}), 200


# ── POST /volunteers/shifts ───────────────────────────────────
@volunteer_bp.route("/shifts", methods=["POST"])
@jwt_required()
def assign_shift():
    """
    Assign shift to volunteer
    ---
    tags: [Volunteers]
    summary: Core team assigns a shift to a volunteer
    description: "Story 2.2: Volunteer Shift Dashboard"
    security: [{BearerAuth: []}]
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [volunteer_id, event_id, time_slot]
          properties:
            volunteer_id: {type: string}
            event_id: {type: string}
            availability_id: {type: string}
            time_slot: {type: string, example: "morning"}
    responses:
      201: {description: Shift assigned}
      400: {description: Already assigned}
      403: {description: Core team only}
      404: {description: Event not found}
    """
    err = core_only()
    if err: return err
    data = request.get_json(silent=True)
    if not data: return jsonify({"success": False, "message": "JSON required"}), 400
    vol_id = data.get("volunteer_id","").strip()
    event_id = data.get("event_id","").strip()
    time_slot = data.get("time_slot","").strip()
    if not all([vol_id, event_id, time_slot]):
        return jsonify({"success": False, "message": "volunteer_id, event_id, time_slot required"}), 400
    if not db.session.get(Event, event_id):
        return jsonify({"success": False, "message": "Event not found"}), 404
    if Shift.query.filter_by(volunteer_id=vol_id, event_id=event_id).first():
        return jsonify({"success": False, "message": "Shift already assigned for this volunteer+event"}), 400
    s = Shift(volunteer_id=vol_id, event_id=event_id, time_slot=time_slot,
              availability_id=data.get("availability_id","").strip() or None)
    db.session.add(s); db.session.commit()
    return jsonify({"success": True, "data": {"shift": s.to_dict()}}), 201


# ── GET /volunteers/shifts ────────────────────────────────────
@volunteer_bp.route("/shifts", methods=["GET"])
@jwt_required()
def list_shifts():
    """
    List shifts
    ---
    tags: [Volunteers]
    description: "Story 2.2: Volunteer Shift Dashboard"
    security: [{BearerAuth: []}]
    parameters:
      - {in: query, name: event_id, type: string}
      - {in: query, name: volunteer_id, type: string}
      - {in: query, name: status, type: string}
    responses:
      200: {description: List of shifts}
    """
    q = Shift.query
    if e := request.args.get("event_id"): q = q.filter_by(event_id=e)
    if v := request.args.get("volunteer_id"): q = q.filter_by(volunteer_id=v)
    if s := request.args.get("status"): q = q.filter_by(status=s)
    shifts = q.all()
    return jsonify({"success": True, "data": {"shifts": [s.to_dict() for s in shifts], "count": len(shifts)}}), 200


# ── PATCH /volunteers/shifts/<id> ────────────────────────────
@volunteer_bp.route("/shifts/<sid>", methods=["PATCH"])
@jwt_required()
def update_shift(sid):
    """
    Update shift status
    ---
    tags: [Volunteers]
    description: "Story 2.3: Confirm or cancel a shift"
    security: [{BearerAuth: []}]
    parameters:
      - {in: path, name: sid, required: true, type: string}
      - in: body
        name: body
        schema:
          type: object
          required: [status]
          properties:
            status: {type: string, enum: [pending, confirmed, cancelled]}
            time_slot: {type: string}
    responses:
      200: {description: Shift updated}
      400: {description: Invalid status}
      403: {description: Core team only}
      404: {description: Shift not found}
    """
    err = core_only()
    if err: return err
    s = db.session.get(Shift, sid)
    if not s: return jsonify({"success": False, "message": "Shift not found"}), 404
    data = request.get_json(silent=True) or {}
    if "status" in data:
        if data["status"] not in SHIFT_STATUSES:
            return jsonify({"success": False, "message": f"status must be one of {SHIFT_STATUSES}"}), 400
        s.status = data["status"]
        if data["status"] == "confirmed": s.confirmed_at = datetime.utcnow()
    if "time_slot" in data: s.time_slot = data["time_slot"].strip()
    db.session.commit()
    return jsonify({"success": True, "data": {"shift": s.to_dict()}}), 200


# ── GET /volunteers/dashboard/<event_id> ─────────────────────
@volunteer_bp.route("/dashboard/<event_id>", methods=["GET"])
@jwt_required()
def volunteer_dashboard(event_id):
    """
    Volunteer dashboard for an event
    ---
    tags: [Volunteers]
    summary: All volunteers, availability and shifts for an event
    description: "Story 2.2: View dashboard showing all volunteers for an upcoming exhibition"
    security: [{BearerAuth: []}]
    parameters:
      - {in: path, name: event_id, required: true, type: string}
    responses:
      200: {description: Dashboard data}
      404: {description: Event not found}
    """
    if not db.session.get(Event, event_id):
        return jsonify({"success": False, "message": "Event not found"}), 404
    avails = Availability.query.filter_by(event_id=event_id).all()
    shifts = Shift.query.filter_by(event_id=event_id).all()
    return jsonify({"success": True, "data": {
        "event_id": event_id,
        "availabilities": [a.to_dict() for a in avails],
        "shifts": [s.to_dict() for s in shifts],
        "total_available": len(avails),
        "confirmed_shifts": sum(1 for s in shifts if s.status == "confirmed"),
    }}), 200

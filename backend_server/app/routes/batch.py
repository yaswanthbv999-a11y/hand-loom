from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.inventory import ProductionBatch
from app import db

batch_bp = Blueprint("batch", __name__)

@batch_bp.route("", methods=["POST"])
@jwt_required()
def create_batch():
    data = request.get_json() or {}
    farmer_id = data.get("farmer_id")
    if not farmer_id:
        return jsonify({"success": False, "message": "farmer_id required"}), 400
    
    uid = get_jwt_identity()
    batch = ProductionBatch(farmer_id=farmer_id, recorded_by=uid)
    db.session.add(batch)
    db.session.commit()
    
    return jsonify({"success": True, "data": {"batch": batch.to_dict()}}), 201

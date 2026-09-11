from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from app.models.auth import User
from app import db

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")
    
    user = User.query.filter_by(email=email).first()
    if not user or user.password_hash != password:
        return jsonify({"success": False, "message": "Invalid credentials"}), 401
    
    token = create_access_token(identity=user.id, additional_claims={"role": user.role})
    return jsonify({
        "success": True,
        "data": {
            "access_token": token,
            "user": user.to_dict()
        }
    }), 200

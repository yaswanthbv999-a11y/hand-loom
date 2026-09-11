from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager

db = SQLAlchemy()
jwt = JWTManager()

def create_app(config=None):
    app = Flask(__name__)
    
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JWT_SECRET_KEY"] = "super-secret-key-for-jwt-authentication-loom"
    
    if config:
        app.config.update(config)
        
    db.init_app(app)
    jwt.init_app(app)
    
    from app.routes.workshop import workshop_bp
    from app.routes.volunteer import volunteer_bp
    from app.routes.payment import payment_bp
    from app.routes.auth import auth_bp
    from app.routes.batch import batch_bp
    
    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
    app.register_blueprint(batch_bp, url_prefix="/api/v1/batches")
    app.register_blueprint(workshop_bp, url_prefix="/api/v1/workshops")
    app.register_blueprint(volunteer_bp, url_prefix="/api/v1/volunteers")
    app.register_blueprint(payment_bp, url_prefix="/api/v1/payments")
    
    with app.app_context():
        db.create_all()
        # Seed default admin user if not exists
        from app.models.auth import User
        if not User.query.filter_by(email="admin@tulaindia.org").first():
            admin = User(
                id="admin-1",
                name="Admin User",
                email="admin@tulaindia.org",
                password_hash="admin123",
                role="core_team_member"
            )
            db.session.add(admin)
            db.session.commit()
            
    return app

from flask import Flask
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from pymongo import MongoClient
from config import Config
from flask_mail import Mail
from flask_cors import CORS

bcrypt = Bcrypt()
jwt = JWTManager()
mail = Mail()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    bcrypt.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)

    # ✅ FIX: Enable CORS with credentials and origin
    frontend_url = app.config.get('FRONTEND_URL', 'http://localhost:3000')
    CORS(app, 
         supports_credentials=True, 
         origins=[frontend_url, "https://scissorsproperties.com", "https://www.scissorsproperties.com"],
         allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

    # Database connection with error handling
    try:
        if app.config.get('MONGO_URI') is None:
            raise ValueError("MONGO_URI environment variable is not set")
        
        # Add SSL configuration to fix handshake issues
        client = MongoClient(
            app.config['MONGO_URI'],
            tls=True,
            tlsAllowInvalidCertificates=True,
            tlsAllowInvalidHostnames=True,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            socketTimeoutMS=20000
        )
        app.db = client.get_default_database()
        # Test the connection
        app.db.command('ping')
        print("✅ Database connected successfully")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        app.db = None

    from app.route_controller.auth_route import auth_bp
    from app.route_controller.admin_route import admin_bp
    from app.route_controller.partner_route import partner_bp
    from app.route_controller.service_route import service_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp,url_prefix='/admin')
    app.register_blueprint(partner_bp,url_prefix='/partner')
    app.register_blueprint(service_bp,url_prefix='/service')

    return app


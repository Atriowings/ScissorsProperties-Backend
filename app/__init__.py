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

    # ✅ FIX: Enable CORS with comprehensive configuration
    CORS(app, 
         supports_credentials=True, 
         origins=[
             "https://scissorsproperties.com", 
             "https://www.scissorsproperties.com",
             "http://localhost:3000",
             "http://127.0.0.1:3000"
         ],
         allow_headers=[
             "Content-Type", 
             "Authorization", 
             "X-Requested-With",
             "Accept",
             "Origin",
             "Access-Control-Request-Method",
             "Access-Control-Request-Headers"
         ],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
         expose_headers=["Content-Range", "X-Content-Range"],
         max_age=3600)

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

    # Add CORS preflight handler
    @app.before_request
    def handle_preflight():
        from flask import request, make_response
        if request.method == "OPTIONS":
            response = make_response()
            response.headers.add("Access-Control-Allow-Origin", "*")
            response.headers.add('Access-Control-Allow-Headers', "*")
            response.headers.add('Access-Control-Allow-Methods', "*")
            return response

    from app.route_controller.auth_route import auth_bp
    from app.route_controller.admin_route import admin_bp
    from app.route_controller.partner_route import partner_bp
    from app.route_controller.service_route import service_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp,url_prefix='/admin')
    app.register_blueprint(partner_bp,url_prefix='/partner')
    app.register_blueprint(service_bp,url_prefix='/service')

    return app


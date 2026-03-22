import os
import sys
import logging
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_talisman import Talisman
from .config import Config

# Initialize global loggers/extensions
logger = logging.getLogger("freelancer-admin")
db = SQLAlchemy()
migrate = Migrate()
cors = CORS()
talisman = Talisman()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app)
    # Configure security headers (relaxed for now to avoid breaking UI)
    talisman.init_app(app, content_security_policy=None, force_https=False)
    
    # ── Health Check ──────────────────────────────────────────────────
    @app.route("/ping")
    def ping():
        return jsonify({"status": "ok", "message": "Backend is alive!"})
    
    # ── Logging Configuration ──────────────────────────────────────────
    if not app.debug:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler("app.log")
            ]
        )
    
    # Initialize the database
    from . import database as db_setup
    with app.app_context():
        db_setup.init_db()
    
    # Register Blueprints
    from .routes.chat import chat_bp
    from .routes.api import api_bp
    
    app.register_blueprint(chat_bp)
    app.register_blueprint(api_bp)
    
    # Global Error Handler
    @app.errorhandler(Exception)
    def handle_exception(e):
        logger.error(f"Unhandled Exception: {str(e)}")
        code = 500
        if hasattr(e, 'code'):
            code = e.code
        return jsonify({
            "ok": False,
            "reply": "A server error occurred. Our team has been notified.",
            "error": str(e) if app.debug else "Internal Server Error"
        }), code

    return app

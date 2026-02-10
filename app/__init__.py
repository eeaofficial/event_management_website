"""
app/__init__.py
"""

from flask import Flask
# from flask_sqlalchemy import SQLAlchemy
# from flask_bcrypt import Bcrypt
# from flask_login import LoginManager
from flask_migrate import Migrate
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

from app.extensions import db, bcrypt, login_manager
from app.init_data import ensure_super_admin, create_passes
from app.error_handlers import register_error_handlers
from app.routes import bp
from app.verifier_routes import bp as verifier_bp
from app.organizer_routes import bp as organizer_bp
from app.admin_routes import bp as admin_bp
from app.spectator_routes import spectator_bp


load_dotenv()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("SQLALCHEMY_DATABASE_URI")
# db = SQLAlchemy(app)
migrate = Migrate(app, db) 

# bcrypt = Bcrypt(app)

# login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

app.config["UPLOAD_FOLDER"] = os.environ.get("UPLOAD_FOLDER")

upload_dir = Path(app.config['UPLOAD_FOLDER']).resolve()
upload_dir.mkdir(parents=True, exist_ok=True)

static_dir = Path(app.static_folder).resolve()
static_dir.mkdir(parents=True, exist_ok=True)

login_manager.init_app(app)
db.init_app(app)
bcrypt.init_app(app)

app.register_blueprint(bp, url_prefix='/')
app.register_blueprint(verifier_bp, url_prefix='/verifier')
app.register_blueprint(organizer_bp, url_prefix='/organizer')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(spectator_bp, url_preview='/spectator')

register_error_handlers(app)

with app.app_context():
    # db.create_all()
    ensure_super_admin()
    create_passes()
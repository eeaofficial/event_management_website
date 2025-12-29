"""
app/__init__.py
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

from app.extensions import db, bcrypt, login_manager
from app.routes import bp
from app.init_data import ensure_super_admin
from app.error_handlers import register_error_handlers

load_dotenv()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("SQLALCHEMY_DATABASE_URI")
app.config["UPLOAD_FOLDER"] = os.environ.get("UPLOAD_FOLDER")

upload_dir = Path(app.config['UPLOAD_FOLDER']).resolve()
upload_dir.mkdir(parents=True, exist_ok=True)

static_dir = Path(app.static_folder).resolve()
static_dir.mkdir(parents=True, exist_ok=True)

login_manager.init_app(app)
db.init_app(app)
bcrypt.init_app(app)

app.register_blueprint(bp, url_prefix='/')

register_error_handlers(app)

with app.app_context():
    db.create_all()
    ensure_super_admin()

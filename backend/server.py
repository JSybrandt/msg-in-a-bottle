from flask import Flask, jsonify, abort
from flask_cors import CORS
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from pathlib import Path

import database
import mail
import routes

APP_NAME = "msg-in-a-bottle"
API_NAME=f"{APP_NAME}-api"

def _get_run_args():
  fullchain_path=Path(
    f"/etc/letsencrypt/live/{API_NAME}.sybrandt.com/fullchain.pem")
  privkey_path=Path(
    f"/etc/letsencrypt/live/{API_NAME}.sybrandt.com/privkey.pem")
  if fullchain_path.is_file() and privkey_path.is_file():
    return dict(
      ssl_context=(str(fullchain_path), str(privkey_path)),
      port=8080,
      host="0.0.0.0")
  print("WARNING: Failed to get ssl cert. This only makes.")
  return {}


def create_app(**config_overwrites):
  # Create app with default configs
  app = Flask(APP_NAME)
  database.init_app(app, config_overwrites)
  mail.init_app(app, config_overwrites)
  cors = CORS(app)
  app.register_blueprint(routes.blueprint)
  app.app_context().push() # this does the binding
  return app


def run_app(app=None):
  if app is None:
    app = create_app()
  app.run(threaded=True, **_get_run_args())

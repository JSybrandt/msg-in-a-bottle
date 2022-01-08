from flask import Flask, jsonify, abort
from flask_cors import CORS
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from pathlib import Path
import os


# CONFIGURE APP
APP_NAME = "msg-in-a-bottle"
API_NAME=f"{APP_NAME}-api"
app = Flask(APP_NAME)
cors = CORS(app)

## DATABASE
DATABASE_PATH=Path(f"{APP_NAME}.sqlite.db")
DATABASE_URI=f"sqlite:///{DATABASE_PATH}"
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
db = SQLAlchemy(app)

## MAIL
MAIL_SENDER="msg.in.a.bottle.mgmt@gmail.com"
MAIL_CRED_PATH = Path(f"/etc/creds/{APP_NAME}-mail-pass")

app.config["MAIL_PORT"] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config["MAIL_DEFAULT_SENDER"] = ("Message In A Bottle", MAIL_SENDER)

def _configure_mailtrap():
  print("Configuring test mail to send to mailtrap")
  assert "MAILTRAP_USERNAME" in os.environ
  assert "MAILTRAP_PASSWORD" in os.environ
  app.config["MAIL_SERVER"] = "smtp.mailtrap.io"
  app.config["MAIL_USERNAME"] = os.environ["MAILTRAP_USERNAME"]
  app.config["MAIL_PASSWORD"] = os.environ["MAILTRAP_PASSWORD"]

def _configure_gmail():
  print("Configuring mail to send with gmail")
  assert MAIL_CRED_PATH.is_file(), f"Set MAIL_CRED_PATH at {MAIL_CRED_PATH}"
  app.config["MAIL_SERVER"] = "smtp.gmail.com"
  app.config["MAIL_USERNAME"] = MAIL_SENDER
  with open(MAIL_CRED_PATH) as cred_file:
    app.config["MAIL_PASSWORD"] = cred_file.read().strip()

if "MAILTRAP_USERNAME" in os.environ:
  _configure_mailtrap()
else:
  _configure_gmail()
mail = Mail(app)

################################################################################

def _get_args():
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

def send_mail(subject, body, recipients):
  msg = Message(subject, recipients=recipients)
  msg.body=body
  mail.send(msg)

def run():
  db.create_all()
  app.run(threaded=True, **_get_args())

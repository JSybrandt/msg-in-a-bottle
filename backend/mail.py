from flask_mail import Mail, Message
from pathlib import Path
import os

# The user of this module will need to init this.
mail = Mail()

MAIL_SENDER = "msg.in.a.bottle.mgmt@gmail.com"
MAIL_CRED_PATH = Path(f"/etc/creds/msg-in-a-bottle-mail-pass")


def _configure_mailtrap(app):
  print("Configuring test mail to send to mailtrap")
  assert "MAILTRAP_USERNAME" in os.environ
  assert "MAILTRAP_PASSWORD" in os.environ
  app.config["MAIL_SERVER"] = "smtp.mailtrap.io"
  app.config["MAIL_USERNAME"] = os.environ["MAILTRAP_USERNAME"]
  app.config["MAIL_PASSWORD"] = os.environ["MAILTRAP_PASSWORD"]


def _configure_gmail(app):
  print("Configuring mail to send with gmail")
  assert MAIL_CRED_PATH.is_file(), f"Set MAIL_CRED_PATH at {MAIL_CRED_PATH}"
  app.config["MAIL_SERVER"] = "smtp.gmail.com"
  app.config["MAIL_USERNAME"] = MAIL_SENDER
  with open(MAIL_CRED_PATH) as cred_file:
    app.config["MAIL_PASSWORD"] = cred_file.read().strip()


def init_app(app, config_overwrites):
  app.config["MAIL_PORT"] = 587
  app.config['MAIL_USE_TLS'] = True
  app.config['MAIL_USE_SSL'] = False
  app.config["MAIL_DEFAULT_SENDER"] = ("Message In A Bottle", MAIL_SENDER)
  if "MAILTRAP_USERNAME" in os.environ:
    _configure_mailtrap(app)
  else:
    _configure_gmail(app)
  app.config.update(config_overwrites)
  mail.init_app(app)


def send_mail(subject, body, recipients):
  msg = Message(subject, recipients=recipients)
  msg.body = body
  mail.send(msg)

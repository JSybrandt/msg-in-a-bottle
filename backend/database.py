from sqlalchemy.sql import func
import util
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy

# The user of this module will need to init this.
db = SQLAlchemy()

DATABASE_URI = f"sqlite:///msg-in-a-bottle.sqlite.db"


def init_app(app, config_overwrites):
  app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
  app.config.update(config_overwrites)
  db.init_app(app)


VALID_LOGIN_ATTEMPT_DELTA = timedelta(minutes=5)
TOKEN_VALID_DELTA = timedelta(days=10)


class User(db.Model):
  email = db.Column(db.String(120), primary_key=True)
  name = db.Column(db.String(120), nullable=False)


class PendingLoginRequest(db.Model):
  email = db.Column(db.String(120), db.ForeignKey(User.email), primary_key=True)
  secret_key = db.Column(db.String(10), nullable=False)
  timestamp = db.Column(db.DateTime, nullable=False)


class AccessToken(db.Model):
  email = db.Column(db.String(120), db.ForeignKey(User.email))
  token = db.Column(db.String(util.ACCESS_TOKEN_LENGTH), primary_key=True)
  timestamp = db.Column(db.DateTime, nullable=False)


# Login


def open_login_request(email):
  """Returns a secret key that the user can use to login."""
  print("prepare_login_attempt")
  secret_key = util.generate_secret_key()
  existing_query = db.session.query(PendingLoginRequest).filter(
      PendingLoginRequest.email == email)
  if existing_query.first() is None:
    db.session.add(
        PendingLoginRequest(
            email=email, secret_key=secret_key, timestamp=util.now()))
  else:
    existing_query.update(dict(secret_key=secret_key, timestamp=util.now()))
  db.session.commit()
  return secret_key


def close_login_request(email, secret_key):
  """Returns a token if the secret key is valid for the email."""
  attempt_query = db.session.query(PendingLoginRequest).filter(
      PendingLoginRequest.email == email,
      PendingLoginRequest.secret_key == secret_key.upper(),
      PendingLoginRequest.timestamp > util.now() - VALID_LOGIN_ATTEMPT_DELTA)
  if attempt_query.count() != 1:
    raise ValueError(f"Login attempt failed for email: {email}")
  attempt_query.delete()
  token = util.generate_access_token()
  db.session.add(AccessToken(email=email, token=token, timestamp=util.now()))
  db.session.commit()
  return token

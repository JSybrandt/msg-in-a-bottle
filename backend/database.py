from sqlalchemy.sql import func
import util
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy

# The user of this module will need to init this.
db = SQLAlchemy()

DATABASE_URI = f"sqlite:///msg-in-a-bottle.sqlite.db"


def init_app(app, config_overwrites):
  app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
  app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
  app.config.update(config_overwrites)
  db.init_app(app)


VALID_LOGIN_ATTEMPT_DELTA = timedelta(minutes=5)
TOKEN_VALID_DELTA = timedelta(days=10)


class User(db.Model):
  email = db.Column(db.String(120), primary_key=True)
  name = db.Column(db.String(120), nullable=False)


class PendingLoginRequest(db.Model):
  email = db.Column(db.String(120), db.ForeignKey(User.email), primary_key=True)
  secret_key = db.Column(db.String(util.SECRET_KEY_LENGTH), nullable=False)
  timestamp = db.Column(db.DateTime, nullable=False)


class AccessToken(db.Model):
  email = db.Column(db.String(120), db.ForeignKey(User.email))
  token = db.Column(db.String(util.ACCESS_TOKEN_LENGTH), primary_key=True)
  timestamp = db.Column(db.DateTime, nullable=False)

class MessageFragment(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  text = db.Column(db.String(200), nullable=False)

class Message(db.Model):
  id = db.Column(db.Integer, primary_key=True)

class MessageAndFragment(db.Model):
  message_id = db.Column(db.Integer, primary_key=True, foreign_key=Message.id)
  fragment_id = db.Column(db.Integer, primary_key=True, foreign_key=MessageFragment.id)
  fragment = db.relationship("MessageFragment")


# Login


def open_login_request(email):
  """Returns a secret key that the user can use to login."""
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
    raise ValueError("Invalid secret key")
  attempt_query.delete()
  token = util.generate_access_token()
  db.session.add(AccessToken(email=email, token=token, timestamp=util.now()))
  db.session.commit()
  return token

def new_message(text):
  message_id = util.new_id()
  fragment_id = util.new_id()
  db.session.add(Message(id=message_id))
  db.session.add(MessageFragment(id=fragment_id))
  db.session.add(MessageAndFragment(message_id=message_id, fragment_id=fragment_id))
  db.session.commit()
  return message_id

def append_message(old_message_id, text):
  new_message_id = util.new_id()
  new_fragment_id = util.new_id()
  fragment_ids = db.session.query(MessageAndFragment).filter(MessageAndFragment.message_id == old_message_id).all()
  fragment_ids.append(new_fragment_id)
  db.session.add(Message(id=new_message_id))
  db.session.add(MessageFragment(id=new_fragment_id))
  for frag_id in fragment_ids:
    db.session.add(MessageAndFragment(message_id=new_message_id, fragment_id=frag_id))
  db.session.commit()
  return new_message_id

def get_message(message_id):
  fragments = db.session.query(MessageAndFragment.fragment).filter(MessageAndFragment.message_id == message_id).all()
  return [f.text for f in fragments]




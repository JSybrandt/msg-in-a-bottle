from sqlalchemy.sql import func
import util
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy

# The user of this module will need to init this.
db = SQLAlchemy()


# A little syntactic sugar to make queries easier.
def query(*args, **kwargs):
  return db.session.query(*args, **kwargs)


def add(*args, **kwargs):
  return db.session.add(*args, **kwargs)


def commit(*args, **kwargs):
  return db.session.commit(*args, **kwargs)


DATABASE_URI = f"sqlite:///msg-in-a-bottle.sqlite.db"


def init_app(app, config_overwrites):
  app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
  app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
  app.config.update(config_overwrites)
  db.init_app(app)


VALID_LOGIN_ATTEMPT_DELTA = timedelta(minutes=5)
VALID_TOKEN_DELTA = timedelta(days=10)


class User(db.Model):
  email = db.Column(db.String(120), primary_key=True)


class PendingLoginRequest(db.Model):
  email = db.Column(db.String(120), db.ForeignKey(User.email), primary_key=True)
  secret_key = db.Column(db.String(util.SECRET_KEY_LENGTH), nullable=False)
  timestamp = db.Column(db.DateTime, nullable=False)


class AccessToken(db.Model):
  email = db.Column(db.String(120), db.ForeignKey(User.email))
  token = db.Column(db.String(util.ACCESS_TOKEN_LENGTH), primary_key=True)
  timestamp = db.Column(db.DateTime, nullable=False)
  user = db.relationship(User, lazy=True)


# Helps us define a many-to-many relationship between messages and fragments.
message_to_fragment_table = db.Table(
    "message_to_fragment",
    db.Column(
        "message_id", db.Integer, db.ForeignKey("message.id"),
        primary_key=True),
    db.Column(
        "fragment_id",
        db.Integer,
        db.ForeignKey("message_fragment.id"),
        primary_key=True))


class MessageFragment(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  text = db.Column(db.String(200), nullable=False)


class Message(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  fragments = db.relationship(
      MessageFragment, secondary=message_to_fragment_table, lazy=True)


# Login


def open_login_request(email):
  """Returns a secret key that the user can use to login."""
  secret_key = util.generate_secret_key()
  existing_query = query(PendingLoginRequest).filter(
      PendingLoginRequest.email == email)
  if existing_query.first() is None:
    db.session.add(
        PendingLoginRequest(
            email=email, secret_key=secret_key, timestamp=util.now()))
  else:
    existing_query.update(dict(secret_key=secret_key, timestamp=util.now()))
  commit()
  return secret_key


def close_login_request(email, secret_key):
  """Returns a token if the secret key is valid for the email."""
  attempt_query = query(PendingLoginRequest).filter(
      PendingLoginRequest.email == email,
      PendingLoginRequest.secret_key == secret_key.upper(),
      PendingLoginRequest.timestamp > util.now() - VALID_LOGIN_ATTEMPT_DELTA)
  if attempt_query.count() != 1:
    raise ValueError("Invalid secret key")
  if query(User).filter(User.email == email).count() == 0:
    add(User(email=email))
  token = util.generate_access_token()
  add(AccessToken(email=email, token=token, timestamp=util.now()))
  attempt_query.delete()
  commit()
  return token


def validate_token(token):
  """Raises an exception if the api token is invalid."""
  if query(AccessToken).filter(
      AccessToken.token == token,
      AccessToken.timestamp > util.now() - VALID_TOKEN_DELTA).count() != 1:
    raise ValueError(f"Invalid API token: {token}")
  return True


def new_message(token, text):
  """Returns a message id associated with the new message."""
  validate_token(token)
  message_id = util.new_id()
  add(
      Message(
          id=message_id,
          fragments=[MessageFragment(id=util.new_id(), text=text)]))
  commit()
  return message_id


def append_fragment(token, old_message_id, text):
  """Returns a message id for a new message that has the fragment appended."""
  validate_token(token)
  new_message_id = util.new_id()
  old_message = query(Message).filter(Message.id == old_message_id).first()
  if old_message is None:
    raise ValueError(f"No message with id: {old_message_id}")
  new_fragments = old_message.fragments.copy()
  new_fragments.append(MessageFragment(id=util.new_id(), text=text))
  add(Message(id=new_message_id, fragments=new_fragments))
  commit()
  return new_message_id


def get_message(token, message_id):
  validate_token(token)
  msg = query(Message).filter(Message.id == message_id).first()
  if msg is None:
    raise ValueError(f"No message with id: {message_id}")
  return [f.text for f in msg.fragments]

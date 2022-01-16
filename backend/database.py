from sqlalchemy.sql import func
import util
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
import random

# The user of this module will need to init this.
db = SQLAlchemy()


# A little syntactic sugar to make queries easier.
def query(*args, **kwargs):
  return db.session.query(*args, **kwargs)


def add(*args, **kwargs):
  return db.session.add(*args, **kwargs)


def commit(*args, **kwargs):
  return db.session.commit(*args, **kwargs)


def execute(*args, **kwargs):
  return db.session.execute(*args, **kwargs)


def refresh(*args, **kwargs):
  return db.session.refresh(*args, **kwargs)


DATABASE_URI = f"sqlite:///msg-in-a-bottle.sqlite.db"


def init_app(app, config_overwrites):
  app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
  app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
  app.config.update(config_overwrites)
  db.init_app(app)


VALID_LOGIN_ATTEMPT_DELTA = timedelta(minutes=5)
VALID_TOKEN_DELTA = timedelta(days=10)
NEW_MESSAGE_MIN_DELTA = timedelta(days=1)

EMAIL_MAX_LENGTH = 120

# Defines a many-to-many relationship between messages and fragments.
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


class User(db.Model):
  email = db.Column(db.String(EMAIL_MAX_LENGTH), primary_key=True)
  coordinate_x = db.Column(db.Float, nullable=False, default=random.random)
  coordinate_y = db.Column(db.Float, nullable=False, default=random.random)
  creation_timestamp = db.Column(db.DateTime, nullable=False, default=util.now)
  last_msg_received_timestamp = db.Column(
      db.DateTime, nullable=True, default=util.now)


class PendingLoginRequest(db.Model):
  email = db.Column(
      db.String(EMAIL_MAX_LENGTH), db.ForeignKey(User.email), primary_key=True)
  secret_key = db.Column(db.String(util.SECRET_KEY_LENGTH), nullable=False)
  timestamp = db.Column(
      db.DateTime, nullable=False, default=util.now, onupdate=util.now)


class AccessToken(db.Model):
  email = db.Column(db.String(EMAIL_MAX_LENGTH), db.ForeignKey(User.email))
  token = db.Column(db.String(util.ACCESS_TOKEN_LENGTH), primary_key=True)
  timestamp = db.Column(db.DateTime, nullable=False, default=util.now)
  user = db.relationship(User, lazy=True)


class MessageFragment(db.Model):
  id = db.Column(db.Integer, primary_key=True, default=util.new_id)
  text = db.Column(db.String(500), nullable=False)
  author_email = db.Column(
      db.String(EMAIL_MAX_LENGTH), db.ForeignKey(User.email), nullable=False)
  author = db.relationship(User, lazy=True)
  timestamp = db.Column(db.DateTime, nullable=False, default=util.now)


class Message(db.Model):
  id = db.Column(db.Integer, primary_key=True, default=util.new_id)
  fragments = db.relationship(
      MessageFragment, secondary=message_to_fragment_table, lazy=True)
  may_append_email = db.Column(
      db.String(EMAIL_MAX_LENGTH), db.ForeignKey(User.email), nullable=True)
  author_email = db.Column(
      db.String(EMAIL_MAX_LENGTH), db.ForeignKey(User.email), nullable=False)
  # Fresh messages are still looking for an may_append_user.
  fresh = db.Column(db.Boolean, nullable=False, default=True)
  may_append_user = db.relationship(
      User,
      foreign_keys=may_append_email,
      lazy=True,
      backref=db.backref("may_append_messages", lazy=True))
  author = db.relationship(
      User,
      foreign_keys=author_email,
      lazy=True,
      backref=db.backref("authored_messages", lazy=True))
  timestamp = db.Column(db.DateTime, nullable=False, default=util.now)


def open_login_request(email):
  """Returns a secret key that the user can use to login."""
  secret_key = util.generate_secret_key()
  existing_query = query(PendingLoginRequest).filter(
      PendingLoginRequest.email == email)
  if existing_query.first() is None:
    db.session.add(PendingLoginRequest(email=email, secret_key=secret_key))
  else:
    existing_query.update(dict(secret_key=secret_key))
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
  add(AccessToken(email=email, token=token))
  attempt_query.delete()
  commit()
  return token


def get_user_from_token(token):
  """Raises an exception if the api token is invalid. Returns user."""
  access_token = query(AccessToken).filter(
      AccessToken.token == token,
      AccessToken.timestamp > util.now() - VALID_TOKEN_DELTA).first()
  if access_token is None:
    raise ValueError(f"Invalid API token: {token}")
  return access_token.user


def new_message(user, text):
  """Adds a new message to the database. Returns msg."""
  msg = Message(
      fragments=[MessageFragment(text=text, author=user)], author=user)
  add(msg)
  commit()
  return msg


def append_fragment(user, old_message, text):
  """Adds new message with a new fragment appended. Returns new msg."""
  if old_message.may_append_user != user:
    raise ValueError(
        f"User {user.email} is not the may_append_user of message: {old_message.id}"
    )
  if not old_message.fresh:
    raise ValueError(f"Message {old_message.id} is not fresh.")
  new_fragments = old_message.fragments.copy()
  new_fragments.append(MessageFragment(text=text, author=user))
  msg = Message(fragments=new_fragments, author=user)
  # This old message may no longer be appended to.
  old_message.may_append_user = None
  add(msg)
  commit()
  return msg


def user_may_receive_msg(user):
  """Returns true if the user hasn't received a msg recently."""
  if user.last_msg_received_timestamp is None:
    return True
  return user.last_msg_received_timestamp < util.now() - NEW_MESSAGE_MIN_DELTA


def find_closest_fresh_msg(user):
  """Finds a new message for the user that isn't yet owned."""
  return query(Message).filter(
      Message.may_append_email == None, Message.author_email != user.email,
      Message.fresh).join(User, Message.author).order_by(
          func.abs(User.coordinate_x - user.coordinate_x) +
          func.abs(User.coordinate_y - user.coordinate_y)).first()


def assign_fresh_message(user, message):
  if not message.fresh:
    raise ValueError(f"Message {message.id} isn't fresh.")
  message.may_append_user = user
  message.fresh = False
  user.last_msg_received_timestamp = util.now()
  commit()


def get_message(user, message_id):
  """Return a message if the user has permissions to view it."""
  message = query(Message).filter(Message.id == message_id).first()
  if message is None:
    raise ValueError(f"No message with id: {message_id}")
  if user not in {message.author, message.may_append_user}:
    raise ValueError(
        f"User {user.email} does not have permission to view message {message_id}"
    )
  return message

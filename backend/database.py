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


def execute(*args, **kwargs):
  return db.session.execute(*args, **kwargs)


DATABASE_URI = f"sqlite:///msg-in-a-bottle.sqlite.db"


def init_app(app, config_overwrites):
  app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
  app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
  app.config.update(config_overwrites)
  db.init_app(app)


VALID_LOGIN_ATTEMPT_DELTA = timedelta(minutes=5)
VALID_TOKEN_DELTA = timedelta(days=10)

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

# Defines a many-to-many relationship between readers and .messages.
reader_to_message_table = db.Table(
    "reader_to_message",
    db.Column(
        "user_email",
        db.String(EMAIL_MAX_LENGTH),
        db.ForeignKey("user.email"),
        primary_key=True),
    db.Column(
        "message_id", db.Integer, db.ForeignKey("message.id"),
        primary_key=True))


class User(db.Model):
  email = db.Column(db.String(EMAIL_MAX_LENGTH), primary_key=True)
  readable_messages = db.relationship(
      "Message", secondary=reader_to_message_table, lazy=True)
  # writeable_messages: provided by Message.writer_email backref.


class PendingLoginRequest(db.Model):
  email = db.Column(
      db.String(EMAIL_MAX_LENGTH), db.ForeignKey(User.email), primary_key=True)
  secret_key = db.Column(db.String(util.SECRET_KEY_LENGTH), nullable=False)
  timestamp = db.Column(db.DateTime, nullable=False)


class AccessToken(db.Model):
  email = db.Column(db.String(EMAIL_MAX_LENGTH), db.ForeignKey(User.email))
  token = db.Column(db.String(util.ACCESS_TOKEN_LENGTH), primary_key=True)
  timestamp = db.Column(db.DateTime, nullable=False)
  user = db.relationship(User, lazy=True)


class MessageFragment(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  text = db.Column(db.String(500), nullable=False)
  author_email = db.Column(
      db.String(EMAIL_MAX_LENGTH), db.ForeignKey(User.email), nullable=False)
  author = db.relationship(User, lazy=True)


class Message(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  fragments = db.relationship(
      MessageFragment, secondary=message_to_fragment_table, lazy=True)
  # The person who's allowed to append to this message.
  writer_email = db.Column(
      db.String(EMAIL_MAX_LENGTH), db.ForeignKey(User.email), nullable=True)
  writer = db.relationship(
      User, lazy=True, backref=db.backref("writeable_messages", lazy=True))
  readers = db.relationship(User, secondary=reader_to_message_table, lazy=True)


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
  """Raises an exception if the api token is invalid. Returns user."""
  access_token = query(AccessToken).filter(
      AccessToken.token == token,
      AccessToken.timestamp > util.now() - VALID_TOKEN_DELTA).first()
  if access_token is None:
    raise ValueError(f"Invalid API token: {token}")
  return access_token.user


def new_message(token, text):
  """Returns a message id associated with the new message."""
  user = validate_token(token)
  message_id = util.new_id()
  add(
      Message(
          id=message_id,
          fragments=[
              MessageFragment(
                  id=util.new_id(), text=text, author_email=user.email)
          ],
          readers=[user]))
  commit()
  return message_id


def append_fragment(token, old_message_id, text):
  """Returns a message id for a new message that has the fragment appended."""
  user = validate_token(token)
  new_message_id = util.new_id()
  old_message = query(Message).filter(Message.id == old_message_id).first()
  if old_message is None:
    raise ValueError(f"No message with id: {old_message_id}")
  new_fragments = old_message.fragments.copy()
  new_fragments.append(
      MessageFragment(id=util.new_id(), text=text, author_email=user.email))
  add(Message(id=new_message_id, fragments=new_fragments, readers=[user]))
  commit()
  return new_message_id


def get_message(token, message_id):
  user = validate_token(token)
  msg = query(Message).filter(Message.id == message_id).first()
  if msg is None:
    raise ValueError(f"No message with id: {message_id}")
  if user.email not in set(r.email for r in msg.readers):
    raise ValueError(f"User {user.email} doesn't have permission to view "
                     f"message: {message_id}")
  return [f.text for f in msg.fragments]


def set_message_writer(message_id, email):
  """Updated message to have the specified owner.

  Not intended for users to trigger.
  """
  msg = query(Message).filter(Message.id == message_id).first()
  if msg is None:
    raise ValueError(f"No message with id: {message_id}")
  user = query(User).filter(User.email == email).first()
  if user is None:
    raise ValueError(f"No user with email: {email}")
  msg.writer = user
  commit()

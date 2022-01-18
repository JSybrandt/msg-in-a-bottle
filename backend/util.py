import string
import random
import datetime
import time
import re

SECRET_KEY_LENGTH = 6
SECRET_KEY_CHARS = string.ascii_uppercase + string.digits

ACCESS_TOKEN_LENGTH = 20
ACCESS_TOKEN_CHARS = string.ascii_uppercase + string.digits + string.ascii_lowercase


def generate_secret_key():
  return "".join(
      random.choice(SECRET_KEY_CHARS) for _ in range(SECRET_KEY_LENGTH))


def generate_access_token():
  return "".join(
      random.choice(ACCESS_TOKEN_CHARS) for _ in range(ACCESS_TOKEN_LENGTH))


def now():
  return datetime.datetime.utcnow()


def new_id():
  return time.time_ns()


_EMAIL_REGEX = re.compile(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)")

def is_valid_email(email):
  return _EMAIL_REGEX.fullmatch(email)


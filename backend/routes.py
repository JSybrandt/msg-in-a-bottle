from flask import request, jsonify, Blueprint
import util
import database
import mail

blueprint = Blueprint("main_blueprint", __name__)


def validate_json_data():
  if not request.is_json:
    raise ValueError("Expected request to be json encoded.")
  return request.get_json()


def validate_field(json_data, field_name):
  if field_name not in json_data:
    raise ValueError(f"Expected '{field_name}' value.")
  return json_data[field_name]


@blueprint.errorhandler(ValueError)
def value_error(e):
  return jsonify(error=str(e)), 400


@blueprint.errorhandler(AssertionError)
def value_error(e):
  return jsonify(error=str(e)), 500


@blueprint.route("/login", methods=["POST"])
def login():
  data = validate_json_data()
  email = validate_field(data, "email")
  secret_key = data.get("secret_key")
  if secret_key is None:
    new_key = database.open_login_request(email)
    mail.send_mail(
        "Message in a Bottle: Secret Key",
        f"Your secret key is: {new_key}.\nIt is valid for 10 minutes.", [email])
    return jsonify(status="new-login")
  else:
    token = database.close_login_request(email, secret_key)
    return jsonify(status="login-success", token=token)


@blueprint.route("/get-message", methods=["GET"])
def get_message():
  data = validate_json_data()
  token = validate_field(data, "token")
  message_id = validate_field(data, "message_id")
  user = database.get_user_from_token(token)
  message = database.get_message(user, message_id)
  fragments = [
      dict(text=f.text, author_name=f.author.name) for f in message.fragments
  ]
  return jsonify(message=fragments)


@blueprint.route("/send-message", methods=["POST"])
def send_message():
  data = validate_json_data()
  token = validate_field(data, "token")
  text = validate_field(data, "text")
  message_id = data.get("message_id")
  user = database.get_user_from_token(token)
  if message_id is not None:
    old_message = database.get_message(user, message_id)
    new_message = database.append_fragment(user, old_message, text)
    return jsonify(message_id=new_message.id)
  else:
    new_message = database.new_message(user, text)
    return jsonify(message_id=new_message.id)


@blueprint.route("/", methods=["GET"])
def overview():
  data = validate_json_data()
  token = validate_field(data, "token")
  user = database.get_user_from_token(token)
  if database.allowed_to_recieve_msg(user):
    fresh_msg = database.find_closest_fresh_msg(user)
    if fresh_msg is not None:
      database.assign_fresh_message(user, fresh_msg)
      database.refresh(user)
  authored_message_ids = [m.id for m in user.authored_messages]
  may_append_message_ids = [m.id for m in user.may_append_messages]
  return jsonify(
      authored_message_ids=authored_message_ids,
      may_append_message_ids=may_append_message_ids,
      user_name=user.name)


@blueprint.route("/rename", methods=["POST"])
def rename():
  data = validate_json_data()
  token = validate_field(data, "token")
  name = validate_field(data, "name")
  user = database.get_user_from_token(token)
  database.rename(user, name)
  return jsonify(dict(status="ok"))


@blueprint.route("/delete-message", methods=["POST"])
def delete_message():
  data = validate_json_data()
  token = validate_field(data, "token")
  message_id = validate_field(data, "message_id")
  user = database.get_user_from_token(token)
  message = database.get_message(user, message_id)
  database.delete_message(user, message)
  return jsonify(dict(status="ok"))

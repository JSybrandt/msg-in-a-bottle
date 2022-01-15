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
    mail.send_mail("Msg in a Bottle: Temporary Password",
                   f"Your temporary password is: {new_key}", [email])
    return jsonify(status="new-login")
  else:
    token = database.close_login_request(email, secret_key)
    return jsonify(status="login-success", token=token)


@blueprint.route("/get-message", methods=["GET"])
def message():
  data = validate_json_data()
  token = validate_field(data, "token")
  message_id = validate_field(data, "message_id")
  user = database.get_user_from_token(token)
  message = database.get_message(user, message_id)
  return jsonify(message=[f.text for f in message.fragments])

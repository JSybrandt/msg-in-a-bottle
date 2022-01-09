from flask import request, jsonify, Blueprint
import util
import database
import mail

blueprint = Blueprint("main_blueprint", __name__)


@blueprint.errorhandler(ValueError)
def value_error(e):
  return jsonify(error=str(e)), 400


@blueprint.errorhandler(AssertionError)
def value_error(e):
  return jsonify(error=str(e)), 500


@blueprint.route("/login", methods=["POST"])
def login():
  if not request.is_json:
    raise ValueError("/login expected json-encoded post.")
  data = request.get_json()
  email = data.get("email")
  if email is None:
    raise ValueError("/login expected 'email' parameter.")
  secret_key = data.get("secret_key")
  if secret_key is None:
    new_key = database.open_login_request(email)
    mail.send_mail("Msg in a Bottle: Temporary Password",
                   f"Your temporary password is: {new_key}", [email])
    return jsonify(status="new-login")
  else:
    token = database.close_login_request(email, secret_key)
    return jsonify(status="login-success", token=token)

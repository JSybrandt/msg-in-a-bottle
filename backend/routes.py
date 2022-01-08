from flask import request, jsonify
import util
import database
import server

@server.app.errorhandler(ValueError)
def value_error(e):
  return jsonify(error=str(e)), 400

@server.app.errorhandler(AssertionError)
def value_error(e):
  return jsonify(error=str(e)), 500

@server.app.route("/login", methods=["POST"])
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
    server.send_mail(
      "Msg in a Bottle: Temporary Password",
      f"Your temporary password is: {new_key}",
      [email])
    return jsonify(status="new-login")
  else:
    token=database.close_login_request(email, secret_key)
    return jsonify(status="login-success", token=token)

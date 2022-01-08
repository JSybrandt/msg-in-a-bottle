from server import app, send_mail
from flask import request, jsonify

@app.errorhandler(ValueError)
def value_error(e):
  return jsonify(error=str(e)), 400

@app.errorhandler(AssertionError)
def value_error(e):
  return jsonify(error=str(e)), 500

@app.route("/login", methods=["POST"])
def login():
  send_mail("test subject", "test_body", ["nalta45@gmail.com"])
  if not request.is_json:
    raise ValueError("/login expected json-encoded post.")
  data = request.get_json()
  if "email" not in data:
    raise ValueError("/login expected 'email' parameter.")
  content = validate_content(request_json["content"])
  response_content = database.throw_in_the_void(content)
  return jsonify(content=response_content)

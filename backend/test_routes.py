import routes
import server_test_util
import database
import util


class RoutesTest(server_test_util.ServerTestCase):

  def test_login_empty(self):
    response = self.client.post("/login")
    self.assertEqual(response.status_code, 400)
    self.assertTrue(response.is_json)
    self.assertEqual(response.json,
                     dict(error="Expected request to be json encoded."))

  def test_login_json_empty(self):
    response = self.client.post("/login", json={})
    self.assertEqual(response.status_code, 400)
    self.assertTrue(response.is_json)
    self.assertEqual(response.json, dict(error="Expected 'email' value."))

  def test_login_w_email_no_key(self):
    email = "test@gmail.com"
    response = self.client.post("/login", json={"email": email})
    self.assertEqual(response.status_code, 200)
    self.assertTrue(response.is_json)
    self.assertEqual(response.json, dict(status="new-login"))
    self.assertEqual(
        database.db.session.query(database.PendingLoginRequest).count(), 1)
    # Check mailtrap, we should have spammed an email.

  def test_login_w_email_good_secret_key(self):
    email = "test@gmail.com"
    secret_key = "ABC123"
    database.add(
        database.PendingLoginRequest(
            email=email, secret_key=secret_key, timestamp=util.now()))
    response = self.client.post(
        "/login", json=dict(email=email, secret_key=secret_key))
    self.assertTrue(response.is_json)
    self.assertEqual(response.status_code, 200)
    self.assertIn("status", response.json)
    self.assertEqual(response.json["status"], "login-success")
    self.assertIn("token", response.json)
    self.assertEqual(
        database.db.session.query(database.PendingLoginRequest).count(), 0)
    self.assertEqual(
        database.db.session.query(database.AccessToken).filter(
            database.AccessToken.token == response.json["token"]).count(), 1)

  def test_login_w_email_bad_secret_key(self):
    email = "test@gmail.com"
    database.add(
        database.PendingLoginRequest(
            email=email, secret_key="ABC123", timestamp=util.now()))
    response = self.client.post(
        "/login", json=dict(email=email, secret_key="garbge"))
    self.assertTrue(response.is_json)
    self.assertEqual(response.status_code, 400)
    self.assertEqual(response.json, dict(error="Invalid secret key"))

  def test_login_w_email_timeout(self):
    email = "test@gmail.com"
    secret_key = "ABC123"
    long_ago = util.now() - 2 * database.VALID_LOGIN_ATTEMPT_DELTA
    database.add(
        database.PendingLoginRequest(
            email=email, secret_key=secret_key, timestamp=long_ago))
    response = self.client.post(
        "/login", json=dict(email=email, secret_key=secret_key))
    self.assertTrue(response.is_json)
    self.assertEqual(response.status_code, 400)
    self.assertEqual(response.json, dict(error="Invalid secret key"))

  def test_get_message(self):
    user, token = self.create_test_user("author@gmail.com")
    message = database.new_message(user, "test message")
    response = self.client.get(
        "/get-message", json=dict(token=token, message_id=message.id))
    self.assertTrue(response.is_json)
    self.assertEqual(response.json, dict(message=["test message"]))

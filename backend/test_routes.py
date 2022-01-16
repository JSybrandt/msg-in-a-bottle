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

  def test_get_message_bad_user(self):
    user, _ = self.create_test_user("author@gmail.com")
    bad_user, bad_token = self.create_test_user("bad_user@gmail.com")
    message = database.new_message(user, "test message")
    response = self.client.get(
        "/get-message", json=dict(token=bad_token, message_id=message.id))
    self.assertTrue(response.is_json)
    self.assertEqual(response.status_code, 400)
    self.assertEqual(
        response.json,
        dict(error="User bad_user@gmail.com does not have permission to view "
             f"message {message.id}"))

  def test_get_message_bad_id(self):
    user, token = self.create_test_user("author@gmail.com")
    response = self.client.get(
        "/get-message", json=dict(token=token, message_id=123))
    self.assertTrue(response.is_json)
    self.assertEqual(response.status_code, 400)
    self.assertEqual(response.json, dict(error="No message with id: 123"))

  def test_send_new_message(self):
    user, token = self.create_test_user("author@gmail.com")
    response = self.client.post(
        "/send-message", json=dict(token=token, text="test message"))
    messages = database.query(database.Message).all()
    self.assertTrue(response.is_json)
    self.assertEqual(len(messages), 1)
    self.assertEqual(messages[0].author, user)
    self.assertEqual([f.text for f in messages[0].fragments], ["test message"])
    self.assertTrue(messages[0].may_append_user is None)
    self.assertTrue("message_id" in response.json)
    self.assertEqual(messages[0].id, response.json["message_id"])
    database.refresh(user)
    self.assertEqual(user.authored_messages, messages)

  def test_send_append_message(self):
    author, _ = self.create_test_user("author@gmail.com")
    may_append_user, token = self.create_test_user("may_append_user@gmail.com")
    database.add(
        database.Message(
            id=123,
            fragments=[database.MessageFragment(text="first", author=author)],
            author=author,
            may_append_user=may_append_user))
    response = self.client.post(
        "/send-message", json=dict(token=token, message_id=123, text="second"))
    new_messages = database.query(
        database.Message).filter(database.Message.id != 123).all()
    self.assertEqual(len(new_messages), 1)
    self.assertTrue(response.is_json)
    self.assertEqual([f.text for f in new_messages[0].fragments],
                     ["first", "second"])

  def test_send_append_message_bad_permissions(self):
    author, _ = self.create_test_user("author@gmail.com")
    may_append_user, token = self.create_test_user("may_append_user@gmail.com")
    database.add(
        database.Message(
            id=123,
            fragments=[database.MessageFragment(text="first", author=author)],
            author=author,
            may_append_user=None))
    response = self.client.post(
        "/send-message", json=dict(token=token, message_id=123, text="second"))
    self.assertTrue(response.is_json)
    self.assertEqual(
        response.json,
        dict(
            error="User may_append_user@gmail.com does not have permission to view "
            "message 123"))

  def test_get_overview(self):
    author, _ = self.create_test_user("author@gmail.com")
    user, token = self.create_test_user("user@gmail.com")
    user.authored_messages = [
        database.Message(id=1, author=user),
        database.Message(id=2, author=user)
    ]
    user.may_append_messages = [
        database.Message(id=3, author=author, may_append_user=user),
        database.Message(id=4, author=author, may_append_user=user)
    ]
    database.commit()

    response = self.client.get("/", json=dict(token=token))
    self.assertTrue(response.is_json)
    self.assertEqual(
        response.json,
        dict(authored_message_ids=[1, 2], may_append_message_ids=[3, 4]))

  def test_get_overview_assigns_fresh_messages(self):
    author, _ = self.create_test_user("author@gmail.com")
    new_msg = database.new_message(author, "test message")
    user, token = self.create_test_user("user@gmail.com")
    self.assertTrue(database.allowed_to_recieve_msg(user))
    response = self.client.get("/", json=dict(token=token))
    self.assertTrue(response.is_json)
    self.assertEqual(
        response.json,
        dict(authored_message_ids=[], may_append_message_ids=[new_msg.id]))
    database.refresh(user)
    self.assertEqual(user.may_append_messages, [new_msg])

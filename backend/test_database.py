import database
import server_test_util
import util


class DatabaseTest(server_test_util.ServerTestCase):

  def test_open_login_once(self):
    """Users should be emailed a prompt with a secret key, which shows up in the db."""
    email = "test@gmail.com"

    pre_request_time = util.now()
    secret_key = database.open_login_request(email=email)
    post_request_time = util.now()

    pending_req_query = database.query(database.PendingLoginRequest).filter(
        database.PendingLoginRequest.email == email,
        database.PendingLoginRequest.secret_key == secret_key)

    self.assertEqual(pending_req_query.count(), 1)
    pending_req = pending_req_query.first()

    self.assertEqual(pending_req.email, email)
    self.assertLess(pending_req.timestamp, post_request_time)
    self.assertGreater(pending_req.timestamp, pre_request_time)
    self.assertEqual(pending_req.secret_key, secret_key)

  def test_open_login_twice(self):
    """If the same user attempts to login twice, the old request should be ignored."""
    email = "test@gmail.com"

    pre_request_time_1 = util.now()
    secret_key_1 = database.open_login_request(email=email)
    post_request_time_1 = util.now()

    pre_request_time_2 = util.now()
    secret_key_2 = database.open_login_request(email=email)
    post_request_time_2 = util.now()

    pending_req_query = database.query(database.PendingLoginRequest).filter(
        database.PendingLoginRequest.email == email)
    self.assertEqual(pending_req_query.count(), 1)
    pending_req = pending_req_query.first()

    self.assertEqual(pending_req.email, email)
    self.assertLess(pending_req.timestamp, post_request_time_2)
    self.assertGreater(pending_req.timestamp, pre_request_time_2)
    self.assertEqual(pending_req.secret_key, secret_key_2)

  def test_close_login_after_open(self):
    """Closing an open login request results in an API key."""
    email = "test@gmail.com"
    secret_key = database.open_login_request(email=email)
    pre_close_time = util.now()
    token = database.close_login_request(email=email, secret_key=secret_key)
    post_close_time = util.now()

    token_query = database.query(
        database.AccessToken).filter(database.AccessToken.token == token)

    self.assertEqual(token_query.count(), 1)
    access_token = token_query.first()

    self.assertEqual(access_token.email, email)
    self.assertEqual(access_token.token, token)
    self.assertGreater(access_token.timestamp, pre_close_time)
    self.assertLess(access_token.timestamp, post_close_time)

  def test_close_without_open(self):
    """Closing a login request without opening one first is an error."""
    with self.assertRaises(ValueError):
      database.close_login_request(email="test@gmail.com", secret_key="abc123")
    self.assertEqual(database.query(database.AccessToken).count(), 0)

  def test_close_bad_secret_key(self):
    """Closing a login request without the right key is an error."""
    email = "test@gmail.com"
    database.open_login_request(email=email)
    with self.assertRaises(ValueError):
      database.close_login_request(email=email, secret_key="abc123")
    self.assertEqual(database.query(database.AccessToken).count(), 0)
    # The pending login request should be fine.
    self.assertEqual(
        database.query(database.PendingLoginRequest).filter(
            database.PendingLoginRequest.email == email).count(), 1)

  def test_close_timeout(self):
    """Its an error if it takes too long to close the login attempt."""
    long_ago = util.now() - 2 * database.TOKEN_VALID_DELTA
    email = "test@gmail.com"
    secret_key = "abc123"
    database.add(
        database.PendingLoginRequest(
            email=email, secret_key=secret_key, timestamp=long_ago))

    with self.assertRaises(ValueError):
      database.close_login_request(email=email, secret_key=secret_key)

  def test_new_message(self):
    expected_text = "test message here"
    message_id = database.new_message(expected_text)
    message = database.query(
        database.Message).filter(database.Message.id == message_id).first()
    self.assertTrue(message is not None)
    self.assertEqual(len(message.fragments), 1)
    self.assertEqual(message.fragments[0].text, expected_text)

  def test_append_fragment(self):
    msg_id_1 = database.new_message("first")
    msg_id_2 = database.append_fragment(msg_id_1, "second")
    msg_id_3 = database.append_fragment(msg_id_2, "third")

    msg_1 = database.query(
        database.Message).filter(database.Message.id == msg_id_1).first()
    msg_2 = database.query(
        database.Message).filter(database.Message.id == msg_id_2).first()
    msg_3 = database.query(
        database.Message).filter(database.Message.id == msg_id_3).first()

    self.assertTrue(msg_1 is not None)
    self.assertTrue(msg_2 is not None)
    self.assertTrue(msg_3 is not None)

    self.assertEqual([f.text for f in msg_1.fragments], ["first"])
    self.assertEqual([f.text for f in msg_2.fragments], ["first", "second"])
    self.assertEqual([f.text for f in msg_3.fragments],
                     ["first", "second", "third"])

  def test_append_fragment_missing_old_msg(self):
    with self.assertRaises(ValueError):
      database.append_fragment(12345, "bad_msg_id")
    self.assertEqual(database.query(database.Message).count(), 0)

  def test_get_message(self):
    msg_id = 12345
    database.add(
        database.Message(
            id=msg_id,
            fragments=[
                database.MessageFragment(id=util.new_id(), text="first"),
                database.MessageFragment(id=util.new_id(), text="second")
            ]))
    self.assertEqual(database.get_message(msg_id), ["first", "second"])

  def test_get_message_no_fragments(self):
    msg_id = 12345
    database.add(database.Message(id=msg_id))
    self.assertEqual(database.get_message(msg_id), [])

  def test_get_message_bad_id(self):
    with self.assertRaises(ValueError):
      database.get_message(9876)


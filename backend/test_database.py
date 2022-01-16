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
    database.open_login_request(email=email)

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

  def test_new_user_after_first_login(self):
    email = "test@gmail.com"
    secret_key = database.open_login_request(email=email)
    token = database.close_login_request(email=email, secret_key=secret_key)
    user = database.query(
        database.User).filter(database.User.email == email).first()
    self.assertTrue(user is not None)

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
    # New user NOT created.
    user = database.query(
        database.User).filter(database.User.email == email).first()
    self.assertTrue(user is None)

  def test_close_timeout(self):
    """Its an error if it takes too long to close the login attempt."""
    long_ago = util.now() - 2 * database.VALID_LOGIN_ATTEMPT_DELTA
    email = "test@gmail.com"
    secret_key = "abc123"
    database.add(
        database.PendingLoginRequest(
            email=email, secret_key=secret_key, timestamp=long_ago))

    with self.assertRaises(ValueError):
      database.close_login_request(email=email, secret_key=secret_key)

  def test_new_message(self):
    user, _ = self.create_test_user("test@gmail.com")
    expected_text = "test message here"
    database.new_message(user, expected_text)
    message = database.query(database.Message).first()
    self.assertTrue(message is not None)
    self.assertEqual(len(message.fragments), 1)
    self.assertEqual(message.fragments[0].text, expected_text)

  def test_append_fragment(self):
    user, _ = self.create_test_user("test@gmail.com")
    msg_1 = database.new_message(user, "first")
    msg_1.may_append_user = user
    msg_2 = database.append_fragment(user, msg_1, "second")
    msg_2.may_append_user = user
    msg_3 = database.append_fragment(user, msg_2, "third")

    self.assertEqual([f.text for f in msg_1.fragments], ["first"])
    self.assertEqual([f.text for f in msg_2.fragments], ["first", "second"])
    self.assertEqual([f.text for f in msg_3.fragments],
                     ["first", "second", "third"])

  def test_append_fragment_bad_user(self):
    user, _ = self.create_test_user("test@gmail.com")
    msg = database.new_message(user, "test")
    with self.assertRaises(ValueError):
      database.append_fragment(user, msg, text="user isn't may_append_user")

  def test_append_fragment_twice_fails(self):
    """You should lose permissions after appending a message."""
    user, _ = self.create_test_user("test@gmail.com")
    original_msg = database.new_message(user, "first")
    appender, _ = self.create_test_user("appender@gmail.com")
    original_msg.may_append_user = appender
    # This should work without error.
    database.append_fragment(appender, original_msg, "good append")
    with self.assertRaises(ValueError):
      database.append_fragment(appender, original_msg, "bad append")

  def test_get_user_from_token(self):
    user, token = self.create_test_user("test@gmail.com")
    self.assertEqual(database.get_user_from_token(token), user)

  def test_get_user_from_token(self):
    with self.assertRaises(ValueError):
      database.get_user_from_token("garbage token")

  def test_get_user_from_token_old_value(self):
    token = util.generate_access_token()
    long_ago = util.now() - 2 * database.VALID_TOKEN_DELTA
    database.add(
        database.AccessToken(
            email="test@gmail.com", token=token, timestamp=long_ago))
    with self.assertRaises(ValueError):
      database.get_user_from_token(token)

  def test_assign_fresh_message(self):
    author, _ = self.create_test_user("author@gmail.com")
    may_append_user, _ = self.create_test_user("may_append_user@gmail.com")
    message = database.Message(id=1, author=author)
    database.add(message)
    database.commit()
    database.assign_fresh_message(may_append_user, message)
    database.refresh(message)
    database.refresh(may_append_user)
    self.assertEqual(message.may_append_user, may_append_user)
    self.assertEqual(may_append_user.may_append_messages, [message])

  def test_set_assign_fresh_message_not_fresh(self):
    author, _ = self.create_test_user("author@gmail.com")
    user_1, _ = self.create_test_user("user_1@gmail.com")
    user_2, _ = self.create_test_user("@gmail.2_resucom")
    message = database.Message(id=1, author=author)
    database.add(message)
    database.commit()

    database.assign_fresh_message(user_1, message)
    # This message isn't fresh
    with self.assertRaises(ValueError):
      database.assign_fresh_message(user_2, message)

    database.refresh(user_1)
    database.refresh(user_2)
    self.assertEqual(message.may_append_user, user_1)
    self.assertEqual(len(user_1.may_append_messages), 1)
    self.assertEqual(len(user_2.may_append_messages), 0)

    # This message still isn't fresh
    message.may_append_user = None
    database.commit()
    with self.assertRaises(ValueError):
      database.assign_fresh_message(user_2, message)

  def test_user_may_recieve_msg_new_user(self):
    user, _ = self.create_test_user("test@gmail.com")
    self.assertTrue(database.allowed_to_recieve_msg(user))

  def test_user_may_recieve_msg_returning_user(self):
    long_ago = util.now() - 2 * database.NEW_MESSAGE_MIN_DELTA
    user = database.User(
        email="old_user@gmail.com", last_msg_received_timestamp=long_ago)
    database.add(user)
    self.assertTrue(database.allowed_to_recieve_msg(user))

  def test_user_may_recieve_msg_recent_user(self):
    long_ago = util.now() - 0.5 * database.NEW_MESSAGE_MIN_DELTA
    user = database.User(
        email="recent_user@gmail.com", last_msg_received_timestamp=long_ago)
    database.add(user)
    self.assertFalse(database.allowed_to_recieve_msg(user))

  def test_retrieve_only_closest_msg(self):
    """The user should get the closest message."""
    # Users arranged in a row.
    users = [
        database.User(email="0", coordinate_y=0, coordinate_x=0),
        database.User(email="1", coordinate_y=0, coordinate_x=0.1),
        database.User(email="2", coordinate_y=0, coordinate_x=0.2)
    ]
    for i, u in enumerate(users):
      database.add(u)
      database.add(database.Message(id=i, author=u))
    # Own the closest message.
    msg_1 = database.find_closest_fresh_msg(users[0])
    self.assertEqual(msg_1.id, 1)
    database.assign_fresh_message(users[0], msg_1)

    msg_2 = database.find_closest_fresh_msg(users[0])
    self.assertEqual(msg_2.id, 2)
    database.assign_fresh_message(users[0], msg_2)

    self.assertTrue(database.find_closest_fresh_msg(users[0]) is None)

  def test_retrieve_only_fresh_msg(self):
    author, _ = self.create_test_user("author@gmail.com")
    may_append_user, _ = self.create_test_user("may_append_user@gmail.com")

    fresh_msg = database.new_message(author, "fresh")
    not_fresh_msg = database.new_message(author, "not fresh")
    not_fresh_msg.fresh = False
    database.commit()

    closest_msg = database.find_closest_fresh_msg(may_append_user)
    self.assertEqual(closest_msg, fresh_msg)

    # once may_append_user is set, its no longer a fresh msg.
    database.assign_fresh_message(may_append_user, closest_msg)
    self.assertTrue(database.find_closest_fresh_msg(may_append_user) is None)

  def test_get_message(self):
    user, _ = self.create_test_user("test@gmail.com")
    expected_message = database.new_message(user, "test message")
    self.assertEqual(
        database.get_message(user, expected_message.id), expected_message)

  def test_get_message_bad_id(self):
    user, _ = self.create_test_user("test@gmail.com")
    with self.assertRaises(ValueError):
      database.get_message(user, 12345)

  def test_get_message_bad_permission(self):
    user, _ = self.create_test_user("test@gmail.com")
    message = database.new_message(user, "test message")
    bad_user, _ = self.create_test_user("bad_user@gmail.com")
    with self.assertRaises(ValueError):
      database.get_message(bad_user, message.id)

  def test_user_may_not_retrive_affter_getting_a_msg(self):
    author, _ = self.create_test_user("author@gmail.com")
    msg_1 = database.new_message(author, "msg 1")
    user, _ = self.create_test_user("user@gmail.com")
    database.assign_fresh_message(user, msg_1)
    msg_2 = database.new_message(author, "msg 2")
    self.assertFalse(database.allowed_to_recieve_msg(user))



  # Need to make sure that a message that was appended to doesn't get assigned to anyone.

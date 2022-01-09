import database
import server_test_util
import util


class DatabaseTest(server_test_util.ServerTestCase):

  def test_open_login_once(self):
    """Users should be emailed a prompt with a secret key, which shows up in the db."""
    test_email = "test@gmail.com"

    pre_request_time = util.now()
    secret_key = database.open_login_request(email=test_email)
    post_request_time = util.now()

    pending_req_query = database.db.session.query(
        database.PendingLoginRequest).filter(
            database.PendingLoginRequest.email == test_email,
            database.PendingLoginRequest.secret_key == secret_key)

    self.assertEqual(pending_req_query.count(), 1)
    pending_req = pending_req_query.first()

    self.assertEqual(pending_req.email, test_email)
    self.assertLess(pending_req.timestamp, post_request_time)
    self.assertGreater(pending_req.timestamp, pre_request_time)
    self.assertEqual(pending_req.secret_key, secret_key)

  def test_open_login_twice(self):
    """If the same user attempts to login twice, the old request should be ignored."""
    test_email = "test@gmail.com"

    pre_request_time_1 = util.now()
    secret_key_1 = database.open_login_request(email=test_email)
    post_request_time_1 = util.now()

    pre_request_time_2 = util.now()
    secret_key_2 = database.open_login_request(email=test_email)
    post_request_time_2 = util.now()

    pending_req_query = database.db.session.query(
        database.PendingLoginRequest).filter(
            database.PendingLoginRequest.email == test_email)
    self.assertEqual(pending_req_query.count(), 1)
    pending_req = pending_req_query.first()

    self.assertEqual(pending_req.email, test_email)
    self.assertLess(pending_req.timestamp, post_request_time_2)
    self.assertGreater(pending_req.timestamp, pre_request_time_2)
    self.assertEqual(pending_req.secret_key, secret_key_2)

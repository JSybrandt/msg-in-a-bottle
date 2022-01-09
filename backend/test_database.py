import database
import server_test_util

class DatabaseTest(server_test_util.ServerTestCase):
  def test_open_login_no_secret_key(self):
    """Users should be emailed a prompt with a secret key, which shows up in the db."""
    test_email = "test@gmail.com"
    secret_key = database.open_login_request(email=test_email)
    count = database.db.session.query(database.PendingLoginRequest).filter(database.PendingLoginRequest.email==test_email, database.PendingLoginRequest.secret_key==secret_key).count()
    self.assertEqual(count, 1)


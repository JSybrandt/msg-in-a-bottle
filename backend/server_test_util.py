from flask_testing import TestCase

import database
import server
import util


class ServerTestCase(TestCase):

  def create_app(self):
    return server.create_app(TESTING=True, SQLALCHEMY_DATABASE_URI="sqlite://")

  def setUp(self):
    database.db.create_all()

  def tearDown(self):
    database.db.session.remove()
    database.db.drop_all()

  def create_test_user(self, email):
    """Returns an API key for testing."""
    database.add(database.User(email=email))
    token = util.generate_access_token()
    database.add(
        database.AccessToken(email=email, token=token, timestamp=util.now()))
    return token

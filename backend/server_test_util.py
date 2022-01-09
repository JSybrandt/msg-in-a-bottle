from flask_testing import TestCase

import database
import server

class ServerTestCase(TestCase):
  def create_app(self):
    return server.create_app(TESTING=True,
                             SQLALCHEMY_DATABASE_URI = "sqlite://")

  def setUp(self):
    database.db.create_all()

  def tearDown(self):
    database.db.session.remove()
    database.db.drop_all()

import util
import unittest

class UtilTest(unittest.TestCase):
  def test_valid_email(self):
    self.assertTrue(util.is_valid_email("justin@sybrandt.com"))
    self.assertTrue(util.is_valid_email("justin.sybrandt@gmail.com"))
    self.assertTrue(util.is_valid_email("justin+spam@gmail.com"))

  def test_not_valid_email(self):
    self.assertFalse(util.is_valid_email("justin@sybrandt"))
    self.assertFalse(util.is_valid_email("justin.gmail.com"))
    self.assertFalse(util.is_valid_email("justin"))

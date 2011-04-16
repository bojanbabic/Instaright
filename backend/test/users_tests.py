import unittest, logging
from google.appengine.api import urlfetch
from users import UserUtil


class AppEngineAPITest(unittest.TestCase):
    
    def test_urlfetch(self):
        response = urlfetch.fetch('http://www.google.com')
        self.assertEquals(15, response.content.find('<html>'))
class KloutScoreTest(unittest.TestCase):
    def testKloutScore(self):
	user='gbabun@gmail.com'
	score = UserUtil.getKloutScore(user)
	logging.info('got score %s for %s ' %(score, user))
	self.assertTrue( score > 0)

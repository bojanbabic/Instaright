import unittest, logging, ConfigParser, sys, os
from google.appengine.api import urlfetch
from users import UserUtil

class AppEngineAPITest(unittest.TestCase):
    
    def _test_urlfetch(self):
        response = urlfetch.fetch('http://www.google.com')
        self.assertEquals(15, response.content.find('<html>'))
class KloutScoreTest(unittest.TestCase):
    def _testKloutScore(self):
	user='gbabun@gmail.com'
	config=ConfigParser.ConfigParser()
	config.read(os.path.split(os.path.realpath(__file__))[0]+'/../properties/general.ini')
	klout_api_key=config.get('social', 'klout_api_key')
	score = UserUtil.getKloutScore(user,klout_api_key)
	logging.info('got score %s for %s ' %(score, user))
	self.assertTrue( score > 0)

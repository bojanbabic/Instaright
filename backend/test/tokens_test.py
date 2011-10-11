import unittest
from models import UserTokens, UserDetails

class TokenTest(unittest.TestCase):
	def test_user_token(self):
		user='gbabun@gmail.com'
		ud=UserDetails.gql('WHERE instapaper_account = :1' , user).get()
		#self.assertTrue(ud is not None)
		token=UserTokens()
		#token.user_details=ud
		token.put()

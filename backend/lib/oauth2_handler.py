import logging, os, sys
from uuid import uuid4

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db

from utils.link import LinkUtils

class OAuthAccessToken(db.Model):
    """OAuth Access Token."""

    service = db.StringProperty()
    specifier = db.StringProperty()
    oauth_token = db.StringProperty()
    oauth_token_secret = db.StringProperty()
    additional_info=db.StringProperty()
    created = db.DateTimeProperty(auto_now_add=True)

def create_uuid():
        return 'id-%s' % uuid4()
               
class SimpleOAuthHandler(webapp.RequestHandler):
        def __init__(self, service=None):
                self.service=service
        def set_cookie(self, value, path='/'):
                self.response.headers.add_header(
                'Set-Cookie', 
                '%s=%s; path=%s; expires="Fri, 31-Dec-2021 23:59:59 GMT"' %
                ('oauth.%s' % self.service, value, path)
                )
        
	def get(self, service, method):
                key_name = create_uuid()
        	oauth_code = self.request.get("code")

                oauth_token=''
                self.service = service
        	if service == 'picplz' and oauth_code is not None:
                        logging.info('code %s' % oauth_code)
                        json=LinkUtils.getJsonFromApi('https://picplz.com/oauth2/access_token?client_id=BnYEDMYMrqaKP7DYvQS55meeMHG6s2CA&client_secret=DjZ7DEjzT273tFHvdRPQ49kTA3XJXKpk&grant_type=authorization_code&redirect_uri=http://www.instaright.com/oauth2/picplz/callback&code=%s' % oauth_code)
                	if json is not None:
                                logging.info('picplz response %s' % json)
                        	oauth_token = json['access_token']
                        	logging.info('just got picplz access token %s' % oauth_token)
		self.token = OAuthAccessToken(key_name=key_name, service=service, oauth_token=oauth_token)
        	self.token.put()
                self.set_cookie(key_name)
        	self.redirect('/user/dashboard')

application=webapp.WSGIApplication([
                             ('/oauth2/(.*)/(.*)', SimpleOAuthHandler),
                             ], debug=True)
def main():
        run_wsgi_app(application)

if __name__ == '__main__':
        main()

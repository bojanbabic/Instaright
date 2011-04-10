import sys, os, urllib2, datetime, logging, cgi, uuid

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext.webapp.util import run_wsgi_app
from django.utils import simplejson
from utils import LoginUtil

from models import UserSessionFE, SessionModel, Links
from oauth_handler import OAuthHandler, OAuthClient
from main import UserMessager
import facebook

key='180962951948062'
secret='9ae7202531b3b813baf1bca1fcea6178'

class AccountHandler(webapp.RequestHandler):
    def get(self):

	uu = LoginUtil()
	user_details = uu.getUserDetails(self)
	screen_name = user_details["screen_name"]
	logout_url = user_details["logout_url"]

	google_login_url = users.create_login_url('/') 

        if screen_name is None:
                template_variables = { 'google_login_url': google_login_url }
                #path = os.path.join(os.path.dirname(__file__), 'templates/login.html')
                path = os.path.join(os.path.dirname(__file__), 'templates/register.html')
                self.response.headers["Contant-Type"]= "text/html; charset=utf-8"
                self.response.out.write(template.render(path,template_variables))
        else:
		#user_uuid = uuid.uuid4()
		#userMessager = UserMessager(str(user_uuid))
		#channel_id = userMessager.create_channel()
                #template_variables = {'user':screen_name, 'login_url':None, 'logout_url': logout_url, 'channel_id':channel_id, 'hotlinks': None}
		#path= os.path.join(os.path.dirname(__file__), 'index.html')
                #self.response.headers["Content-Type"] = "text/html; charset=utf-8"
		#self.response.out.write(template.render(path,template_variables))
		self.redirect('/')

application=webapp.WSGIApplication([
                             ('/account', AccountHandler),
                             ], debug=True)
def main():
        run_wsgi_app(application)

if __name__ == '__main__':
        main()

import os, datetime, logging

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.ext.webapp.util import run_wsgi_app

from utils.user import UserUtils

class AccountHandler(webapp.RequestHandler):
    def get(self):

	uu = UserUtils()
        logout_cookie = self.request.cookies.get('user_logged_out')
	user_details = uu.getUserDetails(self)
	screen_name = user_details["screen_name"]

	google_login_url = users.create_login_url('/') 

        if screen_name is None or logout_cookie is not None:
                template_variables = { 'google_login_url': google_login_url }
                path = os.path.join(os.path.dirname(__file__), 'templates/register.html')
                self.response.headers["Contant-Type"]= "text/html; charset=utf-8"
                self.response.out.write(template.render(path,template_variables))
        else:
                template_variables = {}
                path = os.path.join(os.path.dirname(__file__), 'templates/index.html')
                self.response.headers["Contant-Type"]= "text/html; charset=utf-8"
                self.response.out.write(template.render(path,template_variables))

class AccountLogoutHandler(webapp.RequestHandler):
	def get(self):
		uuid_cookie = self.request.cookies.get('user_uuid')
		if uuid_cookie:
			logging.info('deleting login cookie')
                        expires = datetime.datetime.now()
                        exp_format = datetime.datetime.strftime(expires, '%a, %d-%b-%Y %H:%M:%S GMT')
			self.response.headers.add_header('Set-Cookie', 'user_uuid=%s; expires=%s; path=/' %( uuid_cookie, exp_format))

                        expires_logout = datetime.datetime.now() + datetime.timedelta(days=365)
                        exp_format = datetime.datetime.strftime(expires_logout, '%a, %d-%b-%Y %H:%M:%S GMT')
			self.response.headers.add_header('Set-Cookie', 'user_logged_out=%s; expires=%s; path=/' %( '1', exp_format))
		self.redirect('/')
		
			

application=webapp.WSGIApplication([
                             ('/account/logout', AccountLogoutHandler),
                             ('/account', AccountHandler),
                             ], debug=True)
def main():
        run_wsgi_app(application)

if __name__ == '__main__':
        main()

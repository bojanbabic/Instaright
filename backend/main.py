import sys, os, urllib2
import logging 
#import multiprocessing

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp.util import run_wsgi_app
from django.utils import simplejson

class SessionModel(db.Model):
	user_agent=db.StringProperty()
	instaright_account=db.StringProperty()
	ip=db.StringProperty()
	url=db.StringProperty()

class Logging(webapp.RequestHandler):
	def post(self):
		try:
			args=simplejson.loads(self.request.body)
			account=args[0]
			URL=urllib2.unquote(args[1])
			model=SessionModel(user_agent=self.request.headers['User-agent'], ip = self.request.remote_addr, instaright_account=account, url=URL)
			model.put()
			return self.response.out.write(1)
		except:
			e = sys.exc_info()[1]
			logging.error('Error while handling request %s' % e)
		
	def get(self):
		URL=cgi.escape(self.request.get('url'))
		account=cgi.escape(self.request.get('username'))
		self.response.out.write(URL)
		model=SessionModel(user_agent=self.request.headers['User-agent'], ip = self.request.remote_addr, instaright_account=account, url=URL)
		model.put()
		return self.response.out.write(1)
class ErrorHandling(webapp.RequestHandler):
	def post(self):
		args=simplejson.loads(self.request.body)
		error=args[0]
		logging.error('Error caught within extension:'+error)
		return self.response.out.write(1)
		
application = webapp.WSGIApplication(
                                     [('/rpc', Logging),
                                     ('/error', ErrorHandling)],
                                     debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()


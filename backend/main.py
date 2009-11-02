import sys, cgi,re,os
#import multiprocessing

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp.util import run_wsgi_app

class SessionModel(db.Model):
	user_agent=db.StringProperty()
	ip=db.StringProperty()
	url=db.StringProperty()

class Logging(webapp.RequestHandler):
	def post(self):
		args=self.request.body
		url=args[0]
		print args
		model=SessionModel(user_agent=self.request.headers['User-agent'], ip = self.request.remote_addr, url=url)
		model.put()
		
	def get(self):
		URL=cgi.escape(self.request.get('url'))
		self.response.out.write(URL)
		model=SessionModel(user_agent=self.request.headers['User-agent'], ip = self.request.remote_addr, url=URL)
		model.put()
		
application = webapp.WSGIApplication(
                                     [('/rpc', Logging)],
                                     debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()


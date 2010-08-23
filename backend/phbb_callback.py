import logging, datetime, os, urllib2, urllib, Queue
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from main import SessionModel

import feedparser

new_updates = Queue.Queue()

class CallbackHandler(webapp.RequestHandler):
	def get(self):
		token = self.request.get('hub.challenge')
		subscription_token=self.request.get('hub.mode')
		if subscription_token != 'subscribe' and subscription_token != 'unsubscribe':
			logging.info('Don\'t know what you are doing here')
			self.response.out.write('Don\'t know what you are doing here')
		if not token:
			logging.info('This was not expected')
			self.response.out.write('This was not expected')
		
		logging.info('recieved subscription token %s ' % token)
		self.response.out.write(token)
	def post(self):
		feed = feedparser.parse(self.request.body)
		
		#root = ElementTree.fromstring(data)
		logging.info('recieved: ' )
		for update in feed.entries:
			logging.info(' %s ' %update)
			title = update.title
			link = update.link
			#new_updates.put(update)
#class RealTimeUpdateHandler(webapp.RequestHandler):
#	def get(self):
#		try:
#		except Queue.Empty:
#			logging.info('empty queue')
#			pass
		
application = webapp.WSGIApplication(
                                     [
                                     	('/callback', CallbackHandler)
				     ],
                                     debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()

import logging, datetime ,os, urllib2, urllib, Queue
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.api import xmpp
from google.appengine.api import memcache
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from main import SessionModel, BroadcastMessage
from models import Subscription
from utils import UserUtil
from xmpp_handler import XMPPHandler 

import feedparser

new_updates = Queue.Queue()
xmpp_handler = XMPPHandler()

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

                # delete json feed cache
                logging.info('deleting json cache info')
                memcache_key='feed_json_cache'
                memcache.delete(memcache_key)
		
		#root = ElementTree.fromstring(data)
		broadcaster = BroadcastMessage()
		logging.info('recieved:callback ' )
		subscribers = Subscription.gql('WHERE active = True and mute = False').fetch(100)
		subscribers_address = [ s.subscriber.address for s in subscribers ]
		logging.info(' trying to send messages to following addresses %s ' %(','.join(subscribers_address)))
                userUtil = UserUtil()
		for update in feed.entries:
			logging.info(' %s ' %update)
			title = update.title
			link = update.link
			domain = update.domain
			logging.info('domain : %s' % domain)
			message = Message( title = title, link = link , domain = domain)
                        #TODO possible bottleneck
                        user = SessionModel.gql('WHERE __key__ = :1', db.Key(update.id)).get()
                        logging.info('user %s' % user.instaright_account)
                        avatar = userUtil.getAvatar(user.instaright_account)
                        logging.info('avatar %s' %avatar)
                        messageAsJSON = [{'u':{'id':update.id, 't':update.title,'l':update.link,'d':update.domain,'a':avatar, 'u':update.updated}}]
			broadcaster.send_message(messageAsJSON)
			xmpp_handler.send_message(subscribers, message)
class RealTimeUpdateHandler(webapp.RequestHandler):
	def get(self):
		try:
			logging.info('real time update is about tobe implemente')
		except Queue.Empty:
			logging.info('empty queue')
			pass
class Message(object):
	def __init__(self, title, link, domain):
		self.title = title
		self.link = link
		self.domain = domain
		
application = webapp.WSGIApplication(
                                     [
                                     	('/callback', CallbackHandler)
				     ],
                                     debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()

import logging
import os
import Queue
import sys
import time
import datetime
from google.appengine.ext import webapp, db
from google.appengine.api import memcache
from google.appengine.api.labs import taskqueue
from google.appengine.ext.webapp.util import run_wsgi_app
from main import  BroadcastMessage
from models import Subscription, SessionModel

from xmpp_handler import XMPPHandler 

from utils.link import LinkUtils
from utils.user import UserUtils

import feedparser
sys.path.append(os.path.join(os.path.dirname(__file__),'lib'))
import simplejson

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
		logging.info('recieved:callback ' )
		subscribers = Subscription.gql('WHERE active = True and mute = False').fetch(100)
		subscribers_address = [ s.subscriber.address for s in subscribers ]
		logging.info(' trying to send messages to following addresses %s ' %(','.join(subscribers_address)))
		for update in feed.entries:
			logging.info('adding message to broadcast queue %s ' %update)
			taskqueue.add(queue_name='message-broadcast-queue', url= '/message/broadcast/task', params={'user_id':update.id, 'title':update.title, 'link':update.link, 'domain':update.domain, 'updated': update.updated,'subscribers': simplejson.dumps(subscribers, default=lambda s: {'a':s.subscriber.address, 'd':s.domain})})

class BroadcastMessageTask(webapp.RequestHandler):
        def post(self):
		        broadcaster = BroadcastMessage()
                        userUtil = UserUtils()
			title = self.request.get('title', None)
			link = self.request.get('link', None)
			domain = self.request.get('domain', None)
                        user_id = self.request.get('user_id', None)
                        updated = self.request.get('updated', None)
                        embeded = self.request.get('e', None)
                        link_category = self.request.get('link_category', None)
                        subscribers = simplejson.loads(self.request.get('subscribers', None))

			message = Message( title = title, link = link , domain = domain)

                        user = SessionModel.gql('WHERE __key__ = :1', db.Key(user_id)).get()
                        if user is None:
                                logging.info('can\'t determine user by id: %s' % user_id)
                                return
                        logging.info('user %s' % user.instaright_account)
                        avatar = userUtil.getAvatar(user.instaright_account)
                        logging.info('avatar %s' %avatar)
                        messageAsJSON = [{'u':{'id':user_id, 't':title,'ol':link, 'l':LinkUtils.generate_instaright_link(user.url_encode26, LinkUtils.make_title(title)),'d':domain,'dd': LinkUtils.generate_domain_link(domain), 'a':avatar, 'u':updated, 'source': user.client, 'lc':link_category, 'html_lc':LinkUtils.getLinkCategoryHTML(user),  'e': embeded, 'n': int(time.mktime(datetime.datetime.now().timetuple()))}}]
                        logging.info('sending message %s ' %messageAsJSON)
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
                                     	('/callback', CallbackHandler),
                                        ('/message/broadcast/task', BroadcastMessageTask),
				     ],
                                     debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()

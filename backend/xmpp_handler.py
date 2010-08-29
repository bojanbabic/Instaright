import wsgiref.handlers, sys, logging, datetime
from google.appengine.api import xmpp
from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import xmpp_handlers

from cron import WeeklyDomainStats
from models import Subscription

		
#class XMPPHandler(webapp.RequestHandler):
class XMPPHandler(xmpp_handlers.CommandHandler):
	def help_command(self, message=None):
		message.reply("""Hello %s !You can do following commands:\n/subscribe <domain_name> -> follow bookmarks for domain\n/topdomains -> will help you to follow trending domains\n/unsubscribe -> unsubscribe from all subscriptions\n
		""" % message.sender)
		
	def subscribe_command(self, message=None):
		if not message.arg.startswith('http'):
			message.reply('Make sure that your domains starts with http:// ')
			return
		im_from = db.IM('xmpp', message.sender)
		existingSubscription = Subscription.gql(' WHERE subscriber = :1 and domain = :2 and active = True', im_from , message.arg).get()
		if existingSubscription is not None:
			message.reply('You have already subscribed for this domain %s. Remember?' % message.arg)
			return
		subscription = Subscription(subscriber = im_from, domain = message.arg, activationDate = datetime.datetime.now(), active = True)
		subscription.put()
		message.reply('Subscription added.')
	def unsubscribe_command(self, message=None):
		im_from = db.IM('xmpp', message.sender)
		subscribers = Subscription.gql('WHERE subscriber = :1 and active = True' , im_from).fetch(100)
		if not subscribers or len(subscribers) == 0:
			message.reply('Heh! It seems like you don\'t have any active subscriptions')
		for s in subscribers:
			s.active = False
			s.put()
		message.reply('All your subscriptions have been canceled')
		
	def topdomains_command(self, message=None):
		domains = self.cacheTopWeeklyDomains(None);
		if domains is None:
			msg = 'We have no suggestions for you'
		msg = '\n'.join(domains)
		
		message.reply(msg)
		
	def text_message(self, message=None):
		message.reply('Hello')
	def cacheTopWeeklyDomains(self, weekly_stats):
		memcache_top_domains_key = 'latest_top_domains'
		top_domains_cache = memcache.get(memcache_top_domains_key)
		if top_domains_cache:
			logging.info('getting top domains from cache')
			return top_domains_cache
		if weekly_stats is None:
			weekly_stats=WeeklyDomainStats.gql('ORDER BY date DESC, count DESC ').fetch(10)
		if weekly_stats is None or len(weekly_stats) == 0 :
			logging.info('Not enough data')
			return None
		domains = [ w.domain for w in weekly_stats if w.count > 10 ]
		logging.info('returning and storing top domain info in cache')
		memcache.set(memcache_top_domains_key, domains)
		return domains


application = webapp.WSGIApplication([
			('/_ah/xmpp/message/chat/', XMPPHandler),
			], debug=True)

def main():
	#wsgiref.handlers.CGIHandler().run(application)
	run_wsgi_app(application)
if __name__ == "__main__":
	main()

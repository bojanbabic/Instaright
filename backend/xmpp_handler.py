import wsgiref.handlers, sys, logging, datetime, os
from google.appengine.api import xmpp
from google.appengine.api import memcache
from google.appengine.api import mail
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import xmpp_handlers

from cron import WeeklyDomainStats
from models import Subscription,IMInvite
from utils import StatsUtil

		
#class XMPPHandler(webapp.RequestHandler):
class XMPPHandler(xmpp_handlers.CommandHandler):
	def help_command(self, message=None):
		options = []
		options.append('Following commands available:')
		options.append('/subscribe <domain_name> -> follow bookmarks for domain')
		options.append('/unsubscribe -> unsubscribe from all subscriptions')
		options.append('/mute -> temporary mute all subscriptions')
		options.append('/unmute -> unmute all muted subscriptions')
		options.append('/topdomains -> will help you to follow trending domains')
		options.append('... keep on playing::~instaR!ght~')
		
		message.reply('\n'.join(options))
		#message.reply("""You can do following commands:\n/subscribe <domain_name> -> follow bookmarks for domain\n/topdomains -> will help you to follow trending domains\n/unsubscribe -> unsubscribe from all subscriptions\n
		#""" % message.sender)
	def user_mail(self, sender):
		if sender.find("/"):
			return sender[0:sender.find("/")]
		else:
			return sender
		
	def subscribe_command(self, message=None):
		subscriber_mail = self.user_mail(message.sender)
		logging.info('subscribing user: %s' % subscriber_mail)
		im_from = db.IM('xmpp', message.sender)
		domain = StatsUtil.getDomain(message.arg)
		if message.arg == 'all':
			domain = 'all'
		if not domain:
			message.reply('You must provide valide domain for subscription. \'%s\' is not valid domain. Make sure that domain starts with http://'  %message.arg)
			return
		existingSubscription = Subscription.gql('WHERE subscriber_mail = :1 and domain = :2 and active = True', subscriber_mail, domain).get()
		if existingSubscription is not None:
			message.reply('You have already subscribed for this domain %s. Remember?' % domain)
			return
		subscription = Subscription(subscriber = im_from, subscriber_mail = subscriber_mail, domain = domain, activationDate = datetime.datetime.now(), active = True, mute = False)
		invite = IMInvite.gql('WHERE jid = :1 ', subscriber_mail)
		subscription.put()
		if invite:
			invite.subscribed = True
			invite.put()
		message.reply('Subscription added.')

	def mute_command(self, message=None):
		subscriber_mail = self.user_mail(message.sender)
		logging.info('muting user: %s' % subscriber_mail)
		im_from = db.IM('xmpp', message.sender)
		unmutedSubscription = Subscription.gql('WHERE subscriber_mail = :1 and active = True and mute = False', subscriber_mail).fetch(100)
		if unmutedSubscription is not None:
			for es in unmutedSubscription:
				es.mute=True
				es.put()
			message.reply('Subscriptions muted.')
		else:
			message.reply('Nothing to mute.')

	def unmute_command(self, message=None):
		subscriber_mail = self.user_mail(message.sender)
		logging.info('muting user: %s' % subscriber_mail)
		im_from = db.IM('xmpp', message.sender)
		mutedSubscription = Subscription.gql('WHERE subscriber_mail = :1 and active = True and mute = True', subscriber_mail).fetch(100)
		if mutedSubscription is not None:
			for ms in mutedSubscription:
				ms.mute=False
				ms.put()
			message.reply('Subscriptions unmuted.')

	def unsubscribe_command(self, message=None):
		im_from = db.IM('xmpp', message.sender)
		subscriber_mail = self.user_mail(message.sender)
		logging.info('unscribing user: %s' %message.sender)
		subscribers = Subscription.gql('WHERE subscriber_mail = :1 and active = True' , subscriber_mail).fetch(100)
		if not subscribers or len(subscribers) == 0:
			message.reply('Heh! It seems like you don\'t have any active subscriptions')
			return
		for s in subscribers:
			s.active = False
			s.put()
		message.reply('All your subscriptions have been canceled')
		
	def topdomains_command(self, message=None):
		domains = self.cacheTopWeeklyDomains(None);
		if domains is None:
			msg = 'We have no suggestions for you'
			return
		msg = '\n'.join(domains)
		
		message.reply(msg)
		
	def text_message(self, message=None):
                if message.arg.startswith(' '):
                        message.replay('If you are typing command you have trailing space. Try again without space at begining of command.')
                        return
                message.reply('This bot supports commands. All commands start with / ( slash ).\nFor instance try:/help ')
	def cacheTopWeeklyDomains(self, weekly_stats):
		memcache_top_domains_key = 'latest_top_domains'
		top_domains_cache = memcache.get(memcache_top_domains_key)
		if top_domains_cache:
			logging.info('getting top domains from cache')
			return top_domains_cache
		if weekly_stats is None:
			logging.info('fetching top 10 domains from db')
			weekly_stats=WeeklyDomainStats.gql('ORDER BY date DESC, count DESC ').fetch(10)
		if weekly_stats is None:
			logging.info('Not enough data')
			return None
		domains = [ w.domain for w in weekly_stats if w.count > 10 ]
		default_domain = ' ... for more domains visit: http://instaright.appspot.com/stats'
		domains.append(default_domain)
		logging.info('returning and storing top domain info in cache')
		memcache.set(memcache_top_domains_key, domains)
		return domains
	def send_message(self, subscribers, message):
		for s in subscribers:
			if s.domain == message.domain or s.domain == 'all':
				msg = ' %s ( %s )' %( message.title, message.link)
				xmpp.send_message(s.subscriber.address, msg)
			else:
				logging.info('skipping: domain missmatch')

class XMPPUserHandler(webapp.RequestHandler):
	def post(self):
		user_jid = self.request.body
		template_variables = []
		path= os.path.join(os.path.dirname(__file__), 'templates/send_invite.html')
                if user_jid is None or user_jid == '':
		        template_variables = {'success_code':'need to provide jid'}
		        self.response.out.write(template.render(path,template_variables))
                        return
		logging.info('sending invite to: %s' % user_jid )
                msg = "Welcome to instaright@appspot.com. You can track domains that are of your interest. \n\nFor more info type:\n/help"
                #TODO what about other protocols ?
                im = db.IM('xmpp',user_jid)
		xmpp.send_invite(user_jid)
                status_code = xmpp.send_message(im.address, msg)
                if status_code == xmpp.INVALID_JID or status_code == xmpp.OTHER_ERROR:
		        template_variables = {'success_code':'error occured while sending xmpp message'}
		        self.response.out.write(template.render(path,template_variables))
                        return
                chat_send = ( status_code != xmpp.NO_ERROR)
                if not chat_send:
                        mail.send_mail(sender="Instapaper Firefox Addon<gbabun@gmail.com>",to=user_jid,subject="Instaright over XMPP",
                                        body=msg)
                        logging.info('mail has been sent instead of welcome message')
                logging.info('----%s----' % status_code)
                invite = IMInvite()
                invite.im=user_jid
                invite.subscribed = False
                invite.put()
		template_variables = {'success_code':'success'}
		self.response.out.write(template.render(path,template_variables))
        def get(self):
                        self.post();

application = webapp.WSGIApplication([
			('/_ah/xmpp/message/chat/', XMPPHandler),
			('/send_invite', XMPPUserHandler),
			], debug=True)

def main():
	#wsgiref.handlers.CGIHandler().run(application)
	run_wsgi_app(application)
if __name__ == "__main__":
	main()

import sys
import os
import datetime
import ConfigParser
import logging
import thread
import time
import urllib

from utils.handler import RequestUtils
from utils.link import LinkUtils, EncodeUtils
from utils.score import UserScoreUtility
from utils.page import PageUtils

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api.labs import taskqueue
from google.appengine.api import memcache, channel, users, datastore_errors
from google.appengine.ext.db import NotSavedError
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.db import BadValueError
from google.appengine.runtime import apiproxy_errors
from google.appengine.api.taskqueue import TransientError

from models import UserSessionFE, SessionModel, Subscription, UserDetails
import generic_counter
from generic_handler import GenericWebHandler

sys.path.append(os.path.join(os.path.dirname(__file__),'lib'))
import simplejson

conf = ConfigParser.ConfigParser()
conf.read(os.path.split(os.path.realpath(__file__))[0]+'/properties/devel.ini')
ENVIRONMENT=conf.get('server', 'env')

class UserMessager:
	def __init__(self, user_uid):
		self.user_uuid = user_uid
	def create_channel(self):
		return channel.create_channel(self.user_uuid)
	def send(self, message):
		channel.send_message(self.user_uuid, simplejson.dumps(message))

class BroadcastMessage:
	def send_message(self, message, path=None):
		last_hour = datetime.datetime.now() - datetime.timedelta(hours = 1)
                taskqueue.add(queue_name='default', url='/deactivate_channels')
                if path is None:
                        path='/'
                logging.info('looking for active users on %s from %s' %(path, last_hour))
                activeUsers = UserSessionFE.gql("WHERE active = True and path = :1  and last_updatetime > :2", path, last_hour).fetch(1000)
		logging.info('getting all active user channels for path %s' % path)
		for user in activeUsers:
			logging.info('sending message to: %s' %user.user_uuid)
			messager = UserMessager(user.user_uuid)
			try:
				messager.send(message)
			except:
				e0,e = sys.exc_info()[0], sys.exc_info()[1]
				logging.info('message was not send due to %s , %s' %(e0, e)) 
				
class ChannelHandler(webapp.RequestHandler):
	def post(self):
		last_hour = datetime.datetime.now() - datetime.timedelta(hours = 1)
		inActiveUsers = UserSessionFE.gql("WHERE active = True and last_updatetime < :1", last_hour)
		for i in inActiveUsers:
			logging.info('Deactivating channel:  %s' % (i.user_uuid))
			i.active = False
			i.put()

		

class MainHandler(webapp.RequestHandler):
	def post(self):

		ud, args = RequestUtils.parse_request(self.request.body)

		logging.info('Received args:%s' % args)
                client = RequestUtils.getClient(args)
		user=RequestUtils.getUser(ud,args)
		url=RequestUtils.getUrl(args)
		domain=RequestUtils.getDomain(url)
                title = RequestUtils.getTitle(args, client)
                version = RequestUtils.getVersion(args)
                selection = RequestUtils.getSelection(args)
		share_mode = RequestUtils.getShareMode(args)

                if not RequestUtils.checkUrl(url):
                        logging.info('skipping since url is not good!')
			self.response.out.write('{"message":"Bad url"}')
                        return
                user_agent = self.request.headers['User-agent']
                if user is None or len(user) == 0:
                        logging.info('skipping since user is not defined ( client %s )' % client )
			from google.appengine.api import mail
			if ENVIRONMENT == 'http://www.instaright.com':
	                        mail.send_mail(sender='gbabun@gmail.com', to='bojan@instaright.com', subject='Bad request!', html='Request: args = %s <br> ud: %s' %( args, ud), body='Request: args = %s <br> ud: %s' %( args, ud))
			self.response.out.write('{"message":"User not defined"}')
                        return
                logging.info('request has been made from valid user %s' % user)
                try:
			taskqueue.add(queue_name='link-queue', url='/article/task', params={'user': user, 'url': url, 'domain': domain, 'title': title, 'version': version,'client': client, 'selection': selection, 'user_agent': user_agent, 'share_mode': share_mode})
                except TransientError:
			taskqueue.add(queue_name='link-queue', url='/article/task', params={'user': user, 'url': url, 'domain': domain, 'title': title, 'version': version,'client': client, 'selection': selection, 'user_agent': user_agent, 'share_mode': share_mode})

		if client == 'bookmarklet':
		        logging.info('bookmarklet specific response')
			self.response.out.write('{"close_html":"Link successfully marked"}')
			return
                cachedBadge = memcache.get('badge_'+user)
                logging.info('looking for badge %s' % 'badge_'+user)
                if cachedBadge is not None:
                        logging.info('response badge %s' %cachedBadge)
                        self.response.out.write(cachedBadge)
                else:
                        logging.info('no badge found, using default')
                        self.response.out.write('')
		
	def get(self):
		return self.response.out.write('<script language="javascript">top.location.href="/"</script>')

class MainTaskHandler(webapp.RequestHandler):
        def post(self):
		user=self.request.get('user',None)
		user=urllib.unquote(user)
		url=self.request.get('url',None)
		domain=self.request.get('domain',None)
                title=self.request.get('title',None)
                share_mode=self.request.get('share_mode',None)
                if not RequestUtils.checkUrl(url):
                    logging.info('skipping since url is not good!')
                    return
                lu = LinkUtils()
                link_info = lu.getLinkInfo(url)
                description = link_info["d"]
                embeded = link_info["e"]
                logging.info('got post title %s' % title)
                title_new = link_info["t"]
		if title is None and title_new is not None and len(title_new) > 0:
			title = title_new
                if title is None or title == 'None' or title == 'null':
                        title=LinkUtils.getLinkTitle(url)
                if title is not None:
                        title = title[:199]
                logging.info('final link title %s' %title)
                logging.info("link info desc: %s embede: %s" %( description, embeded))
                version=self.request.get('version',None)
                client=self.request.get('client',None)
                selection = self.request.get('selection', None)
                user_agent = self.request.get('user_agent',None)

                UserScoreUtility.updateLinkScore(user,url)
                UserScoreUtility.updateDomainScore(user, domain)

                taskqueue.add(url='/user/badge/task', queue_name='badge-queue', params={'url':url, 'domain':domain, 'user':user, 'version': version, 'client': client})
                taskqueue.add(url='/link/traction/task', queue_name='link-queue', params={'url':url, 'user': user, 'title': title})
                taskqueue.add(url='/link/recommendation/task', queue_name='default', params={'url':url })

                name = "url"
                generic_counter.increment(name)
                url_cnt = generic_counter.get_count(name)
                logging.info("total url count %s " % url_cnt)
                e = EncodeUtils()
                enbased=e.encode(url_cnt)
                url_encode26 = e.enbase(enbased)
                logging.info("url encode: %s and enbase : %s" % (enbased, url_encode26))
		url_hash = LinkUtils.getUrlHash(url)
		today = datetime.datetime.now().date()
		model = SessionModel.gql('WHERE instaright_account = :1 and url_hash = :2 and date > :3', user, url_hash, today).get()
                new_entity=False
		if model is None:
			logging.info('did not find save dafined by: %s %s for date %s', user, url, str(today))
			model = SessionModel()
                        new_entity=True
		else:
			logging.info('existing url(key %s) updating certain params' %str(model.key()))
                logging.info('link: %s title: %s' %(url, title))
		try:
                        #remove for local testing
                	model.ip = self.request.remote_addr
                	model.instaright_account = user
                	model.date = datetime.datetime.now()
                        if new_entity == True:
                	        model.url = url
                                model.url_hash = url_hash
                                model.url_counter_id = url_cnt
                                model.url_encode26 = url_encode26
                	model.title = title
                        model.user_agent=user_agent
                	model.domain = domain
                	model.short_link = None
                	model.feed_link = None
                	model.version = version
                        model.client = client
                        model.selection = selection 
                        model.embeded = embeded
			while True:
				timeout_ms= 100
				try:
					model.put()
					break
				except datastore_errors.Timeout:
					logging.info('model save timeout retrying in %s' % timeout_ms)
					time.sleep(timeout_ms)
					timeout_ms *= 2
                        logging.info('send link : url_hash %s title %s user_id %s updated %s client: %s' %(model.url_hash, model.title, str(model.key()), str(model.date), model.client))
		except BadValueError, apiproxy_errors.DeadlineExceededError:
		        e0, e1 = sys.exc_info()[0], sys.exc_info()[1]
			logging.error('error while saving url %s ( %s, %s)' % (url, e0, e1))


                try:
                        taskqueue.add(queue_name='message-broadcast-queue', url='/link/category', params={'url': url })
                except TransientError:
                        taskqueue.add(queue_name='message-broadcast-queue', url='/link/category', params={'url': url })

                # xmpp and main stream update
		subscribers = Subscription.gql('WHERE active = True and mute = False').fetch(100)
                #known category
                category = LinkUtils.getLinkCategory(model)
                ud=UserDetails.gql('WHERE instaright_account = :1', user).get()
                if ud is not None and model.key() is not None and share_mode in ['1']:
                        taskqueue.add(url='/service/submit', params={'user_details_key': str(ud.key()), 'session_key': str(model.key())})
                taskqueue.add(queue_name='message-broadcast-queue', url= '/message/broadcast/task', params={'user_id':str(model.key()), 'title':model.title, 'link':model.url, 'domain':model.domain, 'updated': int(time.mktime(model.date.timetuple())), 'link_category': category, 'e': embeded, 'subscribers': simplejson.dumps(subscribers, default=lambda s: {'a':s.subscriber.address, 'd':s.domain})})

                
class ErrorHandling(webapp.RequestHandler):
	def post(self):
                try:
        		args=simplejson.loads(self.request.body)
        		error=args[0]
        		logging.error('Error caught within extension:' %error)
        		return self.response.out.write(1)
                except:
                        e,e0 = sys.exc_info()[0], sys.exc_info()[1]
                        logging.error('weird:ERROR while hadling ERROR for %s: ' % self.request.body)

class IndexHandler(GenericWebHandler):
	def get(self):
                crawler = self.request.get('_escaped_fragment_', None)
                redirect = self.request.get('redirect', None)
                show_login= self.request.get('show_login', None)
                if crawler is not None:
                        self.html_snapshot()
                        return
                logging.info('got redirect %s' % redirect)
                #redirect from appengine domain
                self.redirect_perm()
                self.get_user()

		userMessager = UserMessager(str(self.user_uuid))
		channel_id = userMessager.create_channel()
		login_url = users.create_login_url('/')	
                if self.avatar is None:
                        self.avatar='/static/images/noavatar.png'
                template_variables = {'user':self.screen_name, 'login_url':login_url, 'logout_url':'/account/logout', 'channel_id':channel_id, 'hotlinks': None,'avatar':self.avatar, 'page_footer': PageUtils.get_footer(),'show_login': show_login}
		path= os.path.join(os.path.dirname(__file__), 'templates/index.html')
                self.response.headers["Content-Type"] = "text/html; charset=utf-8"
		self.response.out.write(template.render(path,template_variables))

class YahooVerificationFile(webapp.RequestHandler):
        def get(self):
                self.response.out.write('1')

class PrivacyPolicyHandler(webapp.RequestHandler):
        def get(self):
                template_variables = {'page_footer': PageUtils.get_footer() }
		path= os.path.join(os.path.dirname(__file__), 'templates/privacy_policy.html')
                self.response.headers["Content-Type"] = "text/html; charset=utf-8"
		self.response.out.write(template.render(path,template_variables))


class ToolsHandler(GenericWebHandler):
        def get(self):
                self.redirect_perm()
                self.get_user()
                logging.info('screen_name %s' %self.screen_name)
                if self.avatar is None:
                        self.avatar='/static/images/noavatar.png'
		template_variables = []
                template_variables = {'page_footer':PageUtils.get_footer(), 'user':self.screen_name, 'logout_url':'/account/logout', 'avatar':self.avatar, 'env': ENVIRONMENT}
		path= os.path.join(os.path.dirname(__file__), 'templates/tools.html')
                self.response.headers["Content-Type"]= "text/html"
		self.response.out.write(template.render(path,template_variables))
                
		
application = webapp.WSGIApplication(
                                     [
					('/rpc', MainHandler),
					('/article/task', MainTaskHandler),
                                     	('/error', ErrorHandling),
                                     	('/deactivate_channels', ChannelHandler),
                                     	('/privacy_policy.html', PrivacyPolicyHandler),
                                     	('/0Ci1tA9HYDgTPNzJLQ.ytA--.html', YahooVerificationFile),
                                     	('/tools', ToolsHandler),
                                     	('/', IndexHandler),
				     ],
                                     debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()


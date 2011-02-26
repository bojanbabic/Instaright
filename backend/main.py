import sys, os, urllib2, datetime, logging, cgi, uuid
import pubsubhubbub_publish as pshb

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.api import channel 
from google.appengine.api.labs import taskqueue
from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.ext.webapp.util import run_wsgi_app
from django.utils import simplejson
from utils import StatsUtil

from models import UserSessionFE, SessionModel, Links

class UserMessager:
	def __init__(self, user_uid):
		self.user_uuid = user_uid
	def create_channel(self):
		return channel.create_channel(self.user_uuid)
	def send(self, message):
		channel.send_message(self.user_uuid, simplejson.dumps(message))

class BroadcastMessage:
	def send_message(self, message):
		last_hour = datetime.datetime.now() - datetime.timedelta(hours = 1)
                taskqueue.add(queue_name='deactivate-channels', url='/deactivate_channels')
		activeUsers = UserSessionFE.gql("WHERE active = True and last_updatetime > :1", last_hour)
		logging.info('getting all active user channels')
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
		try:
			args=simplejson.loads(self.request.body)
                       
                        logging.info('Received args:%s' % args)

                        if not StatsUtil.checkUrl(args):
                                logging.info('skipping since url is not good!')
                                return
                        try:
                                taskqueue.add(queue_name='article-queue', url='/article/task', params={'args': self.request.body})
                        except TransientError:
                                taskqueue.add(queue_name='article-queue', url='/article/task', params={'args': self.request.body})

			logging.info('triggering feed update')

                        user = StatsUtil.getUser(args)

                        cachedBadge = memcache.get('badge_'+user)
                        logging.info('looking for badge %s' % 'badge_'+user)
                        if cachedBadge is not None:
                                logging.info('response badge %s' %cachedBadge)
                                self.response.out.write(cachedBadge)
                        else:
                                logging.info('no badge found, using default')
                                self.response.out.write('')
		except:
			e0,e = sys.exc_info()[0],  sys.exc_info()[1]
			logging.error('Error while handling request %s %s' % (e0, e))
		
	def get(self):
		return self.response.out.write('<script language="javascript">top.location.href="/"</script>')

class MainTaskHandler(webapp.RequestHandler):
        def post(self):
                args = simplejson.loads(self.request.get('args', None))
                logging.info(args)
                if args is None:
                        logging.info('missing arg from user rpc body')
                        return

		user=StatsUtil.getUser(args)
		url=StatsUtil.getUrl(args)
		domain=StatsUtil.getDomain(url)
                title = StatsUtil.getTitle(args)
                version = StatsUtil.getVersion(args)

                model = SessionModel()
                model.user_agent = self.request.headers['User-agent']
                model.ip = self.request.remote_addr
                model.instaright_account = user
                model.date = datetime.datetime.now()
                model.url = url
                model.domain = domain
                model.short_link = None
                model.feed_link = None
                model.title = title
                model.version = version

		model.put()
                logging.info('model: %s' % model.to_xml())

                taskqueue.add(url='/user/badge/task', queue_name='badge-queue', params={'url':url, 'domain':domain, 'user':user, 'version': version})

                logging.info('pubsubhubbub feed update')
		try:
		        pshb.publish('http://pubsubhubbub.appspot.com', 'http://instaright.appspot.com/feed')
		except:
		        e0, e = sys.exc_info()[0], sys.exc_info()[1]
                        logging.info('(handled):Error while triggering pshb update: %s %s' % (e0, e))
                
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

class IndexHandler(webapp.RequestHandler):
	def get(self):
		user = users.get_current_user()
		uuid_cookie = self.request.cookies.get('user_uuid')
		if uuid_cookie:
			#Connect uuid with registered user
			logging.info('reusing uuid: %s' % uuid_cookie)
			user_uuid = uuid_cookie
			userSession = UserSessionFE.gql('WHERE user_uuid = :1' , user_uuid).get()
			userSession.user = user
			userSession.put()
		else:
			user_uuid = uuid.uuid4()
			logging.info('generated uuid: %s' % user_uuid)
                        expires = datetime.datetime.now() + datetime.timedelta(minutes=5)
                        exp_format = datetime.datetime.strftime(expires, '%a, %d-%b-%Y %H:%M:%S GMT')
                        logging.info('expr date %s' %exp_format)

			self.response.headers.add_header('Set-Cookie', 'user_uuid=%s; expires=%s; path=/' %( user_uuid, exp_format))
			userSession = UserSessionFE()
			userSession.user = user
			userSession.user_uuid = str(user_uuid)
			userSession.active=True
			userSession.put()
		userMessager = UserMessager(str(user_uuid))
		channel_id = userMessager.create_channel()
		login_url = users.create_login_url('/')	
		template_variables = []
                template_variables = {'user':user, 'login_url':login_url, 'channel_id':channel_id, 'hotlinks': None}
		path= os.path.join(os.path.dirname(__file__), 'index.html')
                self.response.headers["Content-Type"] = "text/html; charset=utf-8"
		self.response.out.write(template.render(path,template_variables))

class YahooVerificationFile(webapp.RequestHandler):
        def get(self):
                self.response.out.write('1')

class PrivacyPolicyHandler(webapp.RequestHandler):
        def get(self):
		template_variables = []
		path= os.path.join(os.path.dirname(__file__), 'templates/privacy_policy.html')
                self.response.headers["Content-Type"] = "text/html; charset=utf-8"
		self.response.out.write(template.render(path,template_variables))
                
                
		
application = webapp.WSGIApplication(
                                     [('/rpc', MainHandler),
                                     ('/article/task', MainTaskHandler),
                                     ('/error', ErrorHandling),
                                     ('/deactivate_channels', ChannelHandler),
                                     ('/privacy_policy.html', PrivacyPolicyHandler),
                                     ('/0Ci1tA9HYDgTPNzJLQ.ytA--.html', YahooVerificationFile),
                                     ('/', IndexHandler),
				     ],
                                     debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()


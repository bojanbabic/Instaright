import sys, os, urllib2, datetime, logging, cgi, uuid
import pubsubhubbub_publish as pshb

from utils import StatsUtil,LoginUtil

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api.labs import taskqueue
from google.appengine.api import memcache, channel, users, datastore_errors
from google.appengine.ext import db
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.db import BadValueError
from google.appengine.runtime import apiproxy_errors

from models import UserSessionFE, SessionModel, Links, UserDetails
from generic_handler import GenericWebHandler

sys.path.append(os.path.join(os.path.dirname(__file__),'lib'))
import simplejson

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
                client = StatsUtil.getClient(args)

		try:
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
                        model.client = client
			while True:
				timeout_ms= 100
				try:
					model.put()
					break
				except datastore_errors.Timeout:
					logging.info('model save timeout retrying in %s' % timeout_ms)
					thread.sleep(timeout_ms)
					timeout_ms *= 2
                	logging.info('model saved: %s %s' % (model.to_xml() , model.client))
		except BadValueError, apiproxy_errors.DeadlineExceededError:
			logging.info('error while saving url %s' % url)


                taskqueue.add(url='/link/category', queue_name='category-queue', params={'url':url })
                taskqueue.add(url='/user/badge/task', queue_name='badge-queue', params={'url':url, 'domain':domain, 'user':user, 'version': version})
                taskqueue.add(url='/link/traction/task', queue_name='link-queue', params={'url':url, 'user': user, 'title': title})

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

class IndexHandler(GenericWebHandler):
	def get(self):
                #redirect from appengine domain
                self.redirect_perm()
                self.get_user()

		userMessager = UserMessager(str(self.user_uuid))
		channel_id = userMessager.create_channel()
		login_url = users.create_login_url('/')	
                if avatar is None:
                        avatar='/static/images/noavatar.png'
		template_variables = []
                template_variables = {'user':screen_name, 'login_url':login_url, 'logout_url':'/account/logout', 'channel_id':channel_id, 'hotlinks': None,'avatar':avatar}
		path= os.path.join(os.path.dirname(__file__), 'templates/index.html')
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


class ToolsHandler(GenericWebHandler):
        def get(self):
                self.redirect_perm()
                self.get_user()
                logging.info('screen_name %s' %self.screen_name)
                if self.avatar is None:
                        self.avatar='/static/images/noavatar.png'
		template_variables = []
                template_variables = {'user':self.screen_name, 'logout_url':'/account/logout', 'avatar':self.avatar}
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


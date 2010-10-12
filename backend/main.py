import sys, os, urllib2, datetime, logging, cgi, uuid
import pubsubhubbub_publish as pshb

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.api import channel 
from google.appengine.api.labs import taskqueue
from google.appengine.ext import db
from google.appengine.ext.webapp.util import run_wsgi_app
from django.utils import simplejson
from utils import StatsUtil

from models import UserSessionFE

class SessionModel(db.Model):
	user_agent=db.StringProperty()
	instaright_account=db.StringProperty()
	ip=db.StringProperty()
	url=db.LinkProperty()
	date=db.DateTimeProperty()
	domain=db.StringProperty()
	def count_all(self):
		count = 0
		query = SessionModel.all().order('__key__')
		while count % 1000 == 0:
			current_count = query.count()
			count += current_count
			
			if current_count == 1000:
				last_key = query.fetch(1, 999)[0].key()
				query = query.filter('__key__ > ' , last_key)
		return count

	@staticmethod
	def countAll():
		data=SessionModel.gql('ORDER by __key__').fetch(1000)
		lastKey = data[-1].key()
		total=len(data)
		while len(data) == 1000:
			data=SessionModel.gql('WHERE __key__> :1 ORDER by __key__', lastKey).fetch(1000)
			lastKey=data[-1].key()
			total+=len(data)
		return total
	@staticmethod
	def getAll():
		data=SessionModel.gql('ORDER by __key__').fetch(1000)
		if not data:
			return None
		lastKey = data[-1].key()
		results=data
		while len(data) == 1000:
			data=SessionModel.gql('WHERE __key__> :1 ORDER by __key__', lastKey).fetch(1000)
			lastKey=data[-1].key()
			results.extend(data)
		return results
	@staticmethod
	def getDailyStats(targetDate):
		if targetDate is None:
			# take yesterday for targetDate
			targetDate=datetime.date.today() - datetime.timedelta(days=1)
		upperLimitDate = targetDate + datetime.timedelta(days=1)
		data = SessionModel.gql(' WHERE date >= :1 and date < :2 ', targetDate, upperLimitDate).fetch(5000)
		if not data:
			logging.info('no results returned for daily stats')
			return None
		result=[]
		result.extend(data)
		logging.info('daily stats retrieved %s ' % len(result))
		return result
	@staticmethod
	def getWeeklyStats(targetDate):
		if targetDate is None:
			targetDate=datetime.date.today() 
		previousWeek = targetDate - datetime.timedelta(days=7)
		logging.info('ranges %s -> %s ' %( targetDate, previousWeek))
		data = SessionModel.gql(' WHERE date <= :1 and date > :2 ORDER by date, __key__', targetDate, previousWeek).fetch(1000)
		if not data:
			logging.info('no records found for target date %s ' % str(targetDate))
			return None
		lastKey= data[-1].key()
		result = data
		while len(data) == 1000:
			nextK = SessionModel.gql(' WHERE __key__ > :1 ORDER by  __key__, date', lastKey).fetch(1000)
			lastKey=nextK[-1].key()
			#data = SessionModel.gql(' WHERE date <= :1 and date > :2 and __key__ > :3 order by date, __key__', targetDate, previousWeek, lastKey).fetch(1000)
			data = [ x for x in nextK if x.date <= targetDate and x.date > previousWeek ]
			result.extend(data)
		return result

	@staticmethod
	def getYearStats(targetDate):
		if targetDate is None:
			targetDate=datetime.date.today()
		lastYear = targetDate - datetime.timedelta(days=365)
		data = SessionModel.gql(' WHERE date <= :1 and date > :2 ORDER by date, __key__', targetDate, lastYear).fetch(1000)
		if not data:
			return None
		lastKey= data[-1].key()
		result = data
		while len(data) == 1000:
			#data=SessionModel.gql('WHERE date <= :1 and date > :2 and __key__ > :3 order by date, __key__ ', targetDate, lastYear, lastKey).fetch(1000)
			nextK = SessionModel.gql(' WHERE __key__ > :1 ORDER by  __key__, date', lastKey).fetch(1000)
			lastKey=nextK[-1].key()
			data = [ x for x in nextK if x.date <= targetDate and x.date > previousWeek ]
			lastKey=data[-1].key()
			result.extend(data)
		return result
		
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

		

class Logging(webapp.RequestHandler):
	def post(self):
		try:
			args=simplejson.loads(self.request.body)
			account=args[0]
			URL=urllib2.unquote(args[1])
			domain=StatsUtil.getDomain(URL)
			model=SessionModel(user_agent=self.request.headers['User-agent'], ip = self.request.remote_addr, instaright_account=account, date=datetime.datetime.now(), url=URL, domain=domain)
			model.put()
			logging.info('bookmark update written: % s' % model.to_xml())
			logging.info('triggering feed update')
			#trigger taskqueue that generates feed
			try:
				pshb.publish('http://pubsubhubbub.appspot.com', 'http://instaright.appspot.com/feed')
			except:
				e0, e = sys.exc_info()[0], sys.exc_info()[1]
                                logging.info('(handled):Error while triggering pshb update: %s %s' % (e0, e))
		except:
			e0,e = sys.exc_info()[0],  sys.exc_info()[1]
			logging.error('Error while handling request %s %s' % (e0, e))
		
	def get(self):
		URL=cgi.escape(self.request.get('url'))
		account=cgi.escape(self.request.get('username'))
		if URL is None:
			return
		self.response.out.write(URL)
		domain=StatsUtil.getDomain(URL)
		model=SessionModel(user_agent=self.request.headers['User-agent'], ip = self.request.remote_addr, instaright_account=account, date = datetime.datetime.now(), url=URL, domain=domain)
		model.put()
		return self.response.out.write(1)
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


class Redirect(webapp.RequestHandler):
	def get(self):
		url = 'http://bojanbabic.blogspot.com'
		return self.response.out.write('<script language="javascript">top.location.href="' + url + '"</script>')

class IndexHandlerVar1(webapp.RequestHandler):
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
			self.response.headers.add_header('Set-Cookie', 'uuid=%s' %user_uuid)
			userSession = UserSessionFE()
			userSession.user = user
			userSession.user_uuid = str(user_uuid)
			userSession.active=True
			userSession.put()
		userMessager = UserMessager(str(user_uuid))
		channel_id = userMessager.create_channel()
		login_url = users.create_login_url('/index_1.html')	
		template_variables = []
		template_variables = {'user':user, 'login_url':login_url, 'channel_id':channel_id}
		path= os.path.join(os.path.dirname(__file__), 'index_1.html')
		
		self.response.out.write(template.render(path,template_variables))

class IndexHandlerVar2(webapp.RequestHandler):
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
			self.response.headers.add_header('Set-Cookie', 'uuid=%s' %user_uuid)
			userSession = UserSessionFE()
			userSession.user = user
			userSession.user_uuid = str(user_uuid)
			userSession.active=True
			userSession.put()
		userMessager = UserMessager(str(user_uuid))
		channel_id = userMessager.create_channel()
		login_url = users.create_login_url('/index_2.html')	
		template_variables = []
		template_variables = {'user':user, 'login_url':login_url, 'channel_id':channel_id}
		path= os.path.join(os.path.dirname(__file__), 'index_2.html')
		
		self.response.out.write(template.render(path,template_variables))

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
			self.response.headers.add_header('Set-Cookie', 'uuid=%s' %user_uuid)
			userSession = UserSessionFE()
			userSession.user = user
			userSession.user_uuid = str(user_uuid)
			userSession.active=True
			userSession.put()
		userMessager = UserMessager(str(user_uuid))
		channel_id = userMessager.create_channel()
		login_url = users.create_login_url('/')	
		template_variables = []
		template_variables = {'user':user, 'login_url':login_url, 'channel_id':channel_id}
		path= os.path.join(os.path.dirname(__file__), 'index.html')
		
		self.response.out.write(template.render(path,template_variables))
		
class IndexHandlerV1(webapp.RequestHandler):
	def get(self):
		template_variables = []
		path= os.path.join(os.path.dirname(__file__), 'index1.html')
		self.response.out.write(template.render(path,template_variables))
		
application = webapp.WSGIApplication(
                                     [('/rpc', Logging),
                                     ('/error', ErrorHandling),
                                     ('/deactivate_channels', ChannelHandler),
                                     #('/', Redirect),
                                     ('/', IndexHandler),
                                     ('/index_1.html', IndexHandlerVar1),
                                     ('/index_2.html', IndexHandlerVar2),
                                     ('/v1', IndexHandlerV1),
				     ],
                                     debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()


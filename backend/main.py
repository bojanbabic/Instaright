import sys, os, urllib2, datetime, logging, cgi
import pubsubhubbub_publish as pshb

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext import db
from google.appengine.ext.webapp.util import run_wsgi_app
from django.utils import simplejson
from utils import StatsUtil

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
			pshb.publish('http://pubsubhubbub.appspot.com', 'http://instaright.appspot.com/feed')
		except:
			e0 = sys.exc_info()[0]
			e = sys.exc_info()[1]
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
		args=simplejson.loads(self.request.body)
		error=args[0]
		logging.error('Error caught within extension:'+error)
		return self.response.out.write(1)

class Redirect(webapp.RequestHandler):
	def get(self):
		url = 'http://bojanbabic.blogspot.com'
		return self.response.out.write('<script language="javascript">top.location.href="' + url + '"</script>')

class IndexHandler(webapp.RequestHandler):
	def get(self):
		template_variables = []
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
                                    # ('/', Redirect)
                                     ('/', IndexHandler),
                                     ('/v1', IndexHandlerV1),
				     ],
                                     debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()


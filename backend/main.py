import sys, os, urllib2, datetime, logging
#import multiprocessing

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp.util import run_wsgi_app
from django.utils import simplejson

class SessionModel(db.Model):
	user_agent=db.StringProperty()
	instaright_account=db.StringProperty()
	ip=db.StringProperty()
	url=db.LinkProperty()
	date=db.DateProperty(auto_now_add=True)
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
	def getDailyStats():
		today=datetime.date.today()
		yesterday=datetime.date.today() - datetime.timedelta(days=1)
		data = SessionModel.gql(' WHERE date = :1 ORDER by __key__', yesterday).fetch(1000)
		if not data:
			return None
		lastKey= data[-1].key()
		result = data
		while len(data) == 1000:
			data=SessionModel.gql('WHERE date = :1 __key__ > :2 order by __key__ ', yesterday, lastKey).fetch(1000)
			result.extend(data)
		return result	
	@staticmethod
	def getWeeklyStats():
		today=datetime.date.today()
		lastWeek=datetime.date.today() - datetime.timedelta(days=7)
		data = SessionModel.gql(' WHERE date <= :1 and date > :2 ORDER by date, __key__', today, lastWeek).fetch(1000)
		if not data:
			return None
		lastKey= data[-1].key()
		result = data
		while len(data) == 1000:
			data=SessionModel.gql('WHERE date <= :1 and date > :2 and __key__ > :3 order by date, __key__ ', today, lastWeek, lastKey).fetch(1000)
			result.extend(data)
		return result

	@staticmethod
	def getYearStats():
		today=datetime.date.today()
		lastYear=datetime.date.today() - datetime.timedelta(days=365)
		data = SessionModel.gql(' WHERE date <= :1 and date > :2 ORDER by date, __key__', today, lastYear).fetch(1000)
		if not data:
			return None
		lastKey= data[-1].key()
		result = data
		while len(data) == 1000:
			data=SessionModel.gql('WHERE date <= :1 and date > :2 and __key__ > :3 order by date, __key__ ', today, lastYear, lastKey).fetch(1000)
			result.extend(data)
		return result
		

class Logging(webapp.RequestHandler):
	def post(self):
		try:
			args=simplejson.loads(self.request.body)
			account=args[0]
			URL=urllib2.unquote(args[1])
			model=SessionModel(user_agent=self.request.headers['User-agent'], ip = self.request.remote_addr, instaright_account=account, url=URL)
			model.put()
			return self.response.out.write(1)
		except:
			e = sys.exc_info()[1]
			logging.error('Error while handling request %s' % e)
		
	def get(self):
		URL=cgi.escape(self.request.get('url'))
		account=cgi.escape(self.request.get('username'))
		self.response.out.write(URL)
		model=SessionModel(user_agent=self.request.headers['User-agent'], ip = self.request.remote_addr, instaright_account=account, url=URL)
		model.put()
		return self.response.out.write(1)
class ErrorHandling(webapp.RequestHandler):
	def post(self):
		args=simplejson.loads(self.request.body)
		error=args[0]
		logging.error('Error caught within extension:'+error)
		return self.response.out.write(1)
		
application = webapp.WSGIApplication(
                                     [('/rpc', Logging),
                                     ('/error', ErrorHandling)],
                                     debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()


import datetime
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.api.labs import taskqueue
from google.appengine.ext.webapp.util import run_wsgi_app
from main import SessionModel
from models import DailyDomainStats, WeeklyDomainStats
from google.appengine.ext.webapp import template

class SessionManager(webapp.RequestHandler):
	def get(self):
		dateStr=self.request.get('date', None)
		type=self.request.get('type', None)
		if dateStr is None or type is None:
			self.response.out.write('Get out of here!!')
			return 
		date = datetime.datetime.strptime(dateStr, '%Y-%m-%d').date()
		if date is None:
			self.response.out.write('Get out of here!!')
			return 
		if type == 'daily':
			results = db.GqlQuery('SELECT __key__ from DailyDomainStats WHERE date = :1', date).fetch(400)
		elif type == 'weekly':
			results = db.GqlQuery('SELECT __key__ from WeeklyDomainStats WHERE date = :1', date).fetch(400)
		else:
			self.response.out.write('Mode %s still to be implemented!' %s)
		if results is None or len(results) == 0:
			self.response.out.write('None stats for type %s and date %s' % ( type, date)) 
			return
		db.delete(results)
		self.response.out.write('Just deleted %s for date %s ( type=%s)' %( len(results), date, type))

class StatsTask(webapp.RequestHandler):
	def get(self):
		dateStr=self.request.get('date',None)
		type=self.request.get('type', None)
		if type is None:
			self.response.out.write('Get out of here!!')
			return 
		if dateStr is None:
			dateStr = str(datetime.date.today() - datetime.timedelta(days=1))
		taskqueue.add(url='/cron', params={'date':dateStr, 'type':type})
		
application = webapp.WSGIApplication(
                                     [('/delete_stats', SessionManager), ('/stats_task', StatsTask)],debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
	main()

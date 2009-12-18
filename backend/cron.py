import sys, os, time, datetime
import logging 
#import multiprocessing

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import mail
from main import SessionModel

class StatsModel(db.Model):
	totalNumber=db.IntegerProperty()
	totalDailyNumber=db.IntegerProperty()
	date=db.DateProperty(auto_now_add=True)

class CronTask(webapp.RequestHandler):
	def get(self):
		try:
			logging.info('Started crontask for %s' % datetime.date.today())
			yesterday=datetime.date.today() - datetime.timedelta(days=1)
			logging.info('yesterday: %s',yesterday)
			todayData=SessionModel.gql('WHERE date = :1', yesterday)
			#todayData=SessionModel.gql('WHERE date = :1', datetime.date.today())
			allData=SessionModel.all()
			logging.info('Gathered all data : %d' % allData.count())
			logging.info('Gathered yesterday data : %d' % todayData.count())
			stats=StatsModel()
			stats.totalNumber=allData.count()
			stats.totalDailyNumber=todayData.count()
			#stats.date=datetime.date.today()
			stats.put()
		except:
			e = sys.exc_info()[1]
			logging.error('Error while running crontask.Error: %s' % e)
	def getAll(self):
		try:
			allData=SessionModel.all()
			stats=StatsModel()
			stats.totalNumber=allData.count()
			stats.totalDailyNumber=allData.count()
			stats.put()
		except:
			e = sys.exc_info()[1]
			logging.error('Error while running getALl %s' %e)
	def countAll():
		firstK=SessionModel.fetch()
		total=firstK.count()
		if total < 1000:
			return total
		else:
			iteration = 1
			nextK=SessionModel.fetch(1000, (iteration++)*1000 -1)
			nextKcount=nextK.count()
			while 	nextKcount % 1000 == 0:
				total+=1000
				nextKcount=SessionModel.fetch(1000, (iteration++)*1000 -1).count()
			total+=nextKcount
			return total
				
			
			
		
application = webapp.WSGIApplication(
                                     [('/cron', CronTask)],debug=True)
                                     

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()


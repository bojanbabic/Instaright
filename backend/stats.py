import sys, os, time, datetime, cgi, logging, gviz_api
#import multiprocessing

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import mail
from google.appengine.runtime import DeadlineExceededError
from urlparse import urlparse
from main import SessionModel
from cron import StatsModel, DailyDomainStats, WeeklyDomainStats, YearDomainStats
from google.appengine.ext.webapp import template

class VisualStats(webapp.RequestHandler):
	def get(self):
		#dailyStats = self.latestDailyStats()
		dailyStats = [ '2010-01-14', '2010-01-13','2010-01-12' ]
		weeklyStats = [ '2010-02-16','2010-02-02','2010-01-26', '2010-01-19', '2010-01-12', '2010-01-05','2009-12-29' ]
		#weeklyStats = self.latestWeeklyStats()
		template_variables={'dailyStats':dailyStats, 'weeklyStats':weeklyStats}
		logging.info('generating visual stats')
		path= os.path.join(os.path.dirname(__file__), 'templates/stats.html')
		self.response.out.write(template.render(path,template_variables))
	def latestDailyStats(self):
		allDailyStats = DailyDomainStats.getAll()
		allDailyStatsDates = [ s.date for d in allDailyStats if s.date is not None ]
		uniqDates = set(alldailyStatsDates)
		maxDates = len(uniqDates) 
		if maxDates > 7:
			maxDates = 7
		top7Dates = set(uniqDates)[1:maxDates]
	def latestWeeklyStats(self):
		allWeeklyStats = WeeklyDomainStats.getAll()
		allWeeklyStatsDates = [ s.date for d in allWeeklyStats if s.date is not None ]
		uniqDates = set(allWeeklyStatsDates)
		maxDates = len(uniqDates) 
		if maxDates > 7:
			maxDates = 7
		top7Dates = set(uniqDates)[1:maxDates]

application = webapp.WSGIApplication(
                                     [('/stats', VisualStats)],
					debug=True)
                                     

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()

